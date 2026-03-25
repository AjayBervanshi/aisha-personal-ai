import re
import threading
import logging

class IntentDispatcher:
    """
    A thread-safe registry class to map regex patterns to specific callback functions.
    
    This class provides a dispatch method that iterates through the registered patterns 
    and executes the associated tool function. It ensures the brain can finally process 
    inputs without bloating the primary class.

    Attributes:
        registry (dict): A dictionary to store the regex patterns and their corresponding callback functions.
        lock (threading.Lock): A lock to ensure thread safety.

    Methods:
        register(pattern, callback): Registers a regex pattern and its corresponding callback function.
        dispatch(text): Iterates through the registered patterns and executes the associated tool function.
    """

    def __init__(self):
        self.registry = {}
        self.lock = threading.Lock()

    def register(self, pattern, callback):
        """
        Registers a regex pattern and its corresponding callback function.

        Args:
            pattern (str): The regex pattern to be registered.
            callback (function): The callback function to be executed when the pattern is matched.

        Raises:
            TypeError: If the pattern is not a string or the callback is not a callable function.
        """
        if not isinstance(pattern, str):
            raise TypeError("Pattern must be a string")
        if not callable(callback):
            raise TypeError("Callback must be a callable function")

        with self.lock:
            self.registry[pattern] = callback

    def dispatch(self, text):
        """
        Iterates through the registered patterns and executes the associated tool function.

        Args:
            text (str): The input text to be processed.

        Returns:
            bool: True if a matching pattern is found and the corresponding callback function is executed, False otherwise.
        """
        with self.lock:
            for pattern, callback in self.registry.items():
                try:
                    if re.match(pattern, text):
                        callback(text)
                        return True
                except Exception as e:
                    logging.error(f"Error executing callback for pattern {pattern}: {str(e)}")
        return False


if __name__ == "__main__":
    dispatcher = IntentDispatcher()

    def callback_function(text):
        print(f"Callback function executed with text: {text}")

    dispatcher.register("hello", callback_function)
    print(dispatcher.dispatch("hello"))  # Should print: Callback function executed with text: hello and return True
    print(dispatcher.dispatch("goodbye"))  # Should return False