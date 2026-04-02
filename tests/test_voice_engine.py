import unittest
import os
from unittest.mock import patch
from src.core.voice_engine import cleanup_voice_file

class TestVoiceEngine(unittest.TestCase):
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


class TestGetNextElKey(unittest.TestCase):
    def setUp(self):
        import src.core.voice_engine as voice_engine
        self.ve = voice_engine
        self.ve._EL_KEYS = []
        self.ve._EL_INDEX = 0

    @patch('src.core.voice_engine.os.getenv')
    def test_get_next_el_key_no_keys(self, mock_getenv):
        """Test behavior when no valid keys are found."""
        mock_getenv.return_value = ""
        self.assertIsNone(self.ve._get_next_el_key())

        mock_getenv.return_value = "   ,   "
        # Since _EL_KEYS might be modified by the first call, reset it just in case
        self.ve._EL_KEYS = []
        self.assertIsNone(self.ve._get_next_el_key())

    @patch('src.core.voice_engine.os.getenv')
    def test_get_next_el_key_valid_keys(self, mock_getenv):
        """Test round-robin distribution with valid keys."""
        mock_getenv.return_value = "key1,key2,key3"

        self.assertEqual(self.ve._get_next_el_key(), "key1")
        self.assertEqual(self.ve._get_next_el_key(), "key2")
        self.assertEqual(self.ve._get_next_el_key(), "key3")
        self.assertEqual(self.ve._get_next_el_key(), "key1")
        self.assertEqual(self.ve._get_next_el_key(), "key2")

    @patch('src.core.voice_engine.os.getenv')
    def test_get_next_el_key_filter_invalid(self, mock_getenv):
        """Test filtering out placeholder keys containing 'your_'."""
        mock_getenv.return_value = "key1, your_api_key_here, key2, your_other_key"

        self.assertEqual(self.ve._get_next_el_key(), "key1")
        self.assertEqual(self.ve._get_next_el_key(), "key2")
        self.assertEqual(self.ve._get_next_el_key(), "key1")

if __name__ == '__main__':
    unittest.main()
