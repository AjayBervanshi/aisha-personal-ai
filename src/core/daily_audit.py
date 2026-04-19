"""
daily_audit.py
==============
Aisha's Daily Self-Audit System.

Runs every day at 2 AM IST (20:30 UTC) to:
1. Check all AI providers
2. Check all DB tables
3. Check all critical files exist
4. Check all required env vars
5. Test key integrations
6. Log results to aisha_audit_log table
7. Send summary to Ajay via Telegram
8. Auto-trigger self-improvement for broken items

Audit categories:
- CRITICAL: System will fail without this
- WARNING: Degraded but functional
- INFO: Nice to have
"""

import os
import logging
import requests
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

log = logging.getLogger("Aisha.DailyAudit")

# ── Constants ────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent.parent

CRITICAL_FILES = [
    "src/core/ai_router.py",
    "src/core/voice_engine.py",
    "src/agents/youtube_crew.py",
    "src/core/self_improvement.py",
]

REQUIRED_ENV_VARS = [
    "GEMINI_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "SUPABASE_URL",
    "GITHUB_TOKEN",
    "RENDER_DEPLOY_HOOK_URL",
]

REQUIRED_TABLES = [
    "content_jobs",
    "aisha_memory",
    "api_keys",
    "aisha_approved_users",
    "aisha_improvement_log",
    "aisha_system_log",
    "content_performance",
]

# ── Individual Check Functions ────────────────────────────────────────────────

def check_ai_providers() -> dict:
    """Test each AI provider with a simple call. Returns {provider: 'ok'/'error: msg'}"""
    results = {}

    # --- Gemini ---
    try:
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        if not gemini_key:
            results["gemini"] = "error: GEMINI_API_KEY not set"
        else:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
            payload = {"contents": [{"parts": [{"text": "ping"}]}]}
            resp = requests.post(url, json=payload, timeout=15)
            if resp.status_code == 200:
                results["gemini"] = "ok"
            else:
                results["gemini"] = f"error: HTTP {resp.status_code}"
    except Exception as e:
        results["gemini"] = f"error: {e}"

    # --- Groq ---
    try:
        groq_key = os.getenv("GROQ_API_KEY", "")
        if not groq_key:
            results["groq"] = "error: GROQ_API_KEY not set"
        else:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 5,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                results["groq"] = "ok"
            else:
                results["groq"] = f"error: HTTP {resp.status_code}"
    except Exception as e:
        results["groq"] = f"error: {e}"

    # --- NVIDIA NIM (first available key) ---
    try:
        from src.core.nvidia_pool import NvidiaPool
        pool = NvidiaPool()
        key = pool.get_key("chat")
        if not key:
            results["nvidia_nim"] = "error: no active keys"
        else:
            resp = requests.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": "meta/llama-3.3-70b-instruct",
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 5,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                results["nvidia_nim"] = "ok"
            else:
                results["nvidia_nim"] = f"error: HTTP {resp.status_code}"
    except Exception as e:
        results["nvidia_nim"] = f"error: {e}"

    # --- ElevenLabs ---
    try:
        el_key = os.getenv("ELEVENLABS_API_KEY", "")
        if not el_key:
            results["elevenlabs"] = "error: ELEVENLABS_API_KEY not set"
        else:
            resp = requests.get(
                "https://api.elevenlabs.io/v1/user",
                headers={"xi-api-key": el_key},
                timeout=15,
            )
            if resp.status_code == 200:
                results["elevenlabs"] = "ok"
            else:
                results["elevenlabs"] = f"error: HTTP {resp.status_code}"
    except Exception as e:
        results["elevenlabs"] = f"error: {e}"

    return results


async def check_supabase_tables() -> dict:
    """Check each required table exists and is reachable. Returns {table: 'ok'/'error: msg'}"""
    import asyncio
    results = {}

    async def _check_table(sb, table):
        try:
            await sb.table(table).select("id", count="exact").limit(0).execute()
            return table, "ok"
        except Exception as e:
            return table, f"error: {e}"

    try:
        from supabase import create_async_client
        sb = await create_async_client(
            os.getenv("SUPABASE_URL", ""),
            os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
        )
        tasks = [_check_table(sb, table) for table in REQUIRED_TABLES]
        res = await asyncio.gather(*tasks)
        return dict(res)
    except Exception as e:
        for table in REQUIRED_TABLES:
            results[table] = f"error: supabase client failed: {e}"
    return results


def check_critical_files() -> dict:
    """Verify key source files exist on disk. Returns {file: 'ok'/'missing'}"""
    results = {}
    for rel_path in CRITICAL_FILES:
        full = PROJECT_ROOT / rel_path
        results[rel_path] = "ok" if full.exists() else "missing"
    return results


def check_env_vars() -> dict:
    """Verify all required env vars are set (non-empty). Returns {var: 'ok'/'missing'}"""
    results = {}
    for var in REQUIRED_ENV_VARS:
        val = os.getenv(var, "")
        results[var] = "ok" if val.strip() else "missing"
    return results


def check_self_improvement_freshness() -> dict:
    """Check whether the last self-improvement run was within the past 7 days."""
    result = {"last_improvement": "unknown", "status": "ok"}
    try:
        from supabase import create_client
        sb = create_client(
            os.getenv("SUPABASE_URL", ""),
            os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
        )
        resp = (
            sb.table("aisha_improvement_log")
            .select("started_at")
            .order("started_at", desc=True)
            .limit(1)
            .execute()
        )
        if resp.data:
            last_str = resp.data[0].get("started_at", "")
            result["last_improvement"] = last_str
            # Parse and compare
            from datetime import datetime, timezone, timedelta
            last_dt = datetime.fromisoformat(last_str.replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - last_dt).days
            if age_days > 7:
                result["status"] = f"warning: last improvement was {age_days} days ago"
            else:
                result["status"] = "ok"
        else:
            result["status"] = "warning: no improvement records found"
    except Exception as e:
        result["status"] = f"error: {e}"
    return result


# ── Report Generation ─────────────────────────────────────────────────────────

def generate_audit_report(results: dict) -> str:
    """Format audit results into a Telegram-friendly message."""
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M IST")

    ai = results.get("ai_providers", {})
    tables = results.get("supabase_tables", {})
    files = results.get("critical_files", {})
    env = results.get("env_vars", {})
    improvement = results.get("self_improvement", {})

    # Count totals
    all_checks = {}
    all_checks.update(ai)
    all_checks.update(tables)
    all_checks.update(files)
    all_checks.update(env)

    ok_count = sum(1 for v in all_checks.values() if v == "ok")
    warn_count = sum(1 for v in all_checks.values() if v.startswith("warning"))
    err_count = sum(1 for v in all_checks.values() if v not in ("ok",) and not v.startswith("warning"))

    # AI providers section
    ai_lines = []
    for provider, status in ai.items():
        icon = "✅" if status == "ok" else "❌"
        ai_lines.append(f"  • {provider}: {icon} {status}")

    # DB tables section
    tables_ok = sum(1 for v in tables.values() if v == "ok")
    db_line = f"✅ {tables_ok}/{len(tables)} tables OK" if tables_ok == len(tables) else f"⚠️ {tables_ok}/{len(tables)} tables OK"

    # Files section
    files_ok = all(v == "ok" for v in files.values())
    missing_files = [k for k, v in files.items() if v != "ok"]
    files_line = "✅ All critical files present" if files_ok else f"❌ Missing: {', '.join(missing_files)}"

    # Env vars section
    missing_vars = [k for k, v in env.items() if v != "ok"]
    env_line = "✅ All env vars set" if not missing_vars else f"⚠️ Missing: {', '.join(missing_vars)}"

    # Broken items for self-improvement trigger
    broken = [k for k, v in all_checks.items() if v not in ("ok",) and not v.startswith("warning")]

    # Self-improvement freshness
    imp_status = improvement.get("status", "unknown")
    imp_icon = "✅" if imp_status == "ok" else "⚠️"
    imp_line = f"{imp_icon} Self-improvement: {imp_status}"

    lines = [
        f"🔍 Daily System Audit — {date_str}",
        "",
        f"✅ Working: {ok_count} features",
        f"⚠️ Warnings: {warn_count} items",
        f"❌ Broken: {err_count} items",
        "",
        "AI Providers:",
        *ai_lines,
        "",
        f"Database: {db_line}",
        f"Files: {files_line}",
        f"Env Vars: {env_line}",
        f"{imp_line}",
    ]

    if broken:
        broken_str = ", ".join(broken[:5])
        lines += ["", f"💡 Auto-triggering self-improvement for: {broken_str}"]

    return "\n".join(lines)


# ── Persistence & Notification ────────────────────────────────────────────────

def save_audit_to_db(results: dict):
    """Save audit results to aisha_audit_log table. Creates table row if it doesn't exist."""
    try:
        from supabase import create_client
        sb = create_client(
            os.getenv("SUPABASE_URL", ""),
            os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
        )
        sb.table("aisha_audit_log").insert({
            "audit_date": datetime.now(timezone.utc).isoformat(),
            "ai_providers": results.get("ai_providers", {}),
            "supabase_tables": results.get("supabase_tables", {}),
            "critical_files": results.get("critical_files", {}),
            "env_vars": results.get("env_vars", {}),
            "self_improvement": results.get("self_improvement", {}),
            "summary": results.get("report", ""),
        }).execute()
        log.info("event=audit_saved_to_db")
    except Exception as e:
        log.warning(f"event=audit_db_save_failed err={e}")


def notify_ajay_audit_summary(report: str):
    """Send audit summary to Ajay via Telegram."""
    try:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        ajay_id = os.getenv("AJAY_TELEGRAM_ID", "1002381172")
        if not bot_token:
            log.warning("event=audit_notify_skip reason=no_bot_token")
            return
        resp = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": ajay_id, "text": report},
            timeout=15,
        )
        if resp.status_code == 200:
            log.info("event=audit_notified_ajay")
        else:
            log.warning(f"event=audit_notify_failed status={resp.status_code}")
    except Exception as e:
        log.warning(f"event=audit_notify_error err={e}")


# ── Self-Improvement Trigger ──────────────────────────────────────────────────

def _trigger_self_improvement_for_broken(results: dict):
    """If broken items were found, kick off a self-improvement session."""
    ai = results.get("ai_providers", {})
    files = results.get("critical_files", {})
    broken = []
    for k, v in {**ai, **files}.items():
        if v not in ("ok",) and not v.startswith("warning"):
            broken.append(k)
    if not broken:
        return
    log.info(f"event=audit_trigger_improvement broken={broken}")
    try:
        from src.core.self_editor import SelfEditor
        editor = SelfEditor()
        editor.run_improvement_session()
    except Exception as e:
        log.error(f"event=audit_improvement_trigger_failed err={e}")


# ── Main Entry Point ─────────────────────────────────────────────────────────

async def run_daily_audit() -> dict:
    """Run full system audit, persist results, notify Ajay, and return results dict."""
    log.info("event=daily_audit_start")

    results = {}
    results["ai_providers"] = check_ai_providers()
    results["supabase_tables"] = await check_supabase_tables()
    results["critical_files"] = check_critical_files()
    results["env_vars"] = check_env_vars()
    results["self_improvement"] = check_self_improvement_freshness()

    report = generate_audit_report(results)
    results["report"] = report

    log.info("event=daily_audit_complete")
    log.info(f"audit_report=\n{report}")

    save_audit_to_db(results)
    notify_ajay_audit_summary(report)
    _trigger_self_improvement_for_broken(results)

    return results


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_daily_audit())
