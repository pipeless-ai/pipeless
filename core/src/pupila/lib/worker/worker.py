import importlib
import sys
import traceback
import numpy as np

from pupila.lib.connection import InputPullSocket, OutputPushSocket
from pupila.lib.logger import logger
from pupila.lib.messages import EndOfStreamMsg, RgbImageMsg, deserialize

def fetch_and_process(user_app):
    """
    Processes messages comming from the input
    Returns whether the current worker iteration should continue
    After a worker iteration the user app instance is reset
    """
    r_socket = InputPullSocket()
    raw_msg = r_socket.recv()
    if raw_msg is not None:
        msg = deserialize(raw_msg)
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
            updated_ndframe = user_app._PupilaApp__pre_process(updated_ndframe)
            updated_ndframe = user_app._PupilaApp__process(updated_ndframe)
            updated_ndframe = user_app._PupilaApp__post_process(updated_ndframe)

            msg.update_data(updated_ndframe)

            # Forward the message to the output
            s_socket = OutputPushSocket()
            s_socket.send(msg.serialize())
        elif isinstance(msg, EndOfStreamMsg):
            logger.info('Worker iteration finished. About to reset')
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

def worker(user_module_path):
    if not user_module_path:
        logger.error('Missing app .py file path')
        sys.exit(1)

    try:
        while True:
            # Infinite worker loop
            continue_worker = True
            user_app = load_user_module(user_module_path)
            user_app._PupilaApp__before()
            while continue_worker:
                continue_worker = fetch_and_process(user_app)
            user_app._PupilaApp__after()
    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc()
    finally:
        logger.info('Worker finished!')
        # Retreive and close the sockets
        logger.debug('Cleaning sockets')
        r_socket = InputPullSocket()
        r_socket.close()
        s_socket = OutputPushSocket()
        s_socket.close()