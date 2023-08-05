from functools import wraps
from pynng import Push0, Pull0, Timeout, Pair0
from pynng.exceptions import Closed as ClosedException, TryAgain

from src.pupila.lib.singleton import Singleton
from src.pupila.lib.config import Config
from src.pupila.lib.logger import logger

def send_error_handler(func):
    """
    Decorator to handle sending errors.
    """
    @wraps(func)
    def send_handler(*args, **kwargs):
        socket_name = args[0].get_socket_name()
        try:
            func(*args, **kwargs)
        except Timeout:
            logger.warning(f"Timeout sending message on socket: {socket_name}")
        except ClosedException as e:
            logger.error(f"Trying to write to a closed socket: {socket_name}")
            # Forward to ensure resource cleanup
            raise ClosedException(f"The socket {socket_name} is closed!", e.errno)

    return send_handler

def recv_error_handler(func):
    """
    Decorator to handle reception errors.
    """
    @wraps(func)
    def recv_handler(*args, **kwargs):
        socket_name = args[0].get_socket_name()
        try:
            result = func(*args, **kwargs)
            return result
        except Timeout:
            logger.warning(f"Timeout waiting for message on socket: {socket_name}")
            return None
        except TryAgain:
            # For non-blocking calls
            logger.debug(f"No data to read, try again on: {socket_name}")
            return None
        except ClosedException as e:
            logger.error(f"Trying to read from a closed socket: {socket_name}")
            # Forward to ensure resource cleanup
            raise ClosedException(f"The socket {socket_name} is closed!", e.errno)

    return recv_handler

class InputOutputSocket(metaclass=Singleton):
    """
    nng socket to send messages from the input to the output
    """
    def __init__(self, mode, send_timeout=100, read_timeout=100):
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
            self._name = 'InputOutputSocket-Write'
        elif mode == 'r':
            self._socket = Pair0(dial=self._addr)
            self._socket.recv_timeout = read_timeout
            self._name = 'InputOutputSocket-Read'
        else:
            raise 'Wrong mode for InputOutputSocket'

    @send_error_handler
    def send(self, msg):
        self._socket.send(msg)

    @recv_error_handler
    def recv(self):
        return self._socket.recv(block=False)

    def close(self):
        self._socket.close()

    def get_socket_name(self):
        return self._name

class InputPushSocket(metaclass=Singleton):
    """
    nng push socket to push messages from the input to the workers
    """
    def __init__(self, timeout=100):
        config = Config(None) # Get the already existing config instance
        address = config.get_input().get_address()
        self._addr = f'tcp://{address.get_address()}'
        self._socket = Push0(listen=self._addr)
        self._socket.send_timeout = timeout
        self._name = 'InputPushSocket'

    @send_error_handler
    def send(self, msg):
        self._socket.send(msg)

    def close(self):
        self._socket.close()

    def get_socket_name(self):
        return self._name

class OutputPushSocket(metaclass=Singleton):
    """
    nng push socket to push messages from the workers to the output
    """
    def __init__(self, timeout=100):
        config = Config(None) # Get the already existing config instance
        address = config.get_output().get_address()
        self._addr = f'tcp://{address.get_address()}'
        self._socket = Push0(listen=self._addr)
        self._socket.send_timeout = timeout
        self._name = 'OutputPushSocket'

    @send_error_handler
    def send(self, msg):
        self._socket.send(msg)

    def close(self):
        self._socket.close()

    def get_socket_name(self):
        return self._name

class InputPullSocket(metaclass=Singleton):
    """
    nng pull socket to fetch messages from the input to the workers
    """
    def __init__(self, timeout=100):
        config = Config(None) # Get the already existing config instance
        address = config.get_input().get_address()
        self._addr = f'tcp://{address.get_address()}'
        self._socket = Pull0(dial=self._addr)
        self._socket.recv_timeout = timeout
        self._name = 'InputPullSocket'

    @recv_error_handler
    def recv(self):
        return self._socket.recv(block=False)

    def close(self):
        self._socket.close()

    def get_socket_name(self):
        return self._name

class OutputPullSocket(metaclass=Singleton):
    """
    nng pull socket to fetch messages from the workers to the output
    """
    def __init__(self, timeout=100):
        config = Config(None) # Get the already existing config instance
        address = config.get_output().get_address()
        self._addr = f'tcp://{address.get_address()}'
        self._socket = Pull0(dial=self._addr)
        self._socket.recv_timeout = timeout
        self._name = 'OutputPullSocket'

    @recv_error_handler
    def recv(self):
        return self._socket.recv(block=False)

    def close(self):
        self._socket.close()

    def get_socket_name(self):
        return self._name