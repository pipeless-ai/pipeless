import concurrent.futures

from pupila.lib.input.input import input
from pupila.lib.output.output import output
from pupila.lib.worker.worker import worker
from pupila.lib.logger import logger
from pupila.lib.config import Config

def run_all():
    executor = concurrent.futures.ThreadPoolExecutor()
    input = executor.submit(input.input)
    output = executor.submit(output.output)
    worker = executor.submit(input.worker)
    concurrent.futures.wait([input, output, worker])

class Pupila():
    """
    Main class of the framework
    """
    # TODO: handle flags for input, worker, output

    def __init__(self, config, component):
        """
        Parameters:
        - config(Config): Configuration provided by the user
        - component(str): Component to initialize
        """

        # TODO: DELETE. this is a Mockup for testing. 
        # the config will comes from the run command in the constructor.
        config = {
            'input': {
                'video': {
                    'uri': 'some_hardcoded-uri'
                },
                'address': { # address where the input component runs for the nng connections
                    'host': 'localhost',
                    'port': 1234
                },
            },
            "test_mode": False,
        }
        config = Config(config) # Initialize global configuration

        if component == 'input':
            input.input()
        elif component == 'output':
            output.output()
        elif component == 'worker':
            worker.worker()
        elif component == 'all':
            run_all()
        else:
            logger.info('No (or wrong) component provided {component}. Defaulting to all.')
            run_all()
        
if __name__ == "__main__":
    Pupila()
