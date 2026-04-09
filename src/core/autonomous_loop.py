"""
autonomous_loop.py
==================
The Clona/Molt Autonomous AI background loop.
This script runs continuously 24/7. It allows Aisha to "wake up"
proactively, review her memories, browse for ideas, and text Ajay first.
It also monitors her own error logs and dispatches the DevCrew to fix bugs autonomously.
"""

import time
import schedule
import logging
import os
from datetime import datetime, timedelta

from src.core.config import TIMEZONE
from src.core.aisha_brain import AishaBrain
from src.agents.boss_aisha import AishaManager
from src.core.pr_reviewer import PRReviewer
import telebot

log = logging.getLogger("Aisha.Autonomous")
logging.basicConfig(level=logging.INFO)

class AutonomousLoop:
    def __init__(self):
        self.brain = AishaBrain()
        self.manager = AishaManager()
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.ajay_id = os.getenv("AJAY_TELEGRAM_ID")
        self.telegram = telebot.TeleBot(bot_token) if bot_token else None
        log.info("🌟 Autonomous Loop Initialized.")

    def run_morning_checkin(self):
        """Proactively message Ajay in the morning based on his schedule & memory."""
        log.info(f"[{datetime.now()}] Waking up for Morning Check-in...")
        
        prompt = """
        It is morning. Look at Ajay's schedule for today and his recent memories.
        Write a proactive morning WhatsApp/Telegram message to wake him up.
        Be energetic, loving, and highly contextual. 
        Do not greet him as if he said something, YOU are starting the conversation.
        """
        
        # Get AI response via MultiBot Router
        morning_text = self.brain.ai.generate(
            system_prompt="You are Aisha.",
            user_message=prompt
        ).text
        
        print(f"\n[Aisha's Autonomous Message] ➔ {morning_text}\n")
        
        if self.telegram and self.ajay_id:
            try:
                self.telegram.send_message(self.ajay_id, morning_text)
                log.info("✅ Sent morning check-in to Ajay on Telegram!")
            except Exception as e:
                log.error(f"Failed to send Telegram message: {e}")
                
        self.brain.memory.save_conversation("assistant", f"(Proactive) {morning_text}")

    def run_memory_consolidation(self):
        """Runs at 3 AM: Analyzes all talks from the day and updates deep profile."""
        log.info(f"[{datetime.now()}] Running deep memory consolidation sleep cycle...")

        try:
            # Fetch last 24h conversations
            conversations = self.brain.memory.get_recent_conversation(limit=50)
            if not conversations:
                log.info("No new conversations to consolidate.")
                return

            # Create a summary payload
            chat_log = "\n".join([f"{c['role']}: {c['message']}" for c in conversations])

            prompt = f"""
            Analyze the following conversation logs from today.
            Extract ANY long-term facts, emotional patterns, or new skills that Aisha should remember.
            Summarize them into concise points.

            Logs:
            {chat_log}
            """

            # Use Gemini to extract long-term memory points
            summary = self.brain.ai.generate("You are an expert data extractor.", prompt).text

            # Save the summarized insight as a semantic memory
            self.brain.memory.save_memory(
                category="other",
                title=f"Daily Consolidation - {datetime.now().strftime('%Y-%m-%d')}",
                content=summary,
                importance=4
            )
            log.info("✅ Memory consolidation complete!")

        except Exception as e:
            log.error(f"Memory consolidation failed: {e}")

    def review_and_merge_prs(self):
        """Runs hourly: Evaluates and merges/rejects open Pull Requests."""
        log.info(f"[{datetime.now()}] Waking up to review Pull Requests...")
        try:
            reviewer = PRReviewer()
            reviewer.process_open_prs()
        except Exception as e:
            log.error(f"Failed to review PRs: {e}")

    def monitor_health_and_fix_bugs(self):
        """Runs periodically: Checks Aisha's own logs for exceptions and dispatches the Dev crew to fix them."""
        log.info(f"[{datetime.now()}] Checking system health logs...")

        log_file = "aisha.log"
        if not os.path.exists(log_file):
            return

        try:
            with open(log_file, "r") as f:
                lines = f.readlines()

            # Grab last 100 lines and look for ERROR or Traceback
            recent_logs = "".join(lines[-100:])
            if "ERROR" in recent_logs or "Traceback" in recent_logs:
                log.warning("🚨 Bug detected in logs! Waking up DevCrew...")

                # Boss Aisha delegates the bug-fixing task
                task_description = f"""
                An error was detected in my recent logs. Please analyze the trace, find the root cause, and write a patch to fix it.
                Here are the recent logs:
                ```
                {recent_logs}
                ```
                """

                # Tell telegram about it
                if self.telegram and self.ajay_id:
                    self.telegram.send_message(
                        self.ajay_id,
                        "⚠️ Ajay, I noticed an error in my own code while I was running. I've dispatched Dev & Rex to investigate and fix it! 👩‍💻"
                    )

                # Launch the DevCrew
                fix_report = self.manager.delegate_task(task_description, task_type="coding")

                # Send the DevCrew's final report to Ajay
                if self.telegram and self.ajay_id:
                    self.telegram.send_message(
                        self.ajay_id,
                        f"✅ My dev team finished investigating the bug! Here is their report:\n\n{fix_report[:3500]}"
                    )
        except Exception as e:
            log.error(f"Health monitor failed: {e}")

def start_loop():
    bot = AutonomousLoop()
    
    # Schedule Aisha's autonomous actions
    schedule.every().day.at("08:00").do(bot.run_morning_checkin)
    schedule.every().day.at("03:00").do(bot.run_memory_consolidation)
    
    # Check for bugs every 6 hours
    schedule.every(6).hours.do(bot.monitor_health_and_fix_bugs)

    # Automatically review and merge PRs every hour
    schedule.every(1).hours.do(bot.review_and_merge_prs)

    log.info("⏰ Aisha's autonomous biological clock is ticking. Running 24/7...")
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    start_loop()
