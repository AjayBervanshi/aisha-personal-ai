"""
monitoring_engine.py — Aisha System Health Monitor
Checks all critical systems and reports status to Ajay.
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List

log = logging.getLogger(__name__)

# ── Supabase ─────────────────────────────────────────────────────────────────
try:
    from supabase import create_client
    _SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    _SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")
    _db = create_client(_SUPABASE_URL, _SUPABASE_KEY) if _SUPABASE_URL else None
except Exception:
    _db = None


def check_ai_providers() -> Dict[str, str]:
    """Test each AI provider with a quick ping."""
    import requests
    results = {}

    # Gemini
    try:
        key = os.getenv("GEMINI_API_KEY", "")
        if key:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}",
                json={"contents": [{"parts": [{"text": "ping"}]}]},
                timeout=10
            )
            results["gemini"] = "✅ OK" if r.status_code == 200 else f"❌ {r.status_code}"
        else:
            results["gemini"] = "⚠️ No key"
    except Exception as e:
        results["gemini"] = f"❌ {str(e)[:30]}"

    # Groq
    try:
        key = os.getenv("GROQ_API_KEY", "")
        if key:
            from groq import Groq
            client = Groq(api_key=key)
            client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1
            )
            results["groq"] = "✅ OK"
        else:
            results["groq"] = "⚠️ No key"
    except Exception as e:
        results["groq"] = f"❌ {str(e)[:30]}"

    # ElevenLabs
    try:
        key = os.getenv("ELEVENLABS_API_KEY", "")
        if key:
            r = requests.get(
                "https://api.elevenlabs.io/v1/user",
                headers={"xi-api-key": key},
                timeout=10
            )
            results["elevenlabs"] = "✅ OK" if r.status_code == 200 else f"❌ {r.status_code}"
        else:
            results["elevenlabs"] = "⚠️ No key"
    except Exception as e:
        results["elevenlabs"] = f"❌ {str(e)[:30]}"

    # xAI
    try:
        key = os.getenv("XAI_API_KEY", "")
        if key:
            r = requests.get(
                "https://api.x.ai/v1/models",
                headers={"Authorization": f"Bearer {key}"},
                timeout=10
            )
            results["xai"] = "✅ OK" if r.status_code == 200 else f"❌ {r.status_code}"
        else:
            results["xai"] = "⚠️ No key"
    except Exception as e:
        results["xai"] = f"❌ {str(e)[:30]}"

    return results


def check_database() -> Dict[str, str]:
    """Check Supabase tables and recent activity."""
    results = {}
    if not _db:
        return {"supabase": "❌ Not configured"}

    tables_to_check = [
        "content_jobs", "aisha_memory", "aisha_schedule",
        "aisha_mood_tracker", "api_keys"
    ]

    for table in tables_to_check:
        try:
            r = _db.table(table).select("id", count="exact").limit(1).execute()
            count = r.count if hasattr(r, 'count') and r.count is not None else len(r.data)
            results[table] = f"✅ {count} rows"
        except Exception as e:
            results[table] = f"❌ {str(e)[:40]}"

    return results


def check_recent_jobs() -> List[Dict]:
    """Get last 5 content jobs and their statuses."""
    if not _db:
        return []
    try:
        r = _db.table("content_jobs").select(
            "topic,channel,status,created_at,completed_at,error_text"
        ).order("created_at", desc=True).limit(5).execute()
        return r.data or []
    except Exception:
        return []


def check_render_health() -> str:
    """Ping Render bot health endpoint."""
    import requests
    render_url = os.getenv("RENDER_BOT_URL", "").rstrip("/")
    if not render_url:
        return "⚠️ RENDER_BOT_URL not set"
    try:
        r = requests.get(f"{render_url}/health", timeout=10)
        return f"✅ {r.status_code}" if r.status_code == 200 else f"❌ {r.status_code}"
    except Exception as e:
        return f"❌ {str(e)[:40]}"


def full_health_report() -> str:
    """Generate complete system health report as Telegram-formatted string."""
    lines = ["*🏥 Aisha System Health Report*", f"_{datetime.now().strftime('%d %b %Y %H:%M IST')}_\n"]

    # AI Providers
    lines.append("*AI Providers:*")
    for provider, status in check_ai_providers().items():
        lines.append(f"  • {provider}: {status}")

    # Database
    lines.append("\n*Database Tables:*")
    for table, status in check_database().items():
        lines.append(f"  • {table}: {status}")

    # Render
    lines.append(f"\n*Render Bot:* {check_render_health()}")

    # Recent jobs
    lines.append("\n*Recent Content Jobs:*")
    jobs = check_recent_jobs()
    if jobs:
        for job in jobs:
            icon = "✅" if job.get("status") == "completed" else ("❌" if job.get("status") == "failed" else "⏳")
            lines.append(f"  {icon} [{job.get('channel','?')[:12]}] {job.get('topic','?')[:25]}")
            if job.get("error_text"):
                lines.append(f"     └ Error: {job['error_text'][:50]}")
    else:
        lines.append("  No jobs yet")

    return "\n".join(lines)
