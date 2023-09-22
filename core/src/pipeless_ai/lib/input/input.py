import os
import sys
import traceback
import numpy as np

import gi
gi.require_version('GLib', '2.0')
gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
from gi.repository import Gst, GstApp, GLib

from pipeless_ai.lib.logger import logger, update_logger_component, update_logger_level
from pipeless_ai.lib.connection import InputOutputSocket, InputPushSocket, WorkerReadySocket
from pipeless_ai.lib.config import Config
from pipeless_ai.lib.messages import EndOfStreamMsg, RgbImageMsg, StreamCapsMsg, StreamTagsMsg

def on_new_sample(sink: GstApp.AppSink) -> Gst.FlowReturn:
    sample = sink.pull_sample()
    if sample is None:
        logger.error('Sample is None!')
        return Gst.FlowReturn.ERROR # TODO: We should return a different status if we want to leave the app running forever and being able to recover from flows

    logger.debug(f'Sample caps: {sample.get_caps().to_string()}')

    buffer = sample.get_buffer()
    if buffer is None:
        logger.error('Buffer is None!')
        return Gst.FlowReturn.ERROR

    # Get multimedia data from the buffer
    success, info = buffer.map(Gst.MapFlags.READ)
    if not success:
        logger.error('Getting multimedia data from the buffer did not success.')
        return Gst.FlowReturn.ERROR

    caps = sample.get_caps()
    width = caps.get_structure(0).get_value("width")
    height = caps.get_structure(0).get_value("height")
    dts = buffer.dts
    pts = buffer.pts
    duration = buffer.duration
    ndframe : np.ndarray = np.ndarray(
        shape=(height, width, 3),
        dtype=np.uint8, buffer=info.data
    )

    msg = RgbImageMsg(width, height, ndframe, dts, pts, duration)
    s_msg = msg.serialize()

    # Pass msg to the workers
    s_push = InputPushSocket()
    s_push.send(s_msg)

    # Release resources
    buffer.unmap(info)

    return Gst.FlowReturn.OK

def on_pad_upstream_event(pad, info, user_data):
    """
     TODO: if the pad name is always different, we can run simultaneous
     pipelines in both input and output by simply creating a create_pipeline
     function and managing several of them in both the input and the output.
     That would allow users to send several streams to the same app.
     they would be processed on the same workers with the same code.
     How do we distinguish the videos for the output? Right now
     they will both be sent to the same URI
    """
    caps = pad.get_current_caps()
    if caps is not None:
        # Caps negotiation is complete, notify new stream to output component
        logger.info(f'[green]dynamic source pad "{pad.get_name()}" with caps:[/green] {caps.to_string()}')
        config = Config(None)
        if config.get_output().get_video().is_enabled():
            m_socket = InputOutputSocket('w')
            m_msg = StreamCapsMsg(caps.to_string())
            m_socket.send(m_msg.serialize())
        # We already got the caps. Remove the probe from the pad
        return Gst.PadProbeReturn.REMOVE

    return Gst.PadProbeReturn.OK # Leave the probe in place

def handle_caps_change(pad):
    # Connect an async handler to the pad to be notified when caps are set
    pad.add_probe(Gst.PadProbeType.EVENT_UPSTREAM, on_pad_upstream_event, pad)

def on_pad_added(element, pad, *callbacks):
    for callback in callbacks:
        callback(pad)

def get_input_bin(uri):
    """
    Creates the appropiate input bin depending on the configuration
    """
    bin = Gst.Bin.new("source-bin")
    if uri == 'v4l2':
        # Input from webcam
        v4l2src = Gst.ElementFactory.make("v4l2src", "source")
        videoconvert = Gst.ElementFactory.make("videoconvert", "videoconvert")
        videoscale = Gst.ElementFactory.make("videoscale", "videoscale")
        # Webcam resolutions are not standard and we can't read the webcam caps,
        # force a hardcoded resolution so that we annouce a correct resolution to the output.
        forced_size_str = 'video/x-raw,width=1280,height=720'
        capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter")
        capsfilter.set_property("caps", Gst.Caps.from_string(forced_size_str))

        for elem in [v4l2src, videoconvert, videoscale, capsfilter]:
            bin.add(elem)

        # Link elements statically
        if not v4l2src.link(videoconvert):
            logger.error('Error linking v4l2src to videoconvert')
            sys.exit(1)
        if not videoconvert.link(videoscale):
            logger.error('Error linking videoconvert to videoscale')
            sys.exit(1)
        if not videoscale.link(capsfilter):
            logger.error('Error linking videoscale to capsfilter')
            sys.exit(1)

        # Create ghost pads to be able to plug other components
        ghostpad_src = Gst.GhostPad.new("src", capsfilter.get_static_pad("src"))
        bin.add_pad(ghostpad_src)

        config = Config(None)
        if config.get_output().get_video().is_enabled():
            # v4l2src doesn't have caps propert. Notify the output about the new stream
            forced_caps_str = f'{forced_size_str},format=RGB,framerate=1/30'
            m_socket = InputOutputSocket('w')
            m_msg = StreamCapsMsg(forced_caps_str)
            m_socket.send(m_msg.serialize())
    else:
        # Use uridecodebin by default
        uridecodebin = Gst.ElementFactory.make("uridecodebin3", "source")
        videoconvert = Gst.ElementFactory.make("videoconvert", "videoconvert")
        for elem in [uridecodebin, videoconvert]:
            bin.add(elem)

        uridecodebin.set_property("uri", uri)

        # Uridecodebin uses dynamic linking (creates pads on new streams detected)
        videoconvert_sink_pad = videoconvert.get_static_pad("sink")
        def pad_added_callback(pad):
            if not videoconvert_sink_pad.is_linked():
                logger.info('Linking uridecodebin pad to videoconvert pad')
                pad.link(videoconvert_sink_pad) # uridecoder -> videoconvert -> appsink
            else:
                logger.warning('Video converter pad is already linked. Skipping uridecoder link')

        uridecodebin.connect("pad-added", lambda element, pad:
            on_pad_added(
                element, pad, pad_added_callback, handle_caps_change
            )
        )

        # Create ghost pads to be able to plug other components
        ghostpad_src = Gst.GhostPad.new("src", videoconvert.get_static_pad("src"))
        bin.add_pad(ghostpad_src)

    return bin

class Input:
    def __init__(self):
        self.__pipeline : Gst.Pipeline = None
        self.__loop : GLib.MainLoop = None

    def new_pipeline(self):
        """
        Create a new input pipeline
        """
        config = Config(None)
        self.__pipeline = Gst.Pipeline.new("pipeline")
        # Create elements
        # We will force RBG on the sink and videoconvert takes care of
        # converting between space colors negotiating caps automatically.
        # Ref: https://gstreamer.freedesktop.org/documentation/tutorials/basic/handy-elements.html?gi-language=c#videoconvert
        input_bin = get_input_bin(config.get_input().get_video().get_uri())
        appsink = Gst.ElementFactory.make("appsink", "appsink")

        if not self.__pipeline:
            logger.error('Failed to create pipeline')
            sys.exit(1)
        if not appsink:
            logger.error("Failed to create appsink.")
            sys.exit(1)

        # Set properties for elements
        appsink.set_property("emit-signals", True)
        appsink.connect("new-sample", on_new_sample)
        # Force RGB output in sink
        sink_caps = Gst.Caps.from_string("video/x-raw,format=RGB")
        appsink.set_property("caps", sink_caps)

        # Add elemets to the pipeline
        for elem in [input_bin, appsink]: self.__pipeline.add(elem)

        # Link static elements (fixed number of pads): input_bin -> appsink
        if not input_bin.link(appsink):
            logger.error("Error linking input bin to appsink")
            sys.exit(1)

        # Handle bus events on the main loop
        bus = self.__pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", on_bus_message, self)

    def start(self):
        if not self.__pipeline:
            logger.error('[red]The pipeline has not been created. Unable to start.[/red]')
            sys.exit(1)

        logger.info('Starting input pipeline')
        ret = self.__pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            logger.error("[red]Unable to set the pipeline to the playing state.[/red]")
            sys.exit(1)

    def close(self):
        logger.info('Closing pipeline')
        self.__pipeline.set_state(Gst.State.NULL)

    def set_mainloop(self, loop: GLib.MainLoop):
        self.__loop = loop
    def get_mainloop(self):
        return self.__loop

def on_bus_message(bus: Gst.Bus, msg: Gst.Message, input: Input):
    """
    Callback to manage bus messages
    For example, when we receive a new-sample and return an error from
    the processing, we can catch it and stop the pipeline here.
    """
    mtype = msg.type
    if mtype == Gst.MessageType.EOS:
        logger.info("End of stream reached.")
        w_socket = InputPushSocket()
        m_msg = EndOfStreamMsg()
        m_msg = m_msg.serialize()
        config = Config(None)
        for _ in range(config.get_worker().get_n_workers()):
            # The socket is round robin, send to all workers
            # TODO: a broadcast socket for this is better for scaling
            #       by saving the n_workers config option
            logger.info('Notifying EOS to worker')
            w_socket.ensure_send(m_msg)

        if (config.get_output().get_video().get_uri_protocol() == 'file'
            or config.get_input().get_video().get_uri_protocol() == 'file'):
            # Stop after the first stream when using an input or output file.
            # We do not want to override the output file
            # and we can't get a new stream once the file ends
            input.get_mainloop().quit()
        else:
            # Reset the input pipeline to handle a new stream
            input.close()
            input.new_pipeline()
            input.start()
    elif mtype == Gst.MessageType.ERROR:
        err, debug = msg.parse_error()
        logger.error(f"Error received from element {msg.src.get_name()}: {err.message}")
        logger.error(f"Debugging information: {debug or 'none'}")
        input.get_mainloop().quit()
    elif mtype == Gst.MessageType.WARNING:
        err, debug = msg.parse_warning()
        logger.warning(f"Warning received from element {msg.src.get_name()}: {err.message}")
        logger.warning(f"Debugging information: {debug or 'none'}")
    elif mtype == Gst.MessageType.STATE_CHANGED:
        old_state, new_state, pending_state = msg.parse_state_changed()
        logger.debug(f'New pipeline state: {new_state}')
    elif mtype == Gst.MessageType.TAG:
        tags = msg.parse_tag().to_string()
        logger.info(f'Tags parsed: {tags}')
        config = Config(None)
        if config.get_output().get_video().is_enabled():
            t_socket = InputOutputSocket('w')
            t_msg = StreamTagsMsg(tags)
            t_socket.send(t_msg.serialize())

    return True

def input(config_dict):
    update_logger_component('INPUT')
    config = Config(config_dict)
    update_logger_level(config.get_log_level())

    logger.info(f"Reading video from {config.get_input().get_video().get_uri()}")
    if config.get_input().get_video().get_uri_protocol() == 'file' and not os.path.isfile(config.get_input().get_video().get_uri_location()):
        logger.error("[red]Input video file doesn't exist[/red]")
        sys.exit(1)

    Gst.init(None)
    p_input = Input()
    loop = GLib.MainLoop()
    p_input.set_mainloop(loop)
    p_input.new_pipeline()

    try:
        # Start socket to wait all components connections
        s_push  = InputPushSocket() # Listener
        w_socket = WorkerReadySocket('input')
        logger.info('Waiting first worker to be available')
        w_socket.recv() # Wait for the first worker to appear
        logger.info('First worker ready')
        if config.get_output().get_video().is_enabled():
            m_socket = InputOutputSocket('w') # Waits for output

        p_input.start()

        loop.run()
    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc()
        loop.quit()
    finally:
        # Retrieve and close the sockets
        if config.get_output().get_video().is_enabled():
            m_socket.close()
        s_push.close()
        w_socket.close()
        logger.info('Input finished. Please wait for workers and output (if enabled).')
