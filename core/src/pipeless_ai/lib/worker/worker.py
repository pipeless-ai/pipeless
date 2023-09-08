import importlib
import sys
import traceback
import numpy as np

from pipeless_ai.lib.plugins import exec_hook_with_plugins, inject_plugins
from pipeless_ai.lib.config import Config
from pipeless_ai.lib.connection import InputPullSocket, OutputPushSocket, WorkerReadySocket
from pipeless_ai.lib.logger import logger, update_logger_component, update_logger_level
from pipeless_ai.lib.messages import EndOfStreamMsg, RgbImageMsg, deserialize

def fetch_and_process(user_app):
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
            # TODO: we can use pynng recv_msg to get information about which pipe the message comes from, thus distinguish stream sources and route destinations
            #       Usefull to support several input medias to the same app
            height = msg.get_height()
            width = msg.get_width()
            data = msg.get_data()
            ndframe = np.ndarray(
                shape=(height, width, 3),
                dtype=np.uint8, buffer=data
            )

            # Execute frame processing
            updated_ndframe = ndframe
            updated_ndframe = exec_hook_with_plugins(user_app, 'pre_process', updated_ndframe)
            updated_ndframe = exec_hook_with_plugins(user_app, 'process', updated_ndframe)
            updated_ndframe = exec_hook_with_plugins(user_app, 'post_process', updated_ndframe)
            msg.update_data(updated_ndframe)

            if config.get_output().get_video().is_enabled():
                # Forward the message to the output
                s_socket.send(msg.serialize())
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
    Load the user app module from the path.
    Returns an instance of the user defined App class
    """
    spec = importlib.util.spec_from_file_location('user_app', path)
    user_app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(user_app_module)
    UserApp = getattr(user_app_module, 'App')
    user_app = UserApp()
    return user_app

def worker(config_dict, user_module_path):
    update_logger_component('WORKER')
    config = Config(config_dict)
    update_logger_level(config.get_log_level())

    if not user_module_path:
        logger.error('Missing app .py file path')
        sys.exit(1)

    plugins_dir = config.get_plugins().get_plugins_dir()
    plugins_order = config.get_plugins().get_plugins_order()

    logger.info('Notifying worker ready to input')
    w_socket = WorkerReadySocket('worker')
    w_socket.send(b'ready') # Notify the input that a worker is available

    try:
        while True:
            r_socket = InputPullSocket()
            if config.get_output().get_video().is_enabled():
                s_socket = OutputPushSocket()

            # Infinite worker loop
            continue_worker = True
            # Reset user app on every new stream
            user_app = load_user_module(user_module_path)
            inject_plugins(user_app, plugins_dir, plugins_order)
            exec_hook_with_plugins(user_app, 'before')
            while continue_worker:
                continue_worker = fetch_and_process(user_app)
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
        # Retrieve and close the sockets
        logger.debug('Cleaning sockets')
        r_socket.close()
        if config.get_output().get_video().is_enabled():
            s_socket.close()
        logger.info('Worker finished. Please wait for the output (if enabled).')
