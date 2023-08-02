import os

from lib.input import input
from lib.logger import logger
from lib.config import Config

def main ():
    """
    Entrypoint for all components.
    Each component is executed depending on the provided flags
    """
    # TODO: handle flags for input, worker, output

    config_file_path = 'ADD_PATH_HERE!' # TODO
    config = Config(config_file_path)

    logger.info(f"Reading video from {config.get_input().get_video().get_uri()}")

    input.input()

if __name__ == "__main__":
    main()
