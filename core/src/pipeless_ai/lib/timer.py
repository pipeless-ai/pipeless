from functools import wraps
import time
from pipeless_ai.lib.logger import logger

def timer(func):
    """
    Decorator to measure user code execution time.
    """
    @wraps(func)
    def timer_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        exec_time = end_time - start_time
        logger.debug(f'[green] {func.__name__} executed in {exec_time:.4f} seconds[green]')
        return result
    return timer_wrapper