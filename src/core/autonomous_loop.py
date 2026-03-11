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
        self._used_topics = []  # Deduplication — never produce the same topic twice
        log.info("[Aisha] Autonomous Loop Initialized.")

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

        Format your response as a JSON object with keys: 'episodic', 'emotional', 'skills'.
        Each value should be a list of strings.
        """
        
        try:
            res = self.brain.ai.generate("You are Aisha.", prompt, response_mime_type="application/json").text
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
        from src.agents.run_youtube import run_production
        
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

        # Launch production as a background process
        try:
            import subprocess
            subprocess.Popen([
                "python", "-m", "src.agents.run_youtube",
                "--topic", topic,
                "--channel", selected['name'],
                "--format", selected['format']
            ])
            log.info(f"[Studio] Production crew launched for: {topic}")
        except Exception as e:
            log.error(f"[Studio] Failed to launch production: {e}")

def start_loop():
    bot = AutonomousLoop()
    
    # Schedule Aisha's autonomous actions
    schedule.every().day.at("08:00").do(bot.run_morning_checkin)
    schedule.every().day.at("03:00").do(bot.run_memory_consolidation)
    
    # NEW: Studio Management (Every 4 Hours)
    schedule.every(4).hours.do(bot.run_studio_session)
    
    # Run the first session instantly on startup to show Ajay she's working
    bot.run_studio_session()
    
    log.info("⏰ Aisha's autonomous biological clock is ticking. Running 24/7...")
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    start_loop()
