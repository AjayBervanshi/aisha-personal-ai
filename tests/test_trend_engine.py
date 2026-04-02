import unittest
from unittest.mock import patch

import os
import json
from src.core.trend_engine import get_duckduckgo_trends, get_google_trends, get_youtube_trending, synthesize_trends_with_ai, _fallback_trend_report


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



    # ── Google Trends Tests ──────────────────────────────────────

    @patch("src.core.trend_engine.log")
    @patch.dict("sys.modules", {"pytrends.request": unittest.mock.MagicMock()})
    def test_get_google_trends_success(self, mock_log):
        import sys
        mock_trend_req = sys.modules["pytrends.request"].TrendReq

        # Setup mock instance
        mock_instance = mock_trend_req.return_value

        # We mock related_queries to return a nested dict
        # Rising df needs iterrows
        import unittest.mock
        df = unittest.mock.MagicMock()
        df.iterrows.return_value = [
            (0, {"query": "rising keyword 1", "value": 100}),
            (1, {"query": "rising keyword 2", "value": 50})
        ]
        df.head.return_value = df

        mock_instance.related_queries.return_value = {
            "test1": {"rising": df},
            "test2": {"rising": None}
        }

        result = get_google_trends(["test1", "test2"])

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["query"], "rising keyword 1")
        self.assertEqual(result[0]["value"], 100)
        self.assertEqual(result[0]["type"], "rising")
        self.assertEqual(result[0]["keyword"], "test1")

    @patch("src.core.trend_engine.log")
    def test_get_google_trends_no_pytrends(self, mock_log):
        # We ensure pytrends is NOT in sys.modules, or mock the import to fail
        with patch.dict('sys.modules', {'pytrends.request': None}):
            result = get_google_trends(["test1"])
            self.assertEqual(result, [])
            mock_log.warning.assert_called_with("pytrends not installed. Run: pip install pytrends")

    @patch("src.core.trend_engine.log")
    @patch.dict("sys.modules", {"pytrends.request": unittest.mock.MagicMock()})
    def test_get_google_trends_exception(self, mock_log):
        import sys
        mock_trend_req = sys.modules["pytrends.request"].TrendReq
        mock_trend_req.side_effect = Exception("Some weird error")

        result = get_google_trends(["test1"])
        self.assertEqual(result, [])
        mock_log.warning.assert_called_with("Google Trends failed: Some weird error")


    # ── YouTube Trends Tests ─────────────────────────────────────

    @patch("src.core.trend_engine.os.getenv")
    @patch("src.core.trend_engine.requests.get")
    def test_get_youtube_trending_success(self, mock_get, mock_getenv):
        mock_getenv.return_value = "fake_yt_key"
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "snippet": {
                        "title": "Test Video 1",
                        "channelTitle": "Test Channel",
                        "description": "Test Description " * 10,  # long description
                        "publishedAt": "2025-02-01T00:00:00Z"
                    }
                }
            ]
        }

        result = get_youtube_trending("test query")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Test Video 1")
        self.assertEqual(result[0]["channel"], "Test Channel")
        self.assertEqual(result[0]["description"], ("Test Description " * 10)[:100])

        mock_getenv.assert_called()

    @patch("src.core.trend_engine.os.getenv")
    @patch("src.core.trend_engine.log")
    def test_get_youtube_trending_no_key(self, mock_log, mock_getenv):
        mock_getenv.return_value = None
        result = get_youtube_trending("test query")
        self.assertEqual(result, [])
        mock_log.warning.assert_called_with("YOUTUBE_API_KEY not set — skipping YouTube trending search")

    @patch("src.core.trend_engine.os.getenv")
    @patch("src.core.trend_engine.requests.get")
    def test_get_youtube_trending_api_error(self, mock_get, mock_getenv):
        mock_getenv.return_value = "fake_yt_key"
        mock_response = mock_get.return_value
        mock_response.status_code = 403

        result = get_youtube_trending("test query")
        self.assertEqual(result, [])

    @patch("src.core.trend_engine.os.getenv")
    @patch("src.core.trend_engine.requests.get")
    def test_get_youtube_trending_exception(self, mock_get, mock_getenv):
        mock_getenv.return_value = "fake_yt_key"
        mock_get.side_effect = Exception("Connection Refused")

        result = get_youtube_trending("test query")
        self.assertEqual(result, [])


    # ── AI Synthesis Tests ───────────────────────────────────────

    @patch("src.core.trend_engine.os.getenv")
    @patch("src.core.trend_engine.requests.post")
    def test_synthesize_trends_with_ai_success(self, mock_post, mock_getenv):
        mock_getenv.return_value = "fake_gemini_key"

        expected_json = {
            "top_angles": ["Angle 1"],
            "trending_topics": ["topic1"],
            "viral_keywords": ["kw1"],
            "recommended_topic": "Rec topic",
            "hook_idea": "Hook",
            "best_thumbnail_concept": "Thumb"
        }

        mock_response = mock_post.return_value
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": f"```json\n{json.dumps(expected_json)}\n```"}
                        ]
                    }
                }
            ]
        }

        google_data = [{"query": "g1", "value": 1}]
        youtube_data = [{"title": "y1"}]
        ddg_data = ["d1"]

        result = synthesize_trends_with_ai("Test Channel", google_data, youtube_data, ddg_data)
        self.assertEqual(result, expected_json)

    @patch("src.core.trend_engine.os.getenv")
    def test_synthesize_trends_with_ai_no_key(self, mock_getenv):
        mock_getenv.return_value = None
        result = synthesize_trends_with_ai("Story With Aisha", [], [], [])
        self.assertIn("top_angles", result)
        self.assertEqual(result["recommended_topic"], "Office colleagues who fall in love during a project deadline")

    @patch("src.core.trend_engine.os.getenv")
    @patch("src.core.trend_engine.requests.post")
    @patch("src.core.trend_engine.log")
    def test_synthesize_trends_with_ai_exception(self, mock_log, mock_post, mock_getenv):
        mock_getenv.return_value = "fake_gemini_key"
        mock_post.side_effect = Exception("Gemini is down")

        result = synthesize_trends_with_ai("Unknown Channel", [], [], [])
        self.assertIn("top_angles", result)
        self.assertEqual(result["recommended_topic"], "A compelling story for your audience")
        mock_log.error.assert_called_with("AI synthesis failed: Gemini is down")

    def test_fallback_trend_report(self):
        res1 = _fallback_trend_report("Story With Aisha")
        self.assertEqual(res1["viral_keywords"], ["emotional story", "pyar ki kahani", "hindi love story", "romantic"])

        res2 = _fallback_trend_report("Riya's Dark Whisper")
        self.assertIn("forbidden romance", res2["trending_topics"])

        res3 = _fallback_trend_report("Some Other Channel")
        self.assertEqual(res3["recommended_topic"], "A compelling story for your audience")

if __name__ == "__main__":
    unittest.main()
