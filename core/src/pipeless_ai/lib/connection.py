from functools import wraps
import signal
import sys
import time
import pynng
from pynng import Push0, Pull0, Timeout, Pair0
from pynng.exceptions import Closed as ClosedException, TryAgain, ConnectionRefused

from pipeless_ai.lib.singleton import Singleton
from pipeless_ai.lib.config import Config
from pipeless_ai.lib.logger import logger

# Hack. Override pynng default logger to use our custom one.
pynng.nng.logger = logger

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
            return True # Inidicate data was sent
        except Timeout:
            logger.warning(f"Timeout sending message on socket: {socket_name}")
            return False # Indicate no data was sent
        except TryAgain:
            # For non-blocking calls
            logger.debug(f"[bright_yellow]No data written, try again on: {socket_name}[/bright_yellow]")
            return False # Inidicate no data was sent
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

def wait_socket_dial(socket, addr):
    '''
    Waits until the socket connects to the provided addr
    '''
    connected = False
    while not connected:
        try:
            socket.dial(addr, block=True)
            connected = True
        except ConnectionRefused:
            logger.warning(f'[orange3]Connection to {addr} failed. Connection Refushed. Retrying...[/orange3]')
            time.sleep(1)
        except TryAgain:
            logger.warning(f'[orange3]Connection to {addr} failed. Try Again. Retrying...[/orange3]')
            time.sleep(1)
        except Exception as e:
            logger.error(f'[red]Failed to connect to {addr}. {e}')
            sys.exit(1)

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
        address = config.get_output().get_address()
        # Make this connection to run on the provided port+1.
        # The provided port is for other type of connection
        port = str(address.get_port() + 1)
        self._addr = f'tcp://{address.get_host()}:{port}'
        if mode == 'w':
            self._socket = Pair0()
            self._socket.send_timeout = send_timeout
            self._name = 'InputOutputSocket-Write'

            wait_socket_dial(self._socket, self._addr)
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

    @send_error_handler
    def __block_send(self, msg):
        # Blocking send, we must be sure the message is sent
        self._socket.send(msg)
    def ensure_send(self, msg):
        while not self.__block_send(msg): logger.warning('Retrying send...')

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

        wait_socket_dial(self._socket, self._addr)

    @send_error_handler
    def send(self, msg):
        # Non blocking send.
        # Don't worry if we miss a message from time to time
        self._socket.send(msg, block=False)

    @send_error_handler
    def __block_send(self, msg):
        # Blocking send, we must be sure the message is sent
        self._socket.send(msg)
    def ensure_send(self, msg):
        while not self.__block_send(msg): logger.warning('Retrying send...')

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
        self._socket.recv_buffer_size = config.get_worker().get_recv_buffer_size()
        self._name = 'InputPullSocket'

        wait_socket_dial(self._socket, self._addr)

    @recv_error_handler
    def recv(self):
        # Non blocking receive.
        # Returns data immediatly or raises TryAgain
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
        out_config = config.get_output()
        address = out_config.get_address()
        self._addr = f'tcp://{address.get_address()}'
        self._socket = Pull0(listen=self._addr)
        self._socket.recv_timeout = timeout
        self._socket.recv_max_size = 0 # Unlimited receive size
        self._socket.recv_buffer_size = out_config.get_recv_buffer_size()
        self._name = 'OutputPullSocket'

    @recv_error_handler
    def recv(self):
        # Non blocking receive.
        # Returns data immediatly or raises TryAgain
        return self._socket.recv(block=False)

    def close(self):
        self._socket.close()

    def get_socket_name(self):
        return self._name

class WorkerReadySocket(metaclass=Singleton):
    """
    Allows the input to wait for the first worker before starting to send data
    When the worker needs to install user packages it takes longer to start
    and the data send by the input is lost if we don't wait for at least the first worker
    """
    def __init__(self, mode):
        """
        Parameters:
        - mode: 'input' for the input. 'worker' for the worker
        """
        config = Config(None) # Get the already existing config instance
        address = config.get_input().get_address()
        # Make this connection to run on the provided port+2.
        # The provided port is for other type of connection
        port = str(address.get_port() + 2)
        self._addr = f'tcp://{address.get_host()}:{port}'
        if mode == 'worker':
            self._socket = Pair0()
            self._name = 'WorkerReadySocket-Worker'

            wait_socket_dial(self._socket, self._addr)
        elif mode == 'input':
            self._socket = Pair0(listen=self._addr)
            self._name = 'WorkerReadySocket-Input'
        else:
            raise 'Wrong mode for WorkerReadySocket'

    @send_error_handler
    def send(self, msg):
        # Blocking send call. We always want to ensure the messages
        # from input to output arrive because they change the pipelines
        self._socket.send(msg)

    @recv_error_handler
    def recv(self):
        # Only the input will receive, and once the first worker send, we won't receive again
        # so we create a blocking call
        return self._socket.recv()

    def close(self):
        self._socket.close()

    def get_socket_name(self):
        return self._name
