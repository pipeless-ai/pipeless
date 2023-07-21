from functools import wraps
import time
from rich import print as rprint

def time(func):
    @wraps(func)
    def time_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        exec_time = end_time - start_time
        rprint(f'[green] {func.__name__}{args} {kwargs} executed in {total_time:.4f} seconds[green]')
        return result
    return time_wrapper
