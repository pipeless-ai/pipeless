use uuid;
use tokio;
use tokio::sync::RwLock;
use std::sync::Arc;
use log::{info, error, warn};

use crate as pipeless;

#[derive(Debug)]
pub struct PipelineError {
    msg: String
}
impl std::error::Error for PipelineError {}
impl std::fmt::Display for PipelineError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.msg.to_string())
    }
}
impl From<pipeless::input::pipeline::InputPipelineError> for PipelineError {
    fn from(error: pipeless::input::pipeline::InputPipelineError) -> Self {
        Self {
            msg: error.to_string(),
        }
    }
}
impl From<pipeless::output::pipeline::OutputPipelineError> for PipelineError {
    fn from(error: pipeless::output::pipeline::OutputPipelineError) -> Self {
        Self {
            msg: error.to_string(),
        }
    }
}

/// A Pipeless pipeline is an association of an input pipeline and an
/// output pipeline, plus the stages the frames must pass through
/// The input and output pipelines are handled via independent Gstreamer pipelines
/// We do it on this way for simplicty, because our gst pipelines are open.
/// Also, the input and output pipelines will always run on the same node
/// avoiding inconsistences when a node fails in a cloud setup.
struct Pipeline {
    id: uuid::Uuid,
    _input_stream_def: pipeless::input::pipeline::StreamDef,
    output_stream_def: Option<pipeless::output::pipeline::StreamDef>,
    input_pipeline: pipeless::input::pipeline::Pipeline,
    output_pipeline: Option<pipeless::output::pipeline::Pipeline>,
    frames_path: pipeless::stages::path::FramePath,
}
impl Pipeline {
    fn new(
        pipeless_bus_sender: &tokio::sync::mpsc::UnboundedSender<pipeless::events::Event>,
        input_uri: String,
        output_uri: Option<String>,
        frames_path: pipeless::stages::path::FramePath,
    ) -> Result<Self, PipelineError> {
        let pipeline_id = uuid::Uuid::new_v4();
        let input_stream_def =
            pipeless::input::pipeline::StreamDef::new(input_uri.clone())?;
        let input_pipeline = pipeless::input::pipeline::Pipeline::new(
            pipeline_id,
            input_stream_def.clone(),
            pipeless_bus_sender,
        )?;

        let mut output_stream_def = None;
        if let Some(uri) = output_uri {
            output_stream_def = Some(pipeless::output::pipeline::StreamDef::new(uri)?);
        }

        Ok(Pipeline {
            id: pipeline_id,
            _input_stream_def: input_stream_def,
            output_stream_def,
            input_pipeline,
            // The output pipeline can't be created until we have the input caps
            output_pipeline: None,
            frames_path,
        })
    }

    /// The output stream of a pipeline is created once we got the input capabilities
    /// because the output replicates the input capabilitites by default.
    pub fn create_and_start_output_pipeline(
        &mut self,
        input_caps: String,
        pipeless_bus_sender: &tokio::sync::mpsc::UnboundedSender<pipeless::events::Event>,
    ) -> Result<(), pipeless::output::pipeline::OutputPipelineError> {
        if let Some(stream_def) = &self.output_stream_def {
            // TODO: build streamdefs within pipelines and pass the uri only
            let output_pipeline =
                pipeless::output::pipeline::Pipeline::new(
                    self.id,
                    stream_def.clone(),
                    &input_caps,
                    pipeless_bus_sender
                )?;
            self.output_pipeline = Some(output_pipeline);
        }

        Ok(())
    }

    /// Close only stops the gst pipelines. It does not send EOS.
    pub fn close(&self) {
        if let Err(err) = self.input_pipeline.close() {
            warn!(
                "Error closing input stream. Pipeline id: {}. Error: {}",
                self.id, err.to_string()
            );
        }

        if let Some(out_pipe) = &self.output_pipeline {
            if let Err(err) = out_pipe.close() {
                warn!(
                    "Error closing output stream. Pipeline id: {}. Error: {}",
                    self.id, err.to_string()
                );
            }
        }
    }

    pub fn get_frames_path(&self) -> pipeless::stages::path::FramePath {
        self.frames_path.clone()
    }
}

// TODO: the pipeline manager should distribute the workload
//       when using a cloud setup among all nodes registered
pub struct Manager {
    // The pipeine manager owns the pipeline that will be used
    // in the manager thread
    pipeline: Arc<RwLock<pipeless::pipeline::Pipeline>>,
    // TODO: we could change this by a callback and avoid using references to the dispatcher here
    dispatcher_sender: tokio::sync::mpsc::UnboundedSender<pipeless::dispatcher::DispatcherEvent>,
}
impl Manager {
    pub fn new(
        input_video_uri: String,
        output_video_uri: Option<String>,
        frames_path: pipeless::stages::path::FramePath,
        // The bus needs to be created before the pipeline
        pipeless_bus_sender: &tokio::sync::mpsc::UnboundedSender<pipeless::events::Event>,
        dispatcher_sender: tokio::sync::mpsc::UnboundedSender<pipeless::dispatcher::DispatcherEvent>,
    ) -> Result<Self, PipelineError> {
        let pipeline = Arc::new(RwLock::new(pipeless::pipeline::Pipeline::new(
            &pipeless_bus_sender,
            input_video_uri,
            output_video_uri,
            frames_path,
        )?));

        Ok(Self { pipeline, dispatcher_sender })
    }

    // Start takes ownership of self because we have to access the bus,
    // which cannot be copied nor cloned due to having a receiver field,
    // that does not implement Copy nor Clone traits.
    pub fn start(
        &self,
        event_bus: pipeless::events::Bus,
        frame_path_executor_arc: Arc<RwLock<pipeless::stages::path::FramePathExecutor>>
    ) {
        let rw_pipeline = self.pipeline.clone();
        let dispatcher_sender = self.dispatcher_sender.clone();
        let frame_path_executor_arc = frame_path_executor_arc.clone();
        // Leave the pipeline manager running as a tokio task
        tokio::spawn(async move {
            // Process events on the pipeline concurrently. So frames are processed even
            // before the previous one has finished its processing.
            // The for_each_concurrent will end once the event bus receiver is closed.
            let rw_pipeline = rw_pipeline.clone();
            let dispatcher_sender = dispatcher_sender.clone();
            let pipeless_bus_sender = event_bus.get_sender();
            let concurrent_limit = num_cpus::get() * 2; // NOTE: Making benchmarks we found this is a good value
            let frame_path_executor_arc = frame_path_executor_arc.clone();
            event_bus.process_events(concurrent_limit,
                move |event, end_signal| {
                    let rw_pipeline = rw_pipeline.clone();
                    let dispatcher_sender = dispatcher_sender.clone();
                    let pipeless_bus_sender = pipeless_bus_sender.clone();
                    let frame_path_executor_arc = frame_path_executor_arc.clone();
                    async move {
                        match event {
                            pipeless::events::Event::FrameChangeEvent(e) => {
                                let frame = e.into_frame();
                                let frame_path;
                                {
                                    let read_guard = rw_pipeline.read().await;
                                    frame_path = read_guard.get_frames_path();
                                }
                                let out_frame_opt;
                                {
                                    let frame_path_executor = frame_path_executor_arc.read().await;
                                    out_frame_opt = frame_path_executor.execute_path(frame, frame_path).await;
                                }

                                if let Some(out_frame) = out_frame_opt {
                                    let read_guard = rw_pipeline.read().await;
                                    match &read_guard.output_pipeline {
                                        Some(pipe) => {
                                            if let Err(err) = pipe.on_new_frame(out_frame, &pipeless_bus_sender) {
                                                error!("{}", err);
                                            }
                                        }
                                        None => {}
                                    }
                                } else {
                                    warn!("No frame returned from path execution, skipping frame forwarding to the output (if any).");
                                }
                            }
                            pipeless::events::Event::NewInputCapsEvent(e) => {
                                let caps = e.get_caps();
                                info!("New input caps. Creating output pipeline for caps: {}", caps);

                                let mut write_guard = rw_pipeline.write().await;
                                if let Err(err) = write_guard.create_and_start_output_pipeline(
                                    caps.to_string(),
                                    &pipeless_bus_sender
                                ) {
                                    error!("Error creating output: {}. The stream will be processed without the output", err);
                                };
                            }
                            pipeless::events::Event::TagsChangeEvent(e) => {
                                let tags = e.get_tags();
                                info!("Tags updated to: {}", tags);

                                let mut write_guard = rw_pipeline.write().await;
                                match &write_guard.output_pipeline {
                                    Some(pipe) => pipe.on_new_tags(tags.clone()),
                                    None => {
                                        if let Some(out_stream_def) = &mut write_guard.output_stream_def {
                                            out_stream_def.set_initial_tags(tags.clone());
                                        }
                                    }
                                }
                            }
                            pipeless::events::Event::EndOfInputStreamEvent(_e) => {
                                // TODO: we must take into account that when reading from files the input eos appears sooner than expected
                                //       meaning we could loose frames
                                {
                                    let write_guard = rw_pipeline.write().await;
                                    if let Some(out_pipe) = &write_guard.output_pipeline {
                                        info!("End of input stream reached. Pipeline id: {}", out_pipe.get_pipeline_id());
                                        if let Err(err) = out_pipe.on_eos() {
                                            error!("Error sending end of stream signal to output: {}", err);
                                        }
                                    } else {
                                        // When there is no output, stop the stream as fast as the input EOS is reached
                                        info!("End of stream reached for pipeline: {}", write_guard.input_pipeline.get_pipeline_id());
                                        if let Err(err) = dispatcher_sender
                                            .send(pipeless::dispatcher::DispatcherEvent::PipelineFinished(write_guard.input_pipeline.get_pipeline_id())) {
                                            warn!("Unable to send pipeline finished event to dispatcher. Error: {}", err);
                                        };

                                        // End the processing loop
                                        if let Err(err) = end_signal.send(()).await {
                                            error!("Error signaling stream event loop end: {}", err);
                                        }
                                    }
                                }
                            }
                            pipeless::events::Event::EndOfOutputStreamEvent(_e) => {
                                let pipeline_id;
                                {
                                    let read_guard = rw_pipeline.read().await;
                                    pipeline_id = read_guard.id;
                                }
                                info!("End of output stream reached for pipeline: {}", pipeline_id);

                                if let Err(err) = dispatcher_sender
                                    .send(pipeless::dispatcher::DispatcherEvent::PipelineFinished(pipeline_id)) {
                                    warn!("Unable to send pipeline finished event to dispatcher. Error: {}", err);
                                };

                                // End the processing loop
                                if let Err(err) = end_signal.send(()).await {
                                    error!("Error signaling stream event loop end: {}", err);
                                }
                            }
                            pipeless::events::Event::InputStreamErrorEvent(e) => {
                                let pipeline_id;
                                {
                                    let read_guard = rw_pipeline.read().await;
                                    pipeline_id = read_guard.id;
                                }
                                error!(
                                    "Stopping streams for pipeline: {} due to input stream error: {}",
                                    pipeline_id, e.get_msg()
                                );

                                if let Err(err) = dispatcher_sender
                                    .send(pipeless::dispatcher::DispatcherEvent::PipelineFinished(pipeline_id)) {
                                    warn!("Unable to send pipeline finished event to dispatcher. Error: {}", err);
                                };

                                // End the processing loop
                                if let Err(err) = end_signal.send(()).await {
                                    error!("Error signaling stream event loop end: {}", err)
                                };
                            }
                            pipeless::events::Event::OutputStreamErrorEvent(e) => {
                                let pipeline_id;
                                {
                                    let read_guard = rw_pipeline.read().await;
                                    pipeline_id = read_guard.id;
                                }
                                error!(
                                    "Stopping streams for pipeline: {} due to output stream error: {}",
                                    pipeline_id, e.get_msg()
                                );

                                if let Err(err) = dispatcher_sender
                                    .send(pipeless::dispatcher::DispatcherEvent::PipelineFinished(pipeline_id)) {
                                    warn!("Unable to send pipeline finished event to dispatcher. Error: {}", err);
                                }

                                // End the processing loop
                                if let Err(err) = end_signal.send(()).await {
                                    error!("Error signaling stream event loop end: {}", err)
                                };
                            }
                        }
                    }
                }
            ).await;
        });
    }

    // Calling stop in the manager does not notify send EOS to the gst pipelines, simply stops them.
    // Otherwise, it would produce several undesired EOS events.
    pub async fn stop(&self) -> uuid::Uuid {
        let read_guard = self.pipeline.read().await;
        let pipeline_id = read_guard.id;
        read_guard.close();
        pipeline_id
    }

    pub async fn get_pipeline_id(&self) -> uuid::Uuid {
        let read_guard = self.pipeline.read().await;
        let pipeline_id = read_guard.id;
        pipeline_id
    }
}
