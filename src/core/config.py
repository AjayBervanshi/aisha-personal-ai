"""
config.py
=========
Centralized configuration for the entire Aisha project.
All env vars, AI models, and channel settings live here.

MODEL PHILOSOPHY:
  Always use the most powerful model available for each provider.
  No artificial token limits. Aisha deserves the best brain available.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env from project root ────────────────────────────────
_root = Path(__file__).parent.parent.parent
load_dotenv(_root / ".env")


# ── Helper ─────────────────────────────────────────────────────
import time
_sb_cache = {}

def _fetch_from_supabase(key: str) -> str:
    if key in ["SUPABASE_URL", "SUPABASE_SERVICE_KEY", "SUPABASE_SERVICE_ROLE_KEY"]:
        return None

    sb_url = os.getenv("SUPABASE_URL")
    sb_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not sb_url or not sb_key:
        return None

    if key in _sb_cache:
        return _sb_cache[key]

    try:
        from supabase import create_client
        sb = create_client(sb_url, sb_key)
        res = sb.table("api_keys").select("secret").eq("name", key).eq("active", True).execute()
        if res.data and len(res.data) > 0:
            val = res.data[0].get("secret")
            if val:
                _sb_cache[key] = val
                return val
    except Exception as e:
        print(f"[Config] Supabase fetch failed for {key}: {e}")
    return None

def _get(key: str, default: str = None, required: bool = False) -> str:
    # 1. Check Supabase first
    val = _fetch_from_supabase(key)

    # 2. Fallback to ENV
    if not val:
        val = os.getenv(key)

    if not val:
        val = default

    if required and (not val or "your_" in val.lower()):
        print(f"[Config] MISSING REQUIRED: {key}")
        print(f"         Add it to your .env file or Supabase api_keys table.")

    return val


def _get_int(key: str, default: int = 0) -> int:
    raw = _get(key, str(default))
    try:
        return int(str(raw))
    except (TypeError, ValueError):
        return default


# ══════════════════════════════════════════════════════════════
# AI KEYS
# ══════════════════════════════════════════════════════════════
GEMINI_API_KEY    = _get("GEMINI_API_KEY",    required=False)
OPENAI_API_KEY    = _get("OPENAI_API_KEY",    required=False)
GROQ_API_KEY      = _get("GROQ_API_KEY",      required=False)
ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY", required=False)
XAI_API_KEY       = _get("XAI_API_KEY",       required=False)
HUGGINGFACE_API_KEY = _get("HUGGINGFACE_API_KEY", required=False)

# ══════════════════════════════════════════════════════════════
# CALL-ME PLUGIN SETTINGS
# ══════════════════════════════════════════════════════════════
CALLME_PHONE_PROVIDER    = _get("CALLME_PHONE_PROVIDER", "telnyx")
CALLME_PHONE_ACCOUNT_SID = _get("CALLME_PHONE_ACCOUNT_SID")
CALLME_PHONE_AUTH_TOKEN  = _get("CALLME_PHONE_AUTH_TOKEN")
CALLME_PHONE_NUMBER      = _get("CALLME_PHONE_NUMBER")
CALLME_USER_PHONE_NUMBER = _get("CALLME_USER_PHONE_NUMBER")
CALLME_OPENAI_API_KEY    = _get("CALLME_OPENAI_API_KEY")
CALLME_NGROK_AUTHTOKEN   = _get("CALLME_NGROK_AUTHTOKEN")

# ══════════════════════════════════════════════════════════════
# AI MODELS — Always use the most powerful available
# ══════════════════════════════════════════════════════════════
# These are tried in order by AIRouter. First available wins.
# Allow .env overrides so model routing can be tuned without code edits.
GEMINI_MODEL    = _get("AI_MODEL_GEMINI", "gemini-2.5-pro")        # Most powerful Gemini
GEMINI_FALLBACK = _get("AI_MODEL_GEMINI_FALLBACK", "gemini-2.0-flash,gemini-2.0-flash-lite,gemini-1.5-flash")
OPENAI_MODEL    = _get("AI_MODEL_OPENAI", "gpt-4o")
GROQ_MODEL      = _get("AI_MODEL_GROQ", "llama-3.3-70b-versatile")
ANTHROPIC_MODEL = _get("AI_MODEL_ANTHROPIC", "claude-opus-4-6")
XAI_MODEL       = _get("AI_MODEL_XAI", "grok-2-latest")

# ══════════════════════════════════════════════════════════════
# TELEGRAM
# ══════════════════════════════════════════════════════════════
TELEGRAM_BOT_TOKEN  = _get("TELEGRAM_BOT_TOKEN", required=True)
AJAY_TELEGRAM_ID    = _get_int("AJAY_TELEGRAM_ID", 0)

# ══════════════════════════════════════════════════════════════
# SUPABASE
# ══════════════════════════════════════════════════════════════
SUPABASE_URL         = _get("SUPABASE_URL",          required=True)
SUPABASE_ANON_KEY    = _get("SUPABASE_ANON_KEY",     required=True)
SUPABASE_SERVICE_KEY = _get("SUPABASE_SERVICE_KEY",  required=True)

# ══════════════════════════════════════════════════════════════
# VOICE
# ══════════════════════════════════════════════════════════════
ELEVENLABS_API_KEY  = _get("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = _get("ELEVENLABS_VOICE_ID")

# Channel-specific ElevenLabs voice IDs
AISHA_ELEVENLABS_VOICE_ID = "wdymxIQkYn7MJCYCQF2Q"   # Aisha — warm, emotional narrator
RIYA_ELEVENLABS_VOICE_ID  = "BpjGufoPiobT79j2vtj4"   # Riya  — seductive, bold narrator

CHANNEL_VOICE_IDS: dict = {
    "Story With Aisha":            AISHA_ELEVENLABS_VOICE_ID,
    "Riya's Dark Whisper":         RIYA_ELEVENLABS_VOICE_ID,
    "Riya's Dark Romance Library": RIYA_ELEVENLABS_VOICE_ID,
    "Aisha & Him":                 AISHA_ELEVENLABS_VOICE_ID,
}

# ══════════════════════════════════════════════════════════════
# GMAIL
# ══════════════════════════════════════════════════════════════
GMAIL_USER         = _get("GMAIL_USER",         required=False)
GMAIL_APP_PASSWORD = _get("GMAIL_APP_PASSWORD", required=False)

# ══════════════════════════════════════════════════════════════
# SOCIAL MEDIA APIs (for future auto-posting)
# ══════════════════════════════════════════════════════════════
YOUTUBE_CLIENT_ID     = _get("YOUTUBE_CLIENT_ID",     required=False)
YOUTUBE_CLIENT_SECRET = _get("YOUTUBE_CLIENT_SECRET", required=False)
INSTAGRAM_ACCESS_TOKEN = _get("INSTAGRAM_ACCESS_TOKEN", required=False)
INSTAGRAM_BUSINESS_ID  = _get("INSTAGRAM_BUSINESS_ID",  required=False)

# ══════════════════════════════════════════════════════════════
# APP SETTINGS
# ══════════════════════════════════════════════════════════════
USER_NAME    = _get("USER_NAME",  "Ajay")
TIMEZONE     = _get("TIMEZONE",   "Asia/Kolkata")
LOG_LEVEL    = _get("LOG_LEVEL",  "INFO")
APP_ENV      = _get("APP_ENV",    "development")
IS_DEV       = APP_ENV == "development"

# Secret code for high-risk operations via natural language
AISHA_SECRET_CODE = _get("AISHA_SECRET_CODE", "aisha-69")

# AI generation settings — NO artificial limits
AI_TEMPERATURE   = 0.88
AI_MAX_TOKENS    = 16000  # Maximum for long-form story scripts
AI_HISTORY_LIMIT = 20     # More context = smarter Aisha

# ══════════════════════════════════════════════════════════════
# CHANNEL → AI MODEL ROUTING
# Riya channels: Mistral-Large-3 via NVIDIA NIM (writing pool)
#   - 675B parameter model, minimal content filtering
#   - Handles explicit adult/18+ Hindi romance content
#   - 2 keys (KEY_02 + KEY_17) = 2,000 free credits/month for writing
#   - Fallback: Groq LLaMA-3.3 (also handles mature content)
# Aisha channels: Gemini — warm, emotional, cinematic
# ══════════════════════════════════════════════════════════════
CHANNEL_AI_PROVIDER = {
    "Story With Aisha":           "gemini",   # Warm, emotional
    "Riya's Dark Whisper":        "nvidia",   # Mistral-Large-3 — explicit, dark
    "Riya's Dark Romance Library":"nvidia",   # Mistral-Large-3 — intense, bold
    "Aisha & Him":                "gemini",   # Light, relatable
}

# Task type for NVIDIA NIM pool — ensures Riya uses the WRITING pool (Mistral-Large-3)
CHANNEL_AI_TASK_TYPE = {
    "Story With Aisha":           "writing",
    "Riya's Dark Whisper":        "writing",  # Routes to Mistral-Large-3 (675B)
    "Riya's Dark Romance Library":"writing",  # Routes to Mistral-Large-3 (675B)
    "Aisha & Him":                "writing",
}

# ══════════════════════════════════════════════════════════════
# YOUTUBE CHANNELS
# ══════════════════════════════════════════════════════════════
YOUTUBE_CHANNELS = {
    "Story With Aisha": {
        "narrator": "Aisha",
        "tone": "warm, emotional, cinematic, heart-touching",
        "format": "Long Form",
        "duration": "8-15 min",
    },
    "Riya's Dark Whisper": {
        "narrator": "Riya",
        "tone": "mysterious, seductive, psychological",
        "format": "Long Form",
        "duration": "10-20 min",
    },
    "Riya's Dark Romance Library": {
        "narrator": "Riya",
        "tone": "intense, addictive, mafia romance",
        "format": "Long Form",
        "duration": "15-25 min",
    },
    "Aisha & Him": {
        "narrator": "Aisha",
        "tone": "relatable, funny, sweet, real",
        "format": "Short/Reel",
        "duration": "30s-3 min",
    },
}

# ══════════════════════════════════════════════════════════════
# VALIDATION
# ══════════════════════════════════════════════════════════════
def validate_required() -> bool:
    required_keys = {
        "TELEGRAM_BOT_TOKEN":   TELEGRAM_BOT_TOKEN,
        "SUPABASE_URL":         SUPABASE_URL,
        "SUPABASE_SERVICE_KEY": SUPABASE_SERVICE_KEY,
    }
    missing = [k for k, v in required_keys.items() if not v or "your_" in str(v).lower()]

    ai_keys = {
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "GROQ_API_KEY": GROQ_API_KEY,
        "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
        "XAI_API_KEY": XAI_API_KEY,
    }
    has_any_ai = any(v and "your_" not in str(v).lower() for v in ai_keys.values())
    if not has_any_ai:
        missing.append("AT_LEAST_ONE_AI_API_KEY")

    if missing:
        print("\nMissing required environment variables:")
        for m in missing:
            print(f"   - {m}")
        return False

    print("All required environment variables are set.")
    return True


def print_status():
    """Print a quick status of all config values (masked for security)."""
    def mask(val):
        if not val or "your_" in str(val).lower(): return "NOT SET"
        return str(val)[:8] + "..."

    print("\n=== Aisha Config Status ===")
    print(f"  GEMINI_MODEL     : {GEMINI_MODEL}")
    print(f"  ANTHROPIC_MODEL  : {ANTHROPIC_MODEL}")
    print(f"  OPENAI_MODEL     : {OPENAI_MODEL}")
    print(f"  GROQ_MODEL       : {GROQ_MODEL}")
    print(f"  GEMINI_API_KEY   : {mask(GEMINI_API_KEY)}")
    print(f"  ANTHROPIC_API_KEY: {mask(ANTHROPIC_API_KEY)}")
    print(f"  OPENAI_API_KEY   : {mask(OPENAI_API_KEY)}")
    print(f"  XAI_API_KEY      : {mask(XAI_API_KEY)}")
    print(f"  GROQ_API_KEY     : {mask(GROQ_API_KEY)}")
    print(f"  TELEGRAM_BOT     : {mask(TELEGRAM_BOT_TOKEN)}")
    print(f"  SUPABASE_URL     : {mask(SUPABASE_URL)}")
    print(f"  ELEVENLABS_KEY   : {mask(ELEVENLABS_API_KEY)}")
    print(f"  AISHA_VOICE_ID   : {AISHA_ELEVENLABS_VOICE_ID}")
    print(f"  RIYA_VOICE_ID    : {RIYA_ELEVENLABS_VOICE_ID}")
    print(f"  GMAIL_USER       : {GMAIL_USER or 'NOT SET'}")
    print(f"  AI_MAX_TOKENS    : {AI_MAX_TOKENS}")
    print()


if __name__ == "__main__":
    print_status()
    validate_required()
