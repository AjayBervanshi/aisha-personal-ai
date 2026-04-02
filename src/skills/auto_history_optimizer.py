import functools
import logging
import threading
from collections import OrderedDict

logger = logging.getLogger(__name__)

class AutoHistoryOptimizer:
    """
    Replaces the existing _histories dictionary with a functools.lru_cache decorator 
    or a collections.OrderedDict to improve performance and prevent potential memory leaks.
    
    This class provides a configurable eviction policy and handles threading issues 
    to ensure thread-safety. It logs errors and provides a mechanism to trim the 
    history list to a configurable size to prevent excessive memory usage.
    """

    def __init__(self, max_size=100, eviction_policy='lru'):
        """
        Initializes the AutoHistoryOptimizer.

        Args:
            max_size (int): The maximum size of the history list.
            eviction_policy (str): The eviction policy to use. Can be 'lru' or 'fifo'.
        """
        self.max_size = max_size
        self.eviction_policy = eviction_policy
        self.history = OrderedDict()
        self.lock = threading.Lock()

    def add_to_history(self, key, value):
        """
        Adds a new item to the history list.

        Args:
            key (str): The key of the item to add.
            value (str): The value of the item to add.
        """
        with self.lock:
            try:
                if key in self.history:
                    del self.history[key]
                self.history[key] = value
                if len(self.history) > self.max_size:
                    if self.eviction_policy == 'lru':
                        self.history.popitem(last=False)
                    elif self.eviction_policy == 'fifo':
                        self.history.popitem(last=True)
            except Exception as e:
                logger.error(f"Error adding to history: {e}")

    def get_from_history(self, key):
        """
        Retrieves an item from the history list.

        Args:
            key (str): The key of the item to retrieve.

        Returns:
            str: The value of the item if found, otherwise None.
        """
        with self.lock:
            try:
                if key in self.history:
                    value = self.history[key]
                    if self.eviction_policy == 'lru':
                        del self.history[key]
                        self.history[key] = value
                    return value
            except Exception as e:
                logger.error(f"Error getting from history: {e}")
                return None

    def trim_history(self, size):
        """
        Trims the history list to a specified size.

        Args:
            size (int): The size to trim the history list to.
        """
        with self.lock:
            try:
                while len(self.history) > size:
                    if self.eviction_policy == 'lru':
                        self.history.popitem(last=False)
                    elif self.eviction_policy == 'fifo':
                        self.history.popitem(last=True)
            except Exception as e:
                logger.error(f"Error trimming history: {e}")

def main():
    optimizer = AutoHistoryOptimizer(max_size=10, eviction_policy='lru')
    for i in range(20):
        optimizer.add_to_history(f"key_{i}", f"value_{i}")
    for i in range(20):
        print(optimizer.get_from_history(f"key_{i}"))
    optimizer.trim_history(5)
    for i in range(20):
        print(optimizer.get_from_history(f"key_{i}"))

if __name__ == "__main__":
    main()