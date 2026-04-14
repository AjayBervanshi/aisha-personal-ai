import logging
import re
from typing import Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def validate_text(text: str) -> bool:
    """
    Validate the input text.

    Args:
    text (str): The input text to be validated.

    Returns:
    bool: True if the text is valid, False otherwise.
    """
    if not text:
        logging.error("Text is empty")
        return False
    if len(text) > 1000:
        logging.error("Text is too long. Maximum allowed length is 1000 characters.")
        return False
    return True

def validate_language(language: str) -> bool:
    """
    Validate the input language code.

    Args:
    language (str): The input language code to be validated.

    Returns:
    bool: True if the language code is valid, False otherwise.
    """
    valid_languages = ["en", "fr", "es", "de", "it", "pt", "zh", "ja", "ko"]
    if language not in valid_languages:
        logging.error(f"Invalid language code: {language}. Supported languages are: {', '.join(valid_languages)}")
        return False
    return True

def validate_mood(mood: str) -> bool:
    """
    Validate the input mood setting.

    Args:
    mood (str): The input mood setting to be validated.

    Returns:
    bool: True if the mood setting is valid, False otherwise.
    """
    valid_moods = ["happy", "sad", "neutral"]
    if mood not in valid_moods:
        logging.error(f"Invalid mood setting: {mood}. Supported moods are: {', '.join(valid_moods)}")
        return False
    return True

def validate_input(text: str, language: str, mood: str) -> Dict[str, bool]:
    """
    Validate the input parameters.

    Args:
    text (str): The input text to be validated.
    language (str): The input language code to be validated.
    mood (str): The input mood setting to be validated.

    Returns:
    Dict[str, bool]: A dictionary containing the validation results for each input parameter.
    """
    validation_results = {
        "text": validate_text(text),
        "language": validate_language(language),
        "mood": validate_mood(mood)
    }
    return validation_results

if __name__ == "__main__":
    text = "Hello, world!"
    language = "en"
    mood = "happy"
    validation_results = validate_input(text, language, mood)
    logging.info(f"Validation results: {validation_results}")
    text = ""
    language = "en"
    mood = "happy"
    validation_results = validate_input(text, language, mood)
    logging.info(f"Validation results: {validation_results}")
    text = "Hello, world!"
    language = "invalid"
    mood = "happy"
    validation_results = validate_input(text, language, mood)
    logging.info(f"Validation results: {validation_results}")
    text = "Hello, world!"
    language = "en"
    mood = "invalid"
    validation_results = validate_input(text, language, mood)
    logging.info(f"Validation results: {validation_results}")