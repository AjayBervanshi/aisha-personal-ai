import os
import sys
from unittest.mock import MagicMock, patch
import time

# Mock external dependencies
sys.modules['requests'] = MagicMock()
sys.modules['google.oauth2.credentials'] = MagicMock()
sys.modules['googleapiclient.discovery'] = MagicMock()
sys.modules['google.auth.transport.requests'] = MagicMock()
sys.modules['supabase'] = MagicMock()

from src.core.performance_tracker import generate_performance_report

class MockSupabaseClient:
    def __init__(self):
        self.query_count = 0

    def table(self, table_name):
        return MockTable(self, table_name)

class MockTable:
    def __init__(self, client, table_name):
        self.client = client
        self.table_name = table_name

    def select(self, columns):
        return MockQuery(self.client, self.table_name)

class MockQuery:
    def __init__(self, client, table_name):
        self.client = client
        self.table_name = table_name
        self.filters = []

    def eq(self, column, value):
        self.filters.append(('eq', column, value))
        return self

    def in_(self, column, values):
        self.filters.append(('in', column, values))
        return self

    @property
    def not_(self):
        return self

    def is_(self, column, value):
        return self

    def order(self, column, desc=False):
        return self

    def limit(self, value):
        return self

    def execute(self):
        self.client.query_count += 1
        if self.table_name == "aisha_series":
            # Return some mock series IDs for each channel
            channel_eq = next((val for f, col, val in self.filters if f == 'eq' and col == 'channel'), None)
            if channel_eq:
                return MagicMock(data=[{"id": f"series_{channel_eq}_{i}", "channel": channel_eq} for i in range(2)])

            channels_in = next((val for f, col, val in self.filters if f == 'in' and col == 'channel'), None)
            if channels_in:
                data = []
                for ch in channels_in:
                    data.extend([{"id": f"series_{ch}_{i}", "channel": ch} for i in range(2)])
                return MagicMock(data=data)
            return MagicMock(data=[])
        elif self.table_name == "aisha_episodes":
            # Return some mock episodes
            series_ids_in = next((val for f, col, val in self.filters if f == 'in' and col == 'series_id'), None)
            if series_ids_in:
                data = []
                for sid in series_ids_in:
                    data.extend([
                        {"title": f"Ep {i} for {sid}", "views": 1000 - i * 100, "likes": 100 - i * 10, "youtube_url": "http://yt.com", "series_id": sid}
                        for i in range(3)
                    ])
                return MagicMock(data=data)
            return MagicMock(data=[])
        return MagicMock(data=[])

def benchmark():
    mock_client = MockSupabaseClient()

    with patch('supabase.create_client', return_value=mock_client):
        # We need to set env vars so create_client doesn't fail before mock takes over
        with patch.dict(os.environ, {"SUPABASE_URL": "http://mock", "SUPABASE_SERVICE_KEY": "mock"}):
            start_time = time.time()
            report = generate_performance_report()
            end_time = time.time()

            print(f"Query Count: {mock_client.query_count}")
            print(f"Execution Time: {end_time - start_time:.4f}s")
            print(f"Report:\n{report}")
            return mock_client.query_count

if __name__ == "__main__":
    benchmark()
