from pynng import Push0, Pull0, Timeout, Pair0

from .singleton import Singleton
from .config import Config
from .logger import logger

class InputOutputSocket(metaclass=Singleton):
    """
    nng socket to send messages from the input to the output
    """   
    def __init__(self, mode):
        """
        Parameters:
        - mode: 'w' for the input (write). 'r' for the output (read)
        """
        config = Config(None) # Get the already existing config instance
        address = config.get_input().get_address()
        # Make this connection to run on the provided port+1. 
        # The provided port is for other type of connection
        self._addr = f'tcp://{address.get_host():{address.get_port() + 1}}'
        if mode == 'w':
            self._socket = Pair0(listen=self._addr)
        elif mode == 'r':
            self._socket = Pair0(listen=self._addr)
        else:
            raise 'Wrong mode for InputOutputSocket'

    def send(self, msg):
        self.socket.send(msg)
    def recv(self, timeout):
        try:
            return self.socket.recv(timeout=timeout)
        except Timeout:
            logger.warning("Timeout receiving metadata from input")
            return None

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