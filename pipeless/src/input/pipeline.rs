use log::{error, info, warn, debug};
use std;
use std::str::FromStr;
use gstreamer as gst;
use gst::prelude::*;
use gstreamer_app as gst_app;
use uuid;
use ndarray;

use crate as pipeless;

#[derive(Debug)]
pub struct PipelineError;
impl std::error::Error for PipelineError {}
impl std::fmt::Display for PipelineError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "An error ocurred with the input pipeline")
    }
}

/// Each Pipeline contains a single Stream (which could have audio + video + subtitles, etc)
/// This struct defines a Stream. You can think on it like a stream configuration
#[derive(Clone)]
pub struct StreamDef {
    video: pipeless::config::video::Video,
}
impl StreamDef {
    pub fn new(uri: String) -> Self {
        Self {
            video: pipeless::config::video::Video::new(uri)
        }
    }

    pub fn get_video(&self) -> &pipeless::config::video::Video {
        &self.video
    }
}

fn on_new_sample(
    pipeless_pipeline_id: uuid::Uuid,
    appsink: &gst_app::AppSink,
    pipeless_bus_sender: &tokio::sync::mpsc::UnboundedSender<pipeless::events::Event>,
) -> Result<gst::FlowSuccess, gst::FlowError> {
    let sample = appsink.pull_sample().map_err(|_err| {
        error!("Sample is None");
        gst::FlowError::Error
    })?;

    let buffer = sample.buffer().ok_or_else(|| {
        error!("The sample buffer is None");
        gst::FlowError::Error
    })?;

    let frame_input_instant = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
    let caps = sample.caps().ok_or_else(|| {
        error!("Unable to get sample capabilities");
        gst::FlowError::Error
    })?;
    let caps_structure = caps.structure(0).ok_or_else(|| {
        error!("Unable to get structure from capabilities");
        gst::FlowError::Error
    })?;
    let width = pipeless::gst::utils::i32_from_caps_structure(
        &caps_structure, "width"
    )? as usize; // We need to cast to usize for the ndarray dimension
    let height = pipeless::gst::utils::i32_from_caps_structure(
        &caps_structure, "height"
    )? as usize; // We need to cast to usize for the ndarray dimension
    let channels: usize = 3; // RGB
    let framerate_fraction = pipeless::gst::utils::fraction_from_caps_structure(
        &caps_structure, "framerate"
    )?;
    let fps = framerate_fraction.0 / framerate_fraction.1;
    let pts = buffer.pts().ok_or_else(|| {
        error!("Unable to get presentation timestamp");
        gst::FlowError::Error
    })?;
    let dts = match buffer.dts() {
        Some(d) => d,
        None => {
            debug!("Decoding timestamp not present on frame");
            gst::ClockTime::ZERO
        }
    };
    let duration = buffer.duration().ok_or_else(|| {
        error!("Unable to get duration");
        gst::FlowError::Error
    })?;
    let buffer_info = buffer.map_readable().or_else(|_| {
        error!("Unable to extract the info from the sample buffer.");
        Err(gst::FlowError::Error)
    })?;

    let ndframe = ndarray::Array3::from_shape_vec(
        (height, width, channels), buffer_info.to_vec()
    ).expect("Failed to create ndarray from buffer data");

    let frame = pipeless::data::Frame::new_rgb(
        ndframe, width, height,
        pts, dts, duration,
        fps as u8, frame_input_instant,
        pipeless_pipeline_id
    );
    // The event takes ownership of the frame
    pipeless::events::publish_new_frame_change_event_sync(
        pipeless_bus_sender, frame
    );

    Ok(gst::FlowSuccess::Ok)
}

fn on_pad_added (
    pad: &gst::Pad,
    _info: &mut gst::PadProbeInfo,
    pipeless_bus_sender: &tokio::sync::mpsc::UnboundedSender<pipeless::events::Event>,
 ) -> gst::PadProbeReturn {
    let caps = match pad.current_caps() {
        Some(c) => c,
        None => {
            warn!("Could not get caps from a new added pad");
            return gst::PadProbeReturn::Ok; // Leave the probe in place
        }
    };
    info!("Dynamic source pad {} caps: {}",
        pad.name().as_str(), caps.to_string());

    pipeless::events::publish_new_input_caps_event_sync(
        pipeless_bus_sender, caps.to_string()
    );

    // The probe is no more needed since we already got the caps
    return gst::PadProbeReturn::Remove;
}

fn create_input_bin(
    uri: &str,
    pipeless_bus_sender: &tokio::sync::mpsc::UnboundedSender<pipeless::events::Event>,
) -> gst::Bin {
    let bin = gst::Bin::new();
    if uri == "v4l2" { // Device webcam
        let v4l2src = pipeless::gst::utils::create_generic_component("v4l2src", "v4l2src");
        let videoconvert = pipeless::gst::utils::create_generic_component("videoconvert", "videoconvert");
        let videoscale = pipeless::gst::utils::create_generic_component("videoscale", "videoscale");

        // Webcam resolutions are not standard and we can't read the webcam caps,
        // force a hardcoded resolution so that we annouce a correct resolution to the output.
        let forced_size_str = "video/x-raw,width=1280,height=720";
        let forced_caps = gst::Caps::from_str(forced_size_str).expect("Unable to create caps from string");
        let capsfilter = gst::ElementFactory::make("capsfilter")
            .name("capsfilter")
            .property("caps", forced_caps)
            .build()
            .expect("Failed to create capsfilter");

        bin.add_many([&v4l2src, &videoconvert, &videoscale, &capsfilter])
            .expect("Unable to add elements to input bin");

        v4l2src.link(&videoconvert).expect("Error linking v4l2src to videoconvert");
        videoconvert.link(&videoscale).expect("Error linking videoconvert to videoscale");
        videoscale.link(&capsfilter).expect("Error linking videoscale to capsfilter");

        // Create ghostpad to be able to plug other components to the bin
        let capsfilter_src_pad = capsfilter.static_pad("src")
            .expect("Failed to create the pipeline. Unable to get capsfilter source pad.");
        let ghostpath_src = gst::GhostPad::with_target(&capsfilter_src_pad)
            .expect("Unable to create the ghost pad to link bin");
        bin.add_pad(&ghostpath_src).expect("Unable to add ghostpad to input bin");

        // v4l2src doesn't have caps property that we can handle. Notify the output about the new stream
        let forced_caps_str = format!("{},format=RGB,framerate=1/30", forced_size_str);

        pipeless::events::publish_new_input_caps_event_sync(
            pipeless_bus_sender, forced_caps_str
        );
    } else {
        // Use uridecodebin by default
        let uridecodebin = pipeless::gst::utils::create_generic_component("uridecodebin3", "source");
        let videoconvert = pipeless::gst::utils::create_generic_component("videoconvert", "videoconvert");
        bin.add_many([&uridecodebin, &videoconvert])
            .expect("Unable to add elements to the input bin");
        uridecodebin.set_property("uri", uri);

        // Uridecodebin uses dynamic linking (creates pads automatically for new detected streams)
        let videoconvert_sink_pad = videoconvert.static_pad("sink").expect("Unable to get videoconvert pad");
        let link_new_pad_fn = move |pad: &gst::Pad| {
            if !videoconvert_sink_pad.is_linked() {
                pad.link(&videoconvert_sink_pad)
                    .expect("Unable to link new pad to videoconvert sink pad");
            } else {
                warn!("Videoconvert pad already linked, skipping link.");
            }
        };

        uridecodebin.connect_pad_added({
            let pipeless_bus_sender = pipeless_bus_sender.clone();
            move |_elem, pad| {
                link_new_pad_fn(&pad);
                //// Connect an async handler to the pad to be notified when caps are set
                pad.add_probe(
                    gst::PadProbeType::EVENT_UPSTREAM,
                    {
                        let pipeless_bus_sender = pipeless_bus_sender.clone();
                        move |pad: &gst::Pad, info: &mut gst::PadProbeInfo| {
                            on_pad_added(pad, info, &pipeless_bus_sender)
                        }
                    }
                );
            }
        });

        // Create ghost pad to be able to plug other components
        let videoconvert_src_pad = match videoconvert.static_pad("src") {
            Some(pad) => pad,
            None => {
                panic!("Failed to create the pipeline. Unable to get videoconvert source pad.");
            }
        };
        let ghostpath_src = gst::GhostPad::with_target(&videoconvert_src_pad)
            .expect("Unable to create the ghost pad to link bin");
        bin.add_pad(&ghostpath_src).expect("Unable to add ghostpad to input bin");
    }

    bin
}

fn on_bus_message(
    msg: &gst::Message,
    pipeline_id: uuid::Uuid,
    pipeless_bus_sender: &tokio::sync::mpsc::UnboundedSender<pipeless::events::Event>,
) {
    match msg.view() {
        gst::MessageView::Eos(eos) => {
            let eos_src_name = match eos.src() {
                Some(src) => src.name(),
                None => "no_name".into()
            };

            info!("Received received EOS from source {}.
                Pipeline id: {} ended", eos_src_name, pipeline_id);

            pipeless::events::publish_input_eos_event_sync(pipeless_bus_sender);
        },
        gst::MessageView::Error(err) => {
            let err_msg = err.error().message().to_string();
            let debug_msg = match err.debug() {
                Some(m) => m.as_str().to_string(),
                None => "".to_string()
            };
            let err_src_name = match err.src() {
                Some(src) => src.name(),
                None => "no_name".into()
            };
            debug!("Debug info for the following error: {}", debug_msg);
            // Communicate error
            pipeless::events::publish_input_stream_error_event_sync(pipeless_bus_sender, &err_msg);
            // Exit thread, thus glib pipeline mainloop.
            panic!(
                "Error in input gst pipeline from element {}.
                Pipeline id: {}. Error: {}",
                err_src_name, pipeline_id, err_msg
            );
        },
        gst::MessageView::Warning(w) => {
            let warn_msg = w.error().message().to_string();
            let debug_msg = match w.debug() {
               Some(m) => m.as_str().to_string(),
               None => "".to_string()
            };
            let msg_src = match msg.src() {
                Some(src) => src.name(),
                None => "Element Not Obtained".into()
            };
            warn!(
                "Warning received in input gst pipeline from element {}.
                Pipeline id: {}. Warning: {}",
                msg_src, pipeline_id, warn_msg);
            debug!("Debug info: {}", debug_msg);
        },
        gst::MessageView::StateChanged(sts) => {
            let old_state = pipeless::gst::utils::format_state(sts.old());
            let current_state = pipeless::gst::utils::format_state(sts.current());
            let pending_state = pipeless::gst::utils::format_state(sts.pending());
            debug!(
                "Input gst pipeline state change. Pipeline id: {}.
                Old state: {}. Current state: {}. Pending state: {}",
                pipeline_id, old_state, current_state, pending_state);
        },
        gst::MessageView::Tag(tag) => {
            let tags = tag.tags();
            info!(
                "New tags for input gst pipeline with id {}. Tags: {}",
                pipeline_id, tags);

            pipeless::events::publish_input_tags_changed_event_sync(
                pipeless_bus_sender, tags
            );
        },
        _ => debug!("
            Unhandled message on input gst pipeline bus.
            Pipeline id: {}", pipeline_id)
    }
}

fn create_gst_pipeline(
    pipeless_pipeline_id: uuid::Uuid,
    input_uri: &str,
    pipeless_bus_sender: &tokio::sync::mpsc::UnboundedSender<pipeless::events::Event>,
) -> gst::Pipeline {
    let pipeline = gst::Pipeline::new();
    let input_bin = create_input_bin(input_uri, pipeless_bus_sender);
    // Force RGB output since workers process RGB
    let sink_caps = gst::Caps::from_str("video/x-raw,format=RGB").expect("Unable to create caps from string");
    let appsink = gst::ElementFactory::make("appsink")
        .name("appsink")
        .property("emit-signals", true)
        .property("caps", sink_caps)
        .build()
        .expect("Failed to create appsink")
        .dynamic_cast::<gst_app::AppSink>()
        .expect("Unable to cast element to AppSink");

    let appsink_callbacks = gst_app::AppSinkCallbacks::builder()
        .new_sample(
            {
                let pipeless_bus_sender = pipeless_bus_sender.clone();
                move |appsink: &gst_app::AppSink| {
                on_new_sample(
                    pipeless_pipeline_id,
                    appsink,
                    &pipeless_bus_sender,
                )
            }
        }).build();
    appsink.set_callbacks(appsink_callbacks);

    pipeline.add(&input_bin).expect("Failed to add input bin to input pipeline");
    pipeline.add(&appsink).expect("Failed to add app sink to input pipeline");

    // Link static elements
    input_bin.link(&appsink).expect("Error linking input bin to appsink");

    pipeline
}

pub struct Pipeline {
    id: uuid::Uuid, // Id of the parent pipeline (the one that groups input and output)
    stream: pipeless::input::pipeline::StreamDef,
    gst_pipeline: gst::Pipeline,
}
impl Pipeline {
    pub fn new(
        id: uuid::Uuid,
        stream: pipeless::input::pipeline::StreamDef,
        pipeless_bus_sender: &tokio::sync::mpsc::UnboundedSender<pipeless::events::Event>,
    ) -> Self {
        let input_uri = stream.get_video().get_uri();
        let gst_pipeline = create_gst_pipeline(id, input_uri, pipeless_bus_sender);
        let pipeline = Pipeline {
            id,
            stream,
            gst_pipeline,
        };

        let bus = pipeline.gst_pipeline.bus()
            .expect("Unable to get input gst pipeline bus");
        bus.add_signal_watch();
        let pipeline_id = pipeline.id.clone();
        bus.connect_message(
            None,
            {
                let pipeless_bus_sender = pipeless_bus_sender.clone();
                move |_bus, msg| {
                    on_bus_message(&msg, pipeline_id, &pipeless_bus_sender);
                }
            }
        );

        pipeline.gst_pipeline
            .set_state(gst::State::Playing)
            .expect("Unable to start the input gst pipeline");

        pipeline
    }

    pub fn get_pipeline_id(&self) -> uuid::Uuid {
        self.id
    }

    pub fn close(&self) -> Result<gst::StateChangeSuccess, gst::StateChangeError> {
        self.gst_pipeline.set_state(gst::State::Null)
    }
}