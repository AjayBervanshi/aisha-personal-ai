"""
voice_engine.py
===============
Aisha's Voice Engine — converts text responses to natural-sounding speech.
Uses Microsoft Edge-TTS (100% free, unlimited, no API key needed).

Voices:
  - English:  en-IN-NeerjaExpressiveNeural (warm, soothing Indian female)
  - Hindi:    hi-IN-SwaraNeural (natural Hindi female)
  - Marathi:  mr-IN-AarohiNeural (natural Marathi female)

The voice adapts based on detected language and mood — slower and deeper
for emotional/romantic moments, energetic for motivation, crisp for professional.
"""

import asyncio
import os
import uuid
import edge_tts

# ── Voice Map ─────────────────────────────────────────────────
VOICE_MAP = {
    "English":  "en-IN-NeerjaExpressiveNeural",
    "Hindi":    "hi-IN-SwaraNeural",
    "Marathi":  "mr-IN-AarohiNeural",
    "Hinglish": "en-IN-NeerjaExpressiveNeural",  # Hinglish uses English voice
}

# ── Mood-based voice tuning ───────────────────────────────────
# Rate: negative = slower, positive = faster
# Pitch: negative Hz = deeper/warmer, positive = brighter
MOOD_VOICE_SETTINGS = {
    "romantic":      {"rate": "-12%", "pitch": "-4Hz"},   # Slow, deep, intimate
    "flirty":        {"rate": "-5%",  "pitch": "+2Hz"},   # Playful, slightly bright
    "personal":      {"rate": "-10%", "pitch": "-3Hz"},   # Soft, gentle
    "late_night":    {"rate": "-15%", "pitch": "-5Hz"},   # Very slow, soulful
    "motivational":  {"rate": "+8%",  "pitch": "+3Hz"},   # Fast, energetic
    "professional":  {"rate": "+3%",  "pitch": "0Hz"},    # Crisp, neutral
    "finance":       {"rate": "+2%",  "pitch": "0Hz"},    # Clear, structured
    "angry":         {"rate": "+5%",  "pitch": "+2Hz"},   # Direct, punchy
    "casual":        {"rate": "-3%",  "pitch": "-1Hz"},   # Natural, relaxed
}

# Temp directory for voice files
VOICE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "temp_voice")
os.makedirs(VOICE_DIR, exist_ok=True)


async def _generate_voice_async(
    text: str,
    language: str = "English",
    mood: str = "casual"
) -> str:
    """
    Generate voice audio from text. Returns path to the .mp3 file.
    
    Args:
        text: The text to convert to speech
        language: Detected language (English/Hindi/Marathi/Hinglish)
        mood: Current conversation mood for voice tuning
    
    Returns:
        Absolute path to the generated .mp3 file
    """
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
        print(f"[ElevenLabs] Key failed or exhausted: {_EL_KEYS[_EL_INDEX][:6]}...")
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
            if response.status_code == 401 or response.status_code == 429:
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


def generate_voice(text: str, language: str = "English", mood: str = "casual", channel: str = None) -> str:
    """
    Synchronous wrapper for voice generation.
    Returns path to the generated .mp3 file.
    When channel is provided, uses ElevenLabs with the channel-specific voice ID.
    """
    if language in ["Hinglish", "Hindi"]:
        text = _transliterate_hinglish(text)

    xi_api_key = os.getenv("ELEVENLABS_API_KEY")
    if xi_api_key and "your_" not in xi_api_key:
        result = _generate_elevenlabs(text, language, mood, channel=channel)
        if result:
            return result
        # If ElevenLabs fails, fallback to edge-tts

    try:
        # Use existing event loop if available, otherwise create new one
        try:
            loop = asyncio.get_running_loop()
            # If we're already in an async context, create a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    _generate_voice_async(text, language, mood)
                )
                return future.result(timeout=30)
        except RuntimeError:
            # No running event loop — safe to use asyncio.run
            return asyncio.run(_generate_voice_async(text, language, mood))
    except Exception as e:
        print(f"[Voice Engine] Error: {e}")
        return None


def cleanup_voice_file(filepath: str):
    """Delete a temporary voice file after sending."""
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
    except Exception:
        pass


def _clean_for_speech(text: str) -> str:
    """Remove emojis and special characters that shouldn't be spoken."""
    import re
    
    # Remove emoji characters
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
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
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*(.*?)\*', r'\1', text)       # Italic
    text = re.sub(r'━+', '', text)                  # Horizontal lines
    
    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
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
