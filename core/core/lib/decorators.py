from functools import wraps
import time
from rich import print as rprint

def timer(func):
    @wraps(func)
    def timer_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        exec_time = end_time - start_time
        rprint(f'[green] {func.__name__} executed in {exec_time:.4f} seconds[green]')
        return result
    return timer_wrapper
