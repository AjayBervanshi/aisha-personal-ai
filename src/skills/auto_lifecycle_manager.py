import signal
import logging
import json
import pickle
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
        # Support migration from legacy pkl file
        self._legacy_file = state_file.replace('.json', '.pkl') if state_file.endswith('.json') else state_file
        if not state_file.endswith('.json'):
            state_file = state_file.replace('.pkl', '.json')
        self._state_file = state_file
        self.trap_signals()

    def _signal_handler(self, signum, frame):
        logger.info(f'Received signal {signum}, dumping state and exiting')
        self.dump_state()
        sys.exit(0)

    def dump_state(self):
        try:
            # Convert sets to lists for JSON serialization
            serializable_topics = {}
            for k, v in self._used_topics.items():
                if isinstance(v, set):
                    serializable_topics[k] = list(v)
                else:
                    serializable_topics[k] = v

            with open(self._state_file, 'w') as f:
                json.dump(serializable_topics, f)
            logger.info('State dumped to disk')

            # Remove legacy pickle file after successful JSON dump
            if self._legacy_file != self._state_file and os.path.exists(self._legacy_file):
                try:
                    os.remove(self._legacy_file)
                    logger.info('Removed legacy state file')
                except Exception as e:
                    logger.warning(f'Could not remove legacy file: {e}')
        except Exception as e:
            logger.error(f'Failed to dump state: {e}')

    def load_state(self):
        try:
            # Try to read JSON first
            if os.path.exists(self._state_file):
                with open(self._state_file, 'r') as f:
                    data = json.load(f)

                    # Reconstitute lists back to sets and restore integer keys
                    self._used_topics = {
                        int(k) if isinstance(k, str) and k.isdigit() else k: set(v) if isinstance(v, list) else v
                        for k, v in data.items()
                    }
                logger.info('State loaded from disk (JSON)')
            elif os.path.exists(self._legacy_file):
                # Fallback to pickle migration
                with open(self._legacy_file, 'rb') as f:
                    self._used_topics = pickle.load(f)
                logger.info('Legacy state loaded from disk (Pickle). Will migrate to JSON on next dump.')
                # Force an immediate dump to migrate
                self.dump_state()
            else:
                logger.info('No state file found')
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f'Failed to decode JSON state: {e}')
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