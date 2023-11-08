use pyo3;
use std::sync::Arc;
use tokio::sync::RwLock;
use gstreamer as gst;
use glib;
use tokio;

use crate::{self as pipeless, dispatcher};

pub fn start_pipeless_node(stages_dir: &str) {
    pipeless::setup_logger();
    pyo3::prepare_freethreaded_python(); // Setup Pyo3

    // Initialize GLib mainloop
    let main_context = glib::MainContext::default();
    let glib_main_loop = glib::MainLoop::new(Some(&main_context), false);

    // Initialize Gstreamer
    gst::init().expect("Unable to initialize gstreamer");

    let frame_path_executor = Arc::new(RwLock::new(pipeless::stages::path::FramePathExecutor::new(stages_dir)));

    // Init Tokio runtime
    let tokio_rt = tokio::runtime::Runtime::new().expect("Unable to create Tokio runtime");
    tokio_rt.block_on(async {
        let streams_table = Arc::new(RwLock::new(pipeless::config::streams::StreamsTable::new()));
        let dispatcher = pipeless::dispatcher::Dispatcher::new(streams_table.clone());
        let dispatcher_sender = dispatcher.get_sender().clone();
        pipeless::dispatcher::start(dispatcher, frame_path_executor);

        // Use the REST adapter to manage streams
        let rest_adapter = pipeless::config::adapters::rest::RestAdapter::new(streams_table.clone());
        rest_adapter.start(dispatcher_sender);
    });

    glib_main_loop.run();
}