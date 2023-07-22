import queue

from .input import InputStream
from .output import OutputStream

class MediaPipeline():
    def __init__(self, config):
        in_stream_url = config['input']['video']['url']
        out_stream_url = config['output']['video']['url']

        self.__input_stream = InputStream(in_stream_url)
        video_stream_metadata = self.__input_stream.get_video_metadata()
        audio_stream_metadata = self.__input_stream.get_audio_metadata()

        self.__in_audio_buffer = self.__input_stream.get_audio_buffer()
        self.__in_video_buffer = self.__input_stream.get_video_buffer()
        # Create output buffers
        self.__out_video_buffer = queue.Queue()
        self.__out_audio_buffer = queue.Queue()

        self.__output_stream = OutputStream(
            out_stream_url,
            self.__out_video_buffer, video_stream_metadata,
            # TODO: we must pass out_audio_buffer once we support audio processing
            self.__in_audio_buffer, audio_stream_metadata,
        )

    def get_input_audio_buffer(self):
        return self.__in_audio_buffer
    def get_output_audio_buffer(self):
        return self.__out_audio_buffer
    def get_input_video_buffer(self):
        return self.__in_video_buffer
    def get_output_video_buffer(self):
        return self.__out_video_buffer

    def input_stream_is_active(self):
        return self.__input_stream.is_stream_active()
