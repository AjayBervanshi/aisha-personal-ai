import logging
import collections
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HistoryManager:
    """
    Manages user conversation histories, trimming them to a specified limit, 
    merging redundant histories, and implementing a least-recently-used (LRU) 
    eviction policy to manage guest sessions.

    Attributes:
        history_limit (int): The maximum number of conversation history items.
        guest_sessions (Dict[str, List[str]]): A dictionary of guest sessions, 
            where each key is a session ID and each value is a list of conversation history items.
        lru_cache (collections.OrderedDict): An ordered dictionary that stores 
            the order of access for each session ID, used for LRU eviction.

    Methods:
        add_history(session_id: str, history_item: str): Adds a conversation history item to the specified session.
        get_history(session_id: str): Retrieves the conversation history for the specified session.
        trim_history(session_id: str): Trims the conversation history for the specified session to the specified limit.
        merge_histories(session_id1: str, session_id2: str): Merges the conversation histories of two sessions.
    """

    def __init__(self, history_limit: int = 100):
        self.history_limit = history_limit
        self.guest_sessions: Dict[str, List[str]] = {}
        self.lru_cache: collections.OrderedDict = collections.OrderedDict()

    def add_history(self, session_id: str, history_item: str):
        try:
            if session_id not in self.guest_sessions:
                self.guest_sessions[session_id] = []
                self.lru_cache[session_id] = None
            self.guest_sessions[session_id].append(history_item)
            self.lru_cache.move_to_end(session_id)
            self.trim_history(session_id)
        except Exception as e:
            logger.error(f"Error adding history: {e}")

    def get_history(self, session_id: str) -> List[str]:
        try:
            if session_id not in self.guest_sessions:
                return []
            self.lru_cache.move_to_end(session_id)
            return self.guest_sessions[session_id]
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            return []

    def trim_history(self, session_id: str):
        try:
            if session_id not in self.guest_sessions:
                return
            if len(self.guest_sessions[session_id]) > self.history_limit:
                self.guest_sessions[session_id] = self.guest_sessions[session_id][-self.history_limit:]
        except Exception as e:
            logger.error(f"Error trimming history: {e}")

    def merge_histories(self, session_id1: str, session_id2: str):
        try:
            if session_id1 not in self.guest_sessions or session_id2 not in self.guest_sessions:
                return
            self.guest_sessions[session_id1] = list(set(self.guest_sessions[session_id1] + self.guest_sessions[session_id2]))
            self.guest_sessions[session_id1] = self.guest_sessions[session_id1][-self.history_limit:]
            del self.guest_sessions[session_id2]
            self.lru_cache.move_to_end(session_id1)
        except Exception as e:
            logger.error(f"Error merging histories: {e}")

def main():
    history_manager = HistoryManager()
    history_manager.add_history("session1", "history_item1")
    history_manager.add_history("session1", "history_item2")
    print(history_manager.get_history("session1"))
    history_manager.trim_history("session1")
    print(history_manager.get_history("session1"))
    history_manager.merge_histories("session1", "session2")
    print(history_manager.get_history("session1"))

if __name__ == "__main__":
    main()