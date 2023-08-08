import concurrent.futures
import sys
import time

from src.pupila.lib.input import input
from src.pupila.lib.output import output
from src.pupila.lib.worker import worker
from src.pupila.lib.logger import logger, update_logger_level
from src.pupila.lib.config import Config

def run_all():
    # TODO: Move this into the CLI component
    executor = concurrent.futures.ProcessPoolExecutor()
    t_input = executor.submit(input.input)
    time.sleep(2) # Allow to create sockets
    t_output = executor.submit(output.output)
    time.sleep(2) # Allow to create sockets
    t_worker = executor.submit(worker.worker)
    concurrent.futures.wait([t_input, t_output, t_worker])

class Pupila():
    """
    Main class of the framework
    """
    # TODO: handle flags for input, worker, output

    def __init__(self, _config, component=None):
        """
        Parameters:
        - config(Config): Configuration provided by the user
        - component(str): Component to initialize
        """
        # Initialize global configuration
        config = Config(_config)

        update_logger_level(config.get_log_level())

        if component == 'input':
            input.input()
        elif component == 'output':
            output.output()
        elif component == 'worker':
            worker.worker()
        elif component == 'all':
            run_all()
        else:
            logger.warning(f'No (or wrong) component provided: {component}. Defaulting to all.')
            run_all()

if __name__ == "__main__":
    # The config comes from the CLI in usua environments.
    # Adding this here just for easy of manual testing while developing.
    config = {
        "test_mode": False,
        'input': {
            'enable': True,
            'video': {
                'uri': 'some_hardcoded-uri'
            },
            'address': { # address where the input component runs for the nng connections
                'host': 'localhost',
                'port': 1234
            },
        },
        "output": {
            'video': {
                'enable': True,
                'uri': 'file:///tmp/my-video.mp4'
            },
            'address': { # address where the input component runs for the nng connections
                'host': 'localhost',
                'port': 1236
            },
        }
    }

    component = sys.argv[1]
    Pupila(config, component)
