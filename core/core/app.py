import queue

from .lib.decorators import timer
from .lib.stream import pipelines
from .lib.logger import logger, update_logger_level

class App():
    """
    Base class to handle an App workflow
    """

    def __init__(self, config):
        self.config = config # TODO: validate config values (must be done on the CLI component)
        update_logger_level(config['log_level'])
        self.ctx = {}
        self.media_pipeline = pipelines.MediaPipeline(self.config)

    @timer
    def __before(self):
        if callable(self.before):
            self.before(self.ctx)

    @timer
    def __pre_process(self, frame):
        if callable(self.pre_process):
            self.pre_process(frame, self.ctx)

    @timer
    def __process(self, frame):
        if callable(self.process):
            self.process(frame, self.ctx)

    @timer
    def __post_process(self, frame):
        if callable(self.post_process):
            self.post_process(frame, self.ctx)

        # Put the buffer in queue for the output stream
        self.media_pipeline.get_output_video_buffer().put(frame)

    @timer
    def __after(self):
        if callable(self.after):
            self.after(self.ctx)

    def start(self):
        in_video_buf = self.media_pipeline.get_input_video_buffer()

        self.__before()

        while True:
            if in_video_buf.qsize() == 0 and not self.media_pipeline.input_stream_is_active():
                # The input stream has stopped and we have read all the frames that were added to the input buffer
                logger.info("[pruple]No more frames to process in the input buffer[/purple]")
                break
            else:
                try:
                    video_frame = in_video_buf.get(block=False)
                except queue.Empty:
                    continue
                video_frame = self.__pre_process(video_frame)
                video_frame = self.__process(video_frame)
                video_frame = self.__post_process(video_frame)

        self.__after()
