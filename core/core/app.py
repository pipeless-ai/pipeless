from rich import print as rprint
import time

from .lib.decorators import timer
from .lib.stream import pipelines

class App():
    """
    Base class to handle an App workflow
    """

    def __init__(self, config):
        self.config = config
        self.ctx = {}

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

    @timer
    def __after(self):
        if callable(self.after):
            self.after(self.ctx)

    def start(self):
        # Create the streams
        media_pipeline = pipelines.MediaPipeline(self.config)
        in_video_buf = media_pipeline.get_input_video_buffer()
        out_video_buffer = media_pipeline.get_output_video_buffer()

        self.__before()

        while True:
            time.sleep(0.1)
            if in_video_buf.qsize() == 0:
                rprint("[yellow]No more frames to process in the input buffer[/yellow]")
                break
            else:
                video_frame = in_video_buf.get()
                video_frame = self.__pre_process(video_frame)
                video_frame = self.__process(video_frame)
                video_frame = self.__post_process(video_frame)

        self.__after()
