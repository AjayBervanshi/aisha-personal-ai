import unittest
from unittest.mock import patch
from src.core.trend_engine import get_duckduckgo_trends, _fallback_trend_report

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


    def test_fallback_trend_report(self):
        expected_keys = {
            "top_angles",
            "trending_topics",
            "viral_keywords",
            "recommended_topic",
            "hook_idea",
            "best_thumbnail_concept"
        }

        channels = ["Story With Aisha", "Riya's Dark Whisper", "Unknown Channel"]
        for channel in channels:
            result = _fallback_trend_report(channel)
            self.assertIsInstance(result, dict)
            self.assertEqual(set(result.keys()), expected_keys)

if __name__ == "__main__":
    unittest.main()
