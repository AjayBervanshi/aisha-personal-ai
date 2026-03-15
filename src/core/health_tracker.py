"""
health_tracker.py
=================
Physical wellbeing tracking for Ajay.

Logs: water intake, sleep (hours + quality), workout sessions.
Stores everything in the aisha_health table (see schema.sql).

Usage via Telegram:
  /water 3           → log 3 glasses of water
  /sleep 7.5 good    → log 7.5 hours, quality = good
  /workout run 30    → log a 30-minute run
  /health            → today's summary

Usage in code:
    tracker = HealthTracker(supabase_client)
    tracker.log_water(3)
    tracker.log_sleep(7.5, "good")
    tracker.log_workout("run", "30 mins easy pace")
    summary = tracker.get_daily_summary()
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from src.core.logger import get_logger

log = get_logger("HealthTracker")

# Healthy daily targets for nudge generation
_WATER_GOAL = 8   # glasses
_SLEEP_MIN = 7.0  # hours


class HealthTracker:
    """Tracks Ajay's physical wellbeing metrics."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    # ── Logging ───────────────────────────────────────────────────────────

    def log_water(self, glasses: int) -> bool:
        """Add to today's water count (upsert on date)."""
        today = datetime.now().date().isoformat()
        try:
            existing = (
                self.db.table("aisha_health")
                .select("id, water_glasses")
                .eq("date", today)
                .limit(1)
                .execute()
            ).data
            if existing:
                current = existing[0].get("water_glasses") or 0
                self.db.table("aisha_health").update({
                    "water_glasses": current + glasses,
                    "updated_at": datetime.now().isoformat(),
                }).eq("id", existing[0]["id"]).execute()
            else:
                self.db.table("aisha_health").insert({
                    "date": today,
                    "water_glasses": glasses,
                }).execute()
            log.info("event=water_logged", glasses=glasses, today=today)
            return True
        except Exception as e:
            log.error("event=water_log_failed", error=str(e))
            return False

    def log_sleep(self, hours: float, quality: str = "okay") -> bool:
        """Log last night's sleep duration and quality."""
        valid_quality = {"poor", "okay", "good", "great"}
        quality = quality.lower() if quality.lower() in valid_quality else "okay"
        today = datetime.now().date().isoformat()
        try:
            existing = (
                self.db.table("aisha_health").select("id")
                .eq("date", today).limit(1).execute()
            ).data
            if existing:
                self.db.table("aisha_health").update({
                    "sleep_hours": hours,
                    "sleep_quality": quality,
                    "updated_at": datetime.now().isoformat(),
                }).eq("id", existing[0]["id"]).execute()
            else:
                self.db.table("aisha_health").insert({
                    "date": today,
                    "sleep_hours": hours,
                    "sleep_quality": quality,
                }).execute()
            log.info("event=sleep_logged", hours=hours, quality=quality)
            return True
        except Exception as e:
            log.error("event=sleep_log_failed", error=str(e))
            return False

    def log_workout(self, workout_type: str, details: str = "") -> bool:
        """Log a workout session. details can be '30 mins easy run'."""
        today = datetime.now().date().isoformat()
        # Try to parse duration from details like "30 mins" or "45"
        duration_mins = None
        import re
        match = re.search(r"(\d+)\s*(min|minute|m\b)", details.lower())
        if match:
            duration_mins = int(match.group(1))

        try:
            existing = (
                self.db.table("aisha_health").select("id")
                .eq("date", today).limit(1).execute()
            ).data
            update_data: Dict[str, Any] = {
                "workout_type": workout_type,
                "updated_at": datetime.now().isoformat(),
            }
            if duration_mins:
                update_data["workout_duration_mins"] = duration_mins

            if existing:
                self.db.table("aisha_health").update(update_data).eq("id", existing[0]["id"]).execute()
            else:
                update_data["date"] = today
                self.db.table("aisha_health").insert(update_data).execute()
            log.info("event=workout_logged", type=workout_type, duration=duration_mins)
            return True
        except Exception as e:
            log.error("event=workout_log_failed", error=str(e))
            return False

    # ── Retrieval ─────────────────────────────────────────────────────────

    def get_daily_summary(self, day: Optional[str] = None) -> Dict[str, Any]:
        """Return today's health data as a dict."""
        target_date = day or datetime.now().date().isoformat()
        try:
            rows = (
                self.db.table("aisha_health").select("*")
                .eq("date", target_date).limit(1).execute()
            ).data
            if rows:
                return rows[0]
            return {"date": target_date, "water_glasses": 0, "note": "No data logged today"}
        except Exception as e:
            log.error("event=health_summary_failed", error=str(e))
            return {"error": str(e)}

    def generate_health_nudge(self) -> Optional[str]:
        """
        Return a nudge string if Ajay is behind on water/sleep targets.
        Returns None if everything looks fine.
        Called by NotificationEngine during morning briefing.
        """
        try:
            summary = self.get_daily_summary()
            nudges = []
            water = summary.get("water_glasses") or 0
            if water < _WATER_GOAL // 2:
                nudges.append(f"You've only had {water} glasses of water so far — aim for {_WATER_GOAL}!")
            sleep = summary.get("sleep_hours")
            quality = summary.get("sleep_quality", "okay")
            if sleep and sleep < _SLEEP_MIN:
                nudges.append(f"You slept {sleep}h last night ({quality}). Try to get {_SLEEP_MIN}h+ tonight.")
            return " ".join(nudges) if nudges else None
        except Exception:
            return None

    def format_summary_text(self, summary: Optional[Dict] = None) -> str:
        """Format health summary as a Telegram-friendly string."""
        if summary is None:
            summary = self.get_daily_summary()
        lines = [f"*Today's Health — {summary.get('date', 'N/A')}*"]
        water = summary.get("water_glasses") or 0
        lines.append(f"  Water: {water}/{_WATER_GOAL} glasses")
        sleep = summary.get("sleep_hours")
        if sleep:
            quality = summary.get("sleep_quality", "")
            lines.append(f"  Sleep: {sleep}h ({quality})")
        else:
            lines.append("  Sleep: not logged")
        workout = summary.get("workout_type")
        if workout:
            dur = summary.get("workout_duration_mins")
            dur_str = f" ({dur} min)" if dur else ""
            lines.append(f"  Workout: {workout}{dur_str}")
        else:
            lines.append("  Workout: rest day")
        return "\n".join(lines)
