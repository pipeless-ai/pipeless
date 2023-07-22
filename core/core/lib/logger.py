import logging
from rich.logging import RichHandler

def create_logger(level):
    FORMAT = '%(message)s'
    rich_handler = RichHandler(markup=True)

    logging.basicConfig(
        level=level, format=FORMAT, datefmt="[%X]", handlers=[rich_handler]
    )
    logger = logging.getLogger("rich")
    return logger

logger = create_logger('INFO')

def update_logger_level(level):
    logger.setLevel(level)
