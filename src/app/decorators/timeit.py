import time
import functools
import logging

logger = logging.getLogger(__name__)

def timeit(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        duration = end - start
        logger.info(f"{func.__name__} executed in {duration:.4f} seconds")
        return result
    return wrapper
