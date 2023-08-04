import traceback
import select
import pynng as nng
import numpy as np

import gi
gi.require_version('GObject', '2.0')
gi.require_version('Gio', '2.0')
gi.require_version('GLib', '2.0')
from gi.repository import Gio, GLib

from src.pupila.lib.connection import InputPullSocket, OutputPushSocket
from src.pupila.lib.logger import logger
from src.pupila.lib.messages import load_msg, MsgType

# TODO: create a process to fetch from the bussocket and edit the pipeline when a metadata message arrives

def fetch_and_process():
    r_socket = InputPullSocket()
    raw_msg = r_socket.recv()
    if raw_msg is not None:
        msg = load_msg(raw_msg)
        if msg.type == MsgType.RGB_IMAGE:
            # TODO: we can use pynng recv_msg to get information about which pipe the message comes from, thus distinguish stream sources and route destinations
            #       Usefull to support several input medias to the same app 
            height = msg.get_height()
            width = msg.get_wigth()
            data = msg.get_data()
            ndframe = np.ndarray(
                shape=(height, width, 3),
                dtype=np.uint8, buffer=data
            )

            # TODO: process message with user defined methods
            #       Is ndframe conversion required? If it isn't we can save it
            updated_ndframe = ndframe

            msg.update_data(updated_ndframe.tobytes())

            # Forward the message to the output
            s_socket = OutputPushSocket()
            s_socket.send(msg.serialize())
        else:
            logger.error(f'Unsupported message type: {msg.type}')
            return False # Indicate GLib to not run the function again

    return True # Indicate the GLib timeout to retry on the next interval

def worker():
    try:
        while True:
            fetch_and_process()
        # GLib.timeout_add(0, on_socket_readable)

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