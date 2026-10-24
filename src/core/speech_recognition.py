import logging
import speech_recognition as sr
from pydub import AudioSegment
from src.core.ai_router import execute_ai_command
from src.core.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def transcribe_voice_note(audio_file: str) -> str:
    """
    Transcribes a voice note from an audio file.

    Args:
    audio_file (str): The path to the audio file.

    Returns:
    str: The transcript of the voice note.
    """
    try:
        sound = AudioSegment.from_file(audio_file)
        sound.export("temp.wav", format="wav")
        r = sr.Recognizer()
        with sr.AudioFile("temp.wav") as source:
            audio = r.record(source)
        transcript = r.recognize_google(audio)
        logger.info(f"Transcript: {transcript}")
        return transcript
    except sr.UnknownValueError:
        logger.error("Speech recognition could not understand audio")
        return ""
    except sr.RequestError as e:
        logger.error(f"Could not request results from Google Speech Recognition service; {e}")
        return ""

def parse_transcript(transcript: str) -> dict:
    """
    Parses a transcript to identify and execute commands.

    Args:
    transcript (str): The transcript to parse.

    Returns:
    dict: A dictionary containing the command and its parameters.
    """
    try:
        # Simple command parsing for demonstration purposes
        command_parts = transcript.split()
        command = command_parts[0].lower()
        params = command_parts[1:]
        return {"command": command, "params": params}
    except Exception as e:
        logger.error(f"Error parsing transcript: {e}")
        return {}

def execute_command(command: dict) -> None:
    """
    Executes a command based on the parsed transcript.

    Args:
    command (dict): A dictionary containing the command and its parameters.
    """
    try:
        execute_ai_command(command["command"], command["params"])
    except Exception as e:
        logger.error(f"Error executing command: {e}")

if __name__ == "__main__":
    config = Config()
    audio_file = "test_audio.mp3"
    transcript = transcribe_voice_note(audio_file)
    command = parse_transcript(transcript)
    execute_command(command)