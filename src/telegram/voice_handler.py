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
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

        # Download the voice file from Telegram
        file_info = bot.get_file(message.voice.file_id)
        downloaded = bot.download_file(file_info.file_path)

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(downloaded)
            voice_path = f.name

        try:
            # Upload to Gemini and transcribe
            audio_file = genai.upload_file(voice_path)
            model = genai.GenerativeModel("gemini-1.5-flash")
            result = model.generate_content([
                (
                    "Please transcribe this voice message exactly as spoken. "
                    "It may be in English, Hindi (Devanagari or Roman), or Marathi. "
                    "Return ONLY the transcription — no extra text, no translation."
                ),
                audio_file
            ])
            transcription = result.text.strip()
            log.info(f"Transcribed voice: {transcription[:80]}")
            return transcription

        finally:
            # Clean up temp file
            Path(voice_path).unlink(missing_ok=True)
            try:
                genai.delete_file(audio_file.name)
            except Exception:
                pass

    except ImportError:
        log.error("google-generativeai not installed. Run: pip install google-generativeai")
        return None
    except Exception as e:
        log.error(f"Voice transcription failed: {e}")
        return None


def get_voice_error_message() -> str:
    """Return a friendly error message when voice transcription fails."""
    return (
        "Arre Ajay, I couldn't catch that voice note 😅\n"
        "My hearing seems to be acting up! Try typing it out? 💜"
    )
