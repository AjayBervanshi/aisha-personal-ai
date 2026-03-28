import logging
import random
import time
from functools import wraps
from typing import Callable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def exponential_backoff(max_attempts: int = 5, initial_delay: float = 1, max_delay: float = 32, backoff_factor: float = 2):
    """
    Decorator to handle API rate limits by implementing an exponential backoff strategy.

    This decorator allows the image engine to retry API calls after a certain delay, 
    and ensures that the delay increases after each failed attempt. It provides a 
    configurable backoff strategy and detects when the rate limit has been lifted, 
    allowing the API calls to resume normally.

    Args:
        max_attempts (int): The maximum number of attempts to make before giving up.
        initial_delay (float): The initial delay between attempts in seconds.
        max_delay (float): The maximum delay between attempts in seconds.
        backoff_factor (float): The factor by which the delay increases after each attempt.

    Returns:
        A decorator that implements the exponential backoff strategy.
    """

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            delay = initial_delay
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                    attempt += 1
                    if attempt < max_attempts:
                        # Add some jitter to the delay to avoid the "thundering herd" problem
                        jitter = random.uniform(0, 1)
                        delay = min(delay * backoff_factor, max_delay)
                        logger.info(f"Waiting for {delay + jitter:.2f} seconds before retrying...")
                        time.sleep(delay + jitter)
                    else:
                        logger.error(f"Max attempts reached. Giving up.")
                        raise
        return wrapper
    return decorator

def main():
    @exponential_backoff(max_attempts=3, initial_delay=1, max_delay=16, backoff_factor=2)
    def example_api_call():
        # Simulate an API call that fails due to rate limiting
        import random
        if random.random() < 0.5:
            raise Exception("Rate limit exceeded")
        else:
            return "API call successful"

    print(example_api_call())

if __name__ == "__main__":
    main()