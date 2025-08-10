import functools
import logging
import time
from functools import lru_cache


# Logging decorator
def log_execution(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logging.info(f"Executing {func.__name__} with args: {args}, kwargs: {kwargs}")
        start_time = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        logging.info(f"Finished {func.__name__} in {duration:.4f} seconds")
        return result

    return wrapper


# Error handling decorator
def handle_errors(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error occurred in {func.__name__}: {str(e)}")
            raise  # Optionally re-raise or handle the error differently

    return wrapper


# Input validation decorator
def validate_input(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        for arg in args:
            if isinstance(arg, str) and not arg.strip():
                raise ValueError(f"Invalid input provided to {func.__name__}")
        return func(*args, **kwargs)

    return wrapper


# Caching decorator
def cache_result(func):
    @functools.wraps(func)
    @lru_cache(maxsize=128)  # Adjust maxsize based on expected use
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


# API key requirement decorator
def require_api_key(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.api_key:
            raise ValueError("API key is required to execute this function")
        return func(self, *args, **kwargs)

    return wrapper
