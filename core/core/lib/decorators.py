from functools import wraps
import time
from rich import print as rprint

def timer(func):
    """
    Decorator to measure user code execution time.
    Note it is designed to work with class methods
    """
    @wraps(func)
    def timer_wrapper(*args, **kwargs):
        debug = getattr(args[0], 'config', {}).get('debug', False) # args[0] should be the "self"
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        exec_time = end_time - start_time
        if debug:
            rprint(f'[green] {func.__name__} executed in {exec_time:.4f} seconds[green]')
        return result
    return timer_wrapper
