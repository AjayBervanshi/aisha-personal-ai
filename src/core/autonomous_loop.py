"""
autonomous_loop.py
==================
The Clona/Molt Autonomous AI background loop.
This script runs continuously 24/7. It allows Aisha to "wake up"
proactively, review her memories, browse for ideas, and text Ajay first.
"""

import time
import schedule
import logging
from datetime import datetime

from src.core.config import TIMEZONE
from src.core.aisha_brain import AishaBrain
import os
import telebot

log = logging.getLogger("Aisha.Autonomous")
logging.basicConfig(level=logging.INFO)

class AutonomousLoop:
    def __init__(self):
        self.brain = AishaBrain()
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.ajay_id = os.getenv("AJAY_TELEGRAM_ID")
        self.telegram = telebot.TeleBot(bot_token) if bot_token else None
        log.info("🌟 Autonomous Loop Initialized.")

    def run_morning_checkin(self):
        """Proactively message Ajay in the morning based on his schedule & memory."""
        log.info(f"[{datetime.now()}] Waking up for Morning Check-in...")
        
        # Aisha 'thinks' about what to say without Ajay texting first
        prompt = """
        It is morning. Look at Ajay's schedule for today and his recent memories.
        Write a proactive morning WhatsApp/Telegram message to wake him up.
        Be energetic, loving, and highly contextual. 
        Do not greet him as if he said something, YOU are starting the conversation.
        """
        
        # Get AI response via MultiBot Router
        morning_text = self.brain.ai.generate("You are Aisha.", prompt).text
        
        # Bridge this output directly to Telegram
        print(f"\n[Aisha's Autonomous Message] ➔ {morning_text}\n")
        
        if self.telegram and self.ajay_id:
            try:
                self.telegram.send_message(self.ajay_id, morning_text)
                log.info("✅ Sent morning check-in to Ajay on Telegram!")
            except Exception as e:
                log.error(f"Failed to send Telegram message: {e}")
                
        # Log to db that she sent a proactive message
        self.brain.memory.save_conversation("assistant", f"(Proactive) {morning_text}")

    def run_memory_consolidation(self):
        """Runs at 3 AM: Analyzes all talks from the day and updates deep profile."""
        log.info(f"[{datetime.now()}] Running deep memory consolidation sleep cycle...")
        pass # Will implement the exact ML compaction logic here

def start_loop():
    bot = AutonomousLoop()
    
    # Schedule Aisha's autonomous actions
    schedule.every().day.at("08:00").do(bot.run_morning_checkin)
    schedule.every().day.at("03:00").do(bot.run_memory_consolidation)
    
    log.info("⏰ Aisha's autonomous biological clock is ticking. Running 24/7...")
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    start_loop()
