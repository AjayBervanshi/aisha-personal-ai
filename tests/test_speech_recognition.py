import unittest
from unittest.mock import patch, MagicMock
import sys

# Mock src.core.ai_router and src.core.config before importing
sys.modules['src.core.ai_router'] = MagicMock()
sys.modules['src.core.config'] = MagicMock()

from src.core.speech_recognition import parse_transcript

class TestSpeechRecognition(unittest.TestCase):
    def test_parse_transcript_normal(self):
        result = parse_transcript("play some music")
        self.assertEqual(result, {"command": "play", "params": ["some", "music"]})

    def test_parse_transcript_varying_case(self):
        result = parse_transcript("PLAY music")
        self.assertEqual(result, {"command": "play", "params": ["music"]})

    def test_parse_transcript_single_word(self):
        result = parse_transcript("stop")
        self.assertEqual(result, {"command": "stop", "params": []})

    def test_parse_transcript_empty(self):
        result = parse_transcript("")
        self.assertEqual(result, {})

    def test_parse_transcript_whitespace(self):
        result = parse_transcript("   ")
        self.assertEqual(result, {})

    def test_parse_transcript_invalid_type(self):
        result = parse_transcript(None)
        self.assertEqual(result, {})

if __name__ == '__main__':
    unittest.main()
