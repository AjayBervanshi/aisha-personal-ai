import signal
import logging
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

    def __init__(self, state_file='state.pkl'):
        self._used_topics = {}
        self._state_file = state_file
        self.trap_signals()

    def _signal_handler(self, signum, frame):
        logger.info(f'Received signal {signum}, dumping state and exiting')
        self.dump_state()
        sys.exit(0)

    def dump_state(self):
        try:
            with open(self._state_file, 'wb') as f:
                pickle.dump(self._used_topics, f)
            logger.info('State dumped to disk')
        except Exception as e:
            logger.error(f'Failed to dump state: {e}')

    def load_state(self):
        try:
            with open(self._state_file, 'rb') as f:
                self._used_topics = pickle.load(f)
            logger.info('State loaded from disk')
        except FileNotFoundError:
            logger.info('No state file found')
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