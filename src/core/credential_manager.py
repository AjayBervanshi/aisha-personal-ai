"""
credential_manager.py
=====================
Credential Health Check & Auto-Routing System for Aisha.

Capabilities:
  1. Test all API keys daily with minimal real API calls
  2. Auto-disable keys that fail 3+ consecutive days (active=False in Supabase)
  3. Smart routing — return best available provider for a given task type
  4. Notify Ajay via Telegram when a key dies or recovers

Key test rules:
  - Timeout: 10s per key
  - 429 (rate limited) → treat as ALIVE
  - Max 1 request per key per check
  - Results logged to aisha_audit_log Supabase table

Provider priority for get_best_ai_provider():
  NVIDIA NIM → Gemini → Groq → OpenAI → Anthropic → xAI
"""

import os
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

log = logging.getLogger("Aisha.CredentialManager")

# ── Supabase helpers ─────────────────────────────────────────────────────────

def _supa_headers() -> dict:
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def _supa_url(path: str) -> str:
    base = os.getenv("SUPABASE_URL", "").rstrip("/")
    return f"{base}/rest/v1/{path}"


# ── Constants ────────────────────────────────────────────────────────────────

AJAY_TELEGRAM_ID = 1002381172

# Number of consecutive daily failures before a key is auto-disabled
FAIL_DAYS_THRESHOLD = 3

# NVIDIA key names (NVIDIA_KEY_01 ... NVIDIA_KEY_22)
NVIDIA_KEY_NAMES = [f"NVIDIA_KEY_{i:02d}" for i in range(1, 23)]

# All non-NVIDIA keys to test and how to test them
# Format: (name_prefix, test_fn_name)
NON_NVIDIA_KEYS = [
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "XAI_API_KEY",
    "ELEVENLABS_API_KEY",
    "HUGGINGFACE_API_KEY",
    "GITHUB_TOKEN",
]

# Provider priority for get_best_ai_provider()
# Maps task_type → ordered list of (key_prefix, provider_label)
PROVIDER_PRIORITY = {
    "chat": [
        ("NVIDIA_KEY_",  "nvidia"),
        ("GEMINI_API_KEY", "gemini"),
        ("GROQ_API_KEY",   "groq"),
        ("OPENAI_API_KEY", "openai"),
        ("ANTHROPIC_API_KEY", "anthropic"),
        ("XAI_API_KEY",    "xai"),
    ],
    "writing": [
        ("NVIDIA_KEY_",  "nvidia"),
        ("GEMINI_API_KEY", "gemini"),
        ("GROQ_API_KEY",   "groq"),
        ("OPENAI_API_KEY", "openai"),
        ("ANTHROPIC_API_KEY", "anthropic"),
        ("XAI_API_KEY",    "xai"),
    ],
    "vision": [
        ("GEMINI_API_KEY", "gemini"),
        ("OPENAI_API_KEY", "openai"),
        ("ANTHROPIC_API_KEY", "anthropic"),
        ("NVIDIA_KEY_",  "nvidia"),
    ],
}
# Default for unknown task types
PROVIDER_PRIORITY["default"] = PROVIDER_PRIORITY["chat"]


# ── CredentialManager ────────────────────────────────────────────────────────

class CredentialManager:
    """
    Tests all API keys, auto-disables failing ones, routes to best provider.

    Usage:
        cm = CredentialManager()
        summary = cm.run_daily_health_check()
        provider, key = cm.get_best_ai_provider("chat")
    """

    def __init__(self):
        self._db_keys: dict = {}          # name → {secret, active, fail_days}
        self._test_results: dict = {}     # name → True/False (last run)
        self._telegram_bot_token: Optional[str] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def get_all_key_statuses(self) -> dict:
        """
        Fetch current status of all keys from Supabase api_keys table.
        Returns dict: {name: {"secret": ..., "active": bool, "fail_days": int}}
        """
        try:
            r = requests.get(
                _supa_url("api_keys?select=name,secret,active,fail_days"),
                headers=_supa_headers(),
                timeout=10,
            )
            if r.status_code != 200:
                log.error(f"[CredMgr] get_all_key_statuses HTTP {r.status_code}: {r.text[:200]}")
                return {}
            rows = r.json()
            result = {}
            for row in rows:
                result[row["name"]] = {
                    "secret":    row.get("secret", ""),
                    "active":    row.get("active", True),
                    "fail_days": row.get("fail_days", 0),
                }
            self._db_keys = result
            return result
        except Exception as e:
            log.error(f"[CredMgr] get_all_key_statuses failed: {e}")
            return {}

    def test_single_key(self, name: str, secret: str) -> bool:
        """
        Test a specific API key with a minimal real API call.
        Returns True if alive (including 429 rate-limited = alive).
        Timeout: 10 seconds.
        """
        if not secret or len(secret) < 10:
            log.debug(f"[CredMgr] {name}: empty/invalid secret — skip")
            return False

        try:
            if name == "GEMINI_API_KEY":
                return self._test_gemini(secret)
            elif name == "GROQ_API_KEY":
                return self._test_groq(secret)
            elif name == "OPENAI_API_KEY":
                return self._test_openai(secret)
            elif name == "ANTHROPIC_API_KEY":
                return self._test_anthropic(secret)
            elif name == "XAI_API_KEY":
                return self._test_xai(secret)
            elif name == "ELEVENLABS_API_KEY":
                return self._test_elevenlabs(secret)
            elif name == "HUGGINGFACE_API_KEY":
                return self._test_huggingface(secret)
            elif name == "GITHUB_TOKEN":
                return self._test_github(secret)
            elif name.startswith("NVIDIA_KEY_"):
                return self._test_nvidia(secret, name)
            else:
                # Unknown key — cannot test, assume alive if non-empty
                log.debug(f"[CredMgr] {name}: no test defined — assuming alive")
                return True
        except Exception as e:
            log.warning(f"[CredMgr] {name} test raised exception: {e}")
            return False

    def test_all_keys(self) -> dict:
        """
        Test all API keys fetched from Supabase.
        Returns {key_name: True/False}
        """
        statuses = self.get_all_key_statuses()
        if not statuses:
            log.warning("[CredMgr] No keys fetched from Supabase — falling back to env vars")
            statuses = self._load_keys_from_env()

        results = {}
        for name, info in statuses.items():
            if not info.get("active", True):
                log.info(f"[CredMgr] {name}: already inactive — skipping test")
                results[name] = False
                continue
            secret = info.get("secret", "")
            alive = self.test_single_key(name, secret)
            results[name] = alive
            status_str = "ALIVE" if alive else "DEAD"
            log.info(f"[CredMgr] {name}: {status_str}")

        self._test_results = results
        return results

    def run_daily_health_check(self) -> str:
        """
        Full daily health check:
          1. Test all API keys
          2. Auto-disable keys failing 3+ consecutive days
          3. Log results to aisha_audit_log
          4. Send one Telegram summary to Ajay

        Returns human-readable summary string.
        """
        log.info("[CredMgr] Starting daily health check...")
        start_ts = time.time()

        # Step 1: load current DB state
        statuses = self.get_all_key_statuses()
        if not statuses:
            statuses = self._load_keys_from_env()

        # Step 2: test all active keys
        results = {}
        newly_dead = []
        newly_recovered = []
        just_disabled = []

        for name, info in statuses.items():
            was_active = info.get("active", True)
            prev_fail_days = info.get("fail_days", 0) or 0
            secret = info.get("secret", "")

            if not was_active:
                results[name] = False
                continue

            alive = self.test_single_key(name, secret)
            results[name] = alive

            if alive:
                # Reset fail counter if it was > 0 (recovery)
                if prev_fail_days > 0:
                    newly_recovered.append(name)
                    self._update_key_in_db(name, fail_days=0)
            else:
                new_fail_days = prev_fail_days + 1
                if new_fail_days >= FAIL_DAYS_THRESHOLD:
                    # Auto-disable
                    self._update_key_in_db(name, active=False, fail_days=new_fail_days)
                    just_disabled.append(name)
                    log.warning(f"[CredMgr] AUTO-DISABLED {name} after {new_fail_days} consecutive fail days")
                else:
                    self._update_key_in_db(name, fail_days=new_fail_days)
                    newly_dead.append(name)

        self._test_results = results

        # Step 3: build summary
        total = len(results)
        alive_count = sum(1 for v in results.values() if v)
        dead_count = total - alive_count
        elapsed = int(time.time() - start_ts)

        summary_lines = [
            f"Key Health Report: {alive_count}/{total} working ({elapsed}s)",
        ]
        if just_disabled:
            summary_lines.append(f"Auto-disabled ({FAIL_DAYS_THRESHOLD}d fail): " + ", ".join(just_disabled))
        if newly_dead:
            summary_lines.append(f"Newly failing: " + ", ".join(newly_dead))
        if newly_recovered:
            summary_lines.append(f"Recovered: " + ", ".join(newly_recovered))

        summary = "\n".join(summary_lines)

        # Step 4: log to aisha_audit_log
        self._log_to_audit_table(
            category="credential_health",
            status="ok" if dead_count == 0 else "warning",
            message=summary,
            details=results,
        )

        # Step 5: Telegram notification
        tg_msg = (
            f"*Aisha Credential Health Report*\n"
            f"`{alive_count}/{total}` keys alive\n"
        )
        if just_disabled:
            tg_msg += f"\n*Auto-disabled* (failed {FAIL_DAYS_THRESHOLD}+ days):\n" + "\n".join(f"• `{k}`" for k in just_disabled)
        if newly_dead:
            tg_msg += f"\n*Newly failing*:\n" + "\n".join(f"• `{k}`" for k in newly_dead)
        if newly_recovered:
            tg_msg += f"\n*Recovered*:\n" + "\n".join(f"• `{k}`" for k in newly_recovered)
        if not just_disabled and not newly_dead and not newly_recovered:
            tg_msg += "\nAll keys stable. No changes."

        self._send_telegram(tg_msg)

        log.info(f"[CredMgr] Health check complete: {summary}")
        return summary

    def get_best_ai_provider(self, task_type: str = "chat") -> tuple:
        """
        Return (provider_name, api_key) for the best working provider for task_type.
        Priority: NVIDIA NIM > Gemini > Groq > OpenAI > Anthropic > xAI

        Uses cached test results if available, otherwise queries DB for active keys.
        Returns ("none", "") if nothing is available.
        """
        # Refresh statuses if we don't have them yet
        if not self._db_keys:
            self.get_all_key_statuses()

        priority = PROVIDER_PRIORITY.get(task_type, PROVIDER_PRIORITY["default"])

        for key_prefix, provider_label in priority:
            if key_prefix.endswith("_"):
                # It's a pool prefix (NVIDIA_KEY_)
                for name, info in self._db_keys.items():
                    if name.startswith(key_prefix) and info.get("active", True):
                        # Check test result cache
                        if self._test_results.get(name, True):  # default True (assume alive if not tested)
                            return (provider_label, info.get("secret", ""))
            else:
                # Exact key name
                info = self._db_keys.get(key_prefix, {})
                if info.get("active", True) and self._test_results.get(key_prefix, True):
                    secret = info.get("secret", "")
                    if not secret:
                        # Fall back to env var
                        secret = os.getenv(key_prefix, "")
                    if secret:
                        return (provider_label, secret)

        log.warning(f"[CredMgr] get_best_ai_provider('{task_type}'): no working provider found")
        return ("none", "")

    # ── Individual key testers ────────────────────────────────────────────────

    def _test_gemini(self, secret: str) -> bool:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={secret}"
        r = requests.post(
            url,
            json={"contents": [{"parts": [{"text": "Hi"}]}]},
            timeout=10,
        )
        return r.status_code in (200, 429)

    def _test_groq(self, secret: str) -> bool:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1,
            },
            timeout=10,
        )
        return r.status_code in (200, 429)

    def _test_openai(self, secret: str) -> bool:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1,
            },
            timeout=10,
        )
        return r.status_code in (200, 429)

    def _test_anthropic(self, secret: str) -> bool:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": secret,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "Hi"}],
            },
            timeout=10,
        )
        return r.status_code in (200, 429)

    def _test_xai(self, secret: str) -> bool:
        r = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
            json={
                "model": "grok-3-mini",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1,
            },
            timeout=10,
        )
        return r.status_code in (200, 429)

    def _test_elevenlabs(self, secret: str) -> bool:
        r = requests.get(
            "https://api.elevenlabs.io/v1/user",
            headers={"xi-api-key": secret},
            timeout=10,
        )
        return r.status_code in (200, 429)

    def _test_huggingface(self, secret: str) -> bool:
        r = requests.get(
            "https://huggingface.co/api/whoami",
            headers={"Authorization": f"Bearer {secret}"},
            timeout=10,
        )
        return r.status_code in (200, 429)

    def _test_github(self, secret: str) -> bool:
        r = requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {secret}"},
            timeout=10,
        )
        return r.status_code in (200, 429)

    def _test_nvidia(self, secret: str, name: str) -> bool:
        r = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
            json={
                "model": "meta/llama-3.3-70b-instruct",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1,
            },
            timeout=10,
        )
        # 402 = credits exhausted — key is valid but out of credits; treat as dead
        # 404 = model not found — key may be valid but model gone; treat as dead
        return r.status_code in (200, 429)

    # ── Supabase DB helpers ───────────────────────────────────────────────────

    def _update_key_in_db(self, name: str, active: bool = None, fail_days: int = None):
        """Patch a single row in api_keys table."""
        payload = {}
        if active is not None:
            payload["active"] = active
        if fail_days is not None:
            payload["fail_days"] = fail_days
        if not payload:
            return

        try:
            r = requests.patch(
                _supa_url(f"api_keys?name=eq.{name}"),
                headers=_supa_headers(),
                json=payload,
                timeout=10,
            )
            if r.status_code not in (200, 204):
                log.warning(f"[CredMgr] DB update {name} failed: {r.status_code} {r.text[:100]}")
        except Exception as e:
            log.warning(f"[CredMgr] DB update {name} exception: {e}")

    def _log_to_audit_table(self, category: str, status: str, message: str, details: dict = None):
        """Write a record to aisha_audit_log Supabase table."""
        payload = {
            "category":   category,
            "status":     status,
            "message":    message,
            "details":    details or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            r = requests.post(
                _supa_url("aisha_audit_log"),
                headers={**_supa_headers(), "Prefer": "return=minimal"},
                json=payload,
                timeout=10,
            )
            if r.status_code not in (200, 201, 204):
                log.warning(f"[CredMgr] Audit log insert failed: {r.status_code} {r.text[:100]}")
        except Exception as e:
            log.warning(f"[CredMgr] Audit log exception: {e}")

    # ── Telegram ──────────────────────────────────────────────────────────────

    def _get_telegram_token(self) -> Optional[str]:
        """Fetch TELEGRAM_BOT_TOKEN from api_keys table or env."""
        if self._telegram_bot_token:
            return self._telegram_bot_token

        # Try DB first (may already be loaded)
        info = self._db_keys.get("TELEGRAM_BOT_TOKEN", {})
        token = info.get("secret", "") or os.getenv("TELEGRAM_BOT_TOKEN", "")

        if not token:
            # Fetch specifically from DB
            try:
                r = requests.get(
                    _supa_url("api_keys?name=eq.TELEGRAM_BOT_TOKEN&select=secret"),
                    headers=_supa_headers(),
                    timeout=10,
                )
                if r.status_code == 200:
                    rows = r.json()
                    if rows:
                        token = rows[0].get("secret", "")
            except Exception as e:
                log.warning(f"[CredMgr] Could not fetch Telegram token from DB: {e}")

        self._telegram_bot_token = token or None
        return self._telegram_bot_token

    def _send_telegram(self, message: str):
        """Send a message to Ajay via Telegram."""
        token = self._get_telegram_token()
        if not token:
            log.warning("[CredMgr] No Telegram bot token — cannot send notification")
            return
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id":    AJAY_TELEGRAM_ID,
                    "text":       message,
                    "parse_mode": "Markdown",
                },
                timeout=10,
            )
            if r.status_code != 200:
                log.warning(f"[CredMgr] Telegram send failed: {r.status_code} {r.text[:100]}")
            else:
                log.info("[CredMgr] Telegram notification sent to Ajay")
        except Exception as e:
            log.warning(f"[CredMgr] Telegram send exception: {e}")

    # ── Env fallback ──────────────────────────────────────────────────────────

    def _load_keys_from_env(self) -> dict:
        """
        Fallback: build a statuses dict from environment variables directly.
        Used when Supabase is unreachable.
        """
        result = {}
        all_names = NON_NVIDIA_KEYS + NVIDIA_KEY_NAMES
        for name in all_names:
            secret = os.getenv(name, "")
            if secret:
                result[name] = {"secret": secret, "active": True, "fail_days": 0}
        return result
