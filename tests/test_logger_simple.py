
import unittest
import unittest.mock
import logging
import json
from src.core.logger import get_logger, _JsonFormatter

class TestLogger(unittest.TestCase):
    def test_json_formatter_success(self):
        formatter = _JsonFormatter()
        record = logging.LogRecord("test", logging.INFO, "test.py", 10, "test message", None, None)
        formatted = formatter.format(record)
        data = json.loads(formatted)
        self.assertEqual(data["event"], "test message")
        self.assertEqual(data["level"], "info")
        self.assertEqual(data["logger"], "test")

    def test_json_formatter_extra_kwargs(self):
        formatter = _JsonFormatter()
        record = logging.LogRecord("test", logging.INFO, "test.py", 10, "test message", None, None)
        record.__dict__["extra_key"] = "extra_val"
        formatted = formatter.format(record)
        data = json.loads(formatted)
        self.assertEqual(data["extra_key"], "extra_val")

    def test_json_formatter_exception(self):
        formatter = _JsonFormatter()
        try:
            raise ValueError("test exception")
        except ValueError:
            import sys
            record = logging.LogRecord("test", logging.ERROR, "test.py", 10, "error message", None, sys.exc_info())

        formatted = formatter.format(record)
        data = json.loads(formatted)
        self.assertIn("traceback", data)
        self.assertIn("ValueError: test exception", data["traceback"])

    def test_json_formatter_fail_safe(self):
        formatter = _JsonFormatter()
        record = logging.LogRecord("test", logging.INFO, "test.py", 10, "test message", None, None)

        # Test TypeError handling
        with unittest.mock.patch("json.dumps") as mock_dumps:
            mock_dumps.side_effect = [TypeError("Serialization error"), '{"level": "error", "event": "log_format_failed"}']
            formatted = formatter.format(record)
            data = json.loads(formatted)
            self.assertEqual(data["event"], "log_format_failed")
            self.assertEqual(data["level"], "error")

        # Test ValueError handling
        with unittest.mock.patch("json.dumps") as mock_dumps:
            mock_dumps.side_effect = [ValueError("Value error"), '{"level": "error", "event": "log_format_failed"}']
            formatted = formatter.format(record)
            data = json.loads(formatted)
            self.assertEqual(data["event"], "log_format_failed")
            self.assertEqual(data["level"], "error")

if __name__ == "__main__":
    unittest.main()
