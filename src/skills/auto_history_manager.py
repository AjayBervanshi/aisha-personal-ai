import logging
import os
from typing import Dict, List
from src.core.database import Database
from src.core.config import Config

class HistoryManager:
    """
    A class responsible for handling user histories, including trimming and loading histories from the database.
    
    This class provides methods to load, trim, and reset user histories, ensuring that the owner's history is correctly managed 
    and avoiding redundant loading of histories. It also includes a method to check for and prevent potential memory errors 
    by monitoring the size of user histories.

    Attributes:
        db (Database): The database object used to interact with the database.
        config (Config): The configuration object used to access configuration settings.
        max_history_size (int): The maximum allowed size of a user's history.
        logger (logging.Logger): The logger object used to log events and errors.
    """

    def __init__(self, db: Database, config: Config):
        self.db = db
        self.config = config
        self.max_history_size = self.config.get_int('max_history_size')
        self.logger = logging.getLogger(__name__)

    def load_history(self, user_id: str) -> List[Dict]:
        """
        Load a user's history from the database.

        Args:
            user_id (str): The ID of the user whose history is to be loaded.

        Returns:
            List[Dict]: The user's history, where each item is a dictionary representing a history entry.
        """
        try:
            history = self.db.get_user_history(user_id)
            return history
        except Exception as e:
            self.logger.error(f"Failed to load history for user {user_id}: {str(e)}")
            return []

    def trim_history(self, user_id: str) -> None:
        """
        Trim a user's history to the maximum allowed size.

        Args:
            user_id (str): The ID of the user whose history is to be trimmed.
        """
        try:
            history = self.load_history(user_id)
            if len(history) > self.max_history_size:
                self.db.trim_user_history(user_id, self.max_history_size)
        except Exception as e:
            self.logger.error(f"Failed to trim history for user {user_id}: {str(e)}")

    def reset_history(self, user_id: str) -> None:
        """
        Reset a user's history, removing all entries.

        Args:
            user_id (str): The ID of the user whose history is to be reset.
        """
        try:
            self.db.reset_user_history(user_id)
        except Exception as e:
            self.logger.error(f"Failed to reset history for user {user_id}: {str(e)}")

    def check_history_size(self, user_id: str) -> None:
        """
        Check the size of a user's history and trim it if necessary to prevent memory errors.

        Args:
            user_id (str): The ID of the user whose history is to be checked.
        """
        try:
            history = self.load_history(user_id)
            if len(history) > self.max_history_size:
                self.trim_history(user_id)
        except Exception as e:
            self.logger.error(f"Failed to check history size for user {user_id}: {str(e)}")

if __name__ == "__main__":
    db = Database()
    config = Config()
    history_manager = HistoryManager(db, config)
    user_id = "test_user"
    history_manager.load_history(user_id)
    history_manager.trim_history(user_id)
    history_manager.reset_history(user_id)
    history_manager.check_history_size(user_id)