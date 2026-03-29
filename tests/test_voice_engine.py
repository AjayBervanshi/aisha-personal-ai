import unittest
from unittest.mock import patch
import os

from src.core import voice_engine

class TestVoiceEngine(unittest.TestCase):
    def setUp(self):
        # Save original state
        self.original_el_keys = voice_engine._EL_KEYS.copy() if hasattr(voice_engine, '_EL_KEYS') else []
        self.original_el_index = voice_engine._EL_INDEX if hasattr(voice_engine, '_EL_INDEX') else 0

        # Reset state for tests
        voice_engine._EL_KEYS = []
        voice_engine._EL_INDEX = 0

    def tearDown(self):
        # Restore original state
        voice_engine._EL_KEYS = self.original_el_keys
        voice_engine._EL_INDEX = self.original_el_index

    @patch('os.getenv')
    def test_get_next_el_key_round_robin(self, mock_getenv):
        # Mock the environment variable to return 3 valid keys
        mock_getenv.return_value = "key1,key2,key3"

        # First call should populate _EL_KEYS and return the first key
        self.assertEqual(voice_engine._get_next_el_key(), "key1")
        self.assertEqual(voice_engine._EL_KEYS, ["key1", "key2", "key3"])

        # Subsequent calls should return keys in round-robin fashion
        self.assertEqual(voice_engine._get_next_el_key(), "key2")
        self.assertEqual(voice_engine._get_next_el_key(), "key3")

        # After reaching the end, it should wrap around to the first key
        self.assertEqual(voice_engine._get_next_el_key(), "key1")

    @patch('os.getenv')
    def test_get_next_el_key_filtering(self, mock_getenv):
        # Mock the environment variable with empty keys, whitespace, and 'your_' keys
        mock_getenv.return_value = "  ,key1, your_api_key_here , key2 , ,, your_other_key"

        # The function should filter out empty, whitespace-only, and 'your_' keys
        self.assertEqual(voice_engine._get_next_el_key(), "key1")
        self.assertEqual(voice_engine._EL_KEYS, ["key1", "key2"])
        self.assertEqual(voice_engine._get_next_el_key(), "key2")
        self.assertEqual(voice_engine._get_next_el_key(), "key1")

    @patch('os.getenv')
    def test_get_next_el_key_empty(self, mock_getenv):
        # Mock the environment variable to return empty or invalid keys only
        mock_getenv.return_value = "your_key, ,  "

        # The function should return None when no valid keys are found
        self.assertIsNone(voice_engine._get_next_el_key())
        self.assertEqual(voice_engine._EL_KEYS, [])

if __name__ == '__main__':
    unittest.main()
