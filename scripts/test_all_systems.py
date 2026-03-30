"""
test_all_systems.py
====================
Systematic end-to-end test of all Aisha components.
Sends a live Telegram report to Ajay with pass/fail for each component.

Usage: python scripts/test_all_systems.py
"""

import os
import sys
import time
import json
from pathlib import Path

# Fix Windows cp1252 console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Project root on path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
AJAY_ID = os.getenv("AJAY_TELEGRAM_ID", "")

results = []

def check(name: str, fn):
    """Run a test function, record pass/fail + detail."""
    try:
        detail = fn()
        results.append(("✅", name, detail or "ok"))
        print(f"  ✅ {name}: {detail or 'ok'}")
    except Exception as e:
        results.append(("❌", name, str(e)[:120]))
        print(f"  ❌ {name}: {e}")

def send_telegram(msg: str):
    import requests
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": AJAY_ID, "text": msg, "parse_mode": "Markdown"},
        timeout=10,
    )

# ── 1. TELEGRAM ────────────────────────────────────────────────────────────
print("\n[1] TELEGRAM")

def test_bot_identity():
    import requests
    r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe", timeout=5).json()
    assert r["ok"], r
    return r["result"]["username"]

def test_no_webhook():
    import requests
    r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getWebhookInfo", timeout=5).json()
    url = r["result"].get("url", "")
    assert url == "", f"Webhook still set: {url}"
    return "polling mode confirmed"

def test_send_message():
    import requests
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": AJAY_ID, "text": "🔬 Aisha system test starting..."},
        timeout=5,
    ).json()
    assert r["ok"], r
    return f"message_id={r['result']['message_id']}"

check("Bot identity", test_bot_identity)
check("No webhook conflict", test_no_webhook)
check("Send test message", test_send_message)

# ── 2. SUPABASE ────────────────────────────────────────────────────────────
print("\n[2] SUPABASE")

def test_supabase_read():
    from supabase import create_client
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    r = sb.table("aisha_conversations").select("id").limit(1).execute()
    return f"conversations table accessible"

def test_supabase_write():
    from supabase import create_client
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    r = sb.table("aisha_conversations").insert({
        "platform": "web", "role": "assistant",
        "message": "system_test_ping", "language": "English"
    }).execute()
    assert r.data, "insert returned no data"
    # Clean up
    sb.table("aisha_conversations").delete().eq("message", "system_test_ping").execute()
    return "read+write+delete ok"

def test_content_queue_table():
    from supabase import create_client
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    r = sb.table("content_queue").select("id,youtube_status,instagram_status").limit(1).execute()
    return "content_queue + idempotency columns exist"

def test_api_keys_table():
    from supabase import create_client
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    r = sb.table("api_keys").select("name").execute()
    names = [row["name"] for row in (r.data or [])]
    return f"api_keys rows: {names[:3]}"

check("Supabase read", test_supabase_read)
check("Supabase write+delete", test_supabase_write)
check("content_queue + idempotency columns", test_content_queue_table)
check("api_keys table", test_api_keys_table)

# ── 3. AI ROUTER ───────────────────────────────────────────────────────────
print("\n[3] AI ROUTER")

def test_gemini():
    from src.core.ai_router import AIRouter
    ai = AIRouter()
    r = ai.generate("You are a test bot.", "Reply with exactly: GEMINI_OK", preferred_provider="gemini")
    assert "GEMINI" in r.text.upper() or len(r.text) > 2
    return f"{r.provider} {r.latency_ms}ms"

def test_groq():
    from src.core.ai_router import AIRouter
    ai = AIRouter()
    r = ai.generate("You are a test bot.", "Reply with exactly: GROQ_OK", preferred_provider="groq")
    assert len(r.text) > 2
    return f"{r.provider} {r.latency_ms}ms"

def test_nvidia_mistral():
    from src.core.ai_router import AIRouter
    ai = AIRouter()
    r = ai.generate(
        "You are a creative writing assistant.",
        "Write ONE sentence of a romantic Hindi story in Devanagari script.",
        preferred_provider="nvidia",
        nvidia_task_type="writing"
    )
    assert len(r.text) > 5
    return f"{r.provider} {r.latency_ms}ms | {r.text[:60]}..."

check("Gemini API", test_gemini)
check("Groq LLaMA-3.3", test_groq)
check("NVIDIA Mistral-Large-3 (Riya model)", test_nvidia_mistral)

# ── 4. VOICE ENGINE ────────────────────────────────────────────────────────
print("\n[4] VOICE ENGINE")

def test_elevenlabs_aisha():
    from src.core.voice_engine import generate_voice
    path = generate_voice("Testing Aisha voice.", mood="happy", channel="Story With Aisha")
    assert path and os.path.exists(path), f"No file at {path}"
    size = os.path.getsize(path)
    os.unlink(path)
    return f"ElevenLabs Aisha voice: {size} bytes"

def test_elevenlabs_riya():
    from src.core.voice_engine import generate_voice
    path = generate_voice("Testing Riya voice.", mood="mysterious", channel="Riya's Dark Whisper")
    assert path and os.path.exists(path), f"No file at {path}"
    size = os.path.getsize(path)
    os.unlink(path)
    return f"ElevenLabs Riya voice: {size} bytes"

check("ElevenLabs Aisha voice", test_elevenlabs_aisha)
check("ElevenLabs Riya voice", test_elevenlabs_riya)

# ── 5. SOCIAL MEDIA ENGINE ─────────────────────────────────────────────────
print("\n[5] SOCIAL MEDIA ENGINE")

def test_youtube_token_load():
    from src.core.social_media_engine import SocialMediaEngine
    sme = SocialMediaEngine()
    creds = sme._get_youtube_credentials("Story With Aisha")
    assert creds is not None
    return f"token loaded (has refresh_token={bool(creds.refresh_token)})"

def test_instagram_token_load():
    from src.core.social_media_engine import SocialMediaEngine
    sme = SocialMediaEngine()
    token, biz_id = sme._get_instagram_creds("Story With Aisha")
    assert token, "No Instagram token"
    return f"token={token[:12]}... biz_id={biz_id[:8] if biz_id else 'MISSING'}..."

check("YouTube OAuth token loads from DB", test_youtube_token_load)
check("Instagram token loads from DB", test_instagram_token_load)

# ── 6. CONTENT PIPELINE (mini run — no video render) ──────────────────────
print("\n[6] CONTENT PIPELINE (script only)")

def test_aisha_pipeline():
    from src.agents.youtube_crew import YouTubeCrew
    crew = YouTubeCrew()
    result = crew.kickoff({
        "topic": "पहली मुलाकात में दिल धड़का",
        "channel": "Story With Aisha",
        "format": "Long Form",
        "render_video": False,
    })
    assert result and len(result) > 100, "Pipeline returned empty result"
    return f"Script generated: {len(result)} chars"

def test_riya_pipeline():
    from src.agents.youtube_crew import YouTubeCrew
    crew = YouTubeCrew()
    result = crew.kickoff({
        "topic": "रात का राज़",
        "channel": "Riya's Dark Whisper",
        "format": "Long Form",
        "render_video": False,
    })
    assert result and len(result) > 100
    return f"Riya script generated: {len(result)} chars | model used: Mistral-Large-3"

check("Story With Aisha pipeline (Gemini)", test_aisha_pipeline)
check("Riya's Dark Whisper pipeline (Mistral)", test_riya_pipeline)

# ── 7. MEMORY SYSTEM ───────────────────────────────────────────────────────
print("\n[7] MEMORY SYSTEM")

def test_memory_save_load():
    from src.memory.memory_manager import MemoryManager
    mm = MemoryManager()
    mm.save_memory("general", "system_test", "test ping", importance=1)
    memories = mm.get_semantic_memories("system test ping", limit=1)
    assert memories is not None
    return "memory save+search ok"

check("Memory save + semantic search", test_memory_save_load)

# ── FINAL REPORT ───────────────────────────────────────────────────────────
passed = sum(1 for r in results if r[0] == "✅")
failed = sum(1 for r in results if r[0] == "❌")
total = len(results)

print(f"\n{'='*50}")
print(f"RESULTS: {passed}/{total} passed, {failed} failed")
print(f"{'='*50}")

# Build Telegram report
lines = [f"*🔬 Aisha System Test Report*", f"*{passed}/{total} passed*\n"]
for emoji, name, detail in results:
    lines.append(f"{emoji} *{name}*")
    if emoji == "❌":
        lines.append(f"   └ `{detail}`")

if failed == 0:
    lines.append("\n🟢 *All systems GO. Content factory ready.*")
else:
    lines.append(f"\n🔴 *{failed} issue(s) need fixing before production.*")

report = "\n".join(lines)
send_telegram(report)
print("\nReport sent to Telegram.")

sys.exit(0 if failed == 0 else 1)
