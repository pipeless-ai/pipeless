from pynng import Push0, Pull0, Timeout

from .singleton import Singleton
from .config import Config
from .logger import logger

class PushSocket(metaclass=Singleton):
    """
    nng push socket to share messages
    """
    def __init__(self):
        config = Config(None) # Get the already existing config instance
        address = config.get_input().get_address()
        self._addr = f'tcp://{address.get_address()}'
        self._socket = Push0(listen=self._addr)

    def send(self, msg):
        self.socket.send(msg)

class PullSocket(metaclass=Singleton):
    """
    nng pull socket to share messages
    """
    def __init__(self):
        config = Config(None) # Get the already existing config instance
        address = config.get_input().get_address()
        self._addr = f'tcp://{address.get_address()}'
        self._socket = Pull0(listen=self._addr)

    def recv(self):
        try:
            return self.socket.recv()
        except Timeout:
            return None
