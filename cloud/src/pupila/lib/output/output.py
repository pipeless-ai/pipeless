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

def fetch_and_send(appsrc: GstApp.AppSrc, copy_timestamps: bool):
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
            if copy_timestamps:
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
    elif protocol == 'local':
        return Gst.ElementFactory.make("autovideosink", "autovideosink")
    else:
        logger.warning(f'Unsupported output protocol {protocol}. Defaulting to autovideosink')
        # NOTE: the autovideosink output goes directly to the computer video output (screen mostly)
        return Gst.ElementFactory.make("autovideosink", "autovideosink")

def get_processing_bin(protocol, location):
    """
    Depending on the output protocol and the destination (location)
    we create the required processing pipeline to convert colorspaces,
    encode and mux the video.
    Note the output component will always receive x-raw RGB, so we just
    worry about what we have to produce for each destination
    """
    bin = Gst.Bin.new("video-bin")
    if protocol == 'file':
        """
        The pipeline will also depend on the file extension
        """
        if location.endswith('.mp4'):
            videoconvert = Gst.ElementFactory.make("videoconvert", "videoconvert")
            capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter")
            encoder = Gst.ElementFactory.make("x264enc", "encoder")
            taginject = Gst.ElementFactory.make("taginject", "taginject")
            muxer = Gst.ElementFactory.make("mp4mux", "muxer")
            bin.add(videoconvert, capsfilter, encoder, taginject, muxer)

            capsfilter.set_property("caps", Gst.Caps.from_string("video/x-raw,format=I420"))

            if not videoconvert.link(capsfilter):
                logger.error("Error lining videoconvert to capsfilter")
                sys.exit(1)
            if not capsfilter.link(encoder):
                logger.error("Error linking capsfilter to encoder")
                sys.exit(1)
            if not encoder.link(taginject):
                logger.error("Failed to link encoder to taginject")
                sys.exit(1)
            if not taginject.link(muxer):
                logger.error("Error linking taginject to muxer")
                sys.exit(1)

            # Create ghost pads to be able to plug other components
            ghostpad_sink = Gst.GhostPad.new("sink", videoconvert.get_static_pad("sink"))
            bin.add_pad(ghostpad_sink)
            ghostpad_src = Gst.GhostPad.new("src", muxer.get_static_pad("src"))
            bin.add_pad(ghostpad_src)
        else:
            logger.error('Unsupported file type. Try with a different extension.')
    elif protocol == "rtmp":
        #"videoconvert ! x264enc ! flvmux streamable=true name=mux ! rtmpsink location={file_name}"
        logger.error('Not implemented')
    elif protocol == 'local':
        queue1 = Gst.ElementFactory.make("queue", "queue1")
        videoconvert = Gst.ElementFactory.make("videoconvert", "videoconvert")
        queue2 = Gst.ElementFactory.make("queue", "queue2")
        bin.add(queue1, videoconvert, queue2)

        if not queue1.link(videoconvert):
            logger.error("Error linking queue1 to videoconvert")
            sys.exit(1)
        if not videoconvert.link(queue2):
            logger.error("Error linking videoconvert to queue2")
            sys.exit(1)

        ghostpad_sink = Gst.GhostPad.new("sink", queue1.get_static_pad("sink"))
        bin.add_pad(ghostpad_sink)
        ghostpad_src = Gst.GhostPad.new("src", queue2.get_static_pad("src"))
        bin.add_pad(ghostpad_src)
    else:
        logger.error("Unsupported output protocol")
        sys.exit(1)

    return bin

# TODO: delete when the issue with get_property("tags") is fixed
# Ref: https://gitlab.freedesktop.org/gstreamer/gst-plugins-base/-/issues/1003
current_tags = None

def update_tags(pipeline, new_tags):
    """
    Adds a buffer to the appsrc containing the video tags
    """
    logger.info(f'New tags received: {new_tags}. Updating pipeline')
    # NOTE: we expect an element called 'taginject' on the pipeline
    taginject = pipeline.get_by_name('taginject')
    if not taginject:
        logger.warning("No taginject element found, video tags won't be injected")
    else:
        new_tags_list = Gst.TagList.new_from_string(new_tags)
        # TODO: fetch the tags from the tainjgect component directly
        # Ref: https://gitlab.freedesktop.org/gstreamer/gst-plugins-base/-/issues/1003
        #
        # current_tags = taginject.get_property("tags")
        global current_tags
        merged_tags = None
        if current_tags is not None:
            current_tags_list = Gst.TagList.new_from_string(current_tags)
            merged_tags = new_tags_list.merge(
                current_tags_list,
                Gst.TagMergeMode.KEEP
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
        logger.error(sanitized_tags_string)
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
                # We don't really care about input caps changes
                # we just worry about the output formats
                pass
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
    # Dynamically calculate the output sink to use
    out_protocol = config.get_output().get_video().get_uri_protocol()
    out_location = config.get_output().get_video().get_uri_location()
    pipeline_sink = create_sink(out_protocol, out_location)

    if not pipeline:
        logger.error('Failed to create output pipeline')
        sys.exit(1)
    if not pipeline_appsrc:
        logger.error('Failed to create output pipeline appsrc')
        sys.exit(1)
    if not pipeline_sink:
        logger.error("Failed to create output sink.")
        sys.exit(1)

    pipeline_appsrc.set_property("is-live", True)
    pipeline_appsrc.set_property("do-timestamp", False) # the buffers already wear timestamps
    pipeline_appsrc.set_property("format", Gst.Format.TIME)
    pipeline_appsrc.set_property("max-bytes", 1000000000) # 10 Megabytes of queue size
    input_caps = Gst.Caps.from_string("video/x-raw,format=RGB,width=1920,height=1080,framerate=30/1")
    pipeline_appsrc.set_property("caps", input_caps)

    pipeline.add(
        pipeline_appsrc,
        pipeline_sink
    )
    processing_bin = get_processing_bin(out_protocol, out_location)
    pipeline.add(processing_bin)

    if not pipeline_appsrc.link(processing_bin):
        logger.error("Error linking appsrc to the processing bin")
        sys.exit(1)
    if not processing_bin.link(pipeline_sink):
        logger.error("Error linking processing bin to sink")
        sys.exit(1)

    loop = GLib.MainLoop()
    # Handle bus events on the main loop
    pipeline_bus = pipeline.get_bus()
    pipeline_bus.add_signal_watch()
    pipeline_bus.connect("message", on_bus_message, loop)

    ret = pipeline.set_state(Gst.State.PLAYING) # Start pipeline
    if ret == Gst.StateChangeReturn.FAILURE:
        logger.error("Unable to set the pipeline to the playing state.")
        sys.exit(1)

    try:
        logger.info(f'appsrc state: {pipeline_appsrc.get_state(5)}')
        logger.info(f'appsink state: {pipeline_sink.get_state(5)}')

        copy_timestamps = not out_protocol == 'local'
        # Run on every cicle of the event loop
        GLib.timeout_add(0, lambda: fetch_and_send(pipeline_appsrc, copy_timestamps))
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
