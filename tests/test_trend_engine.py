import unittest
from unittest.mock import patch
from src.core.trend_engine import get_duckduckgo_trends, get_trends_for_channel, CHANNEL_KEYWORDS

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


    @patch("src.core.trend_engine.synthesize_trends_with_ai")
    @patch("src.core.trend_engine.get_duckduckgo_trends")
    @patch("src.core.trend_engine.get_youtube_trending")
    @patch("src.core.trend_engine.get_google_trends")
    def test_get_trends_for_channel_success(self, mock_google, mock_youtube, mock_ddg, mock_synth):
        mock_google.return_value = [{"query": "test", "value": 100}]
        mock_youtube.return_value = [{"title": "test video"}]
        mock_ddg.return_value = ["test insight"]
        mock_synth.return_value = {
            "top_angles": ["Angle 1"],
            "recommended_topic": "Test Topic"
        }

        channel = "Story With Aisha"
        result = get_trends_for_channel(channel)

        config = CHANNEL_KEYWORDS[channel]
        mock_google.assert_called_once_with(config["google_trends"], config["geo"])
        mock_youtube.assert_called_once_with(config["youtube_search"])
        mock_ddg.assert_called_once_with(config["ddg_query"])
        mock_synth.assert_called_once_with(channel, mock_google.return_value, mock_youtube.return_value, mock_ddg.return_value)

        self.assertEqual(result["channel"], channel)
        self.assertIn("fetched_at", result)
        self.assertEqual(result["top_angles"], ["Angle 1"])
        self.assertEqual(result["recommended_topic"], "Test Topic")

    @patch("src.core.trend_engine.synthesize_trends_with_ai")
    @patch("src.core.trend_engine.get_duckduckgo_trends")
    @patch("src.core.trend_engine.get_youtube_trending")
    @patch("src.core.trend_engine.get_google_trends")
    def test_get_trends_for_channel_fallback(self, mock_google, mock_youtube, mock_ddg, mock_synth):
        mock_google.return_value = []
        mock_youtube.return_value = []
        mock_ddg.return_value = []
        mock_synth.return_value = {"recommended_topic": "Fallback"}

        channel = "Unknown Channel"
        result = get_trends_for_channel(channel)

        # Should fall back to Story With Aisha config
        config = CHANNEL_KEYWORDS["Story With Aisha"]
        mock_google.assert_called_once_with(config["google_trends"], config["geo"])
        mock_youtube.assert_called_once_with(config["youtube_search"])
        mock_ddg.assert_called_once_with(config["ddg_query"])
        mock_synth.assert_called_once_with(channel, [], [], [])

        self.assertEqual(result["channel"], channel)
        self.assertIn("fetched_at", result)
        self.assertEqual(result["recommended_topic"], "Fallback")

if __name__ == "__main__":
    unittest.main()
