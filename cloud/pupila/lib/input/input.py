import os
import sys
import traceback
import typing
import numpy as np
#from pulsar import Client, MessageId

import gi
gi.require_version('GLib', '2.0')
gi.require_version('GObject', '2.0')
gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
from gi.repository import Gst, GObject, GstApp

from ..logger import logger

Gst.init(None)

def on_new_sample(sink: GstApp.AppSink) -> Gst.FlowReturn:
    sample = sink.emit("pull-sample")
    if sample is None:
        logger.error('Sample is None!')
        return Gst.FlowReturn.ERROR

    logger.debug(f'Sample caps: {sample.get_caps()}')

    buffer = sample.get_buffer()
    if buffer is None:
        logger.error('Buffer is None!')
        return Gst.FlowReturn.ERROR

    # Get multimedia data from the buffer
    success, info = buffer.map(Gst.MapFlags.READ)
    if not success:
        logger.error('Getting multimedia data from the buffer did not success.')
        return Gst.FlowReturn.ERROR

    # TODO; send info to apache pulsar.
    #       Ideally we should store the frame encoded to save time in write and read from pulsar.
    #       Then the worker would decode to nparray and encode it again before sending it back.
    caps = sample.get_caps()
    height = caps.get_structure(0).get_value("height")
    width = caps.get_structure(0).get_value("width")
    ndframe = np.ndarray(
        shape=(height, width, 3), dtype=np.uint8, buffer=info.data
    )
    logger.info(ndframe)

    # Release resources
    buffer.unmap(info)

    return Gst.FlowReturn.OK

def on_bus_message(bus: Gst.Bus, msg: Gst.Message, loop: GObject.MainLoop):
    """
    Callback to manage bus messages
    For example, when we receive a new-sample and return an error from
    the processing, we can catch it and stop the pipeline here.
    """
    mtype = msg.type
    if mtype == Gst.MessageType.EOS:
        logger.info("End-Of-Stream reached.")
        loop.quit()
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

def input(config):
    # Initialize the Pulsar client
    # client = Client("pulsar://localhost:6650")

    pipeline = Gst.Pipeline.new("pipeline")

    # Create elements
    videoconvert = Gst.ElementFactory.make("videoconvert", "videoconvert")
    uridecodebin = Gst.ElementFactory.make("uridecodebin3", "uridecodebin")
    appsink = Gst.ElementFactory.make("appsink", "appsink")

    if not pipeline:
        logger.error('Failed to create pipeline')
        return
    if not uridecodebin:
        logger.error('Failed to create uridecodebin')
        return
    if not videoconvert:
        logger.error('Failed to create videoconvert')
        return
    if not appsink:
        logger.error("Failed to create appsink.")
        return

    # Set properties for elements
    appsink.set_property("emit-signals", True)
    appsink.connect("new-sample", on_new_sample)
    # Force RGB output in sink
    # TODO: store the images in queue before decoding to make it faster
    caps = Gst.Caps.from_string("video/x-raw,format=RGB") # NOTE: Why is this bgr? should be RGB?
    appsink.set_property("caps", caps)

    # Allow videoconverter to negotiate input and output caps
    videoconvert.set_property("passthrough", True)

    # Add elemets to the pipeline
    pipeline.add(uridecodebin, videoconvert, appsink)

    # Link static elements (fixed number of pads): uridecoder (linked later) -> videoconvert -> appsink
    if not videoconvert.link(appsink):
        logger.error("Failed to link appsink to videoconvert")
        return

    videoconvert_sink_pad = videoconvert.get_static_pad("sink")
    # Link dynamic elements (dynamic number of pads)
    # uridecodebin creates pads for each stream found in the uri (ex: video, audio, subtitles)
    uridecodebin.set_property("uri", config['input']['video']['uri'])
    def pad_added_callback(src, pad):
        if not videoconvert_sink_pad.is_linked():
            logger.info('Linking uridecoderbin pad to videoconvert pad')
            pad.link(videoconvert_sink_pad) # uridecoder -> videoconvert -> appsink
        else:
            logger.warning('Video converter pad is already linked. Skipping uridecoder link')

    uridecodebin.connect("pad-added", pad_added_callback)

    # Handle bus events on the main loop
    bus = pipeline.get_bus()
    loop = GObject.MainLoop()
    bus.add_signal_watch()
    bus.connect("message", on_bus_message, loop)

    logger.info('Starting pipeline')
    ret = pipeline.set_state(Gst.State.PLAYING)
    if ret == Gst.StateChangeReturn.FAILURE:
        logger.error("Unable to set the pipeline to the playing state.")
        return

    try:
        logger.debug(f'uridecodebin state: {uridecodebin.get_state(5)}')
        logger.debug(f'videoconverter state: {videoconvert.get_state(5)}')
        logger.debug(f'appsink state: {appsink.get_state(5)}')
        loop.run()
    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc()
        loop.quit()
    finally:
        logger.info('Closing pipeline')
        # Clean up and close the Pulsar client
        pipeline.set_state(Gst.State.NULL)
        #client.close()
