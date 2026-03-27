"""
system_logger.py
================
Lightweight structured logger that writes to the aisha_system_log Supabase table.
Non-blocking — every call is best-effort. Failures are silently swallowed so
that logging never crashes the main process.

Usage:
    from src.core.system_logger import info, warning, error

    info("ai_router", "gemini success in 1200ms", details={"latency_ms": 1200})
    warning("autonomous_loop", "job_skipped: morning_checkin", details={"reason": "already sent"})
    error("antigravity_agent", "job_failed", details={"job_id": "abc", "error": "timeout"})
"""

import os
import requests

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")


def log(level: str, module: str, message: str, details=None) -> None:
    """Write one row to aisha_system_log. Non-blocking — best effort only."""
    try:
        if not SUPABASE_URL or not SERVICE_KEY:
            return
        requests.post(
            f"{SUPABASE_URL}/rest/v1/aisha_system_log",
            headers={
                "apikey": SERVICE_KEY,
                "Authorization": f"Bearer {SERVICE_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "level": level,
                "module": module,
                "message": message,
                "details": details,
            },
            timeout=3,
        )
    except Exception:
        pass  # Never let logging crash the main process


def info(module: str, message: str, details=None) -> None:
    log("INFO", module, message, details)


def warning(module: str, message: str, details=None) -> None:
    log("WARNING", module, message, details)


def error(module: str, message: str, details=None) -> None:
    log("ERROR", module, message, details)
