"""
context_manager.py
==================
Manages Aisha's conversation context window.

Responsibilities:
  - Build the correct history slice to pass to the AI (token budget aware)
  - Compress old conversation turns into a rolling summary when history grows long
  - Restore conversation continuity across Railway restarts
  - Support per-session history (web vs Telegram don't bleed into each other)

This replaces the bare `self.history = []` list in AishaBrain and the manual
list.append() pattern scattered through think().
"""

import logging
from typing import List, Dict, Any, Optional

log = logging.getLogger("Aisha.ContextManager")

# How many raw turns to keep before compressing the older ones
COMPRESSION_TRIGGER = 15

# After compression, how many raw turns to keep (recent context stays sharp)
KEEP_RECENT_TURNS = 6

# Rough token estimate per character (good enough without tiktoken)
_CHARS_PER_TOKEN = 4

# Maximum characters of history to pass to the LLM
MAX_HISTORY_CHARS = 24_000


class ContextManager:
    """
    Manages Aisha's per-session conversation context.

    Usage (in AishaBrain.__init__):
        self.ctx = ContextManager(self.memory, self.ai, session_id="telegram")

    Usage (in AishaBrain.think):
        self.ctx.add("user", user_message)
        history_slice = self.ctx.build_window()
        result = self.ai.generate(system_prompt, user_message, history_slice)
        self.ctx.add("assistant", response_text)
    """

    def __init__(self, memory_manager, ai_router, session_id: str = "default"):
        self.memory = memory_manager
        self.ai = ai_router
        self.session_id = session_id

        # In-memory history for this session
        self._history: List[Dict[str, str]] = []
        # Optional summary of older turns (survives compression)
        self._summary: Optional[str] = None

        # Warm-start from DB
        self._history = self._restore_from_db()

    # ── Public API ─────────────────────────────────────────────────────────

    def add(self, role: str, content: str) -> None:
        """Append a new turn and auto-compress if needed."""
        self._history.append({"role": role, "content": content})
        if len(self._history) >= COMPRESSION_TRIGGER:
            self._compress()

    def build_window(self) -> List[Dict[str, str]]:
        """
        Return the message list to pass as `history` to ai_router.generate().
        Prepends summary turn if one exists, then recent raw turns, within budget.
        """
        window: List[Dict[str, str]] = []

        if self._summary:
            window.append({"role": "assistant", "content": f"[Earlier context summary]\n{self._summary}"})

        # Add recent turns within character budget
        budget = MAX_HISTORY_CHARS
        for turn in reversed(self._history):
            turn_chars = len(turn.get("content", ""))
            if budget - turn_chars < 0:
                break
            window.insert(1 if self._summary else 0, turn)
            budget -= turn_chars

        return window

    def reset(self) -> None:
        """Clear history for a new session."""
        self._history = []
        self._summary = None

    def get_raw_history(self) -> List[Dict[str, str]]:
        """Return the full untruncated history list (for saving to DB)."""
        return list(self._history)

    # ── Internal ───────────────────────────────────────────────────────────

    def _compress(self) -> None:
        """
        Summarize the older turns into self._summary.
        Keeps only the most recent KEEP_RECENT_TURNS turns as raw messages.
        Uses the cheapest available provider (Groq) to minimize cost.
        """
        older = self._history[:-KEEP_RECENT_TURNS]
        self._history = self._history[-KEEP_RECENT_TURNS:]

        if not older:
            return

        chat_text = "\n".join(
            f"{t['role'].upper()}: {t['content'][:300]}" for t in older
        )
        prompt = (
            "Summarize the following conversation history between Ajay and Aisha "
            "into 3–5 bullet points. Keep key facts, decisions, and emotional context. "
            "Be concise.\n\n" + chat_text
        )
        try:
            result = self.ai.generate(
                "You are a conversation summarizer. Return only the bullet points.",
                prompt,
                preferred_provider="groq",
            )
            new_summary_piece = result.text.strip()
            if self._summary:
                self._summary = self._summary + "\n" + new_summary_piece
            else:
                self._summary = new_summary_piece
            log.info(f"[ContextManager] Compressed {len(older)} turns into summary.")
        except Exception as e:
            log.warning(f"[ContextManager] Compression failed, keeping older turns: {e}")
            # Don't lose older turns if compression fails
            self._history = older + self._history

    def _restore_from_db(self) -> List[Dict[str, str]]:
        """Load recent conversation from Supabase to survive restarts."""
        try:
            recent = self.memory.get_recent_conversation(limit=20)
            return [{"role": c["role"], "content": c["message"]} for c in recent]
        except Exception as e:
            log.warning(f"[ContextManager] Could not restore history from DB: {e}")
            return []
