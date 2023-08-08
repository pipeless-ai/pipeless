import re
import sys
import traceback

import gi
gi.require_version('GLib', '2.0')
gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import Gst, GstApp, GLib, GstPbutils

from src.pupila.lib.connection import InputOutputSocket, OutputPullSocket
from src.pupila.lib.logger import logger
from src.pupila.lib.messages import EndOfStreamMsg, StreamMetadataMsg, StreamTagsMsg, deserialize, RgbImageMsg
from src.pupila.lib.config import Config

def fetch_and_send(appsrc: GstApp.AppSrc):
    # TODO: we may need to use the 'need-data' and 'enough-data' signals to avoid overflowing the appsrc input queue
    r_socket = OutputPullSocket()
    raw_msg = r_socket.recv()
    if raw_msg is not None:
        logger.debug(f'[purple]New message of {len(raw_msg)} bytes[/purple]')
        msg = deserialize(raw_msg)

        if isinstance(msg, RgbImageMsg):
            # Convert the frame to a GStreamer buffer
            data = msg.get_data()
            buffer = Gst.Buffer.new_wrapped(data.tobytes())
            buffer.pts = msg.get_pts()
            buffer.dts = msg.get_dts()
            buffer.duration = msg.get_duration()

            # Send the frame
            appsrc.emit("push-buffer", buffer)
        else:
            logger.error(f'Unsupported message type: {msg.type}')
            return False # Indicate GLib to not run the function again

    return True # Indicate the GLib timeout to retry on the next interval

def on_bus_message(bus: Gst.Bus, msg: Gst.Message, loop: GLib.MainLoop):
    """
    Callback to manage bus messages
    """
    mtype = msg.type
    if mtype == Gst.MessageType.EOS:
        logger.info("End of stream reached.")
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

def create_sink(protocol, location):
    """
    Create the appropiate sink based on the output protocol provided
    """
    if protocol == 'file':
        sink = Gst.ElementFactory.make("filesink", "sink")
        sink.set_property("location", location)
        return sink
    elif protocol == 'https':
        sink = Gst.ElementFactory.make("souphttpsink", "sink")
        sink.set_property("location", location)
        return sink
    elif protocol == 'rtmp':
        sink = Gst.ElementFactory.make("rtmpsink", "sink")
        sink.set_property("location", location)
        return sink
    elif protocol == 'rtsp':
        sink = Gst.ElementFactory.make("rtspclientsink", "sink")
        sink.set_property("location", location)
        return sink
    else:
        logger.warning(f'Unsupported output protocol {protocol}. Defaulting to autovideosink')
        # NOTE: the autovideosink output goes directly to the computer video output (screen mostly)
        return Gst.ElementFactory.make("autovideosink", "autovideosink")

def update_caps(pipeline, str_caps):
    """
    Update the pipeline caps dynamically.
    We update the caps when a new stream arrives
    """
    logger.info(f'Updating pipeline caps to {str_caps}')
    logger.debug('Stopping pipeline')
    # Pause pipeline. NOTE: Setting it to NULL would release
    # resources and won't start again
    pipeline.set_state(Gst.State.PAUSED)

    caps = Gst.Caps.from_string(str_caps)
    # Update caps on the capsfilter
    capsfilter = pipeline.get_by_name("capsfilter")
    capsfilter.set_property("caps", caps)
    # Update caps on the appsrc.
    # TODO: test if sending a new stream with different
    #       caps requires to re-create the appsrc
    appsrc = pipeline.get_by_name("appsrc")
    appsrc.set_property("caps", caps)

    # Create a new encoding profile and update the encodebin
    # TODO: if this fails we may need to create a new encodebin, unlink the old one and link the new one in place
    encodebin = pipeline.get_by_name("encodebin")
    profile = GstPbutils.EncodingVideoProfile.new(caps, None, None, 0)
    encodebin.set_property("profile", profile)

    logger.debug('Starting pipeline')
    ret = pipeline.set_state(Gst.State.PLAYING) # Start pipeline
    if ret == Gst.StateChangeReturn.FAILURE:
        logger.error("Unable to set the pipeline to the playing state.")
        sys.exit(1)
    logger.info(f'Caps updated to {str_caps}')

# TODO: delete when the issue with get_property("tags") is fixed
# Ref: https://gitlab.freedesktop.org/gstreamer/gst-plugins-base/-/issues/1003
current_tags = None

def update_tags(pipeline, new_tags):
    """
    Adds a buffer to the appsrc containing the video tags
    """
    logger.info(f'New tags received: {new_tags}. Updating pipeline')
    taginject = pipeline.get_by_name('taginject')
    new_tags_list = Gst.TagList.new_from_string(new_tags)
    # TODO: fetch the tags from the tainjgect component directly
    # Ref: https://gitlab.freedesktop.org/gstreamer/gst-plugins-base/-/issues/1003
    #
    # current_tags = taginject.get_property("tags")
    global current_tags
    if current_tags is not None:
        current_tags_list = Gst.TagList.new_from_string(current_tags)
        merged_tags = Gst.TagList.merge(
            new_tags_list,
            current_tags_list,
            Gst.TagMergeMode.KEEP_ALL
        )
    else:
        merged_tags = new_tags_list

    logger.info(f'Updating tags to {merged_tags.to_string()}')
    current_tags = merged_tags.to_string() # Update the new tags for later iterations
    # We need to iterate and parse the tags manually because taginject
    #  doesn't work with a direct taglist.to_string()
    tags_array = []
    def taglist_iterator(list, tag, value):
        nonlocal tags_array
        if tag == 'taglist':
            # Remove taglist from the string
            return
        n_tag_values = list.get_tag_size(tag)
        if n_tag_values > 1: logger.warning(f'Some values will be lost for tag: {tag}')
        tag_value = list.get_value_index(tag, 0) # A tag can have several values
        if isinstance(tag_value, str):
            tag_value = f'"{tag_value}"'
        tags_array.append(f'{tag}={tag_value}')

    merged_tags.foreach(taglist_iterator, None)
    sanitized_tags_string = ','.join(tags_array)
    taginject.set_property("tags", sanitized_tags_string)

def handle_input_messages(pipeline):
    """
    Handles messages comming from the input component
    """
    m_socket = InputOutputSocket('r')
    raw_msg = m_socket.recv()
    if raw_msg is not None:
        try:
            msg = deserialize(raw_msg)
            if isinstance(msg, StreamMetadataMsg):
                caps = msg.get_caps()
                update_caps(pipeline, caps)
            elif isinstance(msg, StreamTagsMsg):
                tags = msg.get_tags()
                update_tags(pipeline, tags)
            elif isinstance(msg, EndOfStreamMsg):
                logger.info('End of stream received')
                # TODO: we should finish processing the current stream before
                #      executing appsrc end_of_stream
                appsrc = pipeline.get_by_name("appsrc")
                appsrc.end_of_stream()
        except Exception:
            logger.error('Stopping message handler:')
            traceback.print_exc()
            sys.exit()

    return True # Indicate the GLib timeout to retry on the next interval

def output():
    Gst.init(None)

    config = Config(None)

    # Build decode pipeline
    pipeline = Gst.Pipeline.new("pipeline")
    pipeline_appsrc = Gst.ElementFactory.make("appsrc", "appsrc")
    pipeline_taginject = Gst.ElementFactory.make("taginject", "taginject")
    pipeline_videoconvert = Gst.ElementFactory.make("videoconvert", "videoconvert")
    pipeline_encodebin = Gst.ElementFactory.make("encodebin", "encodebin")
    pipeline_capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter")
    # Dynamically calculate the output sink to use
    pipeline_sink = create_sink(
        config.get_output().get_video().get_uri_protocol(),
        config.get_output().get_video().get_uri_location()
    )

    if not pipeline:
        logger.error('Failed to create output pipeline')
        sys.exit(1)
    if not pipeline_appsrc:
        logger.error('Failed to create output pipeline appsrc')
        sys.exit(1)
    if not pipeline_taginject:
        logger.error('Failed to create output pipeline taginject')
        sys.exit(1)
    if not pipeline_videoconvert:
        logger.error('Failed to create output pipeline videoconvert')
        sys.exit(1)
    if not pipeline_encodebin:
        logger.error('Failed to create output pipeline encodebin')
        sys.exit(1)
    if not pipeline_capsfilter:
        logger.error('Failed to create output pipeline capsfilter')
        sys.exit(1)
    if not pipeline_sink:
        logger.error("Failed to create output sink.")
        sys.exit(1)

    pipeline_appsrc.set_property("is-live", True)
    pipeline_appsrc.set_property("do-timestamp", False) # the buffers already wear timestamps
    pipeline_appsrc.set_property("format", Gst.Format.TIME)
    pipeline_appsrc.set_property("max-bytes", 10000000) # 10 Megabytes of size

    # Set initial default caps. Will be overriden when a stream arrives
    default_caps = 'video/x-raw,format=I420,width=1920,height=1080,framerate=30/1'
    caps = Gst.Caps.from_string(default_caps)
    pipeline_capsfilter.set_property("caps", caps)

    # TODO: if we use EncodingVideoProfile, what happens to audio?
    #       Can we process audio only? There is EncodingAudioProfile.
    #       Should we use EncodingContainerProfile instead?
    # TODO: this is wrong becasue can't be updated. We need to do in update caps
    #       we need to unlink and create a new component
    profile = GstPbutils.EncodingVideoProfile.new(caps, None, None, 0)
    pipeline_encodebin.set_property("profile", profile)

    pipeline.add(
        pipeline_appsrc,
        pipeline_taginject,
        pipeline_videoconvert,
        pipeline_encodebin,
        pipeline_capsfilter,
        pipeline_sink
    )

    # Link elements
    if not pipeline_appsrc.link(pipeline_taginject):
        logger.error("Failed to link appsrc to taginject")
        sys.exit(1)
    if not pipeline_taginject.link(pipeline_videoconvert):
        logger.error("Failed to link taginject to videoconvert")
        sys.exit(1)
    if not pipeline_videoconvert.link(pipeline_encodebin):
        logger.error("Failed to link videoconvert to encodebin")
        sys.exit(1)
    if not pipeline_encodebin.link(pipeline_capsfilter):
        logger.error("Failed to link encodebin to capsfilter")
        sys.exit(1)
    if not pipeline_capsfilter.link(pipeline_sink):
        logger.error("Failed to link capsfilter to sink")
        sys.exit(1)

    loop = GLib.MainLoop()
    # Handle bus events on the main loop
    pipeline_bus = pipeline.get_bus()
    pipeline_bus.add_signal_watch()
    pipeline_bus.connect("message", on_bus_message, loop)

    # NOTE: The pipeline will be started once a new stream is notified

    try:
        logger.debug(f'appsrc state: {pipeline_appsrc}')
        logger.debug(f'videoconverter state: {pipeline_videoconvert.get_state(5)}')
        logger.debug(f'decodebin state: {pipeline_encodebin.get_state(5)}')
        logger.debug(f'appsink state: {pipeline_sink.get_state(5)}')

        # Run on every cicle of the event loop
        GLib.timeout_add(0, lambda: fetch_and_send(pipeline_appsrc))
        GLib.timeout_add(0, lambda: handle_input_messages(pipeline))

        # Start socket listeners
        m_socket = InputOutputSocket('r')
        r_socket = OutputPullSocket()

        loop.run()
    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc()
        loop.quit()
    finally:
        logger.info('Closing pipeline')
        pipeline.set_state(Gst.State.NULL)
        # Retreive and close the sockets
        m_socket = InputOutputSocket('r')
        m_socket.close()
        r_socket = OutputPullSocket()
        r_socket.close()
