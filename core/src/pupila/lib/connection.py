from functools import wraps
import signal
import sys
import time
from pynng import Push0, Pull0, Timeout, Pair0
from pynng.exceptions import Closed as ClosedException, TryAgain, ConnectionRefused

from pupila.lib.singleton import Singleton
from pupila.lib.config import Config
from pupila.lib.logger import logger

# Handle SIGNINT (ctrl+c) during sockets dialing blocking process
def exit(signum, frame):
    sys.exit()
signal.signal(signal.SIGINT, exit)

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
        except TryAgain:
            # For non-blocking calls
            logger.debug(f"[bright_yellow]No data written, try again on: {socket_name}[/bright_yellow]")
            return None
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
            logger.debug(f"[bright_yellow]No data to read, try again on: {socket_name}[/bright_yellow]")
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
            self._socket = Pair0()
            self._socket.send_timeout = send_timeout
            self._name = 'InputOutputSocket-Write'

            connected = False
            while not connected:
                try:
                    self._socket.dial(self._addr, block=True)
                    connected = True
                except ConnectionRefused:
                    logger.warning(f'[orange3]Connection to {self._addr} failed. Retrying...[/orange3]')
                    time.sleep(1)
        elif mode == 'r':
            self._socket = Pair0(listen=self._addr)
            self._socket.recv_timeout = read_timeout
            self._socket.recv_max_size = 0 # Unlimited receive size
            self._name = 'InputOutputSocket-Read'
        else:
            raise 'Wrong mode for InputOutputSocket'

    @send_error_handler
    def send(self, msg):
        # Blocking send call. We always want to ensure the messages
        # from input to output arrive because they change the pipelines
        self._socket.send(msg)

    @recv_error_handler
    def recv(self):
        # We can't block on receptions because limits the throughput
        return self._socket.recv(block=False)

    def close(self):
        self._socket.close()

    def get_socket_name(self):
        return self._name

class InputPushSocket(metaclass=Singleton):
    """
    nng push socket to push messages from the input to the workers
    """
    def __init__(self, timeout=500):
        config = Config(None) # Get the already existing config instance
        address = config.get_input().get_address()
        self._addr = f'tcp://{address.get_address()}'
        self._socket = Push0(listen=self._addr)
        self._socket.send_timeout = timeout
        self._socket.send_buffer_size = 180 # 3 seconds of 60 pfs video
        self._name = 'InputPushSocket'

    @send_error_handler
    def send(self, msg):
        # Non blocking send.
        # Don't worry if we miss a message from time to time
        self._socket.send(msg, block=False)

    def close(self):
        self._socket.close()

    def get_socket_name(self):
        return self._name

class OutputPushSocket(metaclass=Singleton):
    """
    nng push socket to push messages from the workers to the output
    """
    def __init__(self, timeout=500):
        config = Config(None) # Get the already existing config instance
        address = config.get_output().get_address()
        self._addr = f'tcp://{address.get_address()}'
        self._socket = Push0()
        self._socket.send_timeout = timeout
        self._socket.send_buffer_size = 180 # 3 seconds of 60 pfs video
        self._name = 'OutputPushSocket'

        connected = False
        while not connected:
            try:
                self._socket.dial(self._addr, block=True)
                connected = True
            except ConnectionRefused:
                logger.warning(f'[orange3]Connection to {self._addr} failed. Retrying...[/orange3]')
                time.sleep(1)

    @send_error_handler
    def send(self, msg):
        # Non blocking send.
        # Don't worry if we miss a message from time to time
        self._socket.send(msg, block=False)

    def close(self):
        self._socket.close()

    def get_socket_name(self):
        return self._name

class InputPullSocket(metaclass=Singleton):
    """
    nng pull socket to fetch messages from the input in the workers
    """
    def __init__(self, timeout=500):
        config = Config(None) # Get the already existing config instance
        address = config.get_input().get_address()
        self._addr = f'tcp://{address.get_address()}'
        self._socket = Pull0()
        self._socket.recv_timeout = timeout
        self._socket.recv_max_size = 0 # Unlimited receive size
        self._socket.recv_buffer_size = 180 # 3 seconds of 60 pfs video
        self._name = 'InputPullSocket'

        connected = False
        while not connected:
            try:
                self._socket.dial(self._addr, block=True)
                connected = True
            except ConnectionRefused:
                logger.warning(f'[orange3]Connection to {self._addr} failed. Retrying...[/orange3]')
                time.sleep(1)

    @recv_error_handler
    def recv(self):
        # Non blocking receive.
        # Don't worry if we miss a message from time to time
        return self._socket.recv(block=False)

    def close(self):
        self._socket.close()

    def get_socket_name(self):
        return self._name

class OutputPullSocket(metaclass=Singleton):
    """
    nng pull socket to fetch messages from the workers in the output
    """
    def __init__(self, timeout=500):
        config = Config(None) # Get the already existing config instance
        address = config.get_output().get_address()
        self._addr = f'tcp://{address.get_address()}'
        self._socket = Pull0(listen=self._addr)
        self._socket.recv_timeout = timeout
        self._socket.recv_max_size = 0 # Unlimited receive size
        self._socket.recv_buffer_size = 180 # 3 seconds of 60 pfs video
        self._name = 'OutputPullSocket'

    @recv_error_handler
    def recv(self):
        # Non blocking receive.
        # Don't worry if we miss a message from time to time
        return self._socket.recv(block=False)

    def close(self):
        self._socket.close()

    def get_socket_name(self):
        return self._name