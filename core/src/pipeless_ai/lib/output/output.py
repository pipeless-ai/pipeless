import sys
import traceback

import gi
gi.require_version('GLib', '2.0')
gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
from gi.repository import Gst, GstApp, GLib

from pipeless_ai.lib.connection import InputOutputSocket, OutputPullSocket
from pipeless_ai.lib.logger import logger, update_logger_component, update_logger_level
from pipeless_ai.lib.messages import EndOfStreamMsg, StreamCapsMsg, StreamTagsMsg, deserialize, RgbImageMsg
from pipeless_ai.lib.config import Config

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
            if data is None:
                logger.error('The frame received was None. Did you forgot to return a frame from your application hooks?')
                return True # Indicate GLib to retry on the next interval
            buffer = Gst.Buffer.new_wrapped(data.tobytes())

            if copy_timestamps:
                buffer.pts = msg.get_pts()
                buffer.dts = msg.get_dts()
                buffer.duration = msg.get_duration()

            # Send the frame
            appsrc.emit("push-buffer", buffer)
        elif isinstance(msg, EndOfStreamMsg):
            # NOTE: when deploying more than one worker, only the first message will be handled.
            #       There will be a transient period of some frames that could be lost in that case.
            appsrc.end_of_stream()
            return False # Indicate GLib to not run the function again
        else:
            logger.error(f'Unsupported message type: {msg.type}')
            return False # Indicate GLib to not run the function again

    return True # Indicate the GLib timeout to retry on the next interval

def get_sink(sink_type, location=None):
    sink = Gst.ElementFactory.make(sink_type, "sink") # All are named sink
    if location:
        sink.set_property("location", location)
    return sink

def create_sink(protocol, location):
    """
    Create the appropiate sink based on the output protocol provided
    """
    if protocol == 'file':
        return get_sink("filesink", location=location)
    elif protocol == 'https':
        return get_sink("souphttpsink", location=location)
    elif protocol == 'rtmp':
        return get_sink("rtmpsink", location=f'{protocol}://{location}')
    elif protocol == 'rtsp':
        return get_sink("rtspclientsink", location=location)
    elif protocol == 'screen':
        return get_sink("autovideosink")
    else:
        logger.warning(f'Unsupported output protocol {protocol}. Defaulting to autovideosink')
        # NOTE: the autovideosink output goes directly to the computer video output (screen mostly)
        return get_sink("autovideosink")

def get_processing_bin(protocol, location):
    """
    Depending on the output protocol and the destination (location)
    we create the required processing pipeline to convert colorspaces,
    encode and mux the video.
    Note the output component will always receive x-raw RGB, so we just
    worry about what we have to produce for each destination
    """
    g_bin = Gst.Bin.new("video-bin")
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
            for elem in [videoconvert, capsfilter, encoder, taginject, muxer]:
                g_bin.add(elem)

            capsfilter.set_property("caps", Gst.Caps.from_string("video/x-raw,format=I420"))

            if not videoconvert.link(capsfilter):
                logger.error("Error linking videoconvert to capsfilter")
                sys.exit(1)
            if not capsfilter.link(encoder):
                logger.error("Error linking capsfilter to encoder")
                sys.exit(1)
            if not encoder.link(taginject):
                logger.error("Error linking encoder to taginject")
                sys.exit(1)
            if not taginject.link(muxer):
                logger.error("Error linking taginject to muxer")
                sys.exit(1)

            # Create ghost pads to be able to plug other components
            ghostpad_sink = Gst.GhostPad.new("sink", videoconvert.get_static_pad("sink"))
            g_bin.add_pad(ghostpad_sink)
            ghostpad_src = Gst.GhostPad.new("src", muxer.get_static_pad("src"))
            g_bin.add_pad(ghostpad_src)
        else:
            logger.error('Unsupported file type. Try with a different extension.')
    elif protocol == "rtmp":
        videoconvert = Gst.ElementFactory.make("videoconvert", "videoconvert")
        queue = Gst.ElementFactory.make("queue", "queue")
        encoder = Gst.ElementFactory.make("x264enc", "encoder")
        taginject = Gst.ElementFactory.make("taginject", "taginject")
        muxer = Gst.ElementFactory.make("flvmux", "muxer")
        for elem in [videoconvert, queue, encoder, taginject, muxer]:
            g_bin.add(elem)

        muxer.set_property("streamable", True)

        if not videoconvert.link(queue):
            logger.error("Error linking videoconvert to queue")
            sys.exit(1)
        if not queue.link(encoder):
            logger.error("Error linking queue to encoder")
            sys.exit(1)
        if not encoder.link(taginject):
            logger.error("Error linking encoder to taginject")
            sys.exit(1)
        if not taginject.link(muxer):
            logger.error("Error linking taginject to muxer")
            sys.exit(1)

        # Create ghost pads to be able to plug other components
        ghostpad_sink = Gst.GhostPad.new("sink", videoconvert.get_static_pad("sink"))
        g_bin.add_pad(ghostpad_sink)
        ghostpad_src = Gst.GhostPad.new("src", muxer.get_static_pad("src"))
        g_bin.add_pad(ghostpad_src)

    elif protocol == 'screen':
        queue1 = Gst.ElementFactory.make("queue", "queue1") # TODO: is this queue required?
        videoconvert = Gst.ElementFactory.make("videoconvert", "videoconvert")
        queue2 = Gst.ElementFactory.make("queue", "queue2")
        for elem in [queue1, videoconvert, queue2]: g_bin.add(elem)

        if not queue1.link(videoconvert):
            logger.error("Error linking queue1 to videoconvert")
            sys.exit(1)
        if not videoconvert.link(queue2):
            logger.error("Error linking videoconvert to queue2")
            sys.exit(1)

        ghostpad_sink = Gst.GhostPad.new("sink", queue1.get_static_pad("sink"))
        g_bin.add_pad(ghostpad_sink)
        ghostpad_src = Gst.GhostPad.new("src", queue2.get_static_pad("src"))
        g_bin.add_pad(ghostpad_src)
    else:
        logger.error("Unsupported output protocol")
        sys.exit(1)

    return g_bin

def update_encoder_property(pipeline, prop, value):
    if encoder := pipeline.get_by_name('encoder'):
        logger.info(f'Updating bitrate on encoder to {value}')
        encoder.set_property(prop, value)
    else:
        logger.warning("No encoder found, properties won't be updated")

def merge_tags(old_tags: str, new_tags: str) -> str:
    """
    Receives two tags list as string and returns a Gst.TagList
    with the merged tags
    """
    new_tags_list = Gst.TagList.new_from_string(new_tags)
    if old_tags is not None:
        old_tags_list = Gst.TagList.new_from_string(old_tags)
        merged_tags = new_tags_list.merge(
            old_tags_list,
            Gst.TagMergeMode.KEEP
        )
    else:
        merged_tags = new_tags_list

    return merged_tags.to_string()

def update_tags(pipeline, new_tags: str):
    """
    Adds a buffer to the appsrc containing the video tags
    """
    logger.info(f'New tags received: {new_tags}. Updating pipeline')
    # NOTE: we expect an element called 'taginject' on the pipeline
    taginject = pipeline.get_by_name('taginject')
    if not taginject:
        logger.warning("No taginject element found, video tags won't be injected")
    else:
        logger.info(f'Updating tags to {new_tags}')
        # We need to iterate and parse the tags manually because taginject
        # doesn't support a direct taglist.to_string()
        tags_array = []
        def taglist_iterator(list, tag, _):
            nonlocal tags_array
            if tag == 'taglist':
                # Remove taglist from the string
                return
            n_tag_values = list.get_tag_size(tag)
            if n_tag_values > 1: logger.warning(f'Some values will be lost for tag: {tag}')
            tag_value = list.get_value_index(tag, 0) # A tag can have several values
            if tag == 'datetime':
                # Convert Gst.DateTime to string
                tag_value = tag_value.to_iso8601_string()
            if isinstance(tag_value, str):
                tag_value = f'"{tag_value}"'
            tags_array.append(f'{tag}={tag_value}')
            if tag == 'bitrate':
                # Update the encoder bitrate
                update_encoder_property(pipeline, 'bitrate', tag_value)

        Gst.TagList.new_from_string(new_tags).foreach(taglist_iterator, None)
        sanitized_tags_string = ','.join(tags_array)
        taginject.set_property("tags", sanitized_tags_string)

class Output:
    def __init__(self):
        self.__pipeline : Gst.Pipeline = None
        self.__loop : GLib.MainLoop = None
        self.__tags : str = None

    def new_pipeline(self, caps):
        """
        Creates a pipeline for the given capbilities and starts it
        """
        config = Config(None)
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
        pipeline_appsrc.set_property("max-bytes", 1000000000) # 1 Gb of queue size

        # We output the size and framerate from the original video.
        # However, the output always receives raw RGB from the input
        original_caps = Gst.Caps.from_string(caps)
        caps_structure = original_caps.get_structure(0) # There is usually just one structure on the caps
        caps_width = caps_structure.get_value('width')
        caps_height = caps_structure.get_value('height')
        caps_framerate = caps_structure.get_fraction('framerate')
        caps_framerate_str = f"{caps_framerate.value_numerator}/{caps_framerate.value_denominator}"
        input_caps = Gst.Caps.from_string(f"video/x-raw,format=RGB,width={caps_width},height={caps_height},framerate={caps_framerate_str}")
        pipeline_appsrc.set_property("caps", input_caps)

        pipeline.add(pipeline_appsrc)
        pipeline.add(pipeline_sink)
        processing_bin = get_processing_bin(out_protocol, out_location)
        pipeline.add(processing_bin)

        if not pipeline_appsrc.link(processing_bin):
            logger.error("Error linking appsrc to the processing bin")
            sys.exit(1)
        if not processing_bin.link(pipeline_sink):
            logger.error("Error linking processing bin to sink")
            sys.exit(1)

        # Handle bus events on the main loop
        pipeline_bus = pipeline.get_bus()
        pipeline_bus.add_signal_watch()

        pipeline_bus.connect("message", on_bus_message, self)

        ret = pipeline.set_state(Gst.State.PLAYING) # Start pipeline
        if ret == Gst.StateChangeReturn.FAILURE:
            logger.error("Unable to set the pipeline to the playing state.")
            sys.exit(1)

        copy_timestamps = out_protocol != 'screen'
        # Run on every cicle of the event loop
        self.__glib_fetch_and_send_timeout = GLib.timeout_add(
            0, lambda: fetch_and_send(pipeline_appsrc, copy_timestamps)
        )

        self.__pipeline = pipeline

        if self.__tags is not None:
            # The input may have sent the tags before the pipeline is created,
            # (we create the pipeline when the input sends the caps).
            update_tags(self.__pipeline, self.__tags)

    def get_pipeline(self):
        return self.__pipeline

    def remove_pipeline(self):
        self.__pipeline.set_state(Gst.State.NULL)
        self.__pipeline = None

    def set_mainloop(self, loop: GLib.MainLoop):
        self.__loop = loop
    def get_mainloop(self):
        return self.__loop

    def add_tags(self, tags: str):
        self.__tags = merge_tags(self.__tags, tags)
        logger.info(f'Output tags updated to: {self.__tags}')
        if self.__pipeline is not None:
            # Update the tags of the pipeline every time we receive new ones
            update_tags(self.__pipeline, self.__tags)

def on_bus_message(bus: Gst.Bus, msg: Gst.Message, output: Output):
    """
    Callback to manage bus messages
    """
    mtype = msg.type
    if mtype == Gst.MessageType.EOS:
        logger.info("End of stream reached.")
        output.remove_pipeline()

        config = Config(None)
        if (config.get_output().get_video().get_uri_protocol() == 'file'
            or config.get_input().get_video().get_uri_protocol() == 'file'):
            # Stop after the first stream when using an input or output file.
            # We do not want to override the output file
            # and we can't get a new stream once the file ends
            output.get_mainloop().quit()
    elif mtype == Gst.MessageType.ERROR:
        err, debug = msg.parse_error()
        logger.error(f"Error received from element {msg.src.get_name()}: {err.message}")
        logger.error(f"Debugging information: {debug or 'none'}")
        output.get_mainloop().quit()
    elif mtype == Gst.MessageType.WARNING:
        err, debug = msg.parse_warning()
        logger.warning(f"Warning received from element {msg.src.get_name()}: {err.message}")
        logger.warning(f"Debugging information: {debug or 'none'}")

    return True

def handle_input_messages(output: Output):
    """
    Handles messages comming from the input component
    """
    m_socket = InputOutputSocket('r')
    raw_msg = m_socket.recv()
    if raw_msg is not None:
        try:
            msg = deserialize(raw_msg)
            if isinstance(msg, StreamCapsMsg):
                caps = msg.get_caps()
                # When new caps arrive, we create a new pipeline,
                # This handles changes on frame dimensions between streams
                logger.info(f'Creating new pipeline for caps: {caps}')
                output.new_pipeline(caps)
            elif isinstance(msg, StreamTagsMsg):
                tags = msg.get_tags()
                output.add_tags(tags)
        except Exception:
            logger.error('Stopping message handler:')
            traceback.print_exc()
            sys.exit(1)

    return True # Indicate the GLib timeout to retry on the next interval

def output(config_dict):
    update_logger_component('OUTPUT')
    config = Config(config_dict)
    update_logger_level(config.get_log_level())
    if not config.get_output().get_video().is_enabled():
        logger.info('Output video is disabled')
        return

    Gst.init(None)

    output = Output()
    loop = GLib.MainLoop()
    output.set_mainloop(loop)

    try:
        # Start socket listeners
        m_socket = InputOutputSocket('r')
        r_socket = OutputPullSocket()

        GLib.timeout_add(0, lambda: handle_input_messages(output))

        loop.run()
    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc()
        loop.quit()
    finally:
        logger.info('Closing pipeline')
        # Retrieve and close the sockets
        m_socket.close()
        r_socket.close()
        logger.info('Output finished.')
