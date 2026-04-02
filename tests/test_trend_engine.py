import unittest
from unittest.mock import patch, MagicMock
import sys
import pandas as pd
from src.core.trend_engine import get_duckduckgo_trends, get_google_trends

class TestTrendEngine(unittest.TestCase):

    @patch("src.core.trend_engine.requests.get")
    def test_get_duckduckgo_trends_success(self, mock_get):
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "RelatedTopics": [
                {"Text": "Result 1"},
                {"Topics": [{"Text": "Result 2"}, {"Text": "Result 3"}]}
            ]
        }

        result = get_duckduckgo_trends("test query")
        self.assertEqual(result, ["Result 1", "Result 2", "Result 3"])

    @patch("src.core.trend_engine.requests.get")
    def test_get_duckduckgo_trends_limit_results(self, mock_get):
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "RelatedTopics": [
                {"Text": f"Result {i}"} for i in range(15)
            ]
        }

        result = get_duckduckgo_trends("test query")
        self.assertEqual(len(result), 8)
        self.assertEqual(result, [f"Result {i}" for i in range(8)])

    @patch("src.core.trend_engine.requests.get")
    def test_get_duckduckgo_trends_limit_results_with_topics(self, mock_get):
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "RelatedTopics": [
                {"Topics": [{"Text": f"Result {i}-{j}"} for j in range(5)]} for i in range(15)
            ]
        }

        result = get_duckduckgo_trends("test query")
        self.assertEqual(len(result), 10)

    @patch("src.core.trend_engine.requests.get")
    def test_get_duckduckgo_trends_http_error(self, mock_get):
        mock_response = mock_get.return_value
        mock_response.status_code = 404

        result = get_duckduckgo_trends("test query")
        self.assertEqual(result, [])

    @patch("src.core.trend_engine.requests.get")
    def test_get_duckduckgo_trends_exception(self, mock_get):
        mock_get.side_effect = Exception("Network error")

        result = get_duckduckgo_trends("test query")
        self.assertEqual(result, [])

    def test_get_google_trends_success(self):
        mock_trendreq_class = MagicMock()
        mock_instance = MagicMock()
        mock_trendreq_class.return_value = mock_instance

        mock_request_module = MagicMock()
        mock_request_module.TrendReq = mock_trendreq_class

        df = pd.DataFrame({
            "query": ["rising query 1", "rising query 2"],
            "value": [100, 50]
        })

        mock_instance.related_queries.return_value = {
            "keyword1": {"rising": df},
            "keyword2": {"rising": None}
        }

        with patch.dict('sys.modules', {'pytrends': MagicMock(), 'pytrends.request': mock_request_module}):
            result = get_google_trends(["keyword1", "keyword2"])

            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]["query"], "rising query 1")
            self.assertEqual(result[0]["value"], 100)
            self.assertEqual(result[0]["type"], "rising")
            self.assertEqual(result[0]["keyword"], "keyword1")

            self.assertEqual(result[1]["query"], "rising query 2")
            self.assertEqual(result[1]["value"], 50)
            self.assertEqual(result[1]["type"], "rising")
            self.assertEqual(result[1]["keyword"], "keyword1")

    def test_get_google_trends_batching(self):
        mock_trendreq_class = MagicMock()
        mock_instance = MagicMock()
        mock_trendreq_class.return_value = mock_instance

        mock_request_module = MagicMock()
        mock_request_module.TrendReq = mock_trendreq_class

        df1 = pd.DataFrame({
            "query": ["query batch 1"],
            "value": [100]
        })
        df2 = pd.DataFrame({
            "query": ["query batch 2"],
            "value": [50]
        })

        # Simulate related_queries returning different results based on the batch
        mock_instance.related_queries.side_effect = [
            {"k1": {"rising": df1}, "k2": {"rising": None}, "k3": {"rising": None}, "k4": {"rising": None}, "k5": {"rising": None}},
            {"k6": {"rising": df2}}
        ]

        with patch.dict('sys.modules', {'pytrends': MagicMock(), 'pytrends.request': mock_request_module}):
            keywords = ["k1", "k2", "k3", "k4", "k5", "k6"]
            result = get_google_trends(keywords)

            self.assertEqual(mock_instance.build_payload.call_count, 2)
            # Check the batches passed to build_payload
            args_call_1 = mock_instance.build_payload.call_args_list[0][0][0]
            args_call_2 = mock_instance.build_payload.call_args_list[1][0][0]
            self.assertEqual(args_call_1, ["k1", "k2", "k3", "k4", "k5"])
            self.assertEqual(args_call_2, ["k6"])

            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]["query"], "query batch 1") # highest value first
            self.assertEqual(result[1]["query"], "query batch 2")

    def test_get_google_trends_import_error(self):
        # By removing pytrends and pytrends.request from sys.modules,
        # it will raise ImportError when `from pytrends.request import TrendReq` happens
        # BUT we must mock sys.modules to simulate this properly if it was already imported elsewhere
        with patch.dict('sys.modules', {'pytrends.request': None}):
            result = get_google_trends(["k1"])
            self.assertEqual(result, [])

    def test_get_google_trends_exception(self):
        mock_trendreq_class = MagicMock()
        mock_instance = MagicMock()
        mock_trendreq_class.return_value = mock_instance

        mock_request_module = MagicMock()
        mock_request_module.TrendReq = mock_trendreq_class

        mock_instance.build_payload.side_effect = Exception("Test Error")

        with patch.dict('sys.modules', {'pytrends': MagicMock(), 'pytrends.request': mock_request_module}):
            result = get_google_trends(["k1"])
            self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
