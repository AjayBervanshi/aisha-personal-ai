import unittest
from unittest.mock import patch, MagicMock
import sys

# Mock src.core.ai_router and src.core.config before importing
sys.modules['src.core.ai_router'] = MagicMock()
sys.modules['src.core.config'] = MagicMock()

import speech_recognition as sr
from src.core.speech_recognition import parse_transcript, transcribe_voice_note, execute_command

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

    @patch('src.core.speech_recognition.AudioSegment.from_file')
    @patch('src.core.speech_recognition.sr.Recognizer')
    @patch('src.core.speech_recognition.sr.AudioFile')
    def test_transcribe_voice_note_success(self, mock_audio_file, mock_recognizer, mock_from_file):
        # Mocking AudioSegment
        mock_sound = MagicMock()
        mock_from_file.return_value = mock_sound

        # Mocking sr.Recognizer
        mock_r = MagicMock()
        mock_recognizer.return_value = mock_r
        mock_r.recognize_google.return_value = "hello world"

        # Mocking sr.AudioFile
        mock_source = MagicMock()
        mock_audio_file.return_value.__enter__.return_value = mock_source

        # Test
        result = transcribe_voice_note("dummy.ogg")

        # Asserts
        self.assertEqual(result, "hello world")
        mock_from_file.assert_called_once_with("dummy.ogg")
        mock_sound.export.assert_called_once_with("temp.wav", format="wav")
        mock_r.record.assert_called_once_with(mock_source)
        mock_r.recognize_google.assert_called_once()

    @patch('src.core.speech_recognition.AudioSegment.from_file')
    @patch('src.core.speech_recognition.sr.Recognizer')
    @patch('src.core.speech_recognition.sr.AudioFile')
    def test_transcribe_voice_note_unknown_value_error(self, mock_audio_file, mock_recognizer, mock_from_file):
        mock_sound = MagicMock()
        mock_from_file.return_value = mock_sound

        mock_r = MagicMock()
        mock_recognizer.return_value = mock_r
        mock_r.recognize_google.side_effect = sr.UnknownValueError("Could not understand")

        mock_source = MagicMock()
        mock_audio_file.return_value.__enter__.return_value = mock_source

        result = transcribe_voice_note("dummy.ogg")

        self.assertEqual(result, "")

    @patch('src.core.speech_recognition.AudioSegment.from_file')
    @patch('src.core.speech_recognition.sr.Recognizer')
    @patch('src.core.speech_recognition.sr.AudioFile')
    def test_transcribe_voice_note_request_error(self, mock_audio_file, mock_recognizer, mock_from_file):
        mock_sound = MagicMock()
        mock_from_file.return_value = mock_sound

        mock_r = MagicMock()
        mock_recognizer.return_value = mock_r
        mock_r.recognize_google.side_effect = sr.RequestError("API unavailable")

        mock_source = MagicMock()
        mock_audio_file.return_value.__enter__.return_value = mock_source

        result = transcribe_voice_note("dummy.ogg")

        self.assertEqual(result, "")

    @patch('src.core.speech_recognition.execute_ai_command')
    def test_execute_command_success(self, mock_execute_ai_command):
        command = {"command": "play", "params": ["music"]}
        execute_command(command)
        mock_execute_ai_command.assert_called_once_with("play", ["music"])

    @patch('src.core.speech_recognition.execute_ai_command')
    @patch('src.core.speech_recognition.logger')
    def test_execute_command_exception(self, mock_logger, mock_execute_ai_command):
        mock_execute_ai_command.side_effect = Exception("Test Exception")
        command = {"command": "invalid", "params": []}

        # Should not raise exception, should be caught and logged
        execute_command(command)

        mock_execute_ai_command.assert_called_once_with("invalid", [])
        mock_logger.error.assert_called_once()

if __name__ == '__main__':
    unittest.main()
