import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Make sure src is in the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException

# Mock module-level dependencies BEFORE importing the server to prevent errors
import sys
sys.modules['src.core.aisha_brain'] = MagicMock()
sys.modules['supabase'] = MagicMock()

from src.api.server import rate_limit, _request_counts, _RATE_LIMIT, _RATE_WINDOW

class TestRateLimit(unittest.TestCase):
    def setUp(self):
        # Clear the global request counts before each test
        _request_counts.clear()

    def create_mock_request(self, ip="127.0.0.1"):
        mock_request = MagicMock()
        if ip is None:
            mock_request.client = None
        else:
            mock_request.client.host = ip
        return mock_request

    @patch('src.api.server.time.time')
    def test_happy_path_under_limit(self, mock_time):
        mock_time.return_value = 1000.0
        req = self.create_mock_request("192.168.1.1")

        # Make requests up to the limit minus 1
        for _ in range(_RATE_LIMIT - 1):
            rate_limit(req)

        self.assertEqual(len(_request_counts["192.168.1.1"]), _RATE_LIMIT - 1)

    @patch('src.api.server.time.time')
    def test_rate_limit_exceeded(self, mock_time):
        mock_time.return_value = 1000.0
        req = self.create_mock_request("192.168.1.1")

        # Make requests up to the limit
        for _ in range(_RATE_LIMIT):
            rate_limit(req)

        # The next request should raise HTTPException 429
        with self.assertRaises(HTTPException) as context:
            rate_limit(req)

        self.assertEqual(context.exception.status_code, 429)
        self.assertEqual(context.exception.detail, "Rate limit exceeded. Try again shortly.")
        self.assertEqual(len(_request_counts["192.168.1.1"]), _RATE_LIMIT)

    @patch('src.api.server.time.time')
    def test_window_reset(self, mock_time):
        mock_time.return_value = 1000.0
        req = self.create_mock_request("10.0.0.1")

        # Max out the rate limit
        for _ in range(_RATE_LIMIT):
            rate_limit(req)

        with self.assertRaises(HTTPException):
            rate_limit(req)

        # Advance time beyond the rate window
        mock_time.return_value = 1000.0 + _RATE_WINDOW + 1.0

        # Should be allowed again
        rate_limit(req)
        self.assertEqual(len(_request_counts["10.0.0.1"]), 1)

    @patch('src.api.server.time.time')
    def test_multiple_ips(self, mock_time):
        mock_time.return_value = 1000.0
        req1 = self.create_mock_request("192.168.1.1")
        req2 = self.create_mock_request("192.168.1.2")

        # Max out limit for IP 1
        for _ in range(_RATE_LIMIT):
            rate_limit(req1)

        with self.assertRaises(HTTPException):
            rate_limit(req1)

        # IP 2 should still be allowed
        rate_limit(req2)
        self.assertEqual(len(_request_counts["192.168.1.2"]), 1)

    @patch('src.api.server.time.time')
    def test_unknown_ip(self, mock_time):
        mock_time.return_value = 1000.0
        req_unknown = self.create_mock_request(None)

        rate_limit(req_unknown)
        self.assertEqual(len(_request_counts["unknown"]), 1)

if __name__ == '__main__':
    unittest.main()
