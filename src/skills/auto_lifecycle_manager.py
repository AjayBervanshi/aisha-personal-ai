import signal
import logging
import json
import os
import sys
from contextlib import contextmanager
from functools import wraps

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutoLifecycleManager:
    """
    A module that implements context managers or decorators to trap SIGINT and SIGTERM signals,
    ensuring active processing tasks reach a safe termination point before exiting.
    This module also includes a file-based state serialization helper to dump critical memory structures
    like `_used_topics` to disk, preventing data loss during unexpected restarts.

    Attributes:
        _used_topics (dict): A dictionary of used topics.
        _state_file (str): The file path to store the state.

    Methods:
        __init__: Initializes the AutoLifecycleManager.
        _signal_handler: Handles SIGINT and SIGTERM signals.
        dump_state: Dumps the state to disk.
        load_state: Loads the state from disk.
        trap_signals: Traps SIGINT and SIGTERM signals.
        safe_termination: Ensures active processing tasks reach a safe termination point before exiting.
    """

    def __init__(self, state_file='state.json'):
        self._used_topics = {}
        self._state_file = state_file
        self.trap_signals()

    def _signal_handler(self, signum, frame):
        logger.info(f'Received signal {signum}, dumping state and exiting')
        self.dump_state()
        sys.exit(0)

    def dump_state(self):
        try:
            with open(self._state_file, 'w') as f:
                # Convert any sets to lists before serializing
                serializable_topics = {
                    k: (list(v) if isinstance(v, set) else v)
                    for k, v in self._used_topics.items()
                }
                json.dump(serializable_topics, f)
            logger.info('State dumped to disk')
        except Exception as e:
            logger.error(f'Failed to dump state: {e}')

    def load_state(self):
        try:
            with open(self._state_file, 'r') as f:
                raw_topics = json.load(f)
                self._used_topics = {
                    k: (set(v) if isinstance(v, list) else v)
                    for k, v in raw_topics.items()
                }
            logger.info('State loaded from disk')
        except (FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError):
            logger.info('No valid JSON state file found, attempting to migrate from legacy .pkl file.')
            legacy_file = self._state_file.replace('.json', '.pkl') if self._state_file.endswith('.json') else 'state.pkl'
            try:
                import pickle
                with open(legacy_file, 'rb') as f:
                    self._used_topics = pickle.load(f)
                logger.info('Successfully loaded state from legacy .pkl file.')

                # Write to the new format
                self.dump_state()

                # Remove the old file if it is distinct
                if legacy_file != self._state_file and os.path.exists(legacy_file):
                    os.remove(legacy_file)
                    logger.info(f'Deleted legacy state file: {legacy_file}')

            except Exception as e:
                logger.info(f'No valid legacy state file found or migration failed: {e}')
        except Exception as e:
            logger.error(f'Failed to load state: {e}')

    def trap_signals(self):
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def safe_termination(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            finally:
                self.dump_state()
        return wrapper

    @contextmanager
    def safe_execution(self):
        try:
            yield
        finally:
            self.dump_state()

def main():
    manager = AutoLifecycleManager()
    manager.load_state()

    @manager.safe_termination
    def example_function():
        manager._used_topics['topic1'] = 'data1'
        logger.info('Example function executed')

    example_function()

    with manager.safe_execution():
        manager._used_topics['topic2'] = 'data2'
        logger.info('Example block executed')

if __name__ == '__main__':
    main()