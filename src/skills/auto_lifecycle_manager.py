import signal
import logging
import json
import pickle
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
            # Add type metadata for sets and integer keys
            serializable_topics = {}
            for k, v in self._used_topics.items():
                key_str = f"int:{k}" if isinstance(k, int) else f"str:{k}"
                if isinstance(v, set):
                    serializable_topics[key_str] = {"__type__": "set", "data": list(v)}
                else:
                    serializable_topics[key_str] = {"__type__": "primitive", "data": v}

            with open(self._state_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_topics, f)
            logger.info('State dumped to disk')
        except Exception as e:
            logger.error(f'Failed to dump state: {e}')

    def load_state(self):
        try:
            with open(self._state_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)

            reconstituted_topics = {}
            # If the loaded data is in the old format (from a previous json without type info), we handle it gracefully
            for k, v in loaded_data.items():
                if isinstance(v, dict) and "__type__" in v:
                    # New format with metadata
                    actual_key = int(k[4:]) if k.startswith("int:") else k[4:]
                    actual_value = set(v["data"]) if v["__type__"] == "set" else v["data"]
                    reconstituted_topics[actual_key] = actual_value
                else:
                    # Legacy format fallback
                    reconstituted_topics[k] = set(v) if isinstance(v, list) else v

            self._used_topics = reconstituted_topics
            logger.info('State loaded from disk')
        except FileNotFoundError:
            # Fallback to pickle if json file doesn't exist
            old_state_file = self._state_file.replace('.json', '.pkl')
            try:
                with open(old_state_file, 'rb') as f:
                    self._used_topics = pickle.load(f)
                logger.info('State loaded from old pkl file')
                # Rewrite to json
                self.dump_state()
            except FileNotFoundError:
                logger.info('No state file found')
            except Exception as e:
                logger.error(f'Failed to load fallback state: {e}')
        except json.JSONDecodeError:
            logger.error('Failed to decode state JSON')
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