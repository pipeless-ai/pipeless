from pynng import Push0, Pull0, Timeout

from .singleton import Singleton
from .config import Config
from .logger import logger

# TODO: create a InputBusSocket/OutputBusSocket to send metadata messages
#       to all connected workers in order to update the pipelines when the stream type changes

class InputPushSocket(metaclass=Singleton):
    """
    nng push socket to push messages from the input to the workers
    """
    def __init__(self):
        config = Config(None) # Get the already existing config instance
        address = config.get_input().get_address()
        self._addr = f'tcp://{address.get_address()}'
        self._socket = Push0(listen=self._addr)

    def send(self, msg):
        self.socket.send(msg)

class OutputPushSocket(metaclass=Singleton):
    """
    nng push socket to push messages from the workers to the output
    """
    def __init__(self):
        config = Config(None) # Get the already existing config instance
        address = config.get_output().get_address()
        self._addr = f'tcp://{address.get_address()}'
        self._socket = Push0(listen=self._addr)

    def send(self, msg):
        self.socket.send(msg)

class InputPullSocket(metaclass=Singleton):
    """
    nng pull socket to fetch messages from the input to the workers
    """
    def __init__(self):
        config = Config(None) # Get the already existing config instance
        address = config.get_input().get_address()
        self._addr = f'tcp://{address.get_address()}'
        self._socket = Pull0(listen=self._addr)

    def recv(self, timeout):
        try:
            return self.socket.recv(timeout=timeout)
        except Timeout:
            logger.warning("Timeout waiting for new frames")
            return None

class OutputPullSocket(metaclass=Singleton):
    """
    nng pull socket to fetch messages from the workers to the output
    """
    def __init__(self):
        config = Config(None) # Get the already existing config instance
        address = config.get_output().get_address()
        self._addr = f'tcp://{address.get_address()}'
        self._socket = Pull0(listen=self._addr)

    def recv(self, timeout):
        try:
            return self.socket.recv(timeout=timeout)
        except Timeout:
            logger.warning("Timeout waiting for new frames")
            return None
