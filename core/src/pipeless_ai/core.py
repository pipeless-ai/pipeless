import concurrent.futures
import sys
import time

from pipeless_ai.lib.input import input
from pipeless_ai.lib.output import output
from pipeless_ai.lib.worker import worker
from pipeless_ai.lib.logger import logger

def run_all(config_dict, user_app_class):
    executor = concurrent.futures.ProcessPoolExecutor()
    t_output = executor.submit(output.output, config_dict)
    time.sleep(1) # Allow to create sockets
    t_worker = executor.submit(worker.worker, config_dict, user_app_class)
    time.sleep(1) # Allow to create sockets
    t_input = executor.submit(input.input, config_dict)
    concurrent.futures.wait([t_output, t_worker, t_input])

class Pipeless():
    """
    Main class of the framework
    """
    def __init__(self, config_dict, component=None, user_app_module = None):
        """
        Parameters:
        - config_dict: YAML configuration provided by the user
        - component(str): Component to initialize
        """
        logger.info(f'Running component: {component}')

        if component == 'input':
            input.input(config_dict)
        elif component == 'output':
            output.output(config_dict)
        elif component == 'worker':
            worker.worker(config_dict, user_app_module)
        elif component == 'all':
            run_all(config_dict, user_app_module)
        else:
            logger.warning(f'No (or wrong) component provided: {component}. Defaulting to all.')
            run_all(config_dict, user_app_module)

if __name__ == "__main__":
    # The config comes from the CLI in usua environments.
    # Adding this here just for easy of manual testing while developing.
    config = {
        'input': {
            'video': {
                'enable': True,
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

    if len(sys.argv) < 2:
        logger.error('Missing parameter: component')
        sys.exit(1)

    user_module_path = None
    component = sys.argv[1]
    if component in ['worker', 'all']:
        if len(sys.argv) < 3:
            logger.error('Missing parameter: user module path')
            sys.exit(1)
        user_module_path = sys.argv[2]

    Pipeless(config, component, user_module_path)
