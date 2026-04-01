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

    @patch('src.core.voice_engine.os.remove')
    @patch('src.core.voice_engine.os.path.exists')
    def test_cleanup_voice_file_exists_exception(self, mock_exists, mock_remove):
        """Test cleanup handles exception when os.path.exists fails."""
        mock_exists.side_effect = Exception("Cannot check path")

        filepath = "locked_dir/audio.mp3"
        # This should not raise an exception, as it's caught in the function
        cleanup_voice_file(filepath)

        mock_exists.assert_called_once_with(filepath)
        mock_remove.assert_not_called()

if __name__ == '__main__':

    unittest.main()
