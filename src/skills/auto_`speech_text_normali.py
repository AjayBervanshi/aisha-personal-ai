import logging
import re
from num2words import num2words
from word2number import w2n
import inflect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def normalize_for_speech(text: str) -> str:
    """
    Normalize input text to improve clarity and naturalness of generated voice outputs.
    
    This function handles common text-to-speech challenges such as expanding abbreviations, 
    converting numerical values into written words, normalizing punctuation, and filtering 
    out non-speech elements.
    
    Parameters:
    text (str): The input text to be normalized.
    
    Returns:
    str: The normalized text.
    """
    try:
        # Expand abbreviations
        text = re.sub(r'\b(e.g.)\b', 'for example', text)
        text = re.sub(r'\b(i.e.)\b', 'that is', text)
        text = re.sub(r'\b/etc.\b', 'and so on', text)
        
        # Convert numerical values into written words
        text = re.sub(r'\b(\d+)\b', lambda x: num2words(int(x.group(0))), text)
        
        # Convert written-out numbers into spoken form
        text = re.sub(r'\b(one|two|three|four|five|six|seven|eight|nine|ten)\b', 
                      lambda x: w2n.word_to_num(x.group(0)), text)
        
        # Normalize punctuation
        text = re.sub(r'[^\w\s.,!?-]', '', text)
        
        # Filter out non-speech elements
        text = re.sub(r'\b(http|https)://[^\s]+', '', text)
        
        # Use inflect engine to handle plural and singular forms
        p = inflect.engine()
        text = re.sub(r'\b(\w+)\b', lambda x: p.number_to_words(x.group(0)), text)
        
        return text
    
    except Exception as e:
        logger.error(f"Error normalizing text: {e}")
        return None

if __name__ == "__main__":
    text = "Hello, I have 2 dogs and 1 cat. You can visit me at http://example.com for more info, e.g. my phone number is 123-456-7890."
    print(normalize_for_speech(text))