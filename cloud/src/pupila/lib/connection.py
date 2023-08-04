from functools import wraps
from pynng import Push0, Pull0, Timeout, Pair0
from pynng.exceptions import Closed as ClosedException

from src.pupila.lib.singleton import Singleton
from src.pupila.lib.config import Config
from src.pupila.lib.logger import logger

def send_error_handler(func):
    """
    Decorator to handle sending errors.
    """
    @wraps(func)
    def send_handler(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Timeout:
            logger.warning("Timeout sending message")
        except ClosedException as e:
            logger.error('Trying to write to a closed socket')
            # Forward to ensure resource cleanup
            raise ClosedException('The socket is closed!', e.errno)

    return send_handler

def recv_error_handler(func):
    """
    Decorator to handle reception errors.
    """
    @wraps(func)
    def recv_handler(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        except Timeout:
            logger.warning("Timeout waiting for message")
            return None
        except ClosedException as e:
            logger.error('Trying to read from a closed socket')
            # Forward to ensure resource cleanup
            raise ClosedException('The socket is closed!', e.errno)

    return recv_handler

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

    @send_error_handler
    def send(self, msg):
        self._socket.send(msg)

    @recv_error_handler
    def recv(self):
        return self._socket.recv()

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

    @send_error_handler
    def send(self, msg):
        self._socket.send(msg)

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

    @send_error_handler
    def send(self, msg):
        self._socket.send(msg)

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

    @recv_error_handler
    def recv(self):
        return self._socket.recv()

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

    @recv_error_handler
    def recv(self):
        return self._socket.recv()

    def close(self):
        self._socket.close()