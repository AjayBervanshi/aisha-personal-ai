"""
notification_engine.py
======================
All proactive outreach from Aisha to Ajay lives here.

Aisha should speak first — not just reply. This engine handles:
  - Morning briefing (contextual, based on real schedule + memory)
  - Evening wrap-up (tasks done/missed, spending, mood)
  - Task reminders (30 min before due_time)
  - Goal milestone celebrations
  - Inactivity check-in (if Ajay hasn't messaged in 18+ hours)

Called by autonomous_loop.py scheduler. Can also be triggered manually
via Telegram /digest or /morning commands.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional

from src.core.logger import get_logger

log = get_logger("NotificationEngine")


class NotificationEngine:
    """
    Drives Aisha's proactive messaging.

    Usage (in autonomous_loop.py):
        notif = NotificationEngine(brain, memory)
        notif.morning_briefing()
    """

    def __init__(self, brain, memory_manager):
        self.brain = brain
        self.memory = memory_manager
        self._bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self._ajay_id = os.getenv("AJAY_TELEGRAM_ID", "")

    # ── Public Methods ─────────────────────────────────────────────────────

    def morning_briefing(self) -> str:
        """
        Generate and send a contextual morning message.
        Loads real tasks, mood history, and finance context.
        """
        log.info("event=morning_briefing_start")
        context = self._build_daily_context()

        prompt = (
            f"Good morning! Here's Ajay's day ahead:\n{context}\n\n"
            "Write a warm, energetic, personal morning message for Ajay. "
            "Reference his actual tasks and goals. Keep it under 200 words. "
            "You are initiating this conversation — he hasn't messaged you yet."
        )
        text = self.brain.think(prompt, platform="autonomous")
        self.send_telegram(text)
        log.info("event=morning_briefing_sent", chars=len(text))
        return text

    def evening_wrapup(self) -> str:
        """
        Generate and send an evening wrap-up summary.
        """
        log.info("event=evening_wrapup_start")
        context = self._build_daily_context(evening=True)

        prompt = (
            f"It's evening. Here's a summary of Ajay's day:\n{context}\n\n"
            "Write a warm, reflective evening message. Celebrate what he did. "
            "Be gentle about what he missed. Encourage him for tomorrow. "
            "Keep it under 200 words. You are initiating this."
        )
        text = self.brain.think(prompt, platform="autonomous")
        self.send_telegram(text)
        log.info("event=evening_wrapup_sent")
        return text

    def task_reminder(self, task: dict) -> None:
        """Send a specific, contextual reminder for a task due soon."""
        title = task.get("title", "a task")
        priority = task.get("priority", "medium")
        due_time = task.get("due_time", "")
        time_str = f" at {due_time}" if due_time else ""

        msg = (
            f"Hey Ajay! Reminder: *{title}* is due{time_str}. "
            f"Priority: {priority.upper()}. Don't let it slip! 💪"
        )
        self.send_telegram(msg, parse_mode="Markdown")
        log.info("event=task_reminder_sent", task_title=title)

    def milestone_celebration(self, goal: dict) -> None:
        """Celebrate when a goal hits 25/50/75/100% progress."""
        title = goal.get("title", "your goal")
        progress = goal.get("progress", 0)
        emoji = "🎉" if progress >= 100 else "🔥" if progress >= 75 else "💜"
        msg = f"{emoji} You just hit *{progress}%* on your goal: *{title}*! Keep going, Ajay!"
        self.send_telegram(msg, parse_mode="Markdown")
        log.info("event=milestone_celebration", goal_title=title, progress=progress)

    def inactivity_check(self) -> None:
        """
        If Ajay hasn't messaged in 18+ hours, send a warm check-in.
        """
        try:
            recent = self.memory.get_recent_conversation(limit=1)
            if not recent:
                return
            last_ts_str = recent[-1].get("created_at", "")
            if not last_ts_str:
                return
            # Parse ISO timestamp
            last_ts = datetime.fromisoformat(last_ts_str.replace("Z", "+00:00"))
            now = datetime.now(last_ts.tzinfo)
            hours_silent = (now - last_ts).total_seconds() / 3600

            if hours_silent >= 18:
                prompt = (
                    f"Ajay hasn't talked to you in {int(hours_silent)} hours. "
                    "Send him a warm, caring check-in message. Ask how he's doing. "
                    "Be natural, not alarming. Keep it short."
                )
                text = self.brain.think(prompt, platform="autonomous")
                self.send_telegram(text)
                log.info("event=inactivity_check_sent", hours_silent=int(hours_silent))
        except Exception as e:
            log.error("event=inactivity_check_failed — %s", str(e))

    def check_task_reminders(self) -> None:
        """
        Poll aisha_schedule for tasks due in the next 30 minutes.
        Called every 5 minutes by the autonomous loop.
        """
        try:
            now = datetime.now()
            window_end = now + timedelta(minutes=30)
            today = now.date().isoformat()

            tasks = (
                self.memory.db.table("aisha_schedule")
                .select("*")
                .eq("due_date", today)
                .eq("status", "pending")
                .eq("reminder_sent", False)
                .execute()
            ).data or []

            task_ids_to_update = []
            for task in tasks:
                due_time_str = task.get("due_time")
                if not due_time_str:
                    continue
                try:
                    hour, minute = map(int, str(due_time_str).split(":")[:2])
                    due_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    minutes_away = (due_dt - now).total_seconds() / 60
                    if 0 <= minutes_away <= 30:
                        self.task_reminder(task)
                        task_ids_to_update.append(task["id"])
                except Exception:
                    continue

            # Batch update reminder_sent for all triggered tasks
            if task_ids_to_update:
                self.memory.db.table("aisha_schedule").update(
                    {"reminder_sent": True}
                ).in_("id", task_ids_to_update).execute()

        except Exception as e:
            log.error("event=task_reminder_poll_failed — %s", str(e))

    def send_telegram(self, message: str, parse_mode: str = "") -> bool:
        """
        Single point for all proactive Telegram sends.
        Retries once on failure.
        """
        if not self._bot_token or not self._ajay_id:
            log.warning("event=telegram_not_configured")
            return False
        try:
            import telebot
            bot = telebot.TeleBot(self._bot_token)
            kwargs = {"parse_mode": parse_mode} if parse_mode else {}
            bot.send_message(self._ajay_id, message, **kwargs)
            return True
        except Exception as e:
            log.error("event=telegram_send_failed — %s", str(e))
            try:
                import time, telebot as _tb
                time.sleep(3)
                retry_bot = _tb.TeleBot(self._bot_token)
                retry_bot.send_message(self._ajay_id, message)
                return True
            except Exception:
                return False

    # ── Internal ───────────────────────────────────────────────────────────

    def _build_daily_context(self, evening: bool = False) -> str:
        """Build a text block with today's tasks, mood, and spending for the prompt."""
        lines = []
        try:
            today = datetime.now().date().isoformat()

            if evening:
                done = (
                    self.memory.db.table("aisha_schedule")
                    .select("title")
                    .eq("due_date", today)
                    .eq("status", "done")
                    .execute()
                ).data or []
                missed = (
                    self.memory.db.table("aisha_schedule")
                    .select("title")
                    .eq("due_date", today)
                    .eq("status", "missed")
                    .execute()
                ).data or []
                lines.append(f"Tasks completed: {len(done)}")
                lines.append(f"Tasks missed: {len(missed)}")
            else:
                pending = self.memory.get_today_tasks()
                if pending:
                    lines.append("Today's tasks:")
                    for t in pending[:5]:
                        lines.append(f"  [{t.get('priority','?').upper()}] {t.get('title','')}")
                else:
                    lines.append("No pending tasks today.")

            # Today's spending
            spending = (
                self.memory.db.table("aisha_finance")
                .select("amount")
                .eq("date", today)
                .eq("type", "expense")
                .execute()
            ).data or []
            total_spend = sum(float(r.get("amount", 0)) for r in spending)
            if total_spend > 0:
                lines.append(f"Today's spending: ₹{total_spend:,.0f}")

            # Last mood
            mood_row = (
                self.memory.db.table("aisha_mood_tracker")
                .select("mood, mood_score")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            ).data
            if mood_row:
                m = mood_row[0]
                lines.append(f"Last mood: {m.get('mood','?')} (score {m.get('mood_score','?')}/10)")

        except Exception as e:
            log.warning("event=build_daily_context_partial_fail", error=str(e))

        return "\n".join(lines) if lines else "No context available."
