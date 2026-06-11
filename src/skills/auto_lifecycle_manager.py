import signal
import logging
import pickle
import json
import os
import sys
from contextlib import contextmanager
from functools import wraps

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return {'__set__': list(obj)}
        return super().default(obj)

def set_decoder(dct):
    if '__set__' in dct:
        return set(dct['__set__'])
    return dct

class RestrictedUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module == "builtins" and name in {"set", "dict", "list", "str", "int", "float", "bool"}:
            return getattr(__import__(module), name)
        raise pickle.UnpicklingError(f"Global '{module}.{name}' is forbidden")

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
                json.dump(self._used_topics, f, cls=SetEncoder)
            logger.info('State dumped to disk')
        except Exception as e:
            logger.error(f'Failed to dump state: {e}')

    def load_state(self):
        try:
            with open(self._state_file, 'r') as f:
                self._used_topics = json.load(f, object_hook=set_decoder)
            logger.info('State loaded from disk')
        except FileNotFoundError:
            logger.info('No state file found. Checking for legacy state file...')
            legacy_file = self._state_file.replace('.json', '.pkl')
            if os.path.exists(legacy_file):
                try:
                    with open(legacy_file, 'rb') as f:
                        self._used_topics = RestrictedUnpickler(f).load()
                    logger.info('Legacy state loaded from disk. Migrating to JSON...')
                    self.dump_state()
                    if legacy_file != self._state_file:
                        os.remove(legacy_file)
                        logger.info('Legacy state file deleted.')
                except Exception as e:
                    logger.error(f'Failed to load legacy state: {e}')
            else:
                logger.info('No legacy state file found')
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