"""
learning_engine.py
==================
Aisha's Learning System.

Stores and retrieves:
- What improvements worked
- What failed and why
- Better approaches discovered
- Performance metrics over time

Uses improvement_log table in Supabase.
Schema expected:
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid()
  session_id    text UNIQUE NOT NULL
  target_file   text
  skill_name    text
  task_desc     text
  status        text  -- 'started' | 'success' | 'deployed' | 'failed'
  pr_url        text
  pr_number     int
  code_provider text
  code_length   int
  error_message text
  started_at    timestamptz DEFAULT now()
  updated_at    timestamptz DEFAULT now()
"""

import os
import logging
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

log = logging.getLogger("Aisha.LearningEngine")


class LearningEngine:
    """Manages Aisha's self-improvement history stored in Supabase improvement_log."""

    TABLE = "improvement_log"

    def __init__(self):
        from supabase import create_client
        self._sb = create_client(
            os.getenv("SUPABASE_URL", ""),
            os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
        )

    # ── Write Operations ──────────────────────────────────────────────────────

    def log_improvement_started(
        self,
        session_id: str,
        target_file: str,
        skill_name: str,
        task_description: str,
    ) -> str:
        """Log that an improvement session started. Returns the record ID."""
        try:
            resp = self._sb.table(self.TABLE).insert({
                "session_id": session_id,
                "target_file": target_file,
                "skill_name": skill_name,
                "task_desc": task_description,
                "status": "started",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
            record_id = resp.data[0]["id"] if resp.data else session_id
            log.info(f"event=improvement_started session={session_id} file={target_file}")
            return record_id
        except Exception as e:
            log.error(f"event=log_improvement_started_failed err={e}")
            return session_id

    def log_improvement_success(
        self,
        session_id: str,
        pr_url: str,
        pr_number: int,
        code_provider: str,
        code_length: int,
    ):
        """Log successful PR creation."""
        try:
            self._sb.table(self.TABLE).update({
                "status": "success",
                "pr_url": pr_url,
                "pr_number": pr_number,
                "code_provider": code_provider,
                "code_length": code_length,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("session_id", session_id).execute()
            log.info(f"event=improvement_success session={session_id} pr={pr_url}")
        except Exception as e:
            log.error(f"event=log_improvement_success_failed err={e}")

    def log_improvement_deployed(self, session_id: str):
        """Log that the PR was merged and the improvement is live."""
        try:
            self._sb.table(self.TABLE).update({
                "status": "deployed",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("session_id", session_id).execute()
            log.info(f"event=improvement_deployed session={session_id}")
        except Exception as e:
            log.error(f"event=log_improvement_deployed_failed err={e}")

    def log_improvement_failed(self, session_id: str, error_message: str):
        """Log failure with reason."""
        try:
            self._sb.table(self.TABLE).update({
                "status": "failed",
                "error_message": error_message,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("session_id", session_id).execute()
            log.info(f"event=improvement_failed session={session_id} err={error_message[:80]}")
        except Exception as e:
            log.error(f"event=log_improvement_failed_write_failed err={e}")

    # ── Read Operations ───────────────────────────────────────────────────────

    def get_recent_improvements(self, limit: int = 10) -> list:
        """Get the last N improvement records, newest first."""
        try:
            resp = (
                self._sb.table(self.TABLE)
                .select("*")
                .order("started_at", desc=True)
                .limit(limit)
                .execute()
            )
            return resp.data or []
        except Exception as e:
            log.error(f"event=get_recent_improvements_failed err={e}")
            return []

    def get_failure_patterns(self) -> dict:
        """
        Analyze all failed sessions to find the most common error patterns.
        Returns {error_keyword: count} for the top recurring failures.
        """
        try:
            resp = (
                self._sb.table(self.TABLE)
                .select("error_message, target_file, skill_name")
                .eq("status", "failed")
                .execute()
            )
            rows = resp.data or []
            patterns: dict = {}
            for row in rows:
                msg = row.get("error_message", "") or ""
                # Bucket by first meaningful word of the error
                keyword = msg.split(":")[0].strip()[:40] if msg else "unknown"
                patterns[keyword] = patterns.get(keyword, 0) + 1
            # Sort by frequency descending
            return dict(sorted(patterns.items(), key=lambda x: x[1], reverse=True))
        except Exception as e:
            log.error(f"event=get_failure_patterns_failed err={e}")
            return {}

    def get_success_rate(self) -> float:
        """Returns 0.0–1.0 success rate across all improvement sessions."""
        try:
            # ⚡ Bolt Optimization: Using .limit(1) avoids downloading O(N) row data over the network
            # when we only care about the count='exact' header response.
            total_resp = self._sb.table(self.TABLE).select("id", count="exact").limit(1).execute()
            total = total_resp.count or 0
            if total == 0:
                return 0.0

            # ⚡ Bolt Optimization: .limit(1) applied here as well for O(1) performance
            success_resp = (
                self._sb.table(self.TABLE)
                .select("id", count="exact")
                .limit(1)
                .in_("status", ["success", "deployed"])
                .execute()
            )
            successes = success_resp.count or 0
            return round(successes / total, 3)
        except Exception as e:
            log.error(f"event=get_success_rate_failed err={e}")
            return 0.0

    def suggest_next_improvement(self) -> str:
        """
        Based on recent failures and patterns, suggest what to improve next.
        Returns a human-readable suggestion string.
        """
        patterns = self.get_failure_patterns()
        recent = self.get_recent_improvements(5)
        success_rate = self.get_success_rate()

        if not patterns and not recent:
            return "No improvement history found. Start with a full system audit."

        top_failure = next(iter(patterns), None) if patterns else None
        failed_files = [
            r.get("target_file", "")
            for r in recent
            if r.get("status") == "failed" and r.get("target_file")
        ]

        parts = []
        if success_rate < 0.5:
            parts.append(
                f"Success rate is low ({success_rate:.0%}). "
                "Focus on simpler, smaller patches before attempting large rewrites."
            )
        if top_failure:
            parts.append(f"Most common failure pattern: '{top_failure}' — investigate root cause.")
        if failed_files:
            unique_files = list(dict.fromkeys(failed_files))[:3]
            parts.append(f"Files that keep failing: {', '.join(unique_files)}.")
        if not parts:
            parts.append("All recent improvements look healthy. Continue with routine maintenance.")

        return " ".join(parts)
