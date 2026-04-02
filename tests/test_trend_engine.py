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


    def test_fallback_trend_report_known_channels(self):
        result1 = _fallback_trend_report("Story With Aisha")
        self.assertIn("top_angles", result1)
        self.assertIn("Office romance where colleagues fall in love during late night deadlines", result1["top_angles"])
        self.assertEqual(result1["recommended_topic"], "Office colleagues who fall in love during a project deadline")
        self.assertEqual(result1["hook_idea"], "क्या आपने कभी किसी अजनबी से इस तरह प्यार किया जैसे आप उसे हमेशा से जानते थे?")

        result2 = _fallback_trend_report("Riya's Dark Whisper")
        self.assertIn("top_angles", result2)
        self.assertIn("Boss-employee forbidden attraction turning into obsession", result2["top_angles"])
        self.assertEqual(result2["recommended_topic"], "Forbidden boss-employee obsession in a Mumbai corporate office")

    def test_fallback_trend_report_unknown_channel(self):
        result = _fallback_trend_report("Some Unknown Channel")
        self.assertIn("top_angles", result)
        self.assertEqual(result["top_angles"], ["Fresh content idea 1", "Fresh content idea 2", "Fresh content idea 3"])
        self.assertEqual(result["trending_topics"], ["trending", "viral", "popular"])
        self.assertEqual(result["viral_keywords"], ["hindi", "story", "emotional"])
        self.assertEqual(result["recommended_topic"], "A compelling story for your audience")
        self.assertEqual(result["hook_idea"], "A powerful opening line")
        self.assertEqual(result["best_thumbnail_concept"], "Emotional cinematic thumbnail")


if __name__ == "__main__":
    unittest.main()
