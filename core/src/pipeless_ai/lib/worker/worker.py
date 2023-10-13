from collections import deque
import importlib
import math
import sys
import time
import traceback
import numpy as np

from pipeless_ai.lib.plugins import exec_hook_with_plugins, inject_plugins
from pipeless_ai.lib.config import Config
from pipeless_ai.lib.connection import InputPullSocket, OutputPushSocket, WorkerReadySocket
from pipeless_ai.lib.logger import logger, update_logger_component, update_logger_level
from pipeless_ai.lib.messages import EndOfStreamMsg, RgbImageMsg, deserialize
from pipeless_ai.lib.worker.inference.utils import get_inference_session

class ProcessingMetrics():
    '''
    This class is used to maintain some internal metrics to control when to process
    a frame depending on the stream metrics
    '''
    def __init__(self):
        # FIFO queue of 4 values to only take into account the most recent processing times
        self.fifo_list = deque([], maxlen=4)
        self.n_frames_skipped = 0
        self.previous_inference_results = None
    def add_proc_time(self, proc_time):
        self.fifo_list.append(proc_time)
        self.n_frames_skipped = 0
    def get_avg_time(self) -> float:
        fifo_len = len(self.fifo_list)
        return 0 if fifo_len == 0 else sum(self.fifo_list) / fifo_len
    def count_skipped_frame(self):
        self.n_frames_skipped += 1
    def should_skip_frame(self, fps) -> bool:
        f_interval = 1 / fps
        p_space = math.ceil(self.get_avg_time() / f_interval)
        should_process_frame = self.n_frames_skipped >= p_space
        return not should_process_frame

    # The following is not about metrics, but adding here for ease
    def set_previous_inference_results(self, results):
        self.previous_inference_results = results
    def get_previous_inference_results(self):
        return self.previous_inference_results

def fetch_and_process(user_app, inference_session, processing_metrics: ProcessingMetrics):
    """
    Processes messages comming from the input
    Returns whether the current worker iteration should continue
    After a worker iteration the user app instance is reset
    """
    config = Config(None)
    r_socket = InputPullSocket()
    raw_msg = r_socket.recv()
    if raw_msg is not None:
        msg = deserialize(raw_msg)
        if config.get_output().get_video().is_enabled():
            s_socket = OutputPushSocket()
        if isinstance(msg, RgbImageMsg):
            start_processing_time = msg.get_input_time()
            # TODO: we can use pynng recv_msg to get information about which pipe the message comes from, thus distinguish stream sources and route destinations
            #       Usefull to support several input medias to the same app
            height = msg.get_height()
            width = msg.get_width()
            data = msg.get_data()
            ndframe = np.ndarray(
                shape=(height, width, 3),
                dtype=np.uint8, buffer=data
            )
            fps = msg.get_fps()

            # We work with numpy views of the array to avoid complete copying, which is very slow.
            # Set original frame as non writable to raise execption if modified
            ndframe.flags.writeable = False
            user_app.original_frame = ndframe.view() # View of the original frame

            original_ndframe = ndframe.view() # This view will be passed to the user code

            should_skip_process_hook = config.get_worker().get_skip_frames() and processing_metrics.should_skip_frame(fps)

            # Inject into the user app so the user has control on what the pre-process and post-process run when the frame is skipped
            # For example, if you are mesuring the speed of an object, you may need to
            # count the frame but you can save other pre-processing parts because the frame won't be processed
            # TODO: should we create some kind of frame metadata that persists among different stages for multistage applications?
            #       after all, stages usually depend on the results of the previous ones.
            user_app.skip_frame = should_skip_process_hook

            # User pre-processing
            preproc_out = exec_hook_with_plugins(user_app, 'pre_process', original_ndframe)
            # By default, the post-process hook will receive the original frame instead of the pre-process output since the
            # pre-process output is usually not an image but the inference model input.
            if should_skip_process_hook:
                processing_metrics.count_skipped_frame()
                user_app.inference.results = processing_metrics.get_previous_inference_results()
                proc_out = original_ndframe
            else:
                if inference_session:
                    # TODO: we could run inference in batches
                    inference_result = inference_session.run([preproc_out])
                    processing_metrics.set_previous_inference_results(inference_result)
                    user_app.inference.results = inference_result # Embed the inference results into the user application
                    proc_out = original_ndframe
                else:
                    proc_out = exec_hook_with_plugins(user_app, 'process', preproc_out)

            postproc_out = exec_hook_with_plugins(user_app, 'post_process', proc_out)
            msg.update_data(postproc_out)

            if config.get_output().get_video().is_enabled():
                # Forward the message to the output
                s_socket.send(msg.serialize())

            if not should_skip_process_hook:
                # Update the metrics with the processed frame
                processing_time = time.time() - start_processing_time
                processing_metrics.add_proc_time(processing_time)
                if config.get_worker().get_show_exec_time():
                    logger.info(f'Application took {processing_time * 1000:.3f} ms to run for the frame')

        elif isinstance(msg, EndOfStreamMsg):
            logger.info('Worker iteration finished. Notifying output. About to reset worker')
            if config.get_output().get_video().is_enabled():
                # Forward the message to the output
                s_socket.ensure_send(raw_msg)
            return False # Reset worker
        else:
            logger.error(f'Unsupported message type: {msg.type}')
            sys.exit(1)

    return True # Continue the current worker execution

def load_user_module(path):
    """
    Load the user app module from the path. The path must be a directory containing app.py
    Returns an instance of the user defined App class
    """
    sys.path.append(path) # Add to the Python path to allow imports
    spec = importlib.util.spec_from_file_location('user_app', f'{path}/app.py')
    user_app_module = importlib.util.module_from_spec(spec)
    sys.modules['user_app'] = user_app_module # Allows to pickle the App class
    try:
        spec.loader.exec_module(user_app_module)
    except Exception as e:
        logger.error(e)
        sys.exit(1)
    UserApp = getattr(user_app_module, 'App')
    return UserApp()

def worker(config_dict, user_module_path):
    update_logger_component('WORKER')
    config = Config(config_dict)
    update_logger_level(config.get_log_level())

    if not user_module_path:
        logger.error('Missing app .py file path')
        sys.exit(1)

    plugins_dir = config.get_plugins().get_plugins_dir()
    plugins_order = config.get_plugins().get_plugins_order()

    inference_session = get_inference_session(config)
    user_app = load_user_module(user_module_path)
    inject_plugins(user_app, plugins_dir, plugins_order)

    # It confuses people if you are able to implement process when
    # using model inference because the inference is the processing
    if inference_session:
        if hasattr(user_app, 'process'):
            logger.error("The process hook must not be implemented when using model inference. Use 'post_process' instead.")
            sys.exit(1)
        for plugin_id, plugin in vars(user_app.plugins).items():
            if hasattr(plugin, 'before_process') or hasattr(plugin, 'after_process'):
                logger.error(f"The plugin '{plugin_id}' implements hooks for 'process' hook which must not be implemented when using model inference. You can remove it or contact the author of the plugin to evaluate moving the code into 'pre-process' or 'post-process'")
                sys.exit(1)

    if config.get_worker().get_enable_profiler():
        user_app._PipelessApp__enable_profiler()

    logger.info('Worker ready! Notifying input')
    w_socket = WorkerReadySocket('worker')
    w_socket.ensure_send(b'ready') # Notify the input that a worker is available

    try:
        while True:
            r_socket = InputPullSocket()
            if config.get_output().get_video().is_enabled():
                s_socket = OutputPushSocket()

            exec_hook_with_plugins(user_app, 'before')

            processing_metrics = ProcessingMetrics()
            # Stream loop
            continue_worker = True
            while continue_worker:
                continue_worker = fetch_and_process(user_app, inference_session, processing_metrics)

            exec_hook_with_plugins(user_app, 'after')

            if (config.get_output().get_video().get_uri_protocol() == 'file'
                or config.get_input().get_video().get_uri_protocol() == 'file'):
                # Stop after the first stream when using an input or output file.
                # We do not want to override the output file
                # and we can't get a new stream once the file ends
               break

    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc()
    finally:
        user_app._PipelessApp__print_profiler_stats()
        # Retrieve and close the sockets
        logger.debug('Cleaning sockets')
        r_socket.close()
        if config.get_output().get_video().is_enabled():
            s_socket.close()
        logger.info('Worker finished. Please wait for the output (if enabled).')
