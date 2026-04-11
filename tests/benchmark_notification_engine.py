import os
import sys
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Ensure imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.notification_engine import NotificationEngine

class MockMemoryManager:
    def __init__(self, num_tasks=100):
        self.db = MagicMock()
        self.num_tasks = num_tasks
        self.query_count = 0

        # Setup mock db table and its methods
        self.table_mock = MagicMock()
        self.db.table.return_value = self.table_mock

        # For select() sequence
        self.select_mock = MagicMock()
        self.table_mock.select.return_value = self.select_mock
        self.eq_mock1 = MagicMock()
        self.select_mock.eq.return_value = self.eq_mock1
        self.eq_mock2 = MagicMock()
        self.eq_mock1.eq.return_value = self.eq_mock2
        self.eq_mock3 = MagicMock()
        self.eq_mock2.eq.return_value = self.eq_mock3
        self.execute_select_mock = MagicMock()
        self.eq_mock3.execute.return_value = self.execute_select_mock

        # Generate tasks that are due now
        now = datetime.now()
        due_time = (now + timedelta(minutes=15)).strftime("%H:%M")

        self.tasks = []
        for i in range(num_tasks):
            self.tasks.append({
                "id": f"task_{i}",
                "title": f"Task {i}",
                "due_time": due_time,
                "priority": "high"
            })

        self.execute_select_mock.data = self.tasks

        # For update() sequence
        self.update_mock = MagicMock()
        self.table_mock.update.return_value = self.update_mock
        self.eq_mock_update = MagicMock()
        self.update_mock.eq.return_value = self.eq_mock_update
        self.execute_update_mock = MagicMock()
        self.eq_mock_update.execute.return_value = self.execute_update_mock

        # For in_() sequence
        self.in_mock = MagicMock()
        self.update_mock.in_.return_value = self.in_mock
        self.execute_in_mock = MagicMock()
        self.in_mock.execute.return_value = self.execute_in_mock

        # Count queries
        self.execute_select_mock.data = self.tasks

        def count_select_exec(*args, **kwargs):
            self.query_count += 1
            mock = MagicMock()
            mock.data = self.tasks
            return mock
        self.eq_mock3.execute.side_effect = count_select_exec

        def count_update_eq_exec(*args, **kwargs):
            self.query_count += 1
            return MagicMock()
        self.eq_mock_update.execute.side_effect = count_update_eq_exec

        def count_update_in_exec(*args, **kwargs):
            self.query_count += 1
            return MagicMock()
        self.in_mock.execute.side_effect = count_update_in_exec

def benchmark():
    num_tasks = 100
    mock_memory = MockMemoryManager(num_tasks=num_tasks)
    mock_brain = MagicMock()

    engine = NotificationEngine(mock_brain, mock_memory)
    # mock send_telegram to avoid failures and delays
    engine.send_telegram = MagicMock(return_value=True)

    start_time = time.time()
    engine.check_task_reminders()
    end_time = time.time()

    print(f"Number of tasks to process: {num_tasks}")
    print(f"Number of queries executed: {mock_memory.query_count}")
    print(f"Execution time: {end_time - start_time:.4f} seconds")

    if mock_memory.query_count > 2:
        print("RESULT: N+1 query pattern detected!")
    else:
        print("RESULT: Optimized (batched) queries detected!")

if __name__ == "__main__":
    benchmark()
