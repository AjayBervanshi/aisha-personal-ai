"""
voice_engine.py
===============
Aisha's Voice Engine — two modes:

CONTENT MODE (YouTube/Instagram production):
  Primary: ElevenLabs (premium quality, Hindi multilingual v2)
  Fallback: Edge-TTS (free, unlimited)
  Called via: generate_voice(..., use_for="content")

CHAT MODE (Telegram voice replies, morning greetings):
  Only: Microsoft Edge-TTS (free, unlimited, no quota burn)
  Called via: generate_voice(..., use_for="chat")  [default]

ElevenLabs Voices:
  - Aisha: wdymxIQkYn7MJCYCQF2Q (warm, emotional narrator)

Edge-TTS Voices:
  - Hindi: hi-IN-SwaraNeural (warm, natural)
  - English: en-IN-NeerjaExpressiveNeural
"""

import asyncio
import os
import uuid
import logging
import edge_tts

try:
    from src.core.logger import get_logger
    log = get_logger("VoiceEngine")
except Exception:
    log = logging.getLogger("VoiceEngine")

# ── Edge-TTS Voice Map ────────────────────────────────────────
VOICE_MAP = {
    "English":  "en-IN-NeerjaExpressiveNeural",
    "Hindi":    "hi-IN-SwaraNeural",
    "Marathi":  "mr-IN-AarohiNeural",
    "Hinglish": "en-IN-NeerjaExpressiveNeural",
}

CHANNEL_EDGE_TTS_VOICES: dict = {
    "Story With Aisha": "hi-IN-SwaraNeural",
}

# ── Mood-based voice tuning (Edge-TTS) ───────────────────────
MOOD_VOICE_SETTINGS = {
    "romantic":      {"rate": "-8%",  "pitch": "-3Hz"},
    "flirty":        {"rate": "-3%",  "pitch": "+1Hz"},
    "personal":      {"rate": "-6%",  "pitch": "-2Hz"},
    "late_night":    {"rate": "-10%", "pitch": "-4Hz"},
    "motivational":  {"rate": "+5%",  "pitch": "+2Hz"},
    "professional":  {"rate": "+2%",  "pitch": "+0Hz"},
    "finance":       {"rate": "+1%",  "pitch": "+0Hz"},
    "angry":         {"rate": "+3%",  "pitch": "+1Hz"},
    "casual":        {"rate": "-2%",  "pitch": "-1Hz"},
    "storytelling":  {"rate": "-5%",  "pitch": "-2Hz"},
}

# Temp directory for voice files
VOICE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "temp_voice")
os.makedirs(VOICE_DIR, exist_ok=True)

# Clean up stale voice files (>10 min old) on import
try:
    import time as _t
    _now = _t.time()
    for _f in os.listdir(VOICE_DIR):
        _fp = os.path.join(VOICE_DIR, _f)
        if os.path.isfile(_fp) and (_now - os.path.getmtime(_fp)) > 600:
            os.remove(_fp)
except Exception:
    pass


# ═══════════════════════════════════════════════════════════════
# ELEVENLABS — Primary voice for content production
# ═══════════════════════════════════════════════════════════════

_EL_KEYS = []
_EL_INDEX = 0
_EL_QUOTA_CACHE: dict = {}
_EL_FAILED_KEYS: set = set()


def _init_el_keys():
    """Load ElevenLabs keys from env (comma-separated pool)."""
    global _EL_KEYS
    if not _EL_KEYS:
        env_keys = os.getenv("ELEVENLABS_API_KEY", "")
        _EL_KEYS = [k.strip() for k in env_keys.split(",") if k.strip() and "your_" not in k.lower()]


def _get_elevenlabs_chars_left(api_key: str) -> int:
    """Return remaining characters on this ElevenLabs key (cached per session)."""
    if api_key in _EL_QUOTA_CACHE:
        return _EL_QUOTA_CACHE[api_key]
    try:
        import requests as _req
        r = _req.get("https://api.elevenlabs.io/v1/user",
                     headers={"xi-api-key": api_key}, timeout=8)
        if r.status_code == 200:
            sub = r.json().get("subscription", {})
            left = sub.get("character_limit", 0) - sub.get("character_count", 0)
            _EL_QUOTA_CACHE[api_key] = left
            return left
        elif r.status_code == 401:
            log.warning(f"[ElevenLabs] Key invalid (401)")
            _EL_FAILED_KEYS.add(api_key)
    except Exception as e:
        log.warning(f"[ElevenLabs] Quota check failed: {e}")
    _EL_QUOTA_CACHE[api_key] = 0
    return 0


def _get_next_el_key() -> str | None:
    """Round-robin through ElevenLabs keys, skipping permanently failed ones."""
    global _EL_INDEX
    _init_el_keys()
    if not _EL_KEYS:
        return None
    for _ in range(len(_EL_KEYS)):
        key = _EL_KEYS[_EL_INDEX % len(_EL_KEYS)]
        _EL_INDEX = (_EL_INDEX + 1) % len(_EL_KEYS)
        if key not in _EL_FAILED_KEYS:
            return key
    return None


def _generate_elevenlabs(text: str, language: str = "Hindi", channel: str = None) -> str | None:
    """Generate voice via ElevenLabs. Returns filepath or None on failure."""
    import requests

    _init_el_keys()
    attempts = max(len(_EL_KEYS), 1)

    for _ in range(attempts):
        api_key = _get_next_el_key()
        if not api_key:
            log.warning("[ElevenLabs] No valid API keys available")
            return None

        # Check quota before burning characters
        chars_left = _get_elevenlabs_chars_left(api_key)
        text_len = len(text)
        if chars_left < text_len + 100:
            log.warning(f"[ElevenLabs] Quota too low ({chars_left} chars, need ~{text_len})")
            continue

        # Voice selection — Aisha's voice for content
        if channel:
            from src.core.config import CHANNEL_VOICE_IDS
            voice_id = CHANNEL_VOICE_IDS.get(channel, "wdymxIQkYn7MJCYCQF2Q")
        else:
            voice_id = os.getenv("AISHA_ELEVENLABS_VOICE_ID", "wdymxIQkYn7MJCYCQF2Q")

        filename = f"aisha_el_{uuid.uuid4().hex[:8]}.mp3"
        filepath = os.path.join(VOICE_DIR, filename)
        clean_text = _clean_for_speech(text)

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key,
        }
        voice_settings = {
            "stability": 0.45,
            "similarity_boost": 0.78,
            "style": 0.40,
            "use_speaker_boost": True,
        }
        data = {
            "text": clean_text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": voice_settings,
        }

        try:
            response = requests.post(url, json=data, headers=headers, timeout=120)

            if response.status_code == 200 and len(response.content) > 1000:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                # Update quota cache
                _EL_QUOTA_CACHE[api_key] = max(0, chars_left - text_len)
                log.info(f"[ElevenLabs] Voice generated ({len(response.content)} bytes, ~{chars_left - text_len} chars left)")
                return filepath

            if response.status_code == 401:
                log.error(f"[ElevenLabs] Invalid API key (401)")
                _EL_FAILED_KEYS.add(api_key)
                continue
            elif response.status_code in (402, 422):
                log.warning(f"[ElevenLabs] Quota exceeded ({response.status_code})")
                _EL_QUOTA_CACHE[api_key] = 0
                continue
            elif response.status_code == 429:
                log.warning(f"[ElevenLabs] Rate limited (429) — waiting 5s")
                import time
                time.sleep(5)
                continue
            else:
                log.error(f"[ElevenLabs] HTTP {response.status_code}: {response.text[:200]}")
                continue

        except requests.exceptions.Timeout:
            log.warning("[ElevenLabs] Request timed out")
            continue
        except Exception as e:
            log.error(f"[ElevenLabs] Error: {e}")
            continue

    return None


# ═══════════════════════════════════════════════════════════════
# EDGE-TTS — Free voice for chat + fallback for content
# ═══════════════════════════════════════════════════════════════

async def _generate_edge_tts_async(
    text: str,
    language: str = "English",
    mood: str = "casual",
    channel: str = None,
) -> str:
    """Generate voice via Edge-TTS. Returns path to .mp3 file."""
    if channel and channel in CHANNEL_EDGE_TTS_VOICES:
        voice = CHANNEL_EDGE_TTS_VOICES[channel]
    else:
        voice = VOICE_MAP.get(language, VOICE_MAP["English"])

    settings = MOOD_VOICE_SETTINGS.get(mood, MOOD_VOICE_SETTINGS["casual"])

    filename = f"aisha_edge_{uuid.uuid4().hex[:8]}.mp3"
    filepath = os.path.join(VOICE_DIR, filename)

    clean_text = _clean_for_speech(text)

    communicate = edge_tts.Communicate(
        clean_text,
        voice=voice,
        rate=settings["rate"],
        pitch=settings["pitch"],
    )
    await communicate.save(filepath)
    return filepath


def _run_edge_tts(text: str, language: str, mood: str, channel: str = None) -> str | None:
    """Synchronous wrapper for Edge-TTS async generation."""
    try:
        try:
            asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    _generate_edge_tts_async(text, language, mood, channel=channel),
                )
                return future.result(timeout=60)
        except RuntimeError:
            return asyncio.run(_generate_edge_tts_async(text, language, mood, channel=channel))
    except Exception as e:
        log.error(f"[Edge-TTS] Error: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# TRANSLITERATION
# ═══════════════════════════════════════════════════════════════

def _transliterate_hinglish(text: str) -> str:
    """Transliterate Roman Hinglish to Devanagari via Gemini Flash."""
    try:
        import requests as _req
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return text

        prompt = (
            "Transliterate the following Roman Hinglish text exactly into Devanagari script (Hindi). "
            "Return ONLY the pure Devanagari translation, nothing else, no quotes, no extra words:\n\n"
            f"{text}"
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        resp = _req.post(url, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        log.warning(f"[Transliterate] Failed, using original: {e}")

    return text


# ═══════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════

def generate_voice(
    text: str,
    language: str = "English",
    mood: str = "casual",
    channel: str = None,
    use_for: str = "chat",
    force_elevenlabs: bool = False,
    voice_id: str = None,
) -> str | None:
    """
    Generate voice audio from text. Returns path to .mp3 file.

    Args:
        text: Text to speak
        language: Language (English/Hindi/Marathi/Hinglish)
        mood: Mood for voice tuning
        channel: YouTube channel name
        use_for: "content" = ElevenLabs primary (YouTube/Instagram)
                 "chat" = Edge-TTS only (Telegram chat, free)
        force_elevenlabs: Legacy param — treated as use_for="content"
        voice_id: Unused legacy param, kept for backward compat
    """
    if not text or not text.strip():
        return None

    if language in ("Hinglish", "Hindi"):
        text = _transliterate_hinglish(text)

    # Legacy support: force_elevenlabs=True → content mode
    if force_elevenlabs:
        use_for = "content"

    if use_for == "content":
        # ── CONTENT MODE: ElevenLabs primary, Edge-TTS fallback ──
        log.info("[Voice] Content mode — trying ElevenLabs first")
        result = _generate_elevenlabs(text, language=language, channel=channel)
        if result:
            return result
        log.warning("[Voice] ElevenLabs failed for content — falling back to Edge-TTS")
        return _run_edge_tts(text, language, mood or "storytelling", channel=channel)
    else:
        # ── CHAT MODE: Edge-TTS only (free, unlimited) ───────────
        return _run_edge_tts(text, language, mood, channel=channel)


def generate_voice_for_content(
    text: str,
    language: str = "Hindi",
    channel: str = None,
) -> str | None:
    """Convenience wrapper for content production — always uses ElevenLabs primary."""
    return generate_voice(text, language=language, mood="storytelling", channel=channel, use_for="content")


def cleanup_voice_file(filepath: str):
    """Delete a temporary voice file after sending."""
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        log.error(f"[Voice] Cleanup failed: {filepath} — {e}")


# ═══════════════════════════════════════════════════════════════
# TEXT CLEANING
# ═══════════════════════════════════════════════════════════════

def _clean_for_speech(text: str) -> str:
    """Clean text for TTS — remove non-spoken elements while preserving natural flow."""
    import re

    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u2640-\u2642"
        "\u2600-\u2B55"
        "\u200d\u23cf\u23e9\u231a"
        "\ufe0f\u3030"
        "]+", flags=re.UNICODE
    )
    text = emoji_pattern.sub('', text)

    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'━+', '', text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'^(?:TITLE|DESCRIPTION|CAPTION|HASHTAGS|THUMBNAIL|SEO|HOOK|CTA)[:\s].*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'^(?:भाग|PART)\s*\d+.*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'\.{3,}', '...', text)
    text = re.sub(r'#\w+', '', text)
    text = re.sub(r'\n{2,}', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = text.strip()

    return text


# ── Quick test ────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing Aisha's Voice Engine...\n")

    print("=== CHAT MODE (Edge-TTS) ===")
    path = generate_voice("Hey Ajay, how are you doing today?", "English", "casual", use_for="chat")
    if path:
        print(f"  Chat voice: {os.path.basename(path)} ({os.path.getsize(path) / 1024:.1f} KB)")
    else:
        print("  Chat voice: FAILED")

    print("\n=== CONTENT MODE (ElevenLabs → Edge-TTS fallback) ===")
    path = generate_voice(
        "उसने मेरा हाथ पकड़ा... और बोला, तुम कहीं मत जाना। मैं तुम्हारे बिना नहीं रह सकता।",
        "Hindi", "storytelling", use_for="content",
    )
    if path:
        print(f"  Content voice: {os.path.basename(path)} ({os.path.getsize(path) / 1024:.1f} KB)")
    else:
        print("  Content voice: FAILED")

    print("\nDone! Check temp_voice/ folder.")
