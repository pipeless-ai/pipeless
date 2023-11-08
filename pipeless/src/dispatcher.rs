use std::{collections::HashMap, sync::Arc};
use tokio::sync::RwLock;
use async_channel;
use log::{warn, error, info};
use tokio;

use crate as pipeless;

pub enum DispatcherEvent {
    TableChange, // Indicates a change on the config table. Adapters notify changes via this
    PipelineFinished(uuid::Uuid), // Indicates the pipeline with the provided id finished
}

/// The dispatcher is in charge of maintaining a pipeline running for
/// each entry of the streams config table.
/// It receives events that indicate it to check the table and reconcile.
/// These events come from config adapters when the user changes the table,
/// except for the PipelineFinish event, that arrives from the pipelines.
/// Note that several config adapters could be running at the same time.
// TODO: create ETCD config adapter for cloud setup. How do we avoid
//       several nodes to create pipelines for the same stream?
//       we should not use a local table in memory like for edge cases
//       but instead query the table from etcd.
pub struct Dispatcher {
    streams_table: Arc<RwLock<pipeless::config::streams::StreamsTable>>,
    sender: async_channel::Sender<DispatcherEvent>,
    receiver: async_channel::Receiver<DispatcherEvent>,
}
impl Dispatcher {
    pub fn new(streams_table: Arc<RwLock<pipeless::config::streams::StreamsTable>>) -> Self {
        let (sender, receiver) = async_channel::unbounded();
        Self { sender, receiver, streams_table }
    }

    pub fn get_receiver(&self) -> async_channel::Receiver<DispatcherEvent> {
        self.receiver.clone()
    }

    pub fn get_sender(&self) -> async_channel::Sender<DispatcherEvent> {
        self.sender.clone()
    }

    pub fn start(
        &mut self,
        frame_path_executor_arc: Arc<RwLock<pipeless::stages::path::FramePathExecutor>>
    ) {
        let mut running_managers: HashMap<uuid::Uuid, pipeless::pipeline::Manager> = HashMap::new();
        let streams_table = self.streams_table.clone();
        let sender = self.sender.clone();
        let receiver = self.receiver.clone();
        let frame_path_executor_arc = frame_path_executor_arc.clone();

        tokio::spawn(async move {
            // Process events forever in a blocking way,
            // allowing other tokio tasks to run when this is blocked
            // Note we process events in order here, not concurrent, to avoid issues.
            // The dispatcher won't usually have many events so not being concurrent
            // does not affect performance
            while let Some(event) = receiver.recv().await.ok() {
                match event {
                    DispatcherEvent::TableChange => {
                        // When an entry has changed (the URIs hash does not match the content) stop the pipeline and create a new one
                        let different_hash =
                            |x: &&pipeless::config::streams::StreamsTableEntry| x.get_stored_hash() != x.hash();
                        {
                            let streams_table_guard = streams_table.read().await;
                            let streams_table_copy = streams_table_guard.get_table();
                            let modified_entries: Vec<&pipeless::config::streams::StreamsTableEntry> =
                                streams_table_copy.iter().filter(different_hash).collect();
                            for entry in modified_entries {
                                if let Some(pipeline_id) = entry.get_pipeline() {
                                    if let Some(manager) = running_managers.get(&pipeline_id) {
                                        info!("Stopping pipeline due to stream config change. Pipeline id: {}", pipeline_id);
                                        manager.stop().await;
                                        // Handling PipelineFinish will remove the pipeline from the entry and
                                        // will emit a TableChange again, when we will find a stream without
                                        // a pipeline and create a new one.
                                        if let Err(err) =
                                            sender.send(DispatcherEvent::PipelineFinished(pipeline_id)).await {
                                            warn!("Unable to send dispatcher event for finished pipeline. Error: {}", err.to_string());
                                        }
                                    }
                                }
                            }
                        }

                        // When an entry does not have an associated pipeline, create one and assign it
                        let without_pipeline =
                            |x: &&pipeless::config::streams::StreamsTableEntry| x.get_pipeline().is_none();
                        {
                            let mut streams_table_guard = streams_table.write().await;
                            let streams_table_copy = streams_table_guard.get_table();
                            let entries_without_pipeline: Vec<&pipeless::config::streams::StreamsTableEntry> =
                                streams_table_copy.iter().filter(without_pipeline).collect();
                            for entry in entries_without_pipeline {
                                let dispatcher_event_sender = sender.clone();
                                let input_uri = entry.get_input_uri().to_string();
                                let output_uri = entry.get_output_uri().map(|s| s.to_string());
                                let frame_path_vec = entry.get_frame_path();
                                let frame_path_executor = frame_path_executor_arc.read().await;
                                let frame_path = pipeless::stages::path::FramePath::new(
                                    frame_path_vec.join("/").as_str(),
                                    &frame_path_executor
                                );
                                match frame_path {
                                    Ok(frame_path) => {
                                        info!("New stream entry detected, creating pipeline");
                                        let new_pipeless_bus = pipeless::events::Bus::new();
                                        let new_manager = pipeless::pipeline::Manager::new(
                                            input_uri, output_uri, frame_path,
                                            &new_pipeless_bus.get_sender(),
                                            dispatcher_event_sender.clone(),
                                        );
                                        new_manager.start(new_pipeless_bus, frame_path_executor_arc.clone());
                                        streams_table_guard.set_stream_pipeline(
                                            entry.get_id(),
                                            new_manager.get_pipeline_id().await
                                        ).expect("Error adding new stream to the streams config table");
                                        running_managers.insert(new_manager.get_pipeline_id().await, new_manager);
                                    },
                                    Err(err) => {
                                        warn!("Rolling back streams table configuration due to error. Error: {}", err);
                                        streams_table_guard.remove(entry.get_id())
                                            .expect("Error removing new stream from the streams config table");
                                    }
                                }
                            }
                        }

                        // When we have a running manager whose pipeline id is not in any entry, that means the entry was deleted, stop the manager
                        for manager_tuple in &running_managers {
                            let pipeline_id = manager_tuple.0;
                            let manager = manager_tuple.1;
                            let streams_table = streams_table.read().await;
                            if streams_table.find_by_pipeline_id(*pipeline_id).is_none() {
                                info!("Stream config entry removed. Stopping associated pipeline");
                                manager.stop().await;
                            }
                        }
                    }
                    DispatcherEvent::PipelineFinished(pipeline_id) => {
                        let mut stream_entry;
                        {
                            let table_read_guard = streams_table.read().await;
                            let stream_entry_option = table_read_guard.find_by_pipeline_id(pipeline_id);
                            if let Some(entry) = stream_entry_option {
                                stream_entry = entry.clone();
                            } else {
                                warn!("
                                    Unable to unassign from stream config table. Not found.
                                    Pipeline id: {}
                                ", pipeline_id);

                                return;
                            }
                        }

                        stream_entry.unassign_pipeline();

                        let using_input_file = stream_entry.get_input_uri().starts_with("file://");
                        let using_output_file = match stream_entry.get_output_uri() {
                            Some(uri) => uri.starts_with("file://"),
                            None => false
                        };
                        if using_input_file || using_output_file {
                            streams_table.write().await.remove(stream_entry.get_id());
                            warn!("
                                Stream processing finished. Not restarting since was using files.
                                Pipeline id: {}
                            ", pipeline_id);
                        }

                        // Create new event since we have modified the streams config table
                        if let Err(err) = sender.send(DispatcherEvent::TableChange).await {
                            warn!("Unable to send dispatcher event for streams table changed. Error: {}", err.to_string());
                        }
                    }
                }
            }
            // Event is only none in the while loop when there is an error
            error!("Stopping dispatcher. An error happened in the channel when trying to receive");
        });
    }
}