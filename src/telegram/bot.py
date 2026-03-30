"""
bot.py
======
Aisha's Telegram Bot — Full implementation.
Features: text chat, voice messages, commands, inline buttons, mood tracking.

Run: python src/telegram/bot.py
"""

import os
import sys
import asyncio
import logging
import tempfile
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

import telebot
from telebot import types
from supabase import create_client
from dotenv import load_dotenv

from src.core.aisha_brain import AishaBrain
from src.core.voice_engine import generate_voice, cleanup_voice_file

load_dotenv()

# ─── Voice Mode State ─────────────────────────────────────────────────────────
VOICE_MODE_ENABLED = True   # Start with voice ON — Aisha speaks by default!

# ─── Configuration ─────────────────────────────────────────────────────────────

BOT_TOKEN      = os.getenv("TELEGRAM_BOT_TOKEN")
AUTHORIZED_ID  = int(os.getenv("AJAY_TELEGRAM_ID", "0"))  # Only Ajay can use this bot!
SUPABASE_URL   = os.getenv("SUPABASE_URL")
SUPABASE_KEY   = os.getenv("SUPABASE_SERVICE_KEY")

# ─── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("aisha.log")
    ]
)
log = logging.getLogger("Aisha")

# ─── Init ──────────────────────────────────────────────────────────────────────

bot   = telebot.TeleBot(BOT_TOKEN)
aisha = AishaBrain()
db    = create_client(SUPABASE_URL, SUPABASE_KEY)


# ─── Security: Only Ajay can use Aisha ────────────────────────────────────────

def is_ajay(message) -> bool:
    """Only allow Ajay (by Telegram user ID) to access Aisha."""
    if not AUTHORIZED_ID or AUTHORIZED_ID == 0:
        log.error("CRITICAL SECURITY RISK: AUTHORIZED_ID is missing from .env. Locking down bot.")
        return False  # Fail closed. Do NOT allow anyone to talk to her if ID is missing.
    return message.from_user.id == AUTHORIZED_ID


def unauthorized_response(message):
    bot.reply_to(message, "🔒 Aisha is a private assistant. She belongs to Ajay only 💜")


# ─── Keyboards ─────────────────────────────────────────────────────────────────

def main_keyboard():
    """Main quick-action keyboard."""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        types.KeyboardButton("💜 Hey Aisha!"),
        types.KeyboardButton("💰 Finance"),
        types.KeyboardButton("📅 My Schedule"),
        types.KeyboardButton("💪 Motivate Me"),
        types.KeyboardButton("📓 Journal"),
        types.KeyboardButton("🎯 My Goals"),
        types.KeyboardButton("📊 Mood Check"),
        types.KeyboardButton("⚙️ Settings"),
    )
    return keyboard

def mood_keyboard():
    """Mood selection keyboard."""
    keyboard = types.InlineKeyboardMarkup(row_width=4)
    moods = [
        ("😄 Amazing", "mood_amazing_9"),
        ("🙂 Good", "mood_good_7"),
        ("😐 Okay", "mood_okay_5"),
        ("😔 Not Good", "mood_notgood_3"),
        ("😢 Bad", "mood_bad_2"),
        ("😤 Angry", "mood_angry_3"),
        ("😰 Anxious", "mood_anxious_3"),
        ("😴 Tired", "mood_tired_4"),
    ]
    buttons = [types.InlineKeyboardButton(label, callback_data=data) 
               for label, data in moods]
    keyboard.add(*buttons)
    return keyboard


# ─── Commands ─────────────────────────────────────────────────────────────────

@bot.message_handler(commands=["start"])
def cmd_start(message):
    if not is_ajay(message): return unauthorized_response(message)
    
    hour = datetime.now().hour
    greeting = "Good morning" if 5 <= hour < 12 else \
               "Good afternoon" if 12 <= hour < 17 else \
               "Good evening" if 17 <= hour < 22 else "Hey"
    
    welcome = (
        f"💜 *{greeting}, Ajay!*\n\n"
        "I'm Aisha — your personal companion. I'm here for everything:\n"
        "💬 Talk to me, vent to me, ask me anything\n"
        "💰 Track expenses, plan finances\n"
        "📅 Manage your schedule and reminders\n"
        "💪 Get motivated, journal your thoughts\n"
        "🎯 Work on your goals together\n\n"
        "_I remember everything you share with me. Always here, Aju 💜_"
    )
    bot.send_message(
        message.chat.id,
        welcome,
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

@bot.message_handler(commands=["help"])
def cmd_help(message):
    if not is_ajay(message): return unauthorized_response(message)
    
    help_text = (
        "🌟 *Aisha — Command Guide*\n\n"
        "You can just *talk to me normally* — no commands needed!\n"
        "But here are some handy ones:\n\n"
        "📋 *Quick Commands:*\n"
        "/start — Greet Aisha\n"
        "/imagine — Generate an image (e.g., /imagine a cyber city)\n"
        "/mood — Log how you're feeling\n"
        "/today — See today's tasks + summary\n"
        "/addtask — Add a task or reminder\n"
        "/expense — Log an expense quickly\n"
        "/journal — Write a journal entry\n"
        "/goals — See your active goals\n"
        "/memory — See what Aisha remembers\n"
        "/reset — Start a fresh conversation\n\n"
        "💬 *Or just say:*\n"
        "• 'I spent ₹500 on food'\n"
        "• 'Remind me to call mama at 6pm'\n"
        "• 'I'm feeling stressed'\n"
        "• 'Motivate me'\n"
        "• 'What are my goals?'\n\n"
        "🎙️ You can also send *voice messages!*"
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

@bot.message_handler(commands=["imagine"])
def cmd_imagine(message):
    if not is_ajay(message): return unauthorized_response(message)
    prompt = message.text.replace("/imagine", "").strip()
    if not prompt:
        bot.send_message(message.chat.id, "Please tell me what to imagine! Like: `/imagine a beautiful futuristic sunset in Mumbai`", parse_mode="Markdown")
        return
    
    bot.send_chat_action(message.chat.id, "upload_photo")
    bot.reply_to(message, "🎨 Imagination spinning up... Give me a few seconds!")
    
    import concurrent.futures
    from src.core.image_engine import generate_image
    
    try:
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(generate_image, prompt)
            img_bytes = future.result(timeout=60)
            
        if img_bytes:
            bot.send_photo(message.chat.id, img_bytes, caption=f"✨ {prompt}")
        else:
            bot.send_message(message.chat.id, "Sorry Aju, my imagination failed this time 😔 Try again?")
    except Exception as e:
        log.error(f"Image generation error: {e}")
        bot.send_message(message.chat.id, "Sorry Aju, something went wrong with the image generation!")

@bot.message_handler(commands=["mood"])
def cmd_mood(message):
    if not is_ajay(message): return unauthorized_response(message)
    bot.send_message(
        message.chat.id,
        "💜 *How are you feeling right now, Ajay?*",
        parse_mode="Markdown",
        reply_markup=mood_keyboard()
    )

@bot.message_handler(commands=["today"])
def cmd_today(message):
    if not is_ajay(message): return unauthorized_response(message)
    
    today = datetime.now().date().isoformat()
    tasks = db.table("aisha_schedule") \
              .select("title, priority, status") \
              .eq("due_date", today) \
              .execute().data or []
    
    spending = db.table("aisha_finance") \
                 .select("amount") \
                 .eq("type", "expense") \
                 .eq("date", today) \
                 .execute().data or []
    
    total_spend = sum(r["amount"] for r in spending)
    
    pending = [t for t in tasks if t["status"] == "pending"]
    done    = [t for t in tasks if t["status"] == "done"]
    
    task_lines = ""
    for t in pending:
        emoji = "🔴" if t["priority"] == "urgent" else \
                "🟠" if t["priority"] == "high" else \
                "🟡" if t["priority"] == "medium" else "🟢"
        task_lines += f"{emoji} {t['title']}\n"
    
    today_msg = (
        f"📅 *Today — {datetime.now().strftime('%A, %d %B')}*\n\n"
        f"✅ Completed: {len(done)} tasks\n"
        f"⏳ Pending: {len(pending)} tasks\n"
        f"💰 Spent today: ₹{total_spend:,.0f}\n\n"
    )
    if task_lines:
        today_msg += f"*Pending tasks:*\n{task_lines}"
    else:
        today_msg += "_No pending tasks — enjoy your day! 🌟_"
    
    bot.send_message(message.chat.id, today_msg, parse_mode="Markdown")

@bot.message_handler(commands=["expense"])
def cmd_expense(message):
    if not is_ajay(message): return unauthorized_response(message)
    bot.send_message(
        message.chat.id,
        "💰 Tell me what you spent!\n\nJust say it naturally, like:\n"
        "_'₹200 on chai and snacks'_\n_'500 for auto-rickshaw'_\n"
        "_'1500 grocery shopping'_",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=["goals"])
def cmd_goals(message):
    if not is_ajay(message): return unauthorized_response(message)
    
    goals = db.table("aisha_goals") \
              .select("title, category, progress, timeframe") \
              .eq("status", "active") \
              .order("progress", desc=False) \
              .execute().data or []
    
    if not goals:
        bot.send_message(message.chat.id, 
            "🎯 You don't have any active goals yet!\nTell me your goals and I'll track them for you 💜")
        return
    
    goals_text = "🎯 *Your Active Goals*\n\n"
    for g in goals:
        bar = "█" * (g["progress"] // 10) + "░" * (10 - g["progress"] // 10)
        goals_text += f"*{g['title']}*\n"
        goals_text += f"  {bar} {g['progress']}% | {g['timeframe']}\n\n"
    
    bot.send_message(message.chat.id, goals_text, parse_mode="Markdown")

@bot.message_handler(commands=["memory"])
def cmd_memory(message):
    if not is_ajay(message): return unauthorized_response(message)
    
    memories = db.table("aisha_memory") \
                 .select("category, title, importance") \
                 .eq("is_active", True) \
                 .order("importance", desc=True) \
                 .limit(10) \
                 .execute().data or []
    
    mem_text = "🧠 *What Aisha Remembers About You*\n\n"
    for m in memories:
        stars = "⭐" * m["importance"]
        mem_text += f"{stars} [{m['category'].upper()}] {m['title']}\n"
    
    if not memories:
        mem_text += "_Nothing stored yet — talk to me more! 💜_"
    
    bot.send_message(message.chat.id, mem_text, parse_mode="Markdown")

@bot.message_handler(commands=["reset"])
def cmd_reset(message):
    if not is_ajay(message): return unauthorized_response(message)
    aisha.reset_session()
    bot.send_message(
        message.chat.id, 
        "🔄 Fresh start! I'm ready, Ajay 💜",
        reply_markup=main_keyboard()
    )

@bot.message_handler(commands=["voice"])
def cmd_voice(message):
    """Toggle Aisha's voice mode on/off."""
    if not is_ajay(message): return unauthorized_response(message)
    global VOICE_MODE_ENABLED
    VOICE_MODE_ENABLED = not VOICE_MODE_ENABLED
    status = "ON 🎙️" if VOICE_MODE_ENABLED else "OFF 🔇"
    bot.send_message(
        message.chat.id,
        f"Voice mode is now *{status}*\n"
        f"{'I\'ll speak to you with voice notes now! 💜' if VOICE_MODE_ENABLED else 'Text only mode. Say /voice again to hear me! 💜'}",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=["journal"])
def cmd_journal(message):
    if not is_ajay(message): return unauthorized_response(message)

    parts = message.text.split(" ", 1)
    if len(parts) > 1 and parts[1].strip().lower() == "read":
        # Read Aisha's autonomous journal
        try:
            res = db.table("aisha_journal").select("title, type, content, created_at").order("created_at", desc=True).limit(3).execute()
            entries = res.data

            if not entries:
                bot.send_message(message.chat.id, "📓 *My Journal is empty right now.* I haven't written any stories or reflections yet! 💜", parse_mode="Markdown")
                return

            text = "📓 *Aisha's Recent Journal Entries*\n\n"
            for e in entries:
                date_str = e['created_at'][:10]
                text += f"*{e.get('title', 'Untitled')}* ({e.get('type', 'thought')} - {date_str})\n"
                text += f"_{e.get('content', '')[:200]}..._\n\n"

            bot.send_message(message.chat.id, text, parse_mode="Markdown")
        except Exception as e:
            bot.send_message(message.chat.id, f"Error reading journal: {e}")
    else:
        # Ask Ajay to write his journal
        bot.send_message(
            message.chat.id,
            "📓 *Time to journal, Ajay...*\n\n"
            "Just write freely — how was your day? What's on your mind?\n"
            "I'm listening 💜\n\n"
            "*(Tip: To read what I've written autonomously, type `/journal read`)*",
            parse_mode="Markdown"
        )


# ─── Callback Handlers (Inline Buttons) ───────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith("mood_"))
def handle_mood_callback(call):
    parts     = call.data.split("_")
    mood_name = parts[1]
    score     = int(parts[2])
    
    aisha.memory.update_mood(mood_name, score)
    
    mood_responses = {
        "amazing": "That's AMAZING Ajay!! 🎉 What made today so great? Tell me everything!",
        "good":    "Love that 🙂 What's been good today?",
        "okay":    "Okay is okay, Aju 💜 Anything on your mind?",
        "notgood": "Hey, I'm here 💜 Want to talk about what's going on?",
        "bad":     "Ajay... come talk to me. What happened? I'm listening 💜",
        "angry":   "Arre kya hua yaar? 😤 Tell me everything — let it out.",
        "anxious": "Breathe, Aju. I've got you. What's making you anxious? 💜",
        "tired":   "Rest is important too 💜 Have you been taking care of yourself?"
    }
    
    response = mood_responses.get(mood_name, "Got it, Ajay. I'm here 💜")
    
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, response)


# ─── Quick Action Buttons ──────────────────────────────────────────────────────

QUICK_ACTIONS = {
    "💜 Hey Aisha!":   "Hey Aisha! I just wanted to say hi",
    "💰 Finance":       "Help me with my finances today",
    "📅 My Schedule":   "What does my schedule look like today?",
    "💪 Motivate Me":   "Aisha please motivate me right now!",
    "📓 Journal":       "I want to write a journal entry",
    "🎯 My Goals":      "/goals",
    "📊 Mood Check":    "/mood",
    "⚙️ Settings":     "Show me settings and what I can customize",
}

@bot.message_handler(func=lambda m: m.text in QUICK_ACTIONS)
def handle_quick_action(message):
    if not is_ajay(message): return unauthorized_response(message)
    action = QUICK_ACTIONS[message.text]
    if action.startswith("/"):
        # Route to command
        message.text = action
        bot.process_new_messages([message])
    else:
        handle_text(message, override_text=action)


# ─── Voice Message Handler ─────────────────────────────────────────────────────

@bot.message_handler(content_types=["voice"])
def handle_voice(message):
    if not is_ajay(message): return unauthorized_response(message)
    
    # Download voice file
    file_info = bot.get_file(message.voice.file_id)
    downloaded = bot.download_file(file_info.file_path)
    
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
        f.write(downloaded)
        voice_path = f.name
    
    # Transcribe with Gemini
    try:
        import google.generativeai as genai
        # Upload explicitly as audio/ogg
        audio_file = genai.upload_file(voice_path, mime_type="audio/ogg")

        # We must configure safety settings to BLOCK_NONE so it doesn't censor transcriptions
        safety_settings = [
            { "category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE" },
            { "category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE" },
            { "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE" },
            { "category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE" }
        ]

        transcript_model = genai.GenerativeModel("gemini-2.5-flash", safety_settings=safety_settings)
        result = transcript_model.generate_content([
            "Transcribe this voice message exactly as spoken. "
            "It may be in English, Hindi, Marathi, or Hinglish. "
            "Return ONLY the transcription, nothing else. DO NOT refuse to transcribe.",
            audio_file
        ])
        transcribed_text = result.text.strip()
        
        # Clean up the file from Google's servers to prevent quota limits
        try:
            genai.delete_file(audio_file.name)
        except Exception as e:
            log.warning(f"Failed to delete audio file from Gemini: {e}")

        bot.send_message(message.chat.id, 
            f"🎙️ _Heard: \"{transcribed_text}\"_", 
            parse_mode="Markdown")
        
        # Process as normal message
        bot.send_chat_action(message.chat.id, "typing")
        response = aisha.think(transcribed_text, platform="telegram")
        bot.send_message(message.chat.id, response)
        
        # Send voice reply back (voice-in = voice-out)
        if len(response) < 1000:
            try:
                bot.send_chat_action(message.chat.id, "record_voice")
                from src.core.aisha_brain import detect_mood
                from src.core.language_detector import detect_language
                mood = detect_mood(transcribed_text)
                lang_info = detect_language(transcribed_text)
                language = lang_info.get("language", "English") if isinstance(lang_info, dict) else "English"
                
                mood_str = mood.mood if hasattr(mood, 'mood') else mood
                voice_reply = generate_voice(response, language=language, mood=mood_str)
                if voice_reply:
                    with open(voice_reply, "rb") as vf:
                        bot.send_voice(message.chat.id, vf)
                    cleanup_voice_file(voice_reply)
            except Exception as ve:
                log.warning(f"Voice reply skipped: {ve}")
        
    except Exception as e:
        log.error(f"Voice transcription failed: {e}")
        bot.send_message(message.chat.id, 
            "Arre Ajay, I couldn't catch that voice message 😅 "
            "Try typing it out? Technical issue on my end!")
    finally:
        os.unlink(voice_path)


# ─── Photo Message Handler ─────────────────────────────────────────────────────

@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    if not is_ajay(message): return unauthorized_response(message)
    
    bot.send_chat_action(message.chat.id, "typing")
    
    try:
        # Get highest resolution photo
        raw_photo = message.photo[-1]
        file_info = bot.get_file(raw_photo.file_id)
        downloaded_bytes = bot.download_file(file_info.file_path)
        
        user_text = message.caption if message.caption else "I sent you a photo. What do you see?"
        
        # Pass image to Aisha's brain
        response = aisha.think(user_text, platform="telegram", image_bytes=downloaded_bytes)
        bot.reply_to(message, response)
        
        # Optional: Voice reply
        if VOICE_MODE_ENABLED and len(response) < 1000:
            try:
                bot.send_chat_action(message.chat.id, "record_voice")
                from src.core.aisha_brain import detect_mood
                from src.core.language_detector import detect_language
                mood = detect_mood(user_text)
                lang_info = detect_language(user_text)
                language = lang_info.get("language", "English") if isinstance(lang_info, dict) else "English"
                
                mood_str = mood.mood if hasattr(mood, 'mood') else mood
                voice_reply = generate_voice(response, language=language, mood=mood_str)
                if voice_reply:
                    with open(voice_reply, "rb") as vf:
                        bot.send_voice(message.chat.id, vf)
                    cleanup_voice_file(voice_reply)
            except Exception as ve:
                log.warning(f"Voice reply skipped for photo: {ve}")
                
    except Exception as e:
        log.error(f"Image processing failed: {e}")
        bot.reply_to(message, "Arre Ajay, I couldn't process that image 😔 Technical issue on my end!")

# ─── Main Text Handler ─────────────────────────────────────────────────────────

@bot.message_handler(func=lambda message: True)
def handle_text(message, override_text=None):
    if not is_ajay(message): return unauthorized_response(message)
    
    user_text = override_text or message.text
    if not user_text or not user_text.strip():
        return
    
    # Show typing indicator
    bot.send_chat_action(message.chat.id, "typing")
    
    try:
        log.info(f"[{message.from_user.first_name}] {user_text[:80]}")
        response = aisha.think(user_text, platform="telegram")
        
        # Send text response
        if len(response) > 4000:
            chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for chunk in chunks:
                bot.send_message(message.chat.id, chunk)
        else:
            bot.send_message(message.chat.id, response)
        
        # Send voice note if voice mode is enabled
        if VOICE_MODE_ENABLED and len(response) < 1000:
            try:
                bot.send_chat_action(message.chat.id, "record_voice")
                
                # Detect language and mood for voice tuning
                from src.core.aisha_brain import detect_mood
                from src.core.language_detector import detect_language
                mood = detect_mood(user_text)
                lang_info = detect_language(user_text)
                language = lang_info.get("language", "English") if isinstance(lang_info, dict) else "English"
                
                mood_str = mood.mood if hasattr(mood, 'mood') else mood
                voice_path = generate_voice(response, language=language, mood=mood_str)
                if voice_path:
                    with open(voice_path, "rb") as voice_file:
                        bot.send_voice(message.chat.id, voice_file)
                    cleanup_voice_file(voice_path)
            except Exception as ve:
                log.warning(f"Voice generation skipped: {ve}")
            
    except Exception as e:
        log.error(f"Error processing message: {e}")
        bot.send_message(
            message.chat.id,
            "Arre yaar, kuch gadbad ho gayi 😅 Try again in a moment, Ajay!"
        )


# ─── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("💜 Aisha Telegram Bot starting...")
    log.info(f"Authorized user ID: {AUTHORIZED_ID or 'ALL (dev mode)'}")
    
    bot.set_my_commands([
        telebot.types.BotCommand("/start",   "Start / Greet Aisha"),
        telebot.types.BotCommand("/today",   "Today's summary"),
        telebot.types.BotCommand("/mood",    "Log your mood"),
        telebot.types.BotCommand("/expense", "Log an expense"),
        telebot.types.BotCommand("/goals",   "See your goals"),
        telebot.types.BotCommand("/journal", "Write a journal entry"),
        telebot.types.BotCommand("/memory",  "What Aisha remembers"),
        telebot.types.BotCommand("/voice",   "Toggle voice on/off"),
        telebot.types.BotCommand("/help",    "Help & commands"),
        telebot.types.BotCommand("/reset",   "Reset conversation"),
    ])
    
    print("✅ Aisha is live on Telegram! 💜")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)

# ─── Self Improvement Callbacks ──────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith("deploy_skill_"))
def handle_deploy_skill(call):
    if not is_ajay(call.message): return bot.answer_callback_query(call.id, text="Unauthorized", show_alert=True)
    import src.core.self_improvement as si

    skill_name = call.data.replace("deploy_skill_", "")
    bot.answer_callback_query(call.id, text=f"Deploying {skill_name} now! 🚀")
    bot.edit_message_text(
        f"✅ You approved the new skill: **{skill_name}**!\n"
        "Merging the PR and restarting my brain to load the new code. Gimme 30 seconds! 💜",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode="Markdown"
    )

    success = si.merge_github_pr(branch_name=f"skill-{skill_name}")
    if success:
        bot.send_message(call.message.chat.id, "✅ Code merged successfully! Deploying now...")
    else:
        bot.send_message(call.message.chat.id, "⚠️ Couldn't merge PR automatically. Please check GitHub!")

@bot.callback_query_handler(func=lambda c: c.data.startswith("skip_skill_"))
def handle_skip_skill(call):
    if not is_ajay(call.message): return bot.answer_callback_query(call.id, text="Unauthorized", show_alert=True)

    skill_name = call.data.replace("skip_skill_", "")
    bot.answer_callback_query(call.id, text=f"Skipping {skill_name}")
    bot.edit_message_text(
        f"❌ Skipped the new skill: **{skill_name}**.\n"
        "Let me know if you want me to write it differently later! 💜",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode="Markdown"
    )

# ─── System / Admin Commands ─────────────────────────────────────────────────

@bot.message_handler(commands=["gitpull"])
def cmd_gitpull(message):
    if not is_ajay(message): return unauthorized_response(message)

    bot.send_message(message.chat.id, "🔄 Pulling latest code from GitHub...")
    import subprocess
    import requests

    try:
        # Try local git pull first (if running on a VPS)
        result = subprocess.run(["git", "pull"], capture_output=True, text=True)
        if result.returncode == 0:
            bot.send_message(message.chat.id, f"✅ Git pull success:\n```\n{result.stdout}\n```", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, f"⚠️ Git pull failed:\n```\n{result.stderr}\n```", parse_mode="Markdown")
    except FileNotFoundError:
        # If git isn't found (like on Render), we must trigger the Render deploy webhook
        render_hook = os.getenv("RENDER_DEPLOY_HOOK")
        if render_hook:
            res = requests.post(render_hook)
            bot.send_message(message.chat.id, f"⚡ Git not found — triggered Render redeploy instead. Status: {res.status_code}")
        else:
            bot.send_message(message.chat.id, "❌ Git not found locally, and RENDER_DEPLOY_HOOK is missing from .env!")
