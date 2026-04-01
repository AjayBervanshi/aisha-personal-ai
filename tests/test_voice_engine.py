import unittest
import os
from unittest.mock import patch
from src.core.voice_engine import cleanup_voice_file, _get_next_el_key
import src.core.voice_engine as voice_engine

class TestVoiceEngine(unittest.TestCase):
    def setUp(self):
        # Reset globals before each test
        voice_engine._EL_KEYS = []
        voice_engine._EL_INDEX = 0

    @patch('src.core.voice_engine.os.remove')
    @patch('src.core.voice_engine.os.path.exists')
    def test_cleanup_voice_file_success(self, mock_exists, mock_remove):
        """Test successful cleanup of a voice file."""
        mock_exists.return_value = True

        filepath = "fake_audio.mp3"
        cleanup_voice_file(filepath)

        mock_exists.assert_called_once_with(filepath)
        mock_remove.assert_called_once_with(filepath)

    @patch('src.core.voice_engine.os.remove')
    @patch('src.core.voice_engine.os.path.exists')
    def test_cleanup_voice_file_not_exists(self, mock_exists, mock_remove):
        """Test cleanup when the file does not exist."""
        mock_exists.return_value = False

        filepath = "missing_audio.mp3"
        cleanup_voice_file(filepath)

        mock_exists.assert_called_once_with(filepath)
        mock_remove.assert_not_called()

    @patch('src.core.voice_engine.os.remove')
    @patch('src.core.voice_engine.os.path.exists')
    def test_cleanup_voice_file_none(self, mock_exists, mock_remove):
        """Test cleanup with None as filepath."""
        cleanup_voice_file(None)

        mock_exists.assert_not_called()
        mock_remove.assert_not_called()

    @patch('src.core.voice_engine.os.remove')
    @patch('src.core.voice_engine.os.path.exists')
    def test_cleanup_voice_file_empty_string(self, mock_exists, mock_remove):
        """Test cleanup with empty string as filepath."""
        cleanup_voice_file("")

        mock_exists.assert_not_called()
        mock_remove.assert_not_called()

    @patch('src.core.voice_engine.os.remove')
    @patch('src.core.voice_engine.os.path.exists')
    def test_cleanup_voice_file_exception(self, mock_exists, mock_remove):
        """Test cleanup handles exception when os.remove fails."""
        mock_exists.return_value = True
        mock_remove.side_effect = PermissionError("Cannot delete file")

        filepath = "locked_audio.mp3"
        # This should not raise an exception, as it's caught in the function
        cleanup_voice_file(filepath)

        mock_exists.assert_called_once_with(filepath)
        mock_remove.assert_called_once_with(filepath)

    @patch.dict(os.environ, {"ELEVENLABS_API_KEY": ""})
    def test_get_next_el_key_no_env_var(self):
        """Test when ELEVENLABS_API_KEY is empty."""
        self.assertIsNone(_get_next_el_key())

    @patch.dict(os.environ, {"ELEVENLABS_API_KEY": "your_api_key_here, , your_second_key"})
    def test_get_next_el_key_invalid_env_var(self):
        """Test when ELEVENLABS_API_KEY only has invalid or empty keys."""
        self.assertIsNone(_get_next_el_key())

    @patch.dict(os.environ, {"ELEVENLABS_API_KEY": "valid_key_1"})
    def test_get_next_el_key_single_key(self):
        """Test single valid key is returned consistently and index advances (modulo handles it)."""
        self.assertEqual(_get_next_el_key(), "valid_key_1")
        self.assertEqual(voice_engine._EL_INDEX, 0) # Index advances but is modulo 1, so it becomes 0
        self.assertEqual(_get_next_el_key(), "valid_key_1")
        self.assertEqual(voice_engine._EL_INDEX, 0)

    @patch.dict(os.environ, {"ELEVENLABS_API_KEY": "key1, key2, key3"})
    def test_get_next_el_key_multiple_keys_round_robin(self):
        """Test round-robin distribution with multiple valid keys."""
        self.assertEqual(_get_next_el_key(), "key1")
        self.assertEqual(voice_engine._EL_INDEX, 1)
        self.assertEqual(_get_next_el_key(), "key2")
        self.assertEqual(voice_engine._EL_INDEX, 2)
        self.assertEqual(_get_next_el_key(), "key3")
        self.assertEqual(voice_engine._EL_INDEX, 0)
        self.assertEqual(_get_next_el_key(), "key1")
        self.assertEqual(voice_engine._EL_INDEX, 1)

    @patch.dict(os.environ, {"ELEVENLABS_API_KEY": "key1, your_key, , key2, your_other_key"})
    def test_get_next_el_key_mixed_valid_invalid(self):
        """Test with a mix of valid, invalid, and empty keys."""
        self.assertEqual(_get_next_el_key(), "key1")
        self.assertEqual(_get_next_el_key(), "key2")
        self.assertEqual(_get_next_el_key(), "key1")
        self.assertEqual(voice_engine._EL_KEYS, ["key1", "key2"])

if __name__ == '__main__':
    unittest.main()
