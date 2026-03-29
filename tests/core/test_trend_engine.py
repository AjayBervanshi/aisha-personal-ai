import unittest
from src.core.trend_engine import _fallback_trend_report

class TestTrendEngineFallback(unittest.TestCase):
    def test_fallback_story_with_aisha(self):
        channel = "Story With Aisha"
        result = _fallback_trend_report(channel)

        self.assertIsInstance(result, dict)
        self.assertIn("top_angles", result)
        self.assertIn("trending_topics", result)
        self.assertIn("viral_keywords", result)
        self.assertIn("recommended_topic", result)
        self.assertIn("hook_idea", result)
        self.assertIn("best_thumbnail_concept", result)

        self.assertEqual(result["recommended_topic"], "Office colleagues who fall in love during a project deadline")
        self.assertIn("office romance", result["trending_topics"])

    def test_fallback_riyas_dark_whisper(self):
        channel = "Riya's Dark Whisper"
        result = _fallback_trend_report(channel)

        self.assertIsInstance(result, dict)
        self.assertIn("top_angles", result)
        self.assertIn("trending_topics", result)
        self.assertIn("viral_keywords", result)
        self.assertIn("recommended_topic", result)
        self.assertIn("hook_idea", result)
        self.assertIn("best_thumbnail_concept", result)

        self.assertEqual(result["recommended_topic"], "Forbidden boss-employee obsession in a Mumbai corporate office")
        self.assertIn("forbidden romance", result["trending_topics"])

    def test_fallback_unknown_channel(self):
        channel = "Unknown Test Channel 123"
        result = _fallback_trend_report(channel)

        self.assertIsInstance(result, dict)
        self.assertIn("top_angles", result)
        self.assertIn("trending_topics", result)
        self.assertIn("viral_keywords", result)
        self.assertIn("recommended_topic", result)
        self.assertIn("hook_idea", result)
        self.assertIn("best_thumbnail_concept", result)

        self.assertEqual(result["recommended_topic"], "A compelling story for your audience")
        self.assertIn("trending", result["trending_topics"])

if __name__ == '__main__':
    unittest.main()
