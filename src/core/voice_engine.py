"""
voice_engine.py
===============
Aisha's Voice Engine — converts text responses to natural-sounding speech.
Primary: ElevenLabs (premium quality, character-specific voices).
Fallback: Microsoft Edge-TTS (100% free, unlimited, no API key needed).

Voices:
  - English:  en-IN-NeerjaExpressiveNeural (warm, soothing Indian female)
  - Hindi:    hi-IN-SwaraNeural (natural Hindi female — Aisha)
  - Hindi:    hi-IN-MadhurNeural (dark, bold Hindi female — Riya)
  - Marathi:  mr-IN-AarohiNeural (natural Marathi female)

The voice adapts based on detected language and mood — slower and deeper
for emotional/romantic moments, energetic for motivation, crisp for professional.
"""

import asyncio
import os
import uuid
import edge_tts
from src.core.logger import get_logger

log = get_logger("VoiceEngine")

# ── Voice Map — language-based defaults ──────────────────────
VOICE_MAP = {
    "English":  "en-IN-NeerjaExpressiveNeural",
    "Hindi":    "hi-IN-SwaraNeural",        # Aisha default: warm, natural Hindi
    "Marathi":  "mr-IN-AarohiNeural",
    "Hinglish": "en-IN-NeerjaExpressiveNeural",  # Hinglish uses English voice
}

# ── Channel → Edge-TTS voice mapping ─────────────────────────
# Aisha channels: hi-IN-SwaraNeural  (warm, gentle, emotional)
# Riya channels:  hi-IN-MadhurNeural (darker, bolder tone)
CHANNEL_EDGE_TTS_VOICES: dict = {
    "Story With Aisha":            "hi-IN-SwaraNeural",
    "Riya's Dark Whisper":         "hi-IN-MadhurNeural",
    "Riya's Dark Romance Library": "hi-IN-MadhurNeural",
    "Aisha & Him":                 "hi-IN-SwaraNeural",
}

# ── Mood-based voice tuning ───────────────────────────────────
# Optimized for natural, human-like narration.
# Rate: negative = slower, positive = faster
# Pitch: negative Hz = deeper/warmer, positive = brighter
MOOD_VOICE_SETTINGS = {
    "romantic":      {"rate": "-8%",  "pitch": "-3Hz"},   # Warm, intimate but not too slow
    "flirty":        {"rate": "-3%",  "pitch": "+1Hz"},   # Playful, natural
    "personal":      {"rate": "-6%",  "pitch": "-2Hz"},   # Soft, gentle
    "late_night":    {"rate": "-10%", "pitch": "-4Hz"},   # Soulful, quiet
    "motivational":  {"rate": "+5%",  "pitch": "+2Hz"},   # Energetic but clear
    "professional":  {"rate": "+2%",  "pitch": "+0Hz"},   # Crisp, neutral
    "finance":       {"rate": "+1%",  "pitch": "+0Hz"},   # Clear, structured
    "angry":         {"rate": "+3%",  "pitch": "+1Hz"},   # Direct but not harsh
    "casual":        {"rate": "-2%",  "pitch": "-1Hz"},   # Natural, relaxed
    "storytelling":  {"rate": "-5%",  "pitch": "-2Hz"},   # Smooth narration pace
}

# Temp directory for voice files
VOICE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "temp_voice")
os.makedirs(VOICE_DIR, exist_ok=True)

# Clean up any stale voice files left from previous runs (>10 min old)
try:
    import time as _t
    _now = _t.time()
    for _f in os.listdir(VOICE_DIR):
        _fp = os.path.join(VOICE_DIR, _f)
        if os.path.isfile(_fp) and (_now - os.path.getmtime(_fp)) > 600:
            os.remove(_fp)
except Exception as e:
    log.error("stale_voice_cleanup_failed", extra={"error": str(e)})


async def _generate_voice_async(
    text: str,
    language: str = "English",
    mood: str = "casual",
    channel: str = None
) -> str:
    """
    Generate voice audio from text using Edge-TTS. Returns path to the .mp3 file.

    Args:
        text: The text to convert to speech
        language: Detected language (English/Hindi/Marathi/Hinglish)
        mood: Current conversation mood for voice tuning
        channel: YouTube channel name — drives character-specific voice selection

    Returns:
        Absolute path to the generated .mp3 file
    """
    # Channel takes priority: use character-specific Edge-TTS voice
    if channel and channel in CHANNEL_EDGE_TTS_VOICES:
        voice = CHANNEL_EDGE_TTS_VOICES[channel]
    else:
        # Select voice based on language
        voice = VOICE_MAP.get(language, VOICE_MAP["English"])
    
    # Get mood-specific rate and pitch
    settings = MOOD_VOICE_SETTINGS.get(mood, MOOD_VOICE_SETTINGS["casual"])
    rate = settings["rate"]
    pitch = settings["pitch"]
    
    # Generate unique filename
    filename = f"aisha_voice_{uuid.uuid4().hex[:8]}.mp3"
    filepath = os.path.join(VOICE_DIR, filename)
    
    # Clean text for speech (remove emojis and special chars that sound weird)
    clean_text = _clean_for_speech(text)
    
    # Generate speech
    communicate = edge_tts.Communicate(
        clean_text,
        voice=voice,
        rate=rate,
        pitch=pitch
    )
    await communicate.save(filepath)
    
    return filepath


# ── ElevenLabs Key Pool ───────────────────────────────────────
_EL_KEYS = []
_EL_INDEX = 0
_EL_QUOTA_CACHE: dict = {}   # {key: chars_left}  — refreshed once per session
_EL_QUOTA_MIN = 1000          # Disable ElevenLabs below this threshold


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
    except Exception as e:
        log.warning("elevenlabs_quota_check_failed", extra={"error": str(e)})
    _EL_QUOTA_CACHE[api_key] = 0
    return 0

def _get_next_el_key():
    global _EL_KEYS, _EL_INDEX
    if not _EL_KEYS:
        env_keys = os.getenv("ELEVENLABS_API_KEY", "")
        _EL_KEYS = [k.strip() for k in env_keys.split(",") if k.strip() and "your_" not in k]
    if not _EL_KEYS:
        return None
    key = _EL_KEYS[_EL_INDEX % len(_EL_KEYS)]
    # Advance index on each successful fetch for round-robin distribution
    _EL_INDEX = (_EL_INDEX + 1) % len(_EL_KEYS)
    return key

def _mark_key_failed():
    global _EL_KEYS, _EL_INDEX
    if _EL_KEYS:
        print(f"[ElevenLabs] Key failed or exhausted (index {_EL_INDEX}) — rotating to next key.")
        _EL_INDEX = (_EL_INDEX + 1) % len(_EL_KEYS)

def _generate_elevenlabs(text: str, language: str = "English", mood: str = "casual", channel: str = None) -> str:
    import requests

    # Try multiple keys from the pool
    for _ in range(len(_EL_KEYS) or 1):
        api_key = _get_next_el_key()
        if not api_key:
            return None

        # Channel-aware voice selection (channel takes priority over mood)
        if channel:
            from src.core.config import CHANNEL_VOICE_IDS
            voice_id = CHANNEL_VOICE_IDS.get(channel, "wdymxIQkYn7MJCYCQF2Q")
        elif mood in ["romantic", "flirty", "late_night", "riya"]:
            riya_id = os.getenv("RIYA_ELEVENLABS_VOICE_ID", "BpjGufoPiobT79j2vtj4")
            voice_id = riya_id if riya_id else "wdymxIQkYn7MJCYCQF2Q"
        else:
            voice_id = os.getenv("AISHA_ELEVENLABS_VOICE_ID", "wdymxIQkYn7MJCYCQF2Q")
            
        filename = f"aisha_voice_{uuid.uuid4().hex[:8]}.mp3"
        filepath = os.path.join(VOICE_DIR, filename)
        clean_text = _clean_for_speech(text)
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }
        # Riya gets intimate/erotic settings; Aisha gets warm/natural settings
        riya_id = os.getenv("RIYA_ELEVENLABS_VOICE_ID", "BpjGufoPiobT79j2vtj4")
        is_riya = (voice_id == riya_id)
        voice_settings = {
            "stability":        0.30 if is_riya else 0.50,   # Riya: expressive & breathy
            "similarity_boost": 0.88 if is_riya else 0.75,   # Riya: stay true to her velvet tone
            "style":            0.70 if is_riya else 0.35,   # Riya: high dramatic style
            "use_speaker_boost": True
        }
        data = {
            "text": clean_text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": voice_settings
        }
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=90)
            if response.status_code in (401, 402, 422, 429):
                # 401=invalid key, 402=payment/quota, 422=char limit exceeded, 429=rate limit
                _mark_key_failed()
                continue
                
            response.raise_for_status()
            with open(filepath, 'wb') as f:
                f.write(response.content)
            return filepath
        except Exception as e:
            print(f"[ElevenLabs] Error with key: {e}")
            _mark_key_failed()
            
    return None


def _transliterate_hinglish(text: str) -> str:
    """
    Rapidly transliterates Roman Hinglish to Devanagari Hindi script using Gemini 2.5 Flash.
    This drastically improves the TTS quality for ElevenLabs/EdgeTTS.
    """
    try:
        import os, requests as _req
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: return text

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
        print(f"[Voice Engine] Transliteration failed, using original text: {e}")

    return text


def generate_voice(text: str, language: str = "English", mood: str = "casual", channel: str = None, force_elevenlabs: bool = False) -> str:
    """
    Synchronous wrapper for voice generation.
    Returns path to the generated .mp3 file.

    PRIMARY: Edge-TTS (free, unlimited, full Hindi Devanagari support).
    OPTIONAL UPGRADE: ElevenLabs — only when ALL of these are true:
      1. force_elevenlabs=True is passed explicitly, AND
      2. ElevenLabs key is present and not a placeholder, AND
      3. Remaining quota >= 500 characters.

    Channel-aware Edge-TTS voices:
      - Aisha channels → hi-IN-SwaraNeural (warm, emotional)
      - Riya channels  → hi-IN-MadhurNeural (dark, bold)
    """
    if language in ["Hinglish", "Hindi"]:
        text = _transliterate_hinglish(text)

    # ── Optional ElevenLabs upgrade path ──────────────────────
    # Only attempt if caller explicitly opts in via force_elevenlabs=True.
    # Even then, skip if key is missing/placeholder OR quota < 500 chars.
    if force_elevenlabs:
        xi_api_key = os.getenv("ELEVENLABS_API_KEY", "")
        key_valid = xi_api_key and "your_" not in xi_api_key
        if key_valid:
            chars_left = _get_elevenlabs_chars_left(xi_api_key.split(",")[0].strip())
            if chars_left >= 500:
                result = _generate_elevenlabs(text, language, mood, channel=channel)
                if result:
                    print(f"[Voice Engine] ElevenLabs used ({chars_left} chars remaining)")
                    return result
                print("[Voice Engine] ElevenLabs failed — falling back to Edge-TTS")
            else:
                print(f"[Voice Engine] ElevenLabs quota too low ({chars_left} chars) — using Edge-TTS")
        else:
            print("[Voice Engine] ElevenLabs key missing/invalid — using Edge-TTS")

    # ── Primary: Edge-TTS ──────────────────────────────────────
    try:
        try:
            loop = asyncio.get_running_loop()
            # Already inside an async context — run in a thread to avoid nested loop
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    _generate_voice_async(text, language, mood, channel=channel)
                )
                return future.result(timeout=60)
        except RuntimeError:
            # No running event loop — safe to call asyncio.run directly
            return asyncio.run(_generate_voice_async(text, language, mood, channel=channel))
    except Exception as e:
        print(f"[Voice Engine] Edge-TTS error: {e}")
        return None


def cleanup_voice_file(filepath: str):
    """Delete a temporary voice file after sending."""
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        log.error("cleanup_voice_file_failed", extra={"filepath": filepath, "error": str(e)})


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

    # Remove markdown formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'━+', '', text)

    # Remove scene/stage directions like [PAUSE], [MUSIC], etc.
    text = re.sub(r'\[.*?\]', '', text)

    # Remove section headers (lines that are all caps or start with numbered prefixes)
    text = re.sub(r'^(?:TITLE|DESCRIPTION|CAPTION|HASHTAGS|THUMBNAIL|SEO|HOOK|CTA)[:\s].*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'^(?:भाग|PART)\s*\d+.*$', '', text, flags=re.MULTILINE | re.IGNORECASE)

    # Normalize ellipsis for natural pauses
    text = re.sub(r'\.{3,}', '...', text)

    # Remove hashtags
    text = re.sub(r'#\w+', '', text)

    # Clean up extra whitespace while preserving sentence breaks
    text = re.sub(r'\n{2,}', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = text.strip()

    return text


# ── Quick test ────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing Aisha's Voice Engine...\n")
    
    tests = [
        ("Hey Aju, I've been thinking about you. You mean everything to me.", "English", "romantic"),
        ("Listen Ajay, you have every right to be angry. Let's channel that energy.", "English", "angry"),
        ("You've GOT this! Remember your goals! Nothing can stop you!", "English", "motivational"),
        ("अजय, मैं हमेशा तुम्हारे साथ हूँ। तुम बहुत strong हो।", "Hindi", "personal"),
    ]
    
    for text, lang, mood in tests:
        print(f"  [{mood:14s}] Generating...")
        path = generate_voice(text, lang, mood)
        if path:
            size = os.path.getsize(path) / 1024
            print(f"              ✅ {os.path.basename(path)} ({size:.1f} KB)")
        else:
            print(f"              ❌ Failed")
    
    print("\n✅ All voice tests complete! Check temp_voice/ folder.")
