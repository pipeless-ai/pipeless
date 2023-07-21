import ffmpeg
import numpy as np
import time
import multiprocessing
import os
from rich import print as rprint

class OutputStream():
    """
    Class that represents an output stream to a server.

    Builds the output stream from a sequence of audio and video frames
    """

    # Receives the RTMP URL where to send the output, the video parameters and
    # the audio stream that corresponds to the original video.
    def __init__(self, rtmp_url, video_buffer, video_stream_metadata, audio_buffer, audio_stream_metadata):
        """
        Receives the RTMP Url where to send the multimedia and the video and audio parameters.
        """

        video_fps = video_stream_metadata['fps']
        video_frame_width = video_stream_metadata['width']
        video_frame_height = video_stream_metadata['height']

        audio_codec = audio_stream_metadata['codec']
        audio_channels = audio_stream_metadata['channels']
        audio_sample_rate = audio_stream_metadata['sample_rate']
        audio_channel_layout = audio_stream_metadata['channel_layout']

        # Input buffers. Queues with the audio and video frames to mux
        self._audio_input_buffer = audio_buffer
        self._video_input_buffer = video_buffer

        ## We will provide video into stdin pipe and audio via named pipe, which does not write and read to filesystem
        self._audio_input_pipe_name = 'audio_pipe'
        try:
            os.mkfifo(self._audio_input_pipe_name)
        except FileExistsError:
            os.remove(self._audio_input_pipe_name)
            os.mkfifo(self._audio_input_pipe_name)

        self._audio_pipe_fd = os.open(self._audio_input_pipe_name, os.O_RDWR) # create the file descriptor

        video_input = ffmpeg.input('pipe:', format='rawvideo', pix_fmt='rgb24', s='{}x{}'.format(video_frame_width, video_frame_height)) # Video input
        audio_input = ffmpeg.input(self._audio_input_pipe_name, format='s16le', ac=audio_channels, ar=audio_sample_rate, channel_layout=audio_channel_layout)

        ffmpeg_command = (
            ffmpeg
            .output(
                video_input.video.filter('setpts', 'N/({}*TB)'.format(video_fps)), # Filter to create a constant frame frame rate when the original video has a variable rate (happens with low quality record devices)
                audio_input,
                rtmp_url,
                # Video params # TODO: set all these params from the input video metadata
                vcodec="libx264", f='flv', pix_fmt='yuv444p',# TODO (trivial): read this from the original video metadata
                preset='veryfast', r=video_fps,
                g=(video_fps * 2), # Introduce a keyframe every crf frames.
                crf=0, # Used by H.264/H.265 (libx264/libx265) codecs. Lower CRF produces higer quality but bigger file size. Usually 0-51
                # Audio params
                acodec=audio_codec, ac=audio_channels, ar=audio_sample_rate, bit_rate=128000,
                # loglevel='debug'
            )
        )
        self._ffmpeg_process = ffmpeg_command.overwrite_output().run_async(pipe_stdin=True)

        # NOTE: audio and video frames are syncing automatically thanks to the original timestamps. Once we modify audio, that won't happen

        self._pipe_audio_buffer_thread = multiprocessing.Process(
            target=self._read_audio,
        )
        self._pipe_audio_buffer_thread.daemon = True  # Ensures the thread ends with the program
        self._pipe_audio_buffer_thread.start()

        self._pipe_video_buffer_thread = multiprocessing.Process(
            target=self._read_video,
        )
        self._pipe_video_buffer_thread.daemon = True  # Ensures the thread ends with the program
        self._pipe_video_buffer_thread.start()

    def _read_audio(self):
        audio_pipe_fd = os.open(self._audio_input_pipe_name, os.O_RDWR)
        audio_write_pipe_size = os.fstat(audio_pipe_fd).st_blksize

        while True:
            try:
                audio_write_pipe_usage = os.fstat(audio_pipe_fd).st_size / audio_write_pipe_size
                if audio_write_pipe_usage < 0.8:
                    if not self._audio_input_buffer.empty():
                        audio_frame = self._audio_input_buffer.get()
                        os.write(audio_pipe_fd, audio_frame)
                    else:
                        # TODO: we need to identify when the video has ended, if not, processing the video faster could lead to premature stop
                        break
            except BlockingIOError:
                rprint('[yellow]WARN: Audio pipe blocked.[/yellow] Ignore this warning if it just happens from time to time')

    def _read_video(self):
        while True:
            if self._ffmpeg_process is not None:
                if not self._video_input_buffer.empty():
                    video_frame = self._video_input_buffer.get()
                    self._ffmpeg_process.stdin.write(video_frame.astype(np.uint8).tobytes())
                else:
                    # TODO: we need to identify when the video has ended, if not, processing the video faster could lead to premature stop
                    break

    # Release the streams we opened during instantiation
    def close(self):
        print('Cleaning up...')
        os.close(self._audio_pipe_fd)
        os.remove(self._audio_input_pipe_name)

        self._ffmpeg_process.stdin.close()
        self._ffmpeg_process.terminate()
        try:
            self._ffmpeg_process.wait(timeout=10)
        except:
            rprint('[yellow]Timeout expired while waiting the output video pipe to finish.[/yellow] Killing it...')
            self._ffmpeg_process.kill()  # Forcefully terminate the process
            print('Killed.')
