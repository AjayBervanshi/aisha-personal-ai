import time
import asyncio
from unittest.mock import MagicMock
from src.core.notification_engine import NotificationEngine

def test_benchmark_build_daily_context():
    brain = MagicMock()
    memory = MagicMock()

    # Mock the database table and chain
    db_mock = MagicMock()
    table_mock = MagicMock()

    # We want to mock the chain: .table().select().eq().eq().execute()
    # and for the original code vs new code.

    def execute_mock():
        # simulate I/O delay depending on row count
        # but locally it's hard to measure DB latency, we'll just test that it works.
        class Response:
            def __init__(self):
                self.data = [{"title": f"Task {i}"} for i in range(100)]
                self.count = 100
        return Response()

    eq_mock2 = MagicMock()
    eq_mock2.execute = execute_mock

    eq_mock1 = MagicMock()
    eq_mock1.eq.return_value = eq_mock2

    limit_mock = MagicMock()
    limit_mock.eq.return_value = eq_mock1

    select_mock = MagicMock()
    select_mock.eq.return_value = eq_mock1
    select_mock.limit.return_value = limit_mock

    table_mock.select.return_value = select_mock
    db_mock.table.return_value = table_mock

    memory.db = db_mock

    engine = NotificationEngine(brain, memory)

    start = time.time()
    for _ in range(100):
        context = engine._build_daily_context(evening=True)
    duration = time.time() - start

    print(f"Benchmark: 100 calls took {duration:.4f}s")
    assert "Tasks completed:" in context
    assert "Tasks missed:" in context
    print("Benchmark complete.")

if __name__ == "__main__":
    test_benchmark_build_daily_context()
