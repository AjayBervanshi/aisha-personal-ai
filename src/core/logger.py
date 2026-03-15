"""
logger.py
=========
Structured logging for Aisha.

Every module should use:
    from src.core.logger import get_logger
    log = get_logger("ModuleName")

Log lines are emitted as JSON to stdout so Railway captures them cleanly.
Optionally also writes ERROR+ events to the aisha_system_log Supabase table
for in-app observability (set SUPABASE_LOG_ERRORS=true in .env).

Usage:
    log = get_logger("AishaBrain")
    log.info("think_start", user_message=user_message[:80], platform=platform)
    log.error("ai_call_failed", provider="gemini", error=str(e))
"""

import json
import logging
import os
import traceback
from datetime import datetime, timezone
from typing import Any


# ── Output Formatter ─────────────────────────────────────────────────────────

class _JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON for Railway log aggregation."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "event": record.getMessage(),
        }
        # Attach any extra kwargs passed via log.info("event", key=val)
        for key, val in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
            ):
                payload[key] = val

        if record.exc_info:
            payload["traceback"] = self.formatException(record.exc_info)

        try:
            return json.dumps(payload, ensure_ascii=False, default=str)
        except Exception:
            return json.dumps({"level": "error", "event": "log_format_failed"})


# ── Supabase Sink (optional) ─────────────────────────────────────────────────

_supabase_client = None

def _get_supabase():
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if url and key and "your_" not in url:
        try:
            from supabase import create_client
            _supabase_client = create_client(url, key)
        except Exception:
            pass
    return _supabase_client


class _SupabaseSinkHandler(logging.Handler):
    """Writes ERROR+ log records to aisha_system_log table."""

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno < logging.ERROR:
            return
        if os.getenv("SUPABASE_LOG_ERRORS", "").lower() not in ("true", "1", "yes"):
            return
        db = _get_supabase()
        if not db:
            return
        try:
            db.table("aisha_system_log").insert({
                "level": record.levelname.lower(),
                "module": record.name,
                "event": record.getMessage()[:500],
                "context": {},
                "error_trace": (
                    traceback.format_exception(*record.exc_info)[-1]
                    if record.exc_info else None
                ),
            }).execute()
        except Exception:
            pass  # Never let logging crash the app


# ── Factory ──────────────────────────────────────────────────────────────────

_configured = False

def _configure_root() -> None:
    global _configured
    if _configured:
        return
    _configured = True

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Clear any existing handlers to avoid duplicates
    root.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    root.addHandler(handler)

    # Optional Supabase sink for errors
    root.addHandler(_SupabaseSinkHandler())


def get_logger(name: str) -> logging.Logger:
    """Return a logger with JSON formatting wired up."""
    _configure_root()
    return logging.getLogger(f"Aisha.{name}")
