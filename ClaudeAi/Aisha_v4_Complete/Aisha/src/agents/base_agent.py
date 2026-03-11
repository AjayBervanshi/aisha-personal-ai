"""
base_agent.py
=============
Every agent (Riya, Lexi, Zara, Aria...) inherits from this.
Handles: Ollama calls, Supabase logging, error recovery, status updates.

This is the foundation of the entire 20-agent team.
"""

import os
import time
import logging
import requests
import json
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Any, Optional

log = logging.getLogger("Aisha.Agent")

# ── Ollama config (free local AI — your PC) ───────────────────
OLLAMA_URL   = os.getenv("OLLAMA_URL",   "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

# ── Supabase lazy import ──────────────────────────────────────
_db = None
def get_db():
    global _db
    if _db is None:
        from supabase import create_client
        _db = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_KEY")
        )
    return _db


class BaseAgent(ABC):
    """
    Base class for all Aisha agents.
    
    Every agent:
    - Has a name, role, and personality
    - Thinks via Ollama (free local AI)
    - Logs everything to Supabase
    - Reports status (idle/busy/error)
    - Handles retries automatically (max 3)
    """

    MAX_RETRIES = 3  # Anti-loop rule

    def __init__(self, name: str, role: str, personality: str = ""):
        self.name = name
        self.role = role
        self.personality = personality or f"You are {name}, {role}."
        self.log = logging.getLogger(f"Aisha.{name}")

    # ── Abstract method — each agent implements their task ────

    @abstractmethod
    def run_task(self, job_id: str, input_data: Any) -> Any:
        """
        Main task for this agent.
        Must be implemented by each specific agent.
        Returns the output of the task.
        """
        pass

    # ── Main entry point ──────────────────────────────────────

    def execute(self, job_id: str, input_data: Any) -> Any:
        """
        Execute this agent's task with full retry logic and logging.
        Called by the YouTube Commander.
        """
        self._set_status("busy", job_id)
        start = time.time()

        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                self.log.info(f"[{self.name}] Attempt {attempt}/{self.MAX_RETRIES}")
                result = self.run_task(job_id, input_data)
                elapsed = int((time.time() - start) * 1000)

                self._log_to_db(job_id, "execute", str(result)[:300], elapsed, True)
                self._set_status("idle")
                self.log.info(f"[{self.name}] ✅ Done in {elapsed}ms")
                return result

            except Exception as e:
                last_error = e
                self.log.warning(f"[{self.name}] ❌ Attempt {attempt} failed: {e}")
                self._log_to_db(job_id, "execute", None, 0, False, str(e))

                if attempt < self.MAX_RETRIES:
                    wait = 2 ** attempt  # 2s, 4s, 8s
                    self.log.info(f"[{self.name}] Waiting {wait}s before retry...")
                    time.sleep(wait)
                else:
                    # MAX RETRIES HIT — stop and report
                    self._set_status("error")
                    self._block_job(job_id, f"{self.name} failed after {self.MAX_RETRIES} retries: {last_error}")
                    raise RuntimeError(
                        f"[{self.name}] Max retries reached. Job {job_id} blocked. "
                        f"Last error: {last_error}"
                    )

    # ── Ollama — your free local AI ──────────────────────────

    def think(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """
        Send a prompt to Ollama (your local FREE AI).
        Falls back to Gemini if Ollama is not running.
        """
        system = system_prompt or self.personality

        # Try Ollama first (free local)
        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user",   "content": prompt}
                    ],
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    },
                    "stream": False
                },
                timeout=120
            )
            if response.status_code == 200:
                return response.json()["message"]["content"].strip()
        except requests.exceptions.ConnectionError:
            self.log.warning(f"[{self.name}] Ollama not running — falling back to Gemini")
        except Exception as e:
            self.log.warning(f"[{self.name}] Ollama error: {e} — falling back")

        # Fallback to Gemini free API
        return self._think_gemini(prompt, system)

    def _think_gemini(self, prompt: str, system: str) -> str:
        """Gemini API fallback (free tier: 1M tokens/day)."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))
            model = genai.GenerativeModel(
                "gemini-1.5-flash",
                system_instruction=system
            )
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            self.log.error(f"[{self.name}] Gemini also failed: {e}")
            return f"[{self.name}] temporarily unavailable — please retry."

    def think_structured(self, prompt: str, system: str = None) -> dict:
        """
        Ask Ollama for a JSON response.
        Auto-parses and returns a dict.
        """
        full_prompt = f"{prompt}\n\nIMPORTANT: Reply with ONLY valid JSON. No explanation, no markdown, no backticks."
        raw = self.think(full_prompt, system or self.personality)

        # Clean and parse
        import re
        clean = re.sub(r'```json|```', '', raw).strip()
        # Find first { } block
        match = re.search(r'\{.*\}', clean, re.DOTALL)
        if match:
            clean = match.group(0)
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            self.log.warning(f"[{self.name}] Could not parse JSON from response")
            return {"raw": raw}

    # ── Supabase helpers ──────────────────────────────────────

    def _log_to_db(
        self,
        job_id: str,
        action: str,
        result: Optional[str],
        duration_ms: int,
        success: bool,
        error: str = None
    ):
        """Log agent activity to Supabase."""
        try:
            db = get_db()
            db.table("yt_agent_logs").insert({
                "job_id":      str(job_id),
                "agent_name":  self.name,
                "action":      action,
                "result":      result,
                "duration_ms": duration_ms,
                "success":     success,
                "error":       error
            }).execute()
        except Exception as e:
            self.log.debug(f"DB log failed (non-critical): {e}")

    def _set_status(self, status: str, job_id: str = None):
        """Update this agent's status in Supabase."""
        try:
            db = get_db()
            update = {"status": status, "last_seen": datetime.now().isoformat()}
            if job_id:
                update["current_job"] = str(job_id)
            elif status == "idle":
                update["current_job"] = None
            db.table("yt_agents").update(update).eq("name", self.name).execute()
        except Exception:
            pass  # Non-critical

    def _block_job(self, job_id: str, reason: str):
        """Mark a job as blocked — needs Ajay's input."""
        try:
            db = get_db()
            db.table("yt_jobs").update({
                "status":    "failed",
                "error_msg": reason[:500]
            }).eq("id", str(job_id)).execute()
            self.log.error(f"Job {job_id} BLOCKED: {reason}")
        except Exception:
            pass

    def _update_job_status(self, job_id: str, status: str):
        """Update the main job's status."""
        try:
            db = get_db()
            db.table("yt_jobs").update({
                "status":     status,
                "updated_at": datetime.now().isoformat()
            }).eq("id", str(job_id)).execute()
        except Exception:
            pass

    def _save_output(self, job_id: str, table: str, data: dict):
        """Save output to a specific Supabase table."""
        try:
            db = get_db()
            data["job_id"] = str(job_id)
            res = db.table(table).insert(data).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            self.log.error(f"[{self.name}] Save to {table} failed: {e}")
            return None

    def __repr__(self):
        return f"<Agent: {self.name} | {self.role}>"
