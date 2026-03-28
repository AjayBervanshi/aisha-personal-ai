import logging
import logging.config
from src.core.config import settings

logging.config.dictConfig(settings.LOGGING_CONFIG)

logger = logging.getLogger(__name__)

def log_trend_fetching_error(exception, fallback_trends=None):
    """
    Logs trend fetching errors and provides a fallback mechanism to handle exceptions.

    This function is designed to handle trend fetching errors in a centralized manner, 
    making it easier to maintain and debug the code. It logs the exception and returns 
    the fallback trends if provided, otherwise it returns an empty list.

    Args:
        exception (Exception): The exception that occurred during trend fetching.
        fallback_trends (list, optional): The default trends to return in case of an error. Defaults to None.

    Returns:
        list: The fallback trends if provided, otherwise an empty list.
    """
    logger.error("Trend fetching error: %s", exception, exc_info=True)
    if fallback_trends is not None:
        logger.info("Returning fallback trends: %s", fallback_trends)
        return fallback_trends
    else:
        logger.info("Returning empty list due to trend fetching error")
        return []

def fetch_trends_with_fallback(fetch_trends_func, fallback_trends=None):
    """
    Fetches trends using the provided function and logs any errors that occur.

    This function provides a fallback mechanism to handle exceptions, allowing the program 
    to continue execution without interruptions. If an error occurs during trend fetching, 
    it logs the error and returns the fallback trends if provided, otherwise it returns an empty list.

    Args:
        fetch_trends_func (function): The function to use for fetching trends.
        fallback_trends (list, optional): The default trends to return in case of an error. Defaults to None.

    Returns:
        list: The fetched trends if successful, otherwise the fallback trends or an empty list.
    """
    try:
        return fetch_trends_func()
    except Exception as e:
        return log_trend_fetching_error(e, fallback_trends)

def __main__():
    def fetch_trends():
        # Simulate a trend fetching error
        raise Exception("Trend fetching error")

    fallback_trends = ["Trend 1", "Trend 2", "Trend 3"]
    trends = fetch_trends_with_fallback(fetch_trends, fallback_trends)
    print(trends)

if __name__ == "__main__":
    __main__()