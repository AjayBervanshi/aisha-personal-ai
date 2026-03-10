import unittest
from unittest.mock import patch
from datetime import datetime

# build_system_prompt is actually in aisha_brain
from src.core.aisha_brain import build_system_prompt, detect_mood

class TestMoodDetector(unittest.TestCase):

    def test_default_mood(self):
        self.assertEqual(detect_mood("hello there, just checking in"), "casual")

    def test_multiple_keyword_matches(self):
        # A mix of romantic, angry, and finance.
        # "baby" (romantic - 1 pt)
        # "angry" (angry - 1 pt), "hate" (angry - 1 pt) -> Total 2
        # "money" (finance - 1 pt), "spend" (finance - 1 pt), "paisa" (finance - 1 pt) -> Total 3
        text = "baby i am so angry and hate that i had to spend my money and paisa"
        self.assertEqual(detect_mood(text), "finance")

    @patch('src.core.aisha_brain.datetime')
    def test_late_night_hour_detection(self, mock_datetime):
        # Mock datetime to 3 AM
        mock_datetime.now.return_value = datetime(2026, 3, 10, 3, 0, 0)

        context = {
            "mood": "casual",
            "language": "English",
            "memories": "",
            "today_tasks": "None",
            "profile": {}
        }

        prompt = build_system_prompt(context)

        self.assertIn("LATE NIGHT MODE:", prompt)

    @patch('src.core.aisha_brain.datetime')
    def test_day_time_mood_casual(self, mock_datetime):
        # Mock datetime to 3 PM
        mock_datetime.now.return_value = datetime(2026, 3, 10, 15, 0, 0)

        context = {
            "mood": "casual",
            "language": "English",
            "memories": "",
            "today_tasks": "None",
            "profile": {}
        }

        prompt = build_system_prompt(context)

        self.assertNotIn("LATE NIGHT MODE:", prompt)
        self.assertIn("CASUAL MODE:", prompt)

if __name__ == '__main__':
    unittest.main()
