import logging
import functools
from typing import Callable, List
from src.core.config import settings
from src.providers import image_provider_1, image_provider_2, image_provider_3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GenerationManager:
    """
    Orchestrates the generation of images through a prioritized list of provider functions.
    
    This class provides a single public entry point, `generate_image`, which iterates through the list of providers,
    catches exceptions, and validates outputs before returning the generated image. It also integrates a TTL-based cache
    to prevent redundant API calls for identical prompts.
    
    Attributes:
    providers (List[Callable]): A list of provider functions, in order of priority.
    cache (functools.lru_cache): A cache decorator to prevent redundant API calls.
    """
    
    def __init__(self):
        self.providers = [image_provider_1.generate_image, image_provider_2.generate_image, image_provider_3.generate_image]
        self.cache = functools.lru_cache(maxsize=128, typed=True)

    @staticmethod
    def _validate_output(output):
        """
        Validates the output of a provider function.
        
        Args:
        output: The output of a provider function.
        
        Returns:
        bool: True if the output is valid, False otherwise.
        """
        return output is not None and isinstance(output, str)

    @cache
    def _generate_image(self, prompt: str, provider: Callable) -> str:
        """
        Generates an image using a provider function.
        
        Args:
        prompt (str): The prompt to generate an image for.
        provider (Callable): The provider function to use.
        
        Returns:
        str: The generated image.
        
        Raises:
        Exception: If an error occurs during image generation.
        """
        try:
            output = provider(prompt)
            if not self._validate_output(output):
                raise ValueError("Invalid output from provider")
            return output
        except Exception as e:
            logger.error(f"Error generating image with provider {provider.__name__}: {str(e)}")
            raise

    def generate_image(self, prompt: str) -> str:
        """
        Generates an image using the prioritized list of provider functions.
        
        Args:
        prompt (str): The prompt to generate an image for.
        
        Returns:
        str: The generated image.
        
        Raises:
        Exception: If an error occurs during image generation.
        """
        for provider in self.providers:
            try:
                return self._generate_image(prompt, provider)
            except Exception as e:
                logger.error(f"Error generating image with provider {provider.__name__}: {str(e)}")
                continue
        raise Exception("Failed to generate image with all providers")

def generate_image(prompt: str) -> str:
    """
    Public entry point for generating an image.
    
    Args:
    prompt (str): The prompt to generate an image for.
    
    Returns:
    str: The generated image.
    """
    manager = GenerationManager()
    return manager.generate_image(prompt)

if __name__ == "__main__":
    prompt = "A beautiful sunset on a tropical island"
    image = generate_image(prompt)
    print(image)