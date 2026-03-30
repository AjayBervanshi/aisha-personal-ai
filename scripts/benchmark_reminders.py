import time
import os
import sys
from datetime import datetime, timedelta

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class MockQueryBuilder:
    def __init__(self):
        self.updates = 0
        self.calls = 0

    def eq(self, column, value):
        return self

    def in_(self, column, values):
        self.updates = len(values)
        return self

    def execute(self):
        self.calls += 1
        # Simulate network latency
        time.sleep(0.01)
        return type('MockResponse', (), {'data': []})

class MockTable:
    def __init__(self):
        self.builder = MockQueryBuilder()

    def select(self, *args, **kwargs):
        return self.builder

    def update(self, *args, **kwargs):
        return self.builder

    def eq(self, *args, **kwargs):
        return self.builder

class MockDB:
    def __init__(self):
        self.tables = {}
        self.last_table = None

    def table(self, name):
        if name not in self.tables:
            self.tables[name] = MockTable()
        self.last_table = self.tables[name]
        return self.tables[name]

class MockMemory:
    def __init__(self):
        self.db = MockDB()

class MockBrain:
    pass

def benchmark():
    # Setup mock tasks (all due in 15 minutes)
    now = datetime.now()
    due_time = (now + timedelta(minutes=15)).strftime("%H:%M")

    tasks = []
    for i in range(50):
        tasks.append({
            "id": f"task_{i}",
            "title": f"Test Task {i}",
            "due_time": due_time,
            "priority": "medium"
        })

    from src.core.notification_engine import NotificationEngine

    # Override the task_reminder method so we don't send Telegram messages during tests
    def mock_task_reminder(self, task):
        pass

    NotificationEngine.task_reminder = mock_task_reminder

    engine = NotificationEngine(MockBrain(), MockMemory())

    print("Benchmarking NotificationEngine.check_task_reminders()...")

    # --- Simulate Old Method (N+1 Queries) ---
    print("\nSimulating old method (N+1 updates):")
    engine.memory.db.tables['aisha_schedule'] = MockTable()

    def simulate_old_method(tasks_list):
        for task in tasks_list:
            due_time_str = task.get("due_time")
            try:
                hour, minute = map(int, str(due_time_str).split(":")[:2])
                due_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                minutes_away = (due_dt - now).total_seconds() / 60
                if 0 <= minutes_away <= 30:
                    engine.task_reminder(task)
                    # This simulates the old inside-loop query
                    engine.memory.db.table("aisha_schedule").update(
                        {"reminder_sent": True}
                    ).eq("id", task["id"]).execute()
            except Exception as e:
                pass

    start_time = time.time()
    simulate_old_method(tasks)
    old_method_time = time.time() - start_time

    old_table = engine.memory.db.tables['aisha_schedule']
    print(f"Time taken: {old_method_time:.4f} seconds")
    print(f"Network calls made: {old_table.builder.calls}")

    # --- Simulate New Method (Batched Queries) ---
    print("\nSimulating new method (Batched update):")
    engine.memory.db.tables['aisha_schedule'] = MockTable()

    # We patch tasks fetching logic for our benchmark
    original_execute = engine.memory.db.table("aisha_schedule").select("*").eq("due_date", now.date().isoformat()).eq("status", "pending").eq("reminder_sent", False).execute
    def mock_execute():
        return type('MockResponse', (), {'data': tasks})

    engine.memory.db.table("aisha_schedule").select = lambda *args, **kwargs: type('MockQueryBuilder', (), {'eq': lambda *args, **kwargs: type('MockQueryBuilder', (), {'eq': lambda *args, **kwargs: type('MockQueryBuilder', (), {'eq': lambda *args, **kwargs: type('MockQueryBuilder', (), {'execute': mock_execute})})()})()})()

    start_time = time.time()
    engine.check_task_reminders()
    new_method_time = time.time() - start_time

    new_table = engine.memory.db.tables['aisha_schedule']
    print(f"Time taken: {new_method_time:.4f} seconds")
    print(f"Network calls made (update only): {new_table.builder.calls - 1}") # subtract the initial select query that we didn't count in the old method

    if old_method_time > 0:
        improvement = ((old_method_time - new_method_time) / old_method_time) * 100
        print(f"\n⚡ Performance Improvement: {improvement:.2f}% faster")
        print(f"Calls reduced from {len(tasks)} updates to {new_table.builder.calls - 1} update(s).")

if __name__ == "__main__":
    benchmark()
