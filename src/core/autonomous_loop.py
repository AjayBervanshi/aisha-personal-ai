"""
autonomous_loop.py
==================
The Clona/Molt Autonomous AI background loop.
This script runs continuously 24/7. It allows Aisha to "wake up"
proactively, review her memories, browse for ideas, and text Ajay first.
"""

import time
import json
import schedule
import logging
from datetime import datetime
from pathlib import Path

# Project root for relative imports and background process launching
PROJECT_ROOT = Path(__file__).parent.parent.parent

from src.core.config import TIMEZONE
from src.core.aisha_brain import AishaBrain
from src.core.logger import get_logger
import os
import telebot

log = get_logger("Autonomous")

class AutonomousLoop:
    def __init__(self):
        self.brain = AishaBrain()
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.ajay_id = os.getenv("AJAY_TELEGRAM_ID")
        self.telegram = telebot.TeleBot(bot_token) if bot_token else None
        self._used_topics = []  # Deduplication — never produce the same topic twice

        # New engines
        from src.core.notification_engine import NotificationEngine
        from src.core.digest_engine import DigestEngine
        from src.memory.memory_compressor import MemoryCompressor
        self.notif = NotificationEngine(self.brain, self.brain.memory)
        self.digest = DigestEngine(self.brain.memory, self.brain.ai)
        self.compressor = MemoryCompressor(self.brain.memory)

        log.info("event=autonomous_loop_init")

    def run_evening_wrapup(self):
        """Send evening summary at 9 PM IST."""
        log.info("event=evening_wrapup_start")
        try:
            self.notif.evening_wrapup()
        except Exception as e:
            log.error("event=evening_wrapup_failed", error=str(e))

    def run_daily_digest(self):
        """Generate and send daily digest at 9 PM IST."""
        log.info("event=daily_digest_trigger")
        try:
            digest_text = self.digest.generate_daily_digest()
            if self.telegram and self.ajay_id:
                self.telegram.send_message(self.ajay_id, digest_text)
        except Exception as e:
            log.error("event=daily_digest_send_failed", error=str(e))

    def run_weekly_digest(self):
        """Generate and send weekly digest every Sunday."""
        log.info("event=weekly_digest_trigger")
        try:
            digest_text = self.digest.generate_weekly_digest()
            if self.telegram and self.ajay_id:
                self.telegram.send_message(self.ajay_id, digest_text)
        except Exception as e:
            log.error("event=weekly_digest_send_failed", error=str(e))

    def run_task_reminder_poll(self):
        """Poll for tasks due in 30 minutes and send reminders."""
        try:
            self.notif.check_task_reminders()
        except Exception as e:
            log.error("event=task_reminder_poll_failed", error=str(e))

    def run_inactivity_check(self):
        """Check if Ajay has been silent for 18+ hours."""
        try:
            self.notif.inactivity_check()
        except Exception as e:
            log.error("event=inactivity_check_failed", error=str(e))

    def run_memory_cleanup(self):
        """Weekly memory deduplication and decay (Sunday 3 AM)."""
        log.info("event=memory_cleanup_trigger")
        try:
            stats = self.compressor.run_weekly_cleanup()
            log.info("event=memory_cleanup_done", **stats)
        except Exception as e:
            log.error("event=memory_cleanup_failed", error=str(e))

    def run_morning_checkin(self):
        """Proactively message Ajay in the morning based on his schedule & memory."""
        log.info(f"[{datetime.now()}] Waking up for Morning Check-in...")

        # Use brain.think() so full context pipeline runs (memory, mood, tasks, profile)
        prompt = (
            "It is morning. You are waking up Ajay proactively — he has not messaged you yet. "
            "Look at his schedule for today and his recent memories. "
            "Write a warm, energetic, loving morning message. "
            "Be highly contextual — reference his actual tasks, goals, or mood if relevant. "
            "You are starting the conversation, not replying to him."
        )
        morning_text = self.brain.think(prompt, platform="autonomous")

        log.info(f"[Aisha] Morning message: {morning_text[:100]}...")

        if self.telegram and self.ajay_id:
            try:
                self.telegram.send_message(self.ajay_id, morning_text)
                log.info("Sent morning check-in to Ajay on Telegram.")
            except Exception as e:
                log.error(f"Failed to send Telegram message: {e}")

    def run_memory_consolidation(self):
        """Runs at 3 AM: Analyzes all talks from the day and updates deep profile."""
        log.info(f"[{datetime.now()}] Running deep memory consolidation sleep cycle...")
        
        # 1. Pull recent conversations (past 24h)
        chats = self.brain.memory.get_recent_conversation(limit=50)
        if not chats:
            log.info("No conversations to consolidate today.")
            return

        chat_text = "\n".join([f"{c['role']}: {c['message']}" for c in chats])
        
        # 2. Ask Aisha to summarize and extract insights
        prompt = f"""
        You are Aisha. Here are your conversations with Ajay from the last 24 hours:
        {chat_text}

        Your task:
        1. Summarize the key events/facts (Episodic Memory).
        2. Identify any emotional patterns or stresses (Emotional Memory).
        3. Identify any new skills or tasks you learned to do (Skill Memory).

        Return ONLY a valid JSON object (no backticks, no extra text) with keys: 'episodic', 'emotional', 'skills'.
        Each value should be a list of strings.
        """

        try:
            res = self.brain.ai.generate("You are Aisha. Return only valid JSON.", prompt).text
            # Strip any markdown code fences if present
            res = res.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            data = json.loads(res)
            
            # 3. Save to deep memory tables
            for fact in data.get("episodic", []):
                self.brain.memory.save_episodic_memory("Ajay", fact, datetime.now().strftime("%Y-%m-%d"))
            
            for emote in data.get("emotional", []):
                self.brain.memory.save_emotional_memory("detected", "contextual", emote)
                
            for skill in data.get("skills", []):
                self.brain.memory.save_skill_memory(skill, f"Auto-learned during conversation: {skill}")
                
            log.info("✅ Consolidation complete. Memories stored.")
            
        except Exception as e:
            log.error(f"Consolidation failed: {e}")

    def run_studio_session(self):
        """Aisha autonomously decides which channel needs content and starts the crew."""
        log.info(f"[{datetime.now()}] Aisha entering Studio for proactive session...")
        
        import random
        
        channels = [
            {"name": "Story With Aisha",          "format": "Long Form",   "vibe": "Romantic and Heart-touching"},
            {"name": "Riya's Dark Whisper",        "format": "Long Form",   "vibe": "Seductive and Mysterious"},
            {"name": "Riya's Dark Romance Library","format": "Long Form",   "vibe": "Intense Mafia/Obsessive Romance"},
            {"name": "Aisha & Him",                "format": "Short/Reel",  "vibe": "Relatable Couple Moments/Dialogue"}
        ]
        
        selected = random.choice(channels)
        
        # Generate a topic — retry if it was already used
        for attempt in range(5):
            prompt = (f"You are Aisha, the Creative Director. For channel '{selected['name']}', "
                     f"suggest ONE viral {selected['vibe']} story topic title. "
                     f"Already used: {self._used_topics[-10:] if self._used_topics else 'none'}. "
                     "Return ONLY the topic title, nothing else.")
            topic = self.brain.ai.generate("You are Aisha.", prompt).text.strip()
            if topic not in self._used_topics:
                self._used_topics.append(topic)
                break
        
        log.info(f"[Studio] Channel: '{selected['name']}' | Topic: '{topic}'")
        
        # Notify Ajay
        if self.telegram and self.ajay_id:
            try:
                self.telegram.send_message(
                    self.ajay_id,
                    f"Ajju, I'm starting a new production for '{selected['name']}' right now!\n"
                    f"Topic: '{topic}'\nI'll ping you when the script is ready! Let me cook. 💜"
                )
            except Exception as e:
                log.warning(f"[Telegram] Failed to notify: {e}")

        # Primary path: enqueue job for Antigravity queue worker
        try:
            from src.agents.antigravity_agent import AntigravityAgent
            job = AntigravityAgent().enqueue_job(
                topic=topic,
                channel=selected["name"],
                fmt=selected["format"],
                platform_targets=["instagram"],
                auto_post=True,
            )
            log.info(f"[Studio] Enqueued content job: {job.get('id')}")
        except Exception as e:
            log.error(f"[Studio] Queue enqueue failed, falling back to local process: {e}")
            # Fallback path: launch production script directly
            try:
                import subprocess
                subprocess.Popen([
                    "python", "-m", "src.agents.run_youtube",
                    "--topic", topic,
                    "--channel", selected['name'],
                    "--format", selected['format']
                ], cwd=str(PROJECT_ROOT))
                log.info(f"[Studio] Production crew launched for: {topic}")
            except Exception as ex:
                log.error(f"[Studio] Failed to launch production fallback: {ex}")

def run_self_improvement(loop: AutonomousLoop):
    """Aisha audits and improves her own code every night."""
    log.info("[SelfEditor] Starting nightly self-improvement session...")
    try:
        from src.core.self_editor import SelfEditor
        editor = SelfEditor()
        editor.run_improvement_session()
    except Exception as e:
        log.error(f"[SelfEditor] Session failed: {e}")


def start_loop(once: bool = False):
    """
    Start Aisha's autonomous loop.
    --once: Run one studio session and exit (for manual trigger from Telegram)
    """
    bot = AutonomousLoop()

    if once:
        log.info("[Aisha] Running single studio session (--once mode)...")
        bot.run_studio_session()
        return

    # ── Daily Schedule ──────────────────────────────────────────────────
    schedule.every().day.at("08:00").do(bot.run_morning_checkin)
    schedule.every().day.at("21:00").do(bot.run_evening_wrapup)
    schedule.every().day.at("21:30").do(bot.run_daily_digest)
    schedule.every().day.at("03:00").do(bot.run_memory_consolidation)

    # ── Weekly Schedule ────────────────────────────────────────────────
    schedule.every().sunday.at("19:00").do(bot.run_weekly_digest)
    schedule.every().sunday.at("03:00").do(bot.run_memory_cleanup)

    # ── High-frequency Polls ──────────────────────────────────────────
    # Task reminders — check every 5 min
    schedule.every(5).minutes.do(bot.run_task_reminder_poll)
    # Inactivity check — every 3 hours
    schedule.every(3).hours.do(bot.run_inactivity_check)

    # ── Studio Management (Every 4 Hours) ─────────────────────────────
    schedule.every(4).hours.do(bot.run_studio_session)

    # ── Nightly Self-Improvement (2 AM) ───────────────────────────────
    schedule.every().day.at("02:00").do(run_self_improvement, bot)

    # Run the first studio session instantly on startup
    bot.run_studio_session()

    log.info("[Aisha] Autonomous biological clock is ticking. Running 24/7...")

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run one session and exit")
    args = parser.parse_args()
    start_loop(once=args.once)
