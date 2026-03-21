"""
self_repair.py
==============
Aisha's File Integrity Monitor and Auto-Restore System.

Aisha can:
1. Scan protected Python files for syntax errors
2. Detect tampering via SHA256 checksum comparison
3. Auto-restore broken files from GitHub main branch
4. Notify Ajay via Telegram before and after any restore
5. Store checksums in aisha_audit_log for tamper detection

Lifecycle:
  scan_integrity() -> detect_tampering() -> notify_ajay -> restore_from_github() -> notify_ajay
"""

import os
import ast
import hashlib
import json
import logging
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger("Aisha.SelfRepair")

PROJECT_ROOT = Path(__file__).parent.parent.parent

# ── Constants ──────────────────────────────────────────────────────────────────

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")  # loaded from Supabase api_keys at runtime via _get_github_creds()
GITHUB_REPO = os.getenv("GITHUB_REPO", "AjayBervanshi/aisha-personal-ai")
AJAY_TELEGRAM_ID = 1002381172

PROTECTED_FILES = [
    "src/telegram/bot.py",
    "src/core/autonomous_loop.py",
    "src/core/ai_router.py",
    "src/core/voice_engine.py",
    "src/agents/youtube_crew.py",
    "src/agents/antigravity_agent.py",
    "src/core/social_media_engine.py",
    "src/core/self_editor.py",
    "src/core/self_improvement.py",
]


# ── SelfRepairEngine ───────────────────────────────────────────────────────────

class SelfRepairEngine:
    """
    Monitors critical Aisha source files for syntax corruption or tampering.
    Auto-restores broken files from GitHub and notifies Ajay at every step.
    """

    def __init__(self):
        self._bot_token: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
        self._supabase_url: Optional[str] = os.getenv("SUPABASE_URL")
        self._supabase_key: Optional[str] = (
            os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        )

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _sb_headers(self) -> dict:
        return {
            "apikey": self._supabase_key,
            "Authorization": f"Bearer {self._supabase_key}",
            "Content-Type": "application/json",
        }

    def _notify_ajay(self, message: str) -> bool:
        """Send a Telegram message to Ajay. Returns True on success."""
        if not self._bot_token:
            log.warning("event=self_repair_notify_skip reason=no_bot_token")
            return False
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{self._bot_token}/sendMessage",
                json={
                    "chat_id": AJAY_TELEGRAM_ID,
                    "text": message,
                    "parse_mode": "Markdown",
                },
                timeout=15,
            )
            if resp.status_code == 200:
                log.info("event=self_repair_notify_sent")
                return True
            log.warning(f"event=self_repair_notify_failed status={resp.status_code}")
            return False
        except Exception as e:
            log.warning(f"event=self_repair_notify_error err={e}")
            return False

    @staticmethod
    def _check_syntax(filepath: str) -> tuple:
        """
        Check Python syntax of a file.
        Returns (is_valid: bool, error_message: str).
        """
        full = PROJECT_ROOT / filepath
        if not full.exists():
            return False, f"File not found: {filepath}"
        try:
            source = full.read_text(encoding="utf-8")
            ast.parse(source)
            return True, ""
        except SyntaxError as e:
            return False, f"SyntaxError at line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _sha256(filepath: str) -> Optional[str]:
        """Compute SHA256 of a file. Returns None if file missing or unreadable."""
        full = PROJECT_ROOT / filepath
        try:
            data = full.read_bytes()
            return hashlib.sha256(data).hexdigest()
        except Exception:
            return None

    # ── Public API ─────────────────────────────────────────────────────────────

    def scan_integrity(self) -> dict:
        """
        Check all protected files for syntax errors.
        Returns {filepath: {"valid": bool, "error": str}}.
        """
        results = {}
        for rel_path in PROTECTED_FILES:
            valid, error = self._check_syntax(rel_path)
            results[rel_path] = {"valid": valid, "error": error}
            if valid:
                log.info(f"event=integrity_ok file={rel_path}")
            else:
                log.warning(f"event=integrity_broken file={rel_path} error={error}")
        return results

    def fetch_file_from_github(self, filepath: str) -> str:
        """
        Fetch raw file content from GitHub main branch.
        Returns the file content as a string on success.
        Raises Exception on failure.
        """
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filepath}"
        resp = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3.raw",
            },
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.text
        raise Exception(
            f"GitHub fetch failed for '{filepath}': HTTP {resp.status_code} — {resp.text[:200]}"
        )

    def restore_from_github(self, filepath: str) -> bool:
        """
        Fetch a file from GitHub main branch and overwrite the local copy.
        Returns True on success, False on failure.
        """
        try:
            content = self.fetch_file_from_github(filepath)
            full = PROJECT_ROOT / filepath
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
            log.info(f"event=restore_success file={filepath}")
            return True
        except Exception as e:
            log.error(f"event=restore_failed file={filepath} err={e}")
            return False

    def run_repair_cycle(self, notify: bool = True) -> str:
        """
        Full integrity cycle:
          1. Scan all protected files for syntax errors.
          2. For each broken file: notify Ajay → restore from GitHub → notify result.
          3. Returns a human-readable summary string.

        If notify=True, Telegram messages are sent before and after each restore.
        """
        log.info("event=repair_cycle_start")
        scan_results = self.scan_integrity()

        broken = {
            path: info
            for path, info in scan_results.items()
            if not info["valid"]
        }

        if not broken:
            summary = "Self-repair scan complete. All protected files are healthy."
            log.info("event=repair_cycle_clean")
            return summary

        restored = []
        failed = []

        for filepath, info in broken.items():
            filename = Path(filepath).name
            error_msg = info["error"]

            # Notify Ajay before restore
            if notify:
                self._notify_ajay(
                    f"*WARNING:* `{filename}` has syntax errors.\n"
                    f"Error: `{error_msg}`\n\n"
                    f"Restoring from GitHub now..."
                )

            # Attempt restore
            success = self.restore_from_github(filepath)

            if success:
                restored.append(filepath)
                if notify:
                    self._notify_ajay(
                        f"*Restored* `{filename}` from GitHub. All good!"
                    )
            else:
                failed.append(filepath)
                if notify:
                    self._notify_ajay(
                        f"*CRITICAL:* Cannot restore `{filename}`. Please check manually!"
                    )

        # Build summary
        parts = []
        if restored:
            parts.append(f"Restored {len(restored)} file(s): {', '.join(Path(p).name for p in restored)}")
        if failed:
            parts.append(f"FAILED to restore {len(failed)} file(s): {', '.join(Path(p).name for p in failed)}")

        summary = f"Self-repair cycle complete. " + " | ".join(parts)
        log.info(f"event=repair_cycle_done restored={len(restored)} failed={len(failed)}")
        return summary

    def store_checksums(self) -> None:
        """
        Compute SHA256 for every protected file and save to aisha_audit_log
        with module='self_repair'.
        """
        if not self._supabase_url or not self._supabase_key:
            log.warning("event=store_checksums_skip reason=no_supabase_config")
            return

        checksums = {}
        for rel_path in PROTECTED_FILES:
            digest = self._sha256(rel_path)
            checksums[rel_path] = digest or "missing"

        payload = {
            "audit_date": datetime.now(timezone.utc).isoformat(),
            "module": "self_repair",
            "checksums": checksums,
            "summary": f"Checksum snapshot of {len(PROTECTED_FILES)} protected files",
        }

        try:
            resp = requests.post(
                f"{self._supabase_url}/rest/v1/aisha_audit_log",
                headers=self._sb_headers(),
                json=payload,
                timeout=15,
            )
            if resp.status_code in (200, 201):
                log.info("event=checksums_stored count=%d", len(checksums))
            else:
                log.warning(
                    f"event=checksums_store_failed status={resp.status_code} body={resp.text[:200]}"
                )
        except Exception as e:
            log.error(f"event=checksums_store_error err={e}")

    def detect_tampering(self) -> list:
        """
        Compare current file checksums to the most recently stored snapshot.
        Returns a list of file paths whose checksums have changed since the last snapshot.
        An empty list means no tampering detected.
        """
        if not self._supabase_url or not self._supabase_key:
            log.warning("event=detect_tampering_skip reason=no_supabase_config")
            return []

        # Fetch the latest stored snapshot
        try:
            resp = requests.get(
                f"{self._supabase_url}/rest/v1/aisha_audit_log",
                headers={**self._sb_headers(), "Accept": "application/json"},
                params={
                    "module": "eq.self_repair",
                    "order": "audit_date.desc",
                    "limit": "1",
                    "select": "checksums",
                },
                timeout=15,
            )
            if resp.status_code != 200 or not resp.json():
                log.info("event=detect_tampering_no_baseline")
                return []
            stored: dict = resp.json()[0].get("checksums", {})
        except Exception as e:
            log.error(f"event=detect_tampering_fetch_error err={e}")
            return []

        # Compare current checksums to stored
        tampered = []
        for rel_path in PROTECTED_FILES:
            current = self._sha256(rel_path)
            previous = stored.get(rel_path)
            if previous is None:
                continue  # No previous record — skip
            if current != previous:
                tampered.append(rel_path)
                log.warning(
                    f"event=tamper_detected file={rel_path} "
                    f"stored={previous[:12]}... current={current[:12] if current else 'missing'}..."
                )

        if not tampered:
            log.info("event=tamper_check_clean")

        return tampered
