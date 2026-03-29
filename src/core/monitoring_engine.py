import os
import logging
import requests
from datetime import datetime, timezone, timedelta

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
            secs_left = info.get("cooldown_secs_left", 0)
            if available and not cooling:
                icon  = "✅"
                state = "ready"
            elif cooling:
                icon  = "⏳"
                if secs_left >= 3600:
                    state = f"cooling down ({secs_left // 3600}h {(secs_left % 3600) // 60}m)"
                elif secs_left >= 60:
                    state = f"cooling down ({secs_left // 60}m {secs_left % 60}s)"
                else:
                    state = f"cooling down ({secs_left}s)"
            else:
                icon  = "❌"
                state = "unavailable"
            calls    = info.get("calls", 0)
            failures = info.get("failures", 0)
            lines.append(f"{icon} `{name}` — {state} | calls: {calls}, failures: {failures}")
    except Exception as e:
        lines.append(f"❌ AI provider check failed: {e}")
    return lines


def _check_stuck_queue() -> list:
    """Return alert lines for content_jobs stuck in 'queued' for more than 1 hour."""
    lines = []
    base = _supabase_base()
    if not base:
        return []
    headers = _supabase_headers()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    try:
        r = requests.get(
            f"{base}/rest/v1/content_jobs"
            f"?status=eq.queued&created_at=lt.{cutoff}&select=id",
            headers={**headers, "Prefer": "count=exact"},
            timeout=10,
        )
        if r.ok:
            count = int(r.headers.get("Content-Range", "0/0").split("/")[-1])
            if count > 10:
                lines.append(
                    f"⚠️ content_jobs: {count} jobs stuck >1h in 'queued'"
                )
    except Exception as e:
        log.warning("Stuck-queue check failed: %s", e)
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
            # Append stuck-queue alert beneath the status summary
            lines.extend(_check_stuck_queue())
        else:
            lines.append(f"⚠️ `content_jobs` — HTTP {r.status_code}")
    except Exception as e:
        lines.append(f"❌ `content_jobs` — {e}")

    # plain count tables
    for table in ("aisha_memory", "aisha_conversations", "aisha_mood_tracker"):
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


def _get_reliability_stats() -> dict:
    """Query aisha_system_log for reliability metrics and content queue depth."""
    base = _supabase_base()
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not base or not key:
        return {}

    headers = {
        "apikey":        key,
        "Authorization": f"Bearer {key}",
    }
    now = datetime.now(timezone.utc)

    # Last 1h errors
    since_1h = (now - timedelta(hours=1)).isoformat()
    errors_1h = 0
    try:
        r1 = requests.get(
            f"{base}/rest/v1/aisha_system_log?level=eq.ERROR&created_at=gte.{since_1h}&select=id",
            headers={**headers, "Prefer": "count=exact"},
            timeout=5,
        )
        if r1.ok:
            errors_1h = int(r1.headers.get("Content-Range", "0/0").split("/")[-1])
    except (requests.RequestException, ValueError, TypeError) as e:
        log.warning("Failed to fetch metric: %s", e)

    # Last 24h errors
    since_24h = (now - timedelta(hours=24)).isoformat()
    errors_24h = 0
    try:
        r2 = requests.get(
            f"{base}/rest/v1/aisha_system_log?level=eq.ERROR&created_at=gte.{since_24h}&select=id",
            headers={**headers, "Prefer": "count=exact"},
            timeout=5,
        )
        if r2.ok:
            errors_24h = int(r2.headers.get("Content-Range", "0/0").split("/")[-1])
    except (requests.RequestException, ValueError, TypeError) as e:
        log.warning("Failed to fetch metric: %s", e)

    # Content queue depth (queued jobs)
    queue_depth = 0
    try:
        r3 = requests.get(
            f"{base}/rest/v1/content_jobs?status=eq.queued&select=id",
            headers={**headers, "Prefer": "count=exact"},
            timeout=5,
        )
        if r3.ok:
            queue_depth = int(r3.headers.get("Content-Range", "0/0").split("/")[-1])
    except (requests.RequestException, ValueError, TypeError) as e:
        log.warning("Failed to fetch metric: %s", e)

    return {"errors_1h": errors_1h, "errors_24h": errors_24h, "queue_depth": queue_depth}


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
    except requests.RequestException as e:
        log.warning("Failed to write system log: %s", e)


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

    reliability = _get_reliability_stats()
    if reliability:
        sections.append("\n*📊 Reliability (last 24h):*")
        sections.append(
            f"  Errors 1h: {reliability['errors_1h']} | 24h: {reliability['errors_24h']}"
        )
        sections.append(
            f"  Queue depth: {reliability['queue_depth']} jobs pending"
        )

    report = "\n".join(sections)
    _write_system_log(report)
    return report


full_health_report = run_health_check
