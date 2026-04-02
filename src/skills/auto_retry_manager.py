import logging
import time
from typing import Callable, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutoRetryManager:
    """
    A standalone Python module that provides a retry mechanism for database operations.
    
    This module allows for a configurable number of retries and delay between attempts.
    It can handle different types of database exceptions and provide a fallback strategy 
    when all retries fail. The implementation is flexible enough to be easily integrated 
    into the existing autonomous loop codebase.

    Attributes:
        max_retries (int): The maximum number of retries.
        delay (float): The delay between attempts in seconds.
        fallback_strategy (Callable): A callable that provides a fallback strategy.
        exceptions (tuple): A tuple of exception types to catch.

    Methods:
        retry: Retry a database operation with the configured retry policy.
    """

    def __init__(self, max_retries: int = 3, delay: float = 1, fallback_strategy: Optional[Callable] = None, exceptions: tuple = (Exception,)):
        """
        Initialize the AutoRetryManager.

        Args:
            max_retries (int): The maximum number of retries. Defaults to 3.
            delay (float): The delay between attempts in seconds. Defaults to 1.
            fallback_strategy (Callable): A callable that provides a fallback strategy. Defaults to None.
            exceptions (tuple): A tuple of exception types to catch. Defaults to (Exception,).
        """
        self.max_retries = max_retries
        self.delay = delay
        self.fallback_strategy = fallback_strategy
        self.exceptions = exceptions

    def retry(self, func: Callable, *args, **kwargs):
        """
        Retry a database operation with the configured retry policy.

        Args:
            func (Callable): The function to retry.

        Returns:
            The result of the function call.
        """
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except self.exceptions as e:
                if attempt < self.max_retries:
                    logger.warning(f"Attempt {attempt + 1} failed with error: {e}. Retrying in {self.delay} seconds.")
                    time.sleep(self.delay)
                else:
                    logger.error(f"All retries failed with error: {e}.")
                    if self.fallback_strategy:
                        logger.info("Using fallback strategy.")
                        return self.fallback_strategy(*args, **kwargs)
                    else:
                        raise

def example_fallback_strategy(*args, **kwargs):
    logger.info("Fallback strategy: Return a default value.")
    return "Default value"

def example_database_operation():
    logger.info("Simulating a database operation that fails.")
    raise Exception("Database operation failed.")

if __name__ == "__main__":
    retry_manager = AutoRetryManager(max_retries=3, delay=1, fallback_strategy=example_fallback_strategy)
    result = retry_manager.retry(example_database_operation)
    logger.info(f"Result: {result}")