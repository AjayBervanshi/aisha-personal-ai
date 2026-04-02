import logging
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_input(prompt: str, max_length: int = 1000, trim: bool = False, error_message: str = "Invalid input") -> Optional[str]:
    """
    Validates the input prompt string and returns an error message if it's invalid.

    Args:
        prompt (str): The input string to be validated.
        max_length (int): The maximum allowed length of the input string. Defaults to 1000.
        trim (bool): Whether to trim the input string if it exceeds the maximum length. Defaults to False.
        error_message (str): The error message to be returned if the input is invalid. Defaults to "Invalid input".

    Returns:
        Optional[str]: The error message if the input is invalid, otherwise None.
    """
    try:
        if not isinstance(prompt, str):
            logger.error("Input must be a string")
            return error_message
        if not prompt.strip():
            logger.error("Input cannot be empty")
            return error_message
        if len(prompt) > max_length:
            if trim:
                logger.warning("Input exceeds maximum length, trimming...")
                return None
            else:
                logger.error("Input exceeds maximum length")
                return error_message
        return None
    except Exception as e:
        logger.error(f"An error occurred during validation: {str(e)}")
        return error_message

if __name__ == "__main__":
    test_cases = [
        ("Hello, world!", 1000, False, "Invalid input"),
        ("", 1000, False, "Invalid input"),
        ("a" * 1001, 1000, False, "Invalid input"),
        ("a" * 1001, 1000, True, "Invalid input"),
    ]
    for prompt, max_length, trim, error_message in test_cases:
        result = validate_input(prompt, max_length, trim, error_message)
        if result:
            logger.info(f"Test case failed: {prompt} - {result}")
        else:
            logger.info(f"Test case passed: {prompt}")