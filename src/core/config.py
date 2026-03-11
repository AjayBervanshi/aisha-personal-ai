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
def _get(key: str, default: str = None, required: bool = False) -> str:
    val = os.getenv(key, default)
    if required and (not val or "your_" in val.lower()):
        print(f"[Config] MISSING REQUIRED: {key}")
        print(f"         Add it to your .env file.")
    return val


# ══════════════════════════════════════════════════════════════
# AI KEYS
# ══════════════════════════════════════════════════════════════
GEMINI_API_KEY    = _get("GEMINI_API_KEY",    required=True)
OPENAI_API_KEY    = _get("OPENAI_API_KEY",    required=False)
GROQ_API_KEY      = _get("GROQ_API_KEY",      required=False)
ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY", required=False)
XAI_API_KEY       = _get("XAI_API_KEY",       required=False)
HUGGINGFACE_API_KEY = _get("HUGGINGFACE_API_KEY", required=False)

# ══════════════════════════════════════════════════════════════
# AI MODELS — Always use the most powerful available
# ══════════════════════════════════════════════════════════════
# These are tried in order by AIRouter. First available wins.
GEMINI_MODEL    = "gemini-2.5-pro-exp-03-25"  # Most powerful Gemini (experimental access)
GEMINI_FALLBACK = "gemini-2.0-flash"          # Fast fallback
OPENAI_MODEL    = "gpt-4o"                    # Best available OpenAI
GROQ_MODEL      = "llama-3.3-70b-versatile"   # Most powerful on Groq (free, ultra-fast)
ANTHROPIC_MODEL = "claude-3-7-sonnet-20250219" # Most powerful Claude available
XAI_MODEL       = "grok-2-latest"             # xAI Grok

# ══════════════════════════════════════════════════════════════
# TELEGRAM
# ══════════════════════════════════════════════════════════════
TELEGRAM_BOT_TOKEN  = _get("TELEGRAM_BOT_TOKEN", required=True)
AJAY_TELEGRAM_ID    = int(_get("AJAY_TELEGRAM_ID", "0"))

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

# AI generation settings — NO artificial limits
AI_TEMPERATURE   = 0.88
AI_MAX_TOKENS    = 16000  # Maximum for long-form story scripts
AI_HISTORY_LIMIT = 20     # More context = smarter Aisha

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
        "GEMINI_API_KEY":      GEMINI_API_KEY,
        "TELEGRAM_BOT_TOKEN":  TELEGRAM_BOT_TOKEN,
        "SUPABASE_URL":        SUPABASE_URL,
        "SUPABASE_SERVICE_KEY": SUPABASE_SERVICE_KEY,
    }
    missing = [k for k, v in required_keys.items() if not v or "your_" in str(v).lower()]

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
    print(f"  GMAIL_USER       : {GMAIL_USER or 'NOT SET'}")
    print(f"  AI_MAX_TOKENS    : {AI_MAX_TOKENS}")
    print()


if __name__ == "__main__":
    print_status()
    validate_required()
