import os
import logging
import requests
from datetime import datetime, timezone

log = logging.getLogger("Aisha.MonitoringEngine")

_RENDER_HEALTH_URL = "https://aisha-bot-yudp.onrender.com/health"


def _supabase_base() -> str:
    return os.getenv("SUPABASE_URL", "").rstrip("/")


def _supabase_headers() -> dict:
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    return {
        "apikey":        key,
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
    }


def _check_ai_providers() -> list:
    lines = []
    try:
        try:
            from src.core.ai_router import AIRouter
        except ImportError:
            from core.ai_router import AIRouter
        router = AIRouter()
        statuses = router.status()
        for name in ("gemini", "nvidia", "groq", "openai", "xai"):
            if name not in statuses:
                continue
            info = statuses[name]
            available = info.get("available", False)
            cooling   = info.get("cooling_down", False)
            if available and not cooling:
                icon  = "✅"
                state = "ready"
            elif cooling:
                icon  = "⏳"
                state = "cooling down"
            else:
                icon  = "❌"
                state = "unavailable"
            lines.append(f"{icon} `{name}` — {state}")
    except Exception as e:
        lines.append(f"❌ AI provider check failed: {e}")
    return lines


def _check_supabase_tables() -> list:
    lines = []
    base = _supabase_base()
    if not base:
        return ["❌ SUPABASE_URL not set"]
    headers = _supabase_headers()

    # content_jobs — group by status
    try:
        r = requests.get(
            f"{base}/rest/v1/content_jobs?select=status",
            headers=headers, timeout=10
        )
        if r.status_code == 200:
            counts: dict = {}
            for row in r.json():
                s = row.get("status", "unknown")
                counts[s] = counts.get(s, 0) + 1
            summary = ", ".join(f"{s}:{n}" for s, n in sorted(counts.items())) or "empty"
            lines.append(f"✅ `content_jobs` — {summary}")
        else:
            lines.append(f"⚠️ `content_jobs` — HTTP {r.status_code}")
    except Exception as e:
        lines.append(f"❌ `content_jobs` — {e}")

    # plain count tables
    for table in ("aisha_memories", "aisha_conversations", "aisha_mood_tracker"):
        try:
            r = requests.get(
                f"{base}/rest/v1/{table}?select=id",
                headers={**headers, "Prefer": "count=exact"},
                timeout=10
            )
            if r.status_code in (200, 206):
                count = r.headers.get("content-range", "?/?").split("/")[-1]
                lines.append(f"✅ `{table}` — {count} rows")
            else:
                lines.append(f"⚠️ `{table}` — HTTP {r.status_code}")
        except Exception as e:
            lines.append(f"❌ `{table}` — {e}")

    return lines


def _check_render() -> str:
    try:
        r = requests.get(_RENDER_HEALTH_URL, timeout=10)
        if r.status_code == 200:
            return f"✅ Render — online ({r.elapsed.total_seconds():.1f}s)"
        return f"⚠️ Render — HTTP {r.status_code}"
    except requests.Timeout:
        return "❌ Render — timeout (>10s)"
    except Exception as e:
        return f"❌ Render — {e}"


def _check_elevenlabs() -> str:
    try:
        try:
            from src.core.voice_engine import _get_next_el_key, _get_elevenlabs_chars_left
        except ImportError:
            from core.voice_engine import _get_next_el_key, _get_elevenlabs_chars_left
        key = _get_next_el_key()
        if not key:
            return "⚠️ ElevenLabs — no key configured"
        chars_left = _get_elevenlabs_chars_left(key)
        icon = "✅" if chars_left > 5000 else "⚠️" if chars_left > 0 else "❌"
        return f"{icon} ElevenLabs — {chars_left:,} chars left"
    except Exception as e:
        return f"❌ ElevenLabs — {e}"


def _write_system_log(summary: str) -> None:
    base = _supabase_base()
    if not base:
        return
    payload = {
        "event":      "health_check",
        "level":      "info",
        "message":    summary[:500],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        requests.post(
            f"{base}/rest/v1/aisha_system_log",
            json=payload,
            headers=_supabase_headers(),
            timeout=8,
        )
    except Exception:
        pass


def run_health_check() -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    sections = [f"*Aisha — Health Report*\n_{ts}_\n"]

    sections.append("*AI Providers:*")
    sections.extend(_check_ai_providers())

    sections.append("\n*Supabase Tables:*")
    sections.extend(_check_supabase_tables())

    sections.append("\n*Services:*")
    sections.append(_check_render())
    sections.append(_check_elevenlabs())

    report = "\n".join(sections)
    _write_system_log(report)
    return report


full_health_report = run_health_check
