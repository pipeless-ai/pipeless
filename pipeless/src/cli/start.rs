use pyo3;
use std::{env, sync::Arc};
use tokio::sync::RwLock;
use gstreamer as gst;
use glib;
use tokio;
use ctrlc;

use crate as pipeless;

pub fn start_pipeless_node(project_dir: &str, export_redis_events: bool, stream_buffer_size: usize) {
    ctrlc::set_handler(|| {
        println!("Exiting...");
        std::process::exit(0);
    }).expect("Error setting Ctrl+C handler");

    pipeless::setup_logger();
    pyo3::prepare_freethreaded_python(); // Setup Pyo3

    // Initialize GLib mainloop
    let main_context = glib::MainContext::default();
    let glib_main_loop = glib::MainLoop::new(Some(&main_context), false);

    // Initialize Gstreamer
    gst::init().expect("Unable to initialize gstreamer");

    let frame_path_executor = Arc::new(RwLock::new(pipeless::stages::path::FramePathExecutor::new(project_dir)));

    // Init Tokio runtime
    let tokio_rt = tokio::runtime::Runtime::new().expect("Unable to create Tokio runtime");
    tokio_rt.block_on(async {
        // Create event exporter when enabled
        let event_exporter =
        if export_redis_events {
            let redis_url = env::var("PIPELESS_REDIS_URL")
                .expect("Please export the PIPELESS_REDIS_URL environment variable in order to export events to Redis");
            let redis_channel = env::var("PIPELESS_REDIS_CHANNEL")
                .expect("Please export the PIPELESS_REDIS_CHANNEL environment variable in order to export events to Redis");
            pipeless::event_exporters::EventExporter::new_redis_exporter(&redis_url, &redis_channel).await
        } else {
            pipeless::event_exporters::EventExporter::new_none_exporter()
        };
        { // Context to lock the global event exporter in order to set it
            let mut e_exp = pipeless::event_exporters::EVENT_EXPORTER.lock().await;
            *e_exp = event_exporter;
        }

        let streams_table = Arc::new(RwLock::new(pipeless::config::streams::StreamsTable::new()));
        let dispatcher = pipeless::dispatcher::Dispatcher::new(streams_table.clone());
        let dispatcher_sender = dispatcher.get_sender().clone();
        pipeless::dispatcher::start(dispatcher, frame_path_executor, stream_buffer_size);

        // Use the REST adapter to manage streams
        let rest_adapter = pipeless::config::adapters::rest::RestAdapter::new(streams_table.clone());
        rest_adapter.start(dispatcher_sender);
    });

    glib_main_loop.run();
}
