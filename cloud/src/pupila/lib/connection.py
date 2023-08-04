from pynng import Push0, Pull0, Timeout, Pair0

from src.pupila.lib.singleton import Singleton
from src.pupila.lib.config import Config
from src.pupila.lib.logger import logger

class InputOutputSocket(metaclass=Singleton):
    """
    nng socket to send messages from the input to the output
    """   
    def __init__(self, mode, send_timeout=1000, read_timeout=1000):
        """
        Parameters:
        - mode: 'w' for the input (write). 'r' for the output (read)
        """
        config = Config(None) # Get the already existing config instance
        address = config.get_input().get_address()
        # Make this connection to run on the provided port+1. 
        # The provided port is for other type of connection
        port = str(address.get_port() + 1)
        self._addr = f'tcp://{address.get_host()}:{port}'
        if mode == 'w':
            self._socket = Pair0(listen=self._addr)
            self._socket.send_timeout = send_timeout
        elif mode == 'r':
            self._socket = Pair0(listen=self._addr)
            self._socket.recv_timeout = read_timeout
        else:
            raise 'Wrong mode for InputOutputSocket'

    def send(self, msg):
        try:
            self._socket.send(msg)
        except Timeout:
            logger.warning("Timeout sending message")
    def recv(self):
        try:
            return self._socket.recv()
        except Timeout:
            # This function is used in a poll way, log timeouts on debug to avoid noise
            logger.debug("Timeout receiving metadata from input")
            return None
    def close(self):
        self._socket.close()

class InputPushSocket(metaclass=Singleton):
    """
    nng push socket to push messages from the input to the workers
    """
    def __init__(self, timeout=1000):
        config = Config(None) # Get the already existing config instance
        address = config.get_input().get_address()
        self._addr = f'tcp://{address.get_address()}'
        self._socket = Push0(listen=self._addr)
        self._socket.send_timeout = timeout

    def send(self, msg):
        try:
            self._socket.send(msg)
        except Timeout:
            logger.warning("Timeout sending message")
    def close(self):
        self._socket.close()

class OutputPushSocket(metaclass=Singleton):
    """
    nng push socket to push messages from the workers to the output
    """
    def __init__(self, timeout):
        config = Config(None) # Get the already existing config instance
        address = config.get_output().get_address()
        self._addr = f'tcp://{address.get_address()}'
        self._socket = Push0(listen=self._addr)
        self._socket.send_timeout = timeout

    def send(self, msg):
        try:
            self._socket.send(msg)
        except Timeout:
            logger.warning("Timeout sending message")
    def close(self):
        self._socket.close()

class InputPullSocket(metaclass=Singleton):
    """
    nng pull socket to fetch messages from the input to the workers
    """
    def __init__(self, timeout=1000):
        config = Config(None) # Get the already existing config instance
        address = config.get_input().get_address()
        self._addr = f'tcp://{address.get_address()}'
        self._socket = Pull0(dial=self._addr)
        self._socket.recv_timeout = timeout

    def recv(self):
        try:
            return self._socket.recv()
        except Timeout:
            logger.warning("Timeout waiting for new frames")
            return None
    def close(self):
        self._socket.close()

class OutputPullSocket(metaclass=Singleton):
    """
    nng pull socket to fetch messages from the workers to the output
    """
    def __init__(self, timeout=1000):
        config = Config(None) # Get the already existing config instance
        address = config.get_output().get_address()
        self._addr = f'tcp://{address.get_address()}'
        self._socket = Pull0(dial=self._addr)
        self._socket.recv_timeout = timeout

    def recv(self):
        try:
            return self._socket.recv()
        except Timeout:
            logger.warning("Timeout waiting for new frames")
            return None
    def close(self):
        self._socket.close()