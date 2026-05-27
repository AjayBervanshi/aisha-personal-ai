import os
import pickle
import json
from src.skills.auto_lifecycle_manager import AutoLifecycleManager

# Test migration
def test_migration():
    with open('state.pkl', 'wb') as f:
        pickle.dump({'topic1': 'data1'}, f)

    manager = AutoLifecycleManager(state_file='state.json')
    manager.load_state()
    print(manager._used_topics)
    manager.dump_state()

    with open('state.json', 'r') as f:
        print(json.load(f))
