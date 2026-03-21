"""
failure_detector.py
===================
Detects real conversation failures from Supabase logs and converts them
into actionable self-improvement tasks for Aisha.

Instead of random code generation, Aisha now improves based on what
actually went wrong in her conversations.

Flow:
  get_recent_failures() -> detect_failure_patterns() -> failure_to_improvement_task()
  get_top_improvement_task() orchestrates all three and returns the highest-priority task.
"""

import os
import re
import logging
from datetime import datetime, timedelta, timezone
from collections import Counter
from typing import Optional

import requests

log = logging.getLogger("Aisha.FailureDetector")

# ── Supabase REST helpers ──────────────────────────────────────────────────────

def _supabase_headers() -> dict:
    """Build Supabase REST API auth headers using the service key."""
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    return {
        "apikey": key or "",
        "Authorization": f"Bearer {key or ''}",
        "Content-Type": "application/json",
    }


def _supabase_url(table: str, params: str = "") -> str:
    """Build a Supabase REST URL for a given table."""
    base = os.getenv("SUPABASE_URL", "").rstrip("/")
    url = f"{base}/rest/v1/{table}"
    if params:
        url = f"{url}?{params}"
    return url


# ── Core data fetch ────────────────────────────────────────────────────────────

def get_recent_failures(limit: int = 50) -> list:
    """
    Fetch the last 24 hours of conversation rows from Supabase.

    Tries `aisha_conversations` first; if that table is missing or returns
    no usable data, tries `aisha_memory` as a fallback.

    Returns a list of dicts with keys: role, message, created_at, user_id.
    Returns [] on any error so callers never crash.
    """
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

    for table in ("aisha_conversations", "aisha_memory"):
        try:
            params = (
                f"select=role,message,created_at"
                f"&created_at=gte.{since}"
                f"&order=created_at.desc"
                f"&limit={limit}"
            )
            resp = requests.get(
                _supabase_url(table, params),
                headers=_supabase_headers(),
                timeout=15,
            )

            # 404 / 400 with PGRST code means table does not exist — try next
            if resp.status_code in (404, 400):
                body = resp.json() if resp.content else {}
                code = body.get("code", "")
                if "PGRST" in str(code) or resp.status_code == 404:
                    log.debug(f"[FailureDetector] Table '{table}' not found, skipping.")
                    continue

            if resp.status_code != 200:
                log.warning(
                    f"[FailureDetector] Unexpected {resp.status_code} from '{table}': "
                    f"{resp.text[:200]}"
                )
                continue

            rows = resp.json()
            if not isinstance(rows, list):
                continue

            # Normalise: ensure 'message' key exists (aisha_memory may use 'content')
            normalised = []
            for row in rows:
                message = row.get("message") or row.get("content") or ""
                if not message:
                    continue
                normalised.append({
                    "role": row.get("role", "unknown"),
                    "message": message,
                    "created_at": row.get("created_at", ""),
                    "user_id": row.get("user_id", ""),
                })

            log.info(
                f"[FailureDetector] Loaded {len(normalised)} rows from '{table}' "
                f"(last 24 h)."
            )
            return normalised

        except requests.exceptions.ConnectionError:
            log.warning("[FailureDetector] Supabase unreachable — returning []")
            return []
        except Exception as exc:
            log.warning(f"[FailureDetector] Error querying '{table}': {exc}")
            continue

    log.info("[FailureDetector] No conversation data found in any table.")
    return []


# ── Pattern detection ──────────────────────────────────────────────────────────

# Patterns that signal "I did something" when no real action was performed
_FALSE_ACTION_PHRASES = (
    "i've updated",
    "i have updated",
    "i've saved",
    "i have saved",
    "i've forwarded",
    "i have forwarded",
    "i've sent",
    "i have sent",
    "done, i've",
    "i've noted",
    "i have noted",
)

_API_ERROR_SIGNALS = (
    "quota exhausted",
    "quota_exceeded",
    "rate limit",
    "429",
    "401",
    "403",
    "invalid api key",
    "unauthorized",
    "access denied",
)


def detect_failure_patterns(conversations: list) -> list:
    """
    Analyse conversation rows and identify known failure categories.

    Detected patterns
    -----------------
    1. wrong_name_used       – AI called the caller "Ajay" in a message that
                               looks like a response to a different user.
    2. false_action_claim    – AI claimed to have saved/updated/forwarded
                               something but no real action handler exists.
    3. command_error         – Message contains "❌" or starts with "Error:".
    4. unanswered_question   – The same user question appears 3+ times.
    5. api_failure           – Response body contains API error signals.

    Returns a list of pattern dicts:
        {
          pattern_type: str,
          description:  str,
          example_message: str,
          severity: int (1–3),
          suggested_fix: str,
        }
    """
    if not conversations:
        return []

    patterns: list = []

    # Separate assistant replies from user messages
    assistant_msgs = [c for c in conversations if c.get("role") == "assistant"]
    user_msgs = [c for c in conversations if c.get("role") == "user"]

    # ── 1. Wrong name ────────────────────────────────────────────────────────
    for row in assistant_msgs:
        msg_lower = row["message"].lower()
        # Simple heuristic: assistant says "Ajay" when user_id is non-empty
        # (non-empty user_id suggests a user other than the owner is chatting)
        if "ajay" in msg_lower and row.get("user_id", ""):
            patterns.append({
                "pattern_type": "wrong_name_used",
                "description": (
                    "Aisha addressed the caller as 'Ajay' even though the "
                    "conversation appears to be with a different user."
                ),
                "example_message": row["message"][:200],
                "severity": 2,
                "suggested_fix": (
                    "Fix the system prompt in src/core/prompts/builder.py "
                    "to always use the caller_name variable instead of "
                    "hardcoding 'Ajay' for guest users."
                ),
            })
            break  # one instance is enough to flag the pattern

    # ── 2. False action claims ───────────────────────────────────────────────
    for row in assistant_msgs:
        msg_lower = row["message"].lower()
        if any(phrase in msg_lower for phrase in _FALSE_ACTION_PHRASES):
            patterns.append({
                "pattern_type": "false_action_claim",
                "description": (
                    "Aisha claimed to have performed an action (save/update/"
                    "forward) but no real handler executed."
                ),
                "example_message": row["message"][:200],
                "severity": 3,
                "suggested_fix": (
                    "Add real action handlers in src/telegram/bot.py: when the "
                    "user asks to save/update/forward, actually perform the "
                    "operation via Supabase instead of just saying 'done'."
                ),
            })
            break

    # ── 3. Command errors ────────────────────────────────────────────────────
    error_pattern = re.compile(r"(error:[^\n]{0,120})", re.IGNORECASE)
    for row in conversations:
        msg = row["message"]
        has_cross = "❌" in msg
        error_match = error_pattern.search(msg)
        if has_cross or error_match:
            error_text = (error_match.group(1) if error_match else "unknown error")

            # Try to guess which command failed
            cmd_match = re.search(r"/(\w+)", msg)
            cmd = cmd_match.group(1) if cmd_match else "unknown"

            patterns.append({
                "pattern_type": "command_error",
                "description": (
                    f"A command or function crashed: {error_text[:120]}"
                ),
                "example_message": msg[:200],
                "severity": 3,
                "suggested_fix": (
                    f"Fix the /{cmd} command in src/telegram/bot.py that "
                    f"crashes with: {error_text[:80]}"
                ),
            })
            break

    # ── 4. Repeated unanswered questions ────────────────────────────────────
    if user_msgs:
        # Normalise to lowercase stripped strings for comparison
        normalised_questions = [
            m["message"].strip().lower()
            for m in user_msgs
            if m["message"].strip().endswith("?")
        ]
        freq = Counter(normalised_questions)
        repeated = [(q, c) for q, c in freq.items() if c >= 3]
        if repeated:
            question, count = max(repeated, key=lambda x: x[1])
            patterns.append({
                "pattern_type": "unanswered_question",
                "description": (
                    f"The same question was asked {count} times without a "
                    f"satisfactory answer: \"{question[:100]}\""
                ),
                "example_message": question[:200],
                "severity": 2,
                "suggested_fix": (
                    f"Add a dedicated handler or improve the response logic "
                    f"in src/telegram/bot.py to properly answer: "
                    f"\"{question[:80]}\""
                ),
            })

    # ── 5. API failures ──────────────────────────────────────────────────────
    for row in conversations:
        msg_lower = row["message"].lower()
        hit = next(
            (sig for sig in _API_ERROR_SIGNALS if sig in msg_lower),
            None,
        )
        if hit:
            # Guess which provider based on context
            provider = "unknown_provider"
            for name in ("gemini", "groq", "openai", "anthropic", "xai", "nvidia", "mistral"):
                if name in msg_lower:
                    provider = name
                    break

            # Extract the HTTP error code if present
            code_match = re.search(r"\b(401|403|429)\b", row["message"])
            error_code = code_match.group(1) if code_match else hit

            patterns.append({
                "pattern_type": "api_failure",
                "description": (
                    f"API provider '{provider}' returned an error "
                    f"({error_code}) during a live conversation."
                ),
                "example_message": row["message"][:200],
                "severity": 2,
                "suggested_fix": (
                    f"Add NVIDIA NIM as immediate fallback when {provider} "
                    f"returns {error_code} in src/core/ai_router.py."
                ),
            })
            break

    log.info(
        f"[FailureDetector] Detected {len(patterns)} failure pattern(s): "
        f"{[p['pattern_type'] for p in patterns]}"
    )
    return patterns


# ── Task generator ─────────────────────────────────────────────────────────────

def failure_to_improvement_task(pattern: dict) -> str:
    """
    Converts a single failure pattern dict into a specific, actionable
    improvement task description string for the self-improvement engine.
    """
    ptype = pattern.get("pattern_type", "unknown")
    fix = pattern.get("suggested_fix", "")

    if fix:
        # The suggested_fix is already concrete — use it directly
        return fix

    # Fallback descriptions per type
    fallbacks = {
        "wrong_name_used": (
            "Fix the system prompt in src/core/prompts/builder.py to always "
            "use caller_name variable instead of hardcoded 'Ajay' for guest users."
        ),
        "false_action_claim": (
            "Add real action handlers in src/telegram/bot.py: when user asks "
            "to save/update/forward, actually do it via Supabase instead of "
            "just saying 'done'."
        ),
        "command_error": (
            "Add robust try/except error handling and user-friendly error "
            "messages to all command handlers in src/telegram/bot.py."
        ),
        "unanswered_question": (
            "Improve fallback response logic in src/telegram/bot.py so Aisha "
            "acknowledges when she cannot answer a question and offers alternatives."
        ),
        "api_failure": (
            "Add NVIDIA NIM as immediate fallback in src/core/ai_router.py "
            "when primary providers return 401/403/429 errors."
        ),
    }
    return fallbacks.get(
        ptype,
        "Add better error handling and logging to src/telegram/bot.py for "
        "unknown command inputs.",
    )


# ── Orchestrator ───────────────────────────────────────────────────────────────

def get_top_improvement_task() -> Optional[str]:
    """
    Full pipeline:
      1. Fetch recent conversation failures from Supabase.
      2. Detect failure patterns.
      3. Pick the highest-severity pattern.
      4. Convert it to an actionable improvement task string.

    Returns None if no failures were found so the caller can fall back to a
    generic improvement task.
    """
    conversations = get_recent_failures(limit=50)
    if not conversations:
        log.info("[FailureDetector] No recent conversations — no failure task generated.")
        return None

    patterns = detect_failure_patterns(conversations)
    if not patterns:
        log.info("[FailureDetector] No failure patterns detected in recent conversations.")
        return None

    # Pick highest severity; break ties by order of detection
    top = max(patterns, key=lambda p: p.get("severity", 1))
    task = failure_to_improvement_task(top)

    log.info(
        f"[FailureDetector] Top failure: [{top['pattern_type']}] "
        f"severity={top['severity']} → task: {task[:80]}"
    )
    return task


# ── __main__ smoke test ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.DEBUG)

    print("=== FailureDetector smoke test ===\n")

    # Test with synthetic conversation data (no Supabase required)
    fake_conversations = [
        {
            "role": "assistant",
            "message": "Sure Ajay, I've updated your schedule for tomorrow!",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "user_id": "user_abc123",
        },
        {
            "role": "user",
            "message": "❌ Error: /remind command failed with KeyError 'task_id'",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "user_id": "user_abc123",
        },
        {
            "role": "user",
            "message": "What is my balance?",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "user_id": "",
        },
        {
            "role": "user",
            "message": "What is my balance?",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "user_id": "",
        },
        {
            "role": "user",
            "message": "What is my balance?",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "user_id": "",
        },
        {
            "role": "assistant",
            "message": "Gemini returned 429: quota exhausted. Please try again.",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "user_id": "",
        },
    ]

    patterns = detect_failure_patterns(fake_conversations)
    print(f"Detected {len(patterns)} pattern(s):")
    for p in patterns:
        print(json.dumps(p, indent=2))

    print("\n--- Top task ---")
    # Inject fake data directly to skip Supabase
    if patterns:
        top = max(patterns, key=lambda x: x.get("severity", 1))
        print(failure_to_improvement_task(top))
    else:
        print("No patterns detected.")
