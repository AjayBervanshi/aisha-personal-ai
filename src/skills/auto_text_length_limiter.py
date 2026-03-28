import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def limit_text_length(text, limit=1000):
    """
    Limits the length of the input text to prevent errors or performance issues.

    Args:
        text (str): The input text to be limited.
        limit (int): The maximum allowed length of the text. Defaults to 1000.

    Returns:
        str: The limited text.

    Raises:
        TypeError: If the input text is not a string.
        ValueError: If the limit is not a positive integer.
    """
    if not isinstance(text, str):
        logging.error("Input text must be a string.")
        raise TypeError("Input text must be a string.")
    if not isinstance(limit, int) or limit <= 0:
        logging.error("Limit must be a positive integer.")
        raise ValueError("Limit must be a positive integer.")

    if len(text) > limit:
        logging.warning(f"Text length exceeds the limit of {limit} characters. Truncating text.")
        return text[:limit]
    return text

def integrate_with_generate_voice_async(text, limit=1000):
    """
    Integrates the text length limiter with the _generate_voice_async function.

    Args:
        text (str): The input text to be limited and used for voice generation.
        limit (int): The maximum allowed length of the text. Defaults to 1000.

    Returns:
        str: The limited text.
    """
    limited_text = limit_text_length(text, limit)
    # Call the _generate_voice_async function with the limited text
    # For demonstration purposes, a placeholder function is used
    def _generate_voice_async(text):
        return text
    return _generate_voice_async(limited_text)

if __name__ == "__main__":
    try:
        text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
        limited_text = limit_text_length(text)
        print(f"Original text length: {len(text)}")
        print(f"Limited text length: {len(limited_text)}")
        print(f"Limited text: {limited_text}")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        sys.exit(1)