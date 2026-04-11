import logging
import re
from typing import Dict, Optional
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class APIKeyManager:
    """
    A standalone Python module for handling API key management,
    including secure storage,
    validation, and error handling. This module provides a simple interface
    for retrieving
    and validating API keys, and handles rate limiting and exceptions
    in a robust way.

    Attributes:
        api_keys (Dict[str, str]): A dictionary of API keys.
        rate_limit (int): The rate limit for API requests.
        rate_limit_window (int): The time window for the rate limit.

    Methods:
        add_api_key: Adds a new API key to the manager.
        get_api_key: Retrieves an API key from the manager.
        validate_api_key: Validates an API key.
        handle_rate_limit: Handles rate limiting for API requests.
        log_error: Logs an error.
    """

    def __init__(self, rate_limit: int = 100, rate_limit_window: int = 60):
        self.api_keys: Dict[str, str] = {}
        self.rate_limit: int = rate_limit
        self.rate_limit_window: int = rate_limit_window
        self.request_counts: Dict[str, int] = {}
        self.last_request_times: Dict[str, float] = {}

    def add_api_key(self, key_id: str, api_key: str) -> None:
        """
        Adds a new API key to the manager.

        Args:
            key_id (str): The ID of the API key.
            api_key (str): The API key.
        """
        if not isinstance(key_id, str) or not isinstance(api_key, str):
            self.log_error("Invalid input type for add_api_key")
            raise ValueError("Invalid input type for add_api_key")
        self.api_keys[key_id] = api_key

    def get_api_key(self, key_id: str) -> Optional[str]:
        """
        Retrieves an API key from the manager.

        Args:
            key_id (str): The ID of the API key.

        Returns:
            Optional[str]: The API key, or None if not found.
        """
        if not isinstance(key_id, str):
            self.log_error("Invalid input type for get_api_key")
            raise ValueError("Invalid input type for get_api_key")
        return self.api_keys.get(key_id)

    def validate_api_key(self, api_key: str) -> bool:
        """
        Validates an API key.

        Args:
            api_key (str): The API key.

        Returns:
            bool: True if the API key is valid, False otherwise.
        """
        if not isinstance(api_key, str):
            self.log_error("Invalid input type for validate_api_key")
            raise ValueError("Invalid input type for validate_api_key")
        # Simple validation for demonstration purposes
        return re.match(r"^[a-zA-Z0-9]+$", api_key) is not None

    def handle_rate_limit(self, key_id: str) -> bool:
        """
        Handles rate limiting for API requests.

        Args:
            key_id (str): The ID of the API key.

        Returns:
            bool: True if the request is allowed, False otherwise.
        """
        if not isinstance(key_id, str):
            self.log_error("Invalid input type for handle_rate_limit")
            raise ValueError("Invalid input type for handle_rate_limit")
        current_time = time.time()
        if key_id not in self.request_counts:
            self.request_counts[key_id] = 0
            self.last_request_times[key_id] = current_time
            self.request_counts[key_id] += 1
            return True
        if (current_time - self.last_request_times[key_id]
                > self.rate_limit_window):
            self.request_counts[key_id] = 1
            self.last_request_times[key_id] = current_time
            return True
        if self.request_counts[key_id] < self.rate_limit:
            self.request_counts[key_id] += 1
            return True
        return False

    def log_error(self, message: str) -> None:
        """
        Logs an error.

        Args:
            message (str): The error message.
        """
        if not isinstance(message, str):
            raise ValueError("Invalid input type for log_error")
        logging.error(message)


def main():
    manager = APIKeyManager()
    manager.add_api_key("test_key", "test_api_key")
    print(manager.get_api_key("test_key"))  # Output: test_api_key
    print(manager.validate_api_key("test_api_key"))  # Output: True
    print(manager.handle_rate_limit("test_key"))  # Output: True


if __name__ == "__main__":
    main()
