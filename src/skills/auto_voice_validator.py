import logging
import re
from src.core.config import Config

logger = logging.getLogger(__name__)

class VoiceValidator:
    """
    Validates user input for voice generation to prevent potential security issues and ensures rate and pitch settings are within acceptable ranges.

    The VoiceValidator class provides a standardized way to handle errors and exceptions, making it easier to implement robust error handling in the voice generation system.
    It integrates with the existing voice generation system without requiring significant changes to the existing codebase.

    Attributes:
        config (Config): The application configuration.

    Methods:
        validate_text: Validates the input text to prevent SQL injection and XSS attacks.
        validate_rate: Validates the rate setting to ensure it is within the acceptable range.
        validate_pitch: Validates the pitch setting to ensure it is within the acceptable range.
    """

    def __init__(self, config: Config):
        self.config = config

    def validate_text(self, text: str) -> str:
        """
        Validates the input text to prevent SQL injection and XSS attacks.

        Args:
            text (str): The input text to be validated.

        Returns:
            str: The validated text.

        Raises:
            ValueError: If the input text is empty or contains malicious characters.
        """
        if not text:
            logger.error("Input text is empty")
            raise ValueError("Input text is empty")

        if re.search(r"[<>\/\\;]", text):
            logger.error("Input text contains malicious characters")
            raise ValueError("Input text contains malicious characters")

        return text

    def validate_rate(self, rate: float) -> float:
        """
        Validates the rate setting to ensure it is within the acceptable range.

        Args:
            rate (float): The rate setting to be validated.

        Returns:
            float: The validated rate setting.

        Raises:
            ValueError: If the rate setting is outside the acceptable range.
        """
        if rate < self.config.min_rate or rate > self.config.max_rate:
            logger.error(f"Rate setting {rate} is outside the acceptable range [{self.config.min_rate}, {self.config.max_rate}]")
            raise ValueError(f"Rate setting {rate} is outside the acceptable range [{self.config.min_rate}, {self.config.max_rate}]")

        return rate

    def validate_pitch(self, pitch: float) -> float:
        """
        Validates the pitch setting to ensure it is within the acceptable range.

        Args:
            pitch (float): The pitch setting to be validated.

        Returns:
            float: The validated pitch setting.

        Raises:
            ValueError: If the pitch setting is outside the acceptable range.
        """
        if pitch < self.config.min_pitch or pitch > self.config.max_pitch:
            logger.error(f"Pitch setting {pitch} is outside the acceptable range [{self.config.min_pitch}, {self.config.max_pitch}]")
            raise ValueError(f"Pitch setting {pitch} is outside the acceptable range [{self.config.min_pitch}, {self.config.max_pitch}]")

        return pitch

def __main__():
    config = Config()
    validator = VoiceValidator(config)

    try:
        text = validator.validate_text("Hello, World!")
        rate = validator.validate_rate(1.5)
        pitch = validator.validate_pitch(1.2)
        logger.info(f"Validated text: {text}, rate: {rate}, pitch: {pitch}")
    except ValueError as e:
        logger.error(f"Validation error: {e}")

if __name__ == "__main__":
    __main__()