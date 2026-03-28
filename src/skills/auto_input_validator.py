import logging
import datetime
from typing import Union

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def validate_input_type(input_value, expected_type):
    """
    Validate the type of the input value.

    Args:
        input_value: The value to be validated.
        expected_type: The expected type of the input value.

    Raises:
        TypeError: If the input value is not of the expected type.
    """
    if not isinstance(input_value, expected_type):
        logging.error(f"Invalid input type. Expected {expected_type.__name__}, got {type(input_value).__name__}")
        raise TypeError(f"Expected {expected_type.__name__}, got {type(input_value).__name__}")

def validate_input_format(input_value, expected_format):
    """
    Validate the format of the input value.

    Args:
        input_value: The value to be validated.
        expected_format: The expected format of the input value.

    Raises:
        ValueError: If the input value does not match the expected format.
    """
    if not isinstance(input_value, str):
        logging.error(f"Invalid input format. Expected a string, got {type(input_value).__name__}")
        raise ValueError(f"Expected a string, got {type(input_value).__name__}")
    try:
        datetime.datetime.strptime(input_value, expected_format)
    except ValueError:
        logging.error(f"Invalid input format. Expected {expected_format}, got {input_value}")
        raise ValueError(f"Expected {expected_format}, got {input_value}")

def validate_input_range(input_value, min_value, max_value):
    """
    Validate the range of the input value.

    Args:
        input_value: The value to be validated.
        min_value: The minimum allowed value.
        max_value: The maximum allowed value.

    Raises:
        ValueError: If the input value is outside the allowed range.
    """
    if not isinstance(input_value, (int, float)):
        logging.error(f"Invalid input range. Expected a number, got {type(input_value).__name__}")
        raise ValueError(f"Expected a number, got {type(input_value).__name__}")
    if input_value < min_value or input_value > max_value:
        logging.error(f"Invalid input range. Expected a value between {min_value} and {max_value}, got {input_value}")
        raise ValueError(f"Expected a value between {min_value} and {max_value}, got {input_value}")

def validate_run_evening_wrapup_input(input_value):
    """
    Validate the input for the run_evening_wrapup method.

    Args:
        input_value: The value to be validated.

    Raises:
        TypeError: If the input value is not a string.
        ValueError: If the input value does not match the expected format.
    """
    validate_input_type(input_value, str)
    validate_input_format(input_value, "%Y-%m-%d")

def validate_run_daily_digest_input(input_value):
    """
    Validate the input for the run_daily_digest method.

    Args:
        input_value: The value to be validated.

    Raises:
        TypeError: If the input value is not an integer.
        ValueError: If the input value is outside the allowed range.
    """
    validate_input_type(input_value, int)
    validate_input_range(input_value, 1, 365)

def validate_run_weekly_digest_input(input_value):
    """
    Validate the input for the run_weekly_digest method.

    Args:
        input_value: The value to be validated.

    Raises:
        TypeError: If the input value is not a string.
        ValueError: If the input value does not match the expected format.
    """
    validate_input_type(input_value, str)
    validate_input_format(input_value, "%Y-%W")

if __name__ == "__main__":
    try:
        validate_run_evening_wrapup_input("2022-01-01")
        validate_run_daily_digest_input(30)
        validate_run_weekly_digest_input("2022-01")
        print("All tests passed")
    except (TypeError, ValueError) as e:
        logging.error(f"Test failed: {e}")