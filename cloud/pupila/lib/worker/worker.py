import traceback
import pynng as nng
import numpy as np

import gi
gi.require_version('GObject', '2.0')
from gi.repository import GObject

from ..connection import InputPullSocket, OutputPushSocket
from ..logger import logger
from ..messages import load_msg, MsgType

# TODO: create a process to fetch from the bussocket and edit the pipeline when a metadata message arrives

def fetch_and_process():
    r_socket = InputPullSocket()
    raw_msg = r_socket.recv(1)
    msg = load_msg(raw_msg)
    
    if msg.type == MsgType.RGB_IMAGE:
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

def worker():
    try:
        loop = GObject.MainLoop()

        r_socket = InputPullSocket()
        r_socket_fd = r_socket.getsockopt(nng.NNG_OPT_RECVFD)
        r_channel = GObject.IOChannel(r_socket_fd)
        r_channel.add_watch(GObject.IO_IN, fetch_and_process)
        
        loop.run()
    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc()
        loop.quit()
    finally:
        logger.info('Worker finished!')