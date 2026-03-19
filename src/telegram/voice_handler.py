"""
voice_handler.py
================
Handles voice messages sent to Aisha on Telegram.
Transcribes audio using Gemini, then passes text to the brain.
"""

import os
import tempfile
import logging
from pathlib import Path

log = logging.getLogger("Aisha.Voice")


def transcribe_voice_message(bot, message) -> str | None:
    """
    Download a Telegram voice message and transcribe it using Gemini.
    Returns: transcribed text string, or None on failure.
    """
    try:
        import groq

        # Download the voice file from Telegram
        file_info = bot.get_file(message.voice.file_id)
        downloaded = bot.download_file(file_info.file_path)

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(downloaded)
            voice_path = f.name

        try:
            # Transcribe via Groq Whisper (no DNS issues, works on Render)
            client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))
            with open(voice_path, "rb") as audio_f:
                result = client.audio.transcriptions.create(
                    file=(Path(voice_path).name, audio_f.read()),
                    model="whisper-large-v3",
                    prompt="Hindi, English, or Marathi voice message",
                    response_format="text",
                )
            transcription = result.strip() if isinstance(result, str) else result.text.strip()
            log.info(f"Transcribed voice: {transcription[:80]}")
            return transcription

        finally:
            Path(voice_path).unlink(missing_ok=True)

    except Exception as e:
        log.error(f"Voice transcription failed: {e}")
        return None


def get_voice_error_message() -> str:
    """Return a friendly error message when voice transcription fails."""
    return (
        "Arre Ajay, I couldn't catch that voice note 😅\n"
        "My hearing seems to be acting up! Try typing it out? 💜"
    )
