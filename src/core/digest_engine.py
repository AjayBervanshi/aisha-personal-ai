"""
digest_engine.py
================
Generates daily and weekly AI-powered digests for Ajay.

Daily digest (9 PM IST):
  - Tasks done / missed
  - Total spending with top category
  - Mood score trend
  - YouTube content progress
  - Inline keyboard: "Journal this day"

Weekly digest (Sunday 7 PM IST):
  - Week aggregations vs last week (with trend arrows)
  - Spending delta, mood trend, goal progress delta
  - Content performance summary

Usage (in autonomous_loop.py):
    digest = DigestEngine(memory, ai_router)
    digest.generate_daily_digest()
"""

import logging
from datetime import datetime, timedelta, date
from typing import Dict, Any

from src.core.logger import get_logger

log = get_logger("DigestEngine")


class DigestEngine:
    """Generates rich daily and weekly life digests for Ajay."""

    def __init__(self, memory_manager, ai_router):
        self.memory = memory_manager
        self.ai = ai_router

    # ── Public ─────────────────────────────────────────────────────────────

    def generate_daily_digest(self) -> str:
        """Build a personalized daily summary. Returns formatted text."""
        log.info("event=daily_digest_start")
        stats = self._collect_daily_stats()
        prompt = self._build_daily_prompt(stats)
        try:
            result = self.ai.generate(
                system_prompt="You are Aisha. Generate a warm, personal daily digest for Ajay.",
                user_message=prompt,
                nvidia_task_type="writing"
            )
            text = result.text.strip()
            log.info("event=daily_digest_done", chars=len(text))
            return text
        except Exception as e:
            log.error("event=daily_digest_failed — %s", str(e))
            return self._fallback_daily(stats)

    def generate_weekly_digest(self) -> str:
        """Build a weekly summary with deltas vs last week."""
        log.info("event=weekly_digest_start")
        this_week = self._collect_weekly_stats(weeks_ago=0)
        last_week = self._collect_weekly_stats(weeks_ago=1)
        prompt = self._build_weekly_prompt(this_week, last_week)
        try:
            result = self.ai.generate(
                system_prompt="You are Aisha. Generate a warm, insightful weekly digest for Ajay.",
                user_message=prompt,
                nvidia_task_type="writing"
            )
            text = result.strip()
            log.info("event=weekly_digest_done", chars=len(text))
            return text
        except Exception as e:
            log.error("event=weekly_digest_failed — %s", str(e))
            return self._fallback_weekly(this_week, last_week)

    # ── Data Collection ─────────────────────────────────────────────────────

    def _collect_daily_stats(self) -> Dict[str, Any]:
        today = datetime.now().date().isoformat()
        stats: Dict[str, Any] = {"date": today}

        try:
            db = self.memory.db

            # Tasks
            # Optimization: Fetch all task statuses for today in one query
            all_tasks = (db.table("aisha_schedule").select("id, title, status")
                         .eq("due_date", today).in_("status", ["done", "missed", "pending"]).execute()).data or []

            tasks_done = [t for t in all_tasks if t.get("status") == "done"]
            tasks_missed = [t for t in all_tasks if t.get("status") == "missed"]
            tasks_pending = [t for t in all_tasks if t.get("status") == "pending"]

            stats["tasks_done"] = len(tasks_done)
            stats["tasks_missed"] = len(tasks_missed)
            stats["tasks_pending"] = [t["title"] for t in tasks_pending]

            # Spending
            expenses = (db.table("aisha_finance").select("amount, category")
                        .eq("date", today).eq("type", "expense").execute()).data or []
            stats["total_spending"] = sum(float(e.get("amount", 0)) for e in expenses)
            cat_totals: Dict[str, float] = {}
            for e in expenses:
                cat = e.get("category") or "other"
                cat_totals[cat] = cat_totals.get(cat, 0) + float(e.get("amount", 0))
            stats["top_category"] = max(cat_totals, key=cat_totals.get) if cat_totals else None

            # Mood
            mood_rows = (db.table("aisha_mood_tracker").select("mood, mood_score")
                         .eq("date", today).execute()).data or []
            if mood_rows:
                scores = [r.get("mood_score") or 5 for r in mood_rows]
                stats["avg_mood_score"] = sum(scores) / len(scores)
                stats["moods_today"] = list({r.get("mood") for r in mood_rows})
            else:
                stats["avg_mood_score"] = None
                stats["moods_today"] = []

            # Active goals
            active_goals = (db.table("aisha_goals").select("title, progress")
                            .eq("status", "active").execute()).data or []
            stats["active_goals"] = len(active_goals)
            stats["goals_near_complete"] = [
                g["title"] for g in active_goals if g.get("progress", 0) >= 75
            ]

        except Exception as e:
            log.warning("event=daily_stats_partial", error=str(e))

        return stats

    def _collect_weekly_stats(self, weeks_ago: int = 0) -> Dict[str, Any]:
        today = date.today()
        week_start = today - timedelta(days=today.weekday() + weeks_ago * 7)
        week_end = week_start + timedelta(days=6)
        stats: Dict[str, Any] = {
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
        }

        try:
            db = self.memory.db

            # Spending
            expenses = (db.table("aisha_finance")
                        .select("amount")
                        .eq("type", "expense")
                        .gte("date", week_start.isoformat())
                        .lte("date", week_end.isoformat())
                        .execute()).data or []
            stats["total_spending"] = sum(float(e.get("amount", 0)) for e in expenses)

            # Tasks done
            done = (db.table("aisha_schedule")
                    .select("id")
                    .eq("status", "done")
                    .gte("due_date", week_start.isoformat())
                    .lte("due_date", week_end.isoformat())
                    .execute()).data or []
            stats["tasks_done"] = len(done)

            # Mood
            moods = (db.table("aisha_mood_tracker")
                     .select("mood_score")
                     .gte("date", week_start.isoformat())
                     .lte("date", week_end.isoformat())
                     .execute()).data or []
            if moods:
                scores = [r.get("mood_score") or 5 for r in moods]
                stats["avg_mood"] = sum(scores) / len(scores)
            else:
                stats["avg_mood"] = None

        except Exception as e:
            log.warning("event=weekly_stats_partial", error=str(e))

        return stats

    # ── Prompt Builders ─────────────────────────────────────────────────────

    def _build_daily_prompt(self, s: Dict[str, Any]) -> str:
        lines = [f"Daily digest for {s.get('date', 'today')}:"]
        lines.append(f"- Tasks done: {s.get('tasks_done', 0)}, missed: {s.get('tasks_missed', 0)}")
        if s.get("tasks_pending"):
            lines.append(f"- Still pending: {', '.join(s['tasks_pending'][:3])}")
        if s.get("total_spending"):
            lines.append(f"- Spending: ₹{s['total_spending']:,.0f}" +
                         (f" (mostly on {s['top_category']})" if s.get("top_category") else ""))
        if s.get("avg_mood_score") is not None:
            lines.append(f"- Average mood score today: {s['avg_mood_score']:.1f}/10")
        if s.get("goals_near_complete"):
            lines.append(f"- Goals almost done: {', '.join(s['goals_near_complete'])}")
        lines.append("\nWrite a warm, personal, encouraging evening summary for Ajay. "
                     "Max 200 words. Use bullet points sparingly. Sound like you care.")
        return "\n".join(lines)

    def _build_weekly_prompt(self, this_week: Dict, last_week: Dict) -> str:
        def arrow(this, last):
            if last is None or this is None:
                return ""
            return " (up)" if this > last else " (down)" if this < last else " (same)"

        lines = [f"Weekly digest: {this_week.get('week_start')} – {this_week.get('week_end')}"]
        spend_arrow = arrow(this_week.get("total_spending"), last_week.get("total_spending"))
        lines.append(f"- Total spending: ₹{this_week.get('total_spending', 0):,.0f}{spend_arrow}")
        mood_arrow = arrow(this_week.get("avg_mood"), last_week.get("avg_mood"))
        if this_week.get("avg_mood") is not None:
            lines.append(f"- Average mood: {this_week['avg_mood']:.1f}/10{mood_arrow}")
        tasks_arrow = arrow(this_week.get("tasks_done"), last_week.get("tasks_done"))
        lines.append(f"- Tasks completed: {this_week.get('tasks_done', 0)}{tasks_arrow}")
        lines.append("\nWrite a warm, insightful weekly wrap-up for Ajay. "
                     "Highlight what went well and what to focus on next week. Max 250 words.")
        return "\n".join(lines)

    # ── Fallbacks ───────────────────────────────────────────────────────────

    def _fallback_daily(self, s: Dict[str, Any]) -> str:
        return (
            f"Today's summary:\n"
            f"  Tasks done: {s.get('tasks_done', 0)} | Missed: {s.get('tasks_missed', 0)}\n"
            f"  Spending: ₹{s.get('total_spending', 0):,.0f}\n"
            f"  Mood: {s.get('avg_mood_score', 'N/A')}/10"
        )

    def _fallback_weekly(self, this: Dict, last: Dict) -> str:
        return (
            f"Week {this.get('week_start')} – {this.get('week_end')}:\n"
            f"  Spending: ₹{this.get('total_spending', 0):,.0f}\n"
            f"  Tasks done: {this.get('tasks_done', 0)}\n"
            f"  Avg mood: {this.get('avg_mood', 'N/A')}"
        )
