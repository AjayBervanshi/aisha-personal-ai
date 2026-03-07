"""
config.py
=========
Centralized configuration for the entire Aisha project.
All env vars are loaded, validated, and accessible from here.
Import this everywhere instead of calling os.getenv() directly.
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
        print(f"[Config] ❌ MISSING REQUIRED: {key}")
        print(f"         Add it to your .env file.")
        print(f"         See docs/SETUP_GUIDE.md for instructions.")
    return val


# ══════════════════════════════════════════════════════════════
# AI KEYS
# ══════════════════════════════════════════════════════════════
GEMINI_API_KEY   = _get("GEMINI_API_KEY",   required=True)
OPENAI_API_KEY   = _get("OPENAI_API_KEY",   required=False)
GROQ_API_KEY     = _get("GROQ_API_KEY",     required=False)

GEMINI_MODEL     = "gemini-1.5-flash"
OPENAI_MODEL     = "gpt-4o-mini"
GROQ_MODEL       = "llama3-70b-8192"

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
# VOICE (OPTIONAL)
# ══════════════════════════════════════════════════════════════
ELEVENLABS_API_KEY  = _get("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = _get("ELEVENLABS_VOICE_ID")

# ══════════════════════════════════════════════════════════════
# APP SETTINGS
# ══════════════════════════════════════════════════════════════
USER_NAME    = _get("USER_NAME",  "Ajay")
TIMEZONE     = _get("TIMEZONE",   "Asia/Kolkata")
LOG_LEVEL    = _get("LOG_LEVEL",  "INFO")
APP_ENV      = _get("APP_ENV",    "development")
IS_DEV       = APP_ENV == "development"

# AI generation settings
AI_TEMPERATURE   = 0.88
AI_MAX_TOKENS    = 1024
AI_HISTORY_LIMIT = 12   # Max turns to keep in context

# ══════════════════════════════════════════════════════════════
# VALIDATION
# ══════════════════════════════════════════════════════════════
def validate_required() -> bool:
    """
    Check all required env vars are present.
    Returns True if all good, False if something is missing.
    """
    required_keys = {
        "GEMINI_API_KEY":    GEMINI_API_KEY,
        "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
        "SUPABASE_URL":      SUPABASE_URL,
        "SUPABASE_SERVICE_KEY": SUPABASE_SERVICE_KEY,
    }
    missing = []
    for k, v in required_keys.items():
        if not v or "your_" in str(v).lower():
            missing.append(k)

    if missing:
        print("\n❌ Missing required environment variables:")
        for m in missing:
            print(f"   • {m}")
        print("\n📖 See docs/SETUP_GUIDE.md → Step 2 for instructions.\n")
        return False

    print("✅ All required environment variables are set.")
    return True


def print_status():
    """Print a quick status of all config values (masked for security)."""
    def mask(val):
        if not val or "your_" in str(val).lower():
            return "❌ NOT SET"
        return "✅ " + str(val)[:8] + "..."

    print("\n🔑 Config Status:")
    print(f"   GEMINI_API_KEY      : {mask(GEMINI_API_KEY)}")
    print(f"   GROQ_API_KEY        : {mask(GROQ_API_KEY)}")
    print(f"   TELEGRAM_BOT_TOKEN  : {mask(TELEGRAM_BOT_TOKEN)}")
    print(f"   AJAY_TELEGRAM_ID    : {'✅ ' + str(AJAY_TELEGRAM_ID) if AJAY_TELEGRAM_ID else '⚠️  Not set (dev mode)'}")
    print(f"   SUPABASE_URL        : {mask(SUPABASE_URL)}")
    print(f"   SUPABASE_SERVICE_KEY: {mask(SUPABASE_SERVICE_KEY)}")
    print(f"   ELEVENLABS_API_KEY  : {mask(ELEVENLABS_API_KEY)}")
    print(f"   APP_ENV             : {APP_ENV}")
    print()


if __name__ == "__main__":
    print_status()
    validate_required()
