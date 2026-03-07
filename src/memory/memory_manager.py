"""
memory_manager.py
=================
Handles ALL read/write operations to Supabase for Aisha's long-term memory.
Think of this as Aisha's brain's storage layer.
"""

import os
import re
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


class MemoryManager:
    """Manages Aisha's persistent memory in Supabase."""

    def __init__(self, supabase: Optional[Client] = None):
        if supabase:
            self.db = supabase
        else:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_KEY")
            if not url or not key:
                raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
            self.db = create_client(url, key)

    # ── Profile ────────────────────────────────────────────────

    def get_profile(self) -> Dict[str, Any]:
        """Load Ajay's full profile."""
        try:
            res = self.db.table("ajay_profile").select("*").limit(1).execute()
            return res.data[0] if res.data else {}
        except Exception as e:
            print(f"[Memory] get_profile error: {e}")
            return {}

    def update_profile(self, updates: Dict[str, Any]) -> bool:
        """Update specific fields in Ajay's profile."""
        try:
            updates["updated_at"] = datetime.now().isoformat()
            self.db.table("ajay_profile").update(updates).execute()
            return True
        except Exception as e:
            print(f"[Memory] update_profile error: {e}")
            return False

    def update_mood(self, mood: str, score: int = None, notes: str = None):
        """Update current mood in profile and log it in mood tracker."""
        self.update_profile({"current_mood": mood})
        try:
            hour = datetime.now().hour
            time_of_day = (
                "morning"   if 5  <= hour < 12 else
                "afternoon" if 12 <= hour < 17 else
                "evening"   if 17 <= hour < 22 else "night"
            )
            entry = {
                "mood": mood,
                "time_of_day": time_of_day,
            }
            if score:   entry["mood_score"] = score
            if notes:   entry["notes"] = notes
            self.db.table("aisha_mood_tracker").insert(entry).execute()
        except Exception as e:
            print(f"[Memory] mood log error: {e}")

    # ── Memories ──────────────────────────────────────────────

    def save_memory(
        self,
        category: str,
        title: str,
        content: str,
        importance: int = 3,
        tags: List[str] = None
    ) -> bool:
        """Save a new memory about Ajay."""
        try:
            self.db.table("aisha_memory").insert({
                "category":   category,
                "title":      title,
                "content":    content,
                "importance": max(1, min(5, importance)),
                "tags":       tags or [],
                "source":     "conversation",
                "is_active":  True
            }).execute()
            return True
        except Exception as e:
            print(f"[Memory] save_memory error: {e}")
            return False

    def get_top_memories(self, limit: int = 12, category: str = None) -> List[Dict]:
        """Load Ajay's most important active memories."""
        try:
            q = (
                self.db.table("aisha_memory")
                .select("category, title, content, importance, tags")
                .eq("is_active", True)
                .order("importance", desc=True)
                .limit(limit)
            )
            if category:
                q = q.eq("category", category)
            return q.execute().data or []
        except Exception as e:
            print(f"[Memory] get_top_memories error: {e}")
            return []

    def forget_memory(self, memory_id: str) -> bool:
        """Soft-delete a memory (mark inactive)."""
        try:
            self.db.table("aisha_memory").update(
                {"is_active": False}
            ).eq("id", memory_id).execute()
            return True
        except Exception as e:
            print(f"[Memory] forget_memory error: {e}")
            return False

    def format_memories_for_prompt(self, limit: int = 10) -> str:
        """Return memories as a formatted string for the system prompt."""
        memories = self.get_top_memories(limit=limit)
        if not memories:
            return "No specific memories yet — learn about Ajay as you talk."
        lines = []
        for m in memories:
            importance_stars = "★" * m["importance"]
            lines.append(f"[{m['category'].upper()} {importance_stars}] {m['title']}: {m['content']}")
        return "\n".join(lines)

    # ── Conversations ────────────────────────────────────────

    def save_message(
        self,
        role: str,
        message: str,
        platform: str = "web",
        language: str = "English",
        mood: str = "casual"
    ) -> bool:
        """Log one conversation turn."""
        try:
            self.db.table("aisha_conversations").insert({
                "platform":       platform,
                "role":           role,
                "message":        message[:2000],  # Trim very long messages
                "language":       language,
                "mood_detected":  mood
            }).execute()
            return True
        except Exception as e:
            print(f"[Memory] save_message error: {e}")
            return False

    def get_recent_messages(self, limit: int = 10) -> List[Dict]:
        """Load recent conversation history (chronological order)."""
        try:
            res = (
                self.db.table("aisha_conversations")
                .select("role, message, created_at, language")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return list(reversed(res.data or []))
        except Exception as e:
            print(f"[Memory] get_recent_messages error: {e}")
            return []

    # ── Finance ───────────────────────────────────────────────

    def log_expense(
        self,
        amount: float,
        description: str,
        category: str = "general"
    ) -> bool:
        """Log an expense."""
        try:
            self.db.table("aisha_finance").insert({
                "type":        "expense",
                "amount":      amount,
                "description": description,
                "category":    category,
                "currency":    "INR",
                "date":        date.today().isoformat()
            }).execute()
            return True
        except Exception as e:
            print(f"[Memory] log_expense error: {e}")
            return False

    def get_monthly_summary(self) -> Dict[str, float]:
        """Get this month's financial summary."""
        try:
            start = date.today().replace(day=1).isoformat()
            res = (
                self.db.table("aisha_finance")
                .select("type, amount")
                .gte("date", start)
                .execute()
            )
            summary = {"income": 0.0, "expense": 0.0, "saving": 0.0}
            for row in (res.data or []):
                t = row.get("type", "expense")
                if t in summary:
                    summary[t] += float(row.get("amount", 0))
            summary["balance"] = summary["income"] - summary["expense"]
            return summary
        except Exception as e:
            print(f"[Memory] get_monthly_summary error: {e}")
            return {}

    # ── Schedule ──────────────────────────────────────────────

    def get_today_tasks(self) -> List[Dict]:
        """Get all pending tasks for today."""
        try:
            today = date.today().isoformat()
            res = (
                self.db.table("aisha_schedule")
                .select("id, title, priority, status, due_time")
                .eq("due_date", today)
                .eq("status", "pending")
                .order("due_time")
                .execute()
            )
            return res.data or []
        except Exception as e:
            print(f"[Memory] get_today_tasks error: {e}")
            return []

    def add_task(
        self,
        title: str,
        due_date: str = None,
        due_time: str = None,
        priority: str = "medium",
        task_type: str = "task"
    ) -> bool:
        """Add a task or reminder."""
        try:
            entry: Dict[str, Any] = {
                "title":    title,
                "type":     task_type,
                "priority": priority,
                "status":   "pending"
            }
            if due_date: entry["due_date"] = due_date
            if due_time: entry["due_time"] = due_time
            self.db.table("aisha_schedule").insert(entry).execute()
            return True
        except Exception as e:
            print(f"[Memory] add_task error: {e}")
            return False

    def complete_task(self, task_id: str) -> bool:
        """Mark a task as done."""
        try:
            self.db.table("aisha_schedule").update(
                {"status": "done", "updated_at": datetime.now().isoformat()}
            ).eq("id", task_id).execute()
            return True
        except Exception as e:
            print(f"[Memory] complete_task error: {e}")
            return False

    def format_tasks_for_prompt(self) -> str:
        """Return today's tasks as a string for the system prompt."""
        tasks = self.get_today_tasks()
        if not tasks:
            return "No tasks for today."
        priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
        tasks.sort(key=lambda t: priority_order.get(t.get("priority", "medium"), 2))
        lines = []
        for t in tasks:
            icon = {"urgent": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
                t.get("priority", "medium"), "⚪"
            )
            time_str = f" at {t['due_time'][:5]}" if t.get("due_time") else ""
            lines.append(f"{icon} {t['title']}{time_str}")
        return "\n".join(lines)

    # ── Journal ───────────────────────────────────────────────

    def save_journal(
        self,
        entry: str,
        mood: str = None,
        mood_score: int = None,
        aisha_note: str = None,
        tags: List[str] = None
    ) -> bool:
        """Save a journal entry."""
        try:
            data: Dict[str, Any] = {
                "entry": entry,
                "date":  date.today().isoformat()
            }
            if mood:        data["mood"] = mood
            if mood_score:  data["mood_score"] = mood_score
            if aisha_note:  data["aisha_note"] = aisha_note
            if tags:        data["tags"] = tags
            self.db.table("aisha_journal").insert(data).execute()
            return True
        except Exception as e:
            print(f"[Memory] save_journal error: {e}")
            return False

    # ── Goals ─────────────────────────────────────────────────

    def get_active_goals(self) -> List[Dict]:
        """Get all active goals."""
        try:
            res = (
                self.db.table("aisha_goals")
                .select("title, category, progress, timeframe, target_date")
                .eq("status", "active")
                .order("progress")
                .execute()
            )
            return res.data or []
        except Exception as e:
            print(f"[Memory] get_active_goals error: {e}")
            return []

    def update_goal_progress(self, goal_title: str, progress: int) -> bool:
        """Update progress on a goal by title (approximate match)."""
        try:
            self.db.table("aisha_goals").update(
                {"progress": max(0, min(100, progress)),
                 "updated_at": datetime.now().isoformat()}
            ).ilike("title", f"%{goal_title}%").execute()
            return True
        except Exception as e:
            print(f"[Memory] update_goal_progress error: {e}")
            return False

    # ── Auto-extract from conversation ───────────────────────

    def auto_extract_and_save(self, user_message: str):
        """
        Automatically detect and save important info mentioned by Ajay.
        Keyword-based — lightweight and fast.
        """
        msg = user_message.lower()

        # Expense detection
        expense_patterns = [
            r"spent\s+₹?\s*(\d+[\d,]*)",
            r"paid\s+₹?\s*(\d+[\d,]*)",
            r"₹\s*(\d+[\d,]*)\s+(?:on|for|at)",
            r"(\d+[\d,]*)\s+rupees?\s+(?:on|for)"
        ]
        for pattern in expense_patterns:
            match = re.search(pattern, msg)
            if match:
                amount_str = match.group(1).replace(",", "")
                try:
                    amount = float(amount_str)
                    self.log_expense(amount, user_message[:200], "auto-detected")
                    break
                except ValueError:
                    pass

        # Goal detection
        goal_triggers = [
            "my goal is", "i want to", "i'm planning to", "i plan to",
            "dream is to", "want to become", "aiming to", "trying to achieve"
        ]
        if any(t in msg for t in goal_triggers):
            self.save_memory(
                category="goal",
                title=f"Goal mentioned {datetime.now().strftime('%d %b')}",
                content=user_message[:300],
                importance=4,
                tags=["goal", "auto-extracted"]
            )

        # Fear / anxiety detection
        anxiety_triggers = ["i'm scared", "i'm afraid", "i fear", "worried about"]
        if any(t in msg for t in anxiety_triggers):
            self.save_memory(
                category="fear",
                title=f"Concern mentioned {datetime.now().strftime('%d %b')}",
                content=user_message[:200],
                importance=3,
                tags=["emotion", "auto-extracted"]
            )

    # ── Full Context for Prompt ───────────────────────────────

    def build_full_context(self) -> Dict[str, str]:
        """Build the complete context dict for Aisha's system prompt."""
        return {
            "profile":    self.get_profile(),
            "memories":   self.format_memories_for_prompt(),
            "today_tasks": self.format_tasks_for_prompt(),
            "mood_summary": self._get_recent_mood_summary()
        }

    def _get_recent_mood_summary(self) -> str:
        """Get a brief summary of recent moods."""
        try:
            res = (
                self.db.table("aisha_mood_tracker")
                .select("mood, mood_score, date")
                .order("created_at", desc=True)
                .limit(5)
                .execute()
            )
            if not res.data:
                return "No mood data yet."
            moods = [f"{r['mood']} ({r.get('mood_score', '?')}/10)" for r in res.data]
            return "Recent moods: " + ", ".join(moods)
        except Exception:
            return ""
