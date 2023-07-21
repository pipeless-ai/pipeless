import ffmpeg
import numpy as np
import time
import multiprocessing
import os
from rich import print as rprint

class InputStream():
    """
    Read multimedia from a provided input source and split video and audio
    """

    def __init__(self, rtmp_url):
        """
        When instantiating this class it will wait until the input stream has content to be read.
        """
        self._video_buffer = multiprocessing.Queue() # TODO: this could end into an out-of-memory issue if we fail to process images. We should specify a maxsize
        self._audio_buffer = multiprocessing.Queue()

        self._in_stream = ffmpeg.input(rtmp_url)

        self._in_stream_video = (
            self._in_stream.video
            .output('pipe:', format='rawvideo', pix_fmt='rgb24')
            .run_async(pipe_stdout=True)
        )

        self._in_stream_audio = (
            self._in_stream.audio
            .output('pipe:', format='s16le')
            .run_async(pipe_stdout=True)
        )

        rprint(f"Checking input source: [purple]{rtmp_url}[/purple]")
        probe = ffmpeg.probe(rtmp_url)

        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        print('Input video metadata:', video_stream)
        self._in_stream_video_metadata = {
            'width': int(video_stream['width']),
            'height': int(video_stream['height']),
            'fps': eval(video_stream['avg_frame_rate']),
        }
        rprint(f"[green]Input video FPS: {self._in_stream_video_metadata['fps']}[/green]")

        audio_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)
        print('Input audio metadata:', audio_stream)
        self._in_stream_audio_metadata = {
            'channels': int(audio_stream['channels']),
            'codec': audio_stream['codec_name'],
            'sample_rate': int(audio_stream['sample_rate']),
            'channel_layout': audio_stream['channel_layout'],
            'bit_rate': audio_stream['bit_rate'],
        }

        # Process that reads video and fills the video buffer
        self._read_stream_video_process = multiprocessing.Process(
            target=self._read_stream_video_bg,
            args=(self._in_stream_video_metadata['width'], self._in_stream_video_metadata['height'])
        )
        self._read_stream_video_process.daemon = True
        self._read_stream_video_process.start()
        # Process that reads audio and fills the audio buffer
        self._read_stream_audio_process = multiprocessing.Process(
            target=self._read_stream_audio_bg,
            # 16 below comes from s16le (16 bits). TODO(miguelaeh): this depends on the input format
            args=(self._in_stream_audio_metadata['channels'], self._in_stream_audio_metadata['sample_rate'], 16)
        )
        self._read_stream_audio_process.daemon = True
        self._read_stream_audio_process.start()

    # Read the video stream and store frames in the internal buffer.
    def _read_stream_video_bg(self, frame_width, frame_height):
        frame_size = frame_width * frame_height * 3
        reconnect_count = 0
        while True:
            in_bytes = self._in_stream_video.stdout.read(frame_size)
            if len(in_bytes) > 0:
                in_frame = (
                    np
                    .frombuffer(in_bytes, np.uint8)
                    .reshape([frame_height, frame_width, 3])
                )
                self._video_buffer.put(in_frame)
            else:
                # TODO(miguelaeh): setup a signal to indicate the end of streaming, so we can handle reconnections
                print('WARNING: got 0 bytes reading video from the input stream. It could be a temporal cut.')
                if (reconnect_count > 5):
                    print('15 seconds witohout input data, stopping.')
                else:
                    print('Waiting 3 seconds to try again...')
                    time.sleep(3)
                    reconnect_count += 1

    # Read the audio stream and store frames in the internal buffer.
    # Unlike for video, We store raw bytes, becasue we won't transform them
    def _read_stream_audio_bg(self, channels, sample_rate, bit_depth):
        byte_depth = int(bit_depth / 8)
        frame_size = int(channels * byte_depth)
        while True:
            in_bytes = self._in_stream_audio.stdout.read(frame_size)
            if len(in_bytes) > 0:
                # TODO(miguelaeh): to process audio we should decode the frame
                #in_frame = (
                #    np
                #    .frombuffer(in_bytes, np.uint8) # NOTE: 16 because of bit-depth
                #    .reshape([channels, byte_depth])
                #)
                #self._audio_buffer.put(in_frame)
                self._audio_buffer.put(in_bytes)
            else:
                # TODO(miguelaeh): setup a signal to indicate the end of streaming, so we can handle reconnections
                print('WARNING: got 0 bytes reading audio from the input stream. It could be a temporal cut.')
                if (reconnect_count > 5):
                    print('15 seconds witohout input data, stopping.')
                else:
                    print('Waiting 3 seconds to try again...')
                    time.sleep(3)
                    reconnect_count += 1

    # Returns input video metadata
    def get_video_metadata(self):
        return self._in_stream_video_metadata
    # Returns input audio metadata
    def get_audio_metadata(self):
        return self._in_stream_audio_metadata

    # Returns the buffer with audio frames
    def get_audio_buffer(self):
        return self._audio_buffer

    def get_video_buffer(self):
        return self._video_buffer

    def close(self):
        # Close video resources
        if self._read_stream_video_process.is_alive():
            try:
                self._read_stream_video_process.join(timeout=1)
            except:
                print('Failed stopping read stream video thread')

        # TODO(miguelaeh): sometimes closing the stdout gets stuck
        self._in_stream_video.stdout.close()
        self._in_stream_video.terminate()
        try:
            self._in_stream_video.wait(timeout=10)
        except:
            print('Timeout expired while waiting the ffmpeg video pipe to finish. Killing it...')
            self._in_stream_video.kill()  # Forcefully terminate the process
            print('Killed.')
