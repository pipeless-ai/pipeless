import sys
import traceback
import pynng as nng
import numpy as np

import gi
gi.require_version('GLib', '2.0')
gi.require_version('GObject', '2.0')
gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
from gi.repository import Gst, GObject, GstApp

from cloud.pupila.lib.connection import InputOutputSocket, OutputPullSocket
from cloud.pupila.lib.logger import logger
from cloud.pupila.lib.messages import load_msg, MsgType
from cloud.pupila.lib.config import Config

# TODO: create a process to fetch from the bussocket and edit the pipeline when a metadata message arrives

def fetch_and_send(appsrc: GstApp.AppSource):
    # TODO: we may need to use the 'need-data' and 'enough-data' signals to avoid overflowing the appsrc input queue
    r_socket = OutputPullSocket()
    raw_msg = r_socket.recv(1) # 1 second timeout
    msg = load_msg(raw_msg)
    
    if msg.type == MsgType.RGB_IMAGE:
        # Convert the frame to a GStreamer buffer
        data = msg.get_data()
        buffer = Gst.Buffer.new_allocate(None, len(data), None)
        buffer.fill(0, data)
        buffer.pts = msg.get_dts()
        buffer.dts = msg.get_pts()

        # Send the frame
        appsrc.emit("push-buffer", buffer)
    else:
        logger.error(f'Unsupported message type: {msg.type}')

def on_bus_message(bus: Gst.Bus, msg: Gst.Message, loop: GObject.MainLoop):
    """
    Callback to manage bus messages
    """
    mtype = msg.type
    if mtype == Gst.MessageType.EOS:
        logger.info("End-Of-Stream reached.")
    elif mtype == Gst.MessageType.ERROR:
        err, debug = msg.parse_error()
        logger.error(f"Error received from element {msg.src.get_name()}: {err.message}")
        logger.error(f"Debugging information: {debug if debug else 'none'}")
        loop.quit()
    elif mtype == Gst.MessageType.WARNING:
        err, debug = msg.parse_warning()
        logger.warning(f"Warning received from element {msg.src.get_name()}: {err.message}")
        logger.warning(f"Debugging information: {debug if debug else 'none'}")

    return True

def create_sink(protocol):
    """
    Create the appropiate sink based on the output protocol provided
    """
    if protocol == 'file':
        return Gst.ElementFactory.make("filesink", "filesink")
    else:
        logger.warning(f'Unsupported output protocol {protocol}. Defaulting to autovideosink')
        return Gst.ElementFactory.make("autovideosink", "autovideosink")

def set_sink_caps(sink, str_caps, pipeline):
    """
    Update the sink caps dynamically
    This enforces the whole pipeline caps to negotiate for matching the sink ones
    """
    logger.info(f'Updating pipeline caps to {str_caps}')
    logger.debug('Stopping pipeline')
    pipeline.set_state(Gst.State.NULL) # Stop pipeline
    caps = Gst.Caps.from_string(str_caps)
    sink.set_property("caps", caps)
    logger.debug('Starting pipeline')
    pipeline.set_state(Gst.State.PLAYING)
    logger.info('Caps updated to {str_caps}')

def handle_message(pipeline):
    """
    Handles messages comming from the input component
    """
    m_socket = InputOutputSocket('r')
    raw_msg = m_socket.recv(1) # 1 second timeout
    msg = load_msg(raw_msg)

    if msg.type == MsgType.METADATA:
        caps = msg.get_caps()
        sink = pipeline.get_by_interface(Gst.ElementSink) # NOTE: assumes the pipeline has a single sink
        set_sink_caps(sink, caps, pipeline)

def output():
    Gst.init(None)
        
    config = Config(None)

    # Build decode pipeline
    pipeline = Gst.Pipeline.new("pipeline")
    pipeline_appsrc = Gst.ElementFactory.make("appsrc", "appsrc")
    pipeline_videoconvert = Gst.ElementFactory.make("videoconvert", "videoconvert")
    pipeline_encodebin = Gst.ElementFactory.make("encodebin", "encodebin")
    # Dynamically calculate the output sink to use
    pipeline_sink = create_sink(config.get_output().get_protocol()) 

    if not pipeline:
        logger.error('Failed to create output pipeline')
        sys.exit(1)
    if not pipeline_appsrc:
        logger.error('Failed to create output pipeline appsrc')
        sys.exit(1)
    if not pipeline_videoconvert:
        logger.error('Failed to create output pipeline videoconvert')
        sys.exit(1)
    if not pipeline_encodebin:
        logger.error('Failed to create output pipeline encodebin')
        sys.exit(1)
    if not pipeline_sink:
        logger.error("Failed to create output sink.")
        sys.exit(1)

    pipeline_appsrc.set_property("is-live", True)
    pipeline_appsrc.set_property("do-timestamp", False) # the buffers already wear timestamps
    
    # Set initial default caps. Will be overriden once a stream arrives
    default_caps = 'video/x-raw,format=RGBA,width=1920,height=1080,framerate=30/1'
    caps = Gst.Caps.from_string(default_caps)
    pipeline_sink.set_property("caps", caps)

    pipeline.add(
        pipeline_appsrc,
        pipeline_videoconvert,
        pipeline_encodebin,
        pipeline_sink
    )

    # Link elements
    if not pipeline_appsrc.link(pipeline_videoconvert):
        logger.error("Failed to link appsrc to videoconvert")
        sys.exit(1)
    if not pipeline_videoconvert.link(pipeline_encodebin):
        logger.error("Failed to link videoconvert to encodebin")
        sys.exit(1)
    if not pipeline_encodebin.link(pipeline_sink):
        logger.error("Failed to link encodebin to sink")
        sys.exit(1)

    loop = GObject.MainLoop()
    # Handle bus events on the main loop
    pipeline_bus = pipeline.get_bus()
    pipeline_bus.add_signal_watch()
    pipeline_bus.connect("message", on_bus_message, loop)

    logger.info('Starting pipeline')
    ret = pipeline.set_state(Gst.State.PLAYING)
    if ret == Gst.StateChangeReturn.FAILURE:
        logger.error("Unable to set the pipeline to the playing state.")
        sys.exit(1)
    
    try:
        logger.debug(f'appsrc state: {pipeline_appsrc}')
        logger.debug(f'videoconverter state: {pipeline_videoconvert.get_state(5)}')
        logger.debug(f'decodebin state: {pipeline_encodebin.get_state(5)}')
        logger.debug(f'appsink state: {pipeline_sink.get_state(5)}')
        
        r_socket = OutputPullSocket()
        r_socket_fd = r_socket.getsockopt(nng.NNG_OPT_RECVFD)
        r_channel = GObject.IOChannel(r_socket_fd)
        r_channel.add_watch(GObject.IO_IN, lambda: fetch_and_send(pipeline_appsrc))
        
        m_socket = InputOutputSocket('r')
        m_socket_fd = m_socket.getsockopt(nng.NNG_OPT_REVCFD)
        m_channel = GObject.IOChannel(m_socket_fd)
        m_channel.add_watch(GObject.IO_IN, handle_message)

        loop.run()
    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc()
        loop.quit()
    finally:
        logger.info('Closing pipeline')
        pipeline.set_state(Gst.State.NULL)