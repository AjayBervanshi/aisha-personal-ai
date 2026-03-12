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
    if AUTHORIZED_ID == 0:
        return True  # Not configured — allow all (dev mode)
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
        "🎙️ You can also send *voice messages!*\n\n"
        "🎬 *YouTube Studio:*\n"
        "/channels — Your 4 channel brands\n"
        "/produce [channel] — Start a production\n"
        "/studio — Aisha auto-picks topic & channel\n"
        "/inbox — Check business email\n"
        "/aistatus — See active AI brains\n\n"
        "🧠 *Aisha Self-Improvement:*\n"
        "/selfaudit — Aisha audits her own code\n"
        "/addtool [description] — Aisha builds a new tool\n"
        "/skills — See all skills Aisha has learned\n"
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")


@bot.message_handler(commands=["selfaudit"])
def cmd_selfaudit(message):
    """Trigger Aisha's self-improvement engine."""
    if not is_ajay(message): return unauthorized_response(message)
    bot.send_message(message.chat.id, "Starting self-audit now, Ajju! Reading my own code, finding bugs, fixing what I can. I'll report back in a few minutes. 💜🧠")
    import subprocess
    project_root = str(Path(__file__).parent.parent.parent)
    subprocess.Popen(["python", "-c",
        f"import sys; sys.path.insert(0,'{project_root}'); from src.core.self_editor import SelfEditor; e=SelfEditor(); e.run_improvement_session()"
    ], cwd=project_root)


@bot.message_handler(commands=["skills"])
def cmd_skills(message):
    """Show all skills Aisha has learned so far."""
    if not is_ajay(message): return unauthorized_response(message)
    from src.core.self_modifier import get_modifier
    modifier = get_modifier()
    skills = modifier.get_skill_list()
    if not skills:
        bot.send_message(message.chat.id, "I haven't built any new skills yet! Use `/addtool` to ask me to build one. 💜", parse_mode="Markdown")
        return
    text = f"*My Self-Built Skills ({len(skills)}):*\n\n"
    for s in skills:
        text += f"- `{s}`\n"
    text += "\nEach is a Python module I wrote myself! 💜🆙"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


@bot.message_handler(commands=["addtool"])
def cmd_addtool(message):
    """Ask Aisha to write and add a new tool to herself."""
    if not is_ajay(message): return unauthorized_response(message)
    description = message.text.replace("/addtool", "").strip()

    if not description:
        bot.send_message(
            message.chat.id,
            "Tell me what tool to build! Example:\n"
            "`/addtool A tool that checks trending hashtags on Instagram`\n"
            "`/addtool A tool that converts my script to an audio file`",
            parse_mode="Markdown"
        )
        return

    bot.send_message(message.chat.id, f"On it! Building the tool: *{description}*\nGive me a minute... 💜🛠️", parse_mode="Markdown")

    try:
        from src.core.self_editor import SelfEditor
        editor = SelfEditor()
        # Generate tool name from description
        tool_name = "_".join(description.lower().split()[:4])
        path = editor.write_new_tool(tool_name, description)
        if path.startswith("ERROR"):
            bot.send_message(message.chat.id, f"Something went wrong: {path}")
        else:
            bot.send_message(
                message.chat.id,
                f"Done, Ajju! I wrote the new tool and saved it to:\n`{path}`\n\nI'm ready to use it! 💜✅",
                parse_mode="Markdown"
            )
    except Exception as e:
        bot.send_message(message.chat.id, f"Couldn't build the tool right now: {e}")


@bot.message_handler(commands=["aistatus"])
def cmd_aistatus(message):
    """Show which AI brains and social platforms are connected."""
    if not is_ajay(message): return unauthorized_response(message)

    from src.core.ai_router import AIRouter
    from src.core.social_media_engine import SocialMediaEngine

    router = AIRouter()
    sm = SocialMediaEngine()

    ai_status = router.status()
    social_status = sm.status()

    lines = ["*Aisha — System Status*\n", "*AI Brains:*"]
    for name, info in ai_status.items():
        icon = "✅" if info["available"] and not info["cooling_down"] else "⚠️" if info["available"] else "❌"
        model = router._model_name(name)
        lines.append(f"{icon} `{name}` → `{model}`")

    lines.append("\n*Social Media:*")
    for line in social_status.split("\n")[1:]:
        lines.append(line)

    bot.send_message(message.chat.id, "\n".join(lines), parse_mode="Markdown")


@bot.message_handler(commands=["inbox"])
def cmd_inbox(message):
    if not is_ajay(message): return unauthorized_response(message)
    bot.send_message(message.chat.id, "Checking your business inbox... 📬")

    try:
        from src.core.gmail_engine import GmailEngine
        gmail = GmailEngine()
        emails = gmail.check_inbox(limit=5)

        if not emails:
            bot.send_message(message.chat.id, "No new emails! Inbox is clean. 💜")
            return

        summary = f"📬 *{len(emails)} new email(s):*\n\n"
        for i, e in enumerate(emails, 1):
            summary += f"{i}. *From:* {e.get('from', 'Unknown')[:40]}\n"
            summary += f"   *Subject:* {e.get('subject', 'No Subject')[:60]}\n\n"

        bot.send_message(message.chat.id, summary, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"Couldn't check inbox right now: {e}")



@bot.message_handler(commands=["channels"])
def cmd_channels(message):
    if not is_ajay(message): return unauthorized_response(message)
    text = (
        "🎬 *Your YouTube Empire — 4 Channels:*\n\n"
        "1️⃣ *Story With Aisha* — Romantic storytelling (8-15 min)\n"
        "2️⃣ *Riya's Dark Whisper* — Psychological dark tales (10-20 min)\n"
        "3️⃣ *Riya's Dark Romance Library* — Novel-style dark romance (15-25 min)\n"
        "4️⃣ *Aisha & Him* — Couple shorts & reels (30s-3 min)\n\n"
        "📌 To start a production:\n"
        "`/produce Story With Aisha`\n"
        "`/produce Aisha & Him`\n"
        "`/studio` — Let Aisha choose the channel herself"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


@bot.message_handler(commands=["produce"])
def cmd_produce(message):
    if not is_ajay(message): return unauthorized_response(message)
    channel = message.text.replace("/produce", "").strip()
    
    VALID_CHANNELS = [
        "Story With Aisha",
        "Riya's Dark Whisper",
        "Riya's Dark Romance Library",
        "Aisha & Him"
    ]
    
    if not channel or channel not in VALID_CHANNELS:
        bot.send_message(
            message.chat.id,
            "Please specify a channel:\n\n"
            "`/produce Story With Aisha`\n"
            "`/produce Riya's Dark Whisper`\n"
            "`/produce Riya's Dark Romance Library`\n"
            "`/produce Aisha & Him`",
            parse_mode="Markdown"
        )
        return

    bot.send_message(message.chat.id, f"Got it Ajju! Starting production for *{channel}*... Give me a few minutes! 💜🎬", parse_mode="Markdown")
    
    import subprocess
    project_root = str(Path(__file__).parent.parent.parent)
    fmt = "Short/Reel" if channel == "Aisha & Him" else "Long Form"
    subprocess.Popen(["python", "-m", "src.agents.run_youtube", "--channel", channel, "--format", fmt], cwd=project_root)


@bot.message_handler(commands=["studio"])
def cmd_studio(message):
    if not is_ajay(message): return unauthorized_response(message)
    bot.send_message(message.chat.id, "Starting my creative session! I'll pick the best channel and topic myself. Check your email in a few minutes! 💜🎬")
    
    import subprocess
    project_root = str(Path(__file__).parent.parent.parent)
    subprocess.Popen(["python", "-m", "src.core.autonomous_loop", "--once"], cwd=project_root)


@bot.message_handler(commands=["aistatus"])
def cmd_aistatus(message):
    """Show which AI brains and social platforms are connected."""
    if not is_ajay(message): return unauthorized_response(message)
    
    from src.core.ai_router import AIRouter
    from src.core.social_media_engine import SocialMediaEngine
    
    router = AIRouter()
    sm = SocialMediaEngine()
    
    ai_status = router.status()
    social_status = sm.status()
    
    lines = ["*Aisha — System Status*\n"]
    lines.append("*AI Brains:*")
    for name, info in ai_status.items():
        icon = "✅" if info["available"] and not info["cooling_down"] else "⚠️" if info["available"] else "❌"
        model = router._model_name(name)
        lines.append(f"{icon} `{name}` → `{model}`")
    
    lines.append(f"\n*Social Media:*")
    for line in social_status.split("\n")[1:]:
        lines.append(line)
    
    bot.send_message(message.chat.id, "\n".join(lines), parse_mode="Markdown")


@bot.message_handler(commands=["inbox"])
def cmd_inbox(message):
    if not is_ajay(message): return unauthorized_response(message)
    bot.send_message(message.chat.id, "Checking your business inbox... 📬")
    
    try:
        from src.core.gmail_engine import GmailEngine
        gmail = GmailEngine()
        emails = gmail.check_inbox(limit=5)
        
        if not emails:
            bot.send_message(message.chat.id, "No new emails! Inbox is clean. 💜")
            return
        
        summary = f"📬 *{len(emails)} new email(s):*\n\n"
        for i, e in enumerate(emails, 1):
            summary += f"{i}. *From:* {e.get('from', 'Unknown')[:40]}\n"
            summary += f"   *Subject:* {e.get('subject', 'No Subject')[:60]}\n\n"
        
        bot.send_message(message.chat.id, summary, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"Couldn't check inbox right now: {e}")

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
    bot.send_message(
        message.chat.id,
        "📓 *Time to journal, Ajay...*\n\n"
        "Just write freely — how was your day? What's on your mind?\n"
        "I'm listening 💜",
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
        audio_file = genai.upload_file(voice_path)
        transcript_model = genai.GenerativeModel("gemini-2.5-flash")
        result = transcript_model.generate_content([
            "Transcribe this voice message exactly as spoken. "
            "It may be in English, Hindi, Marathi, or Hinglish. "
            "Return ONLY the transcription, nothing else.",
            audio_file
        ])
        transcribed_text = result.text.strip()
        
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
                
                voice_reply = generate_voice(response, language=language, mood=mood)
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
                
                voice_reply = generate_voice(response, language=language, mood=mood)
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
                
                voice_path = generate_voice(response, language=language, mood=mood)
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
    skill_name = call.data.replace("deploy_skill_", "")
    
    # We need the PR URL or number. Since we only have skill_name, 
    # we'll look for it in the message text or would normally store it in a DB.
    # For now, we'll try to find the PR URL from the original message's inline keyboard.
    pr_url = None
    for row in call.message.reply_markup.inline_keyboard:
        for button in row:
            if "Review Code" in button.text:
                pr_url = button.url
                break
    
    bot.answer_callback_query(call.id, text=f"Deploying {skill_name} now! 🚀")
    
    from src.core.self_improvement import merge_github_pr, get_pr_number_from_url
    pr_number = get_pr_number_from_url(pr_url) if pr_url else 0
    
    if pr_number and merge_github_pr(pr_number):
        bot.edit_message_text(
            f"✅ Successfully deployed: **{skill_name}**!\n"
            "The PR has been merged. My brain is now more powerful! 💜",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="Markdown"
        )
    else:
        bot.edit_message_text(
            f"⚠️ Approved **{skill_name}**, but failed to auto-merge PR #{pr_number}.\n"
            "Please check GitHub and merge it manually, Aju! 💜",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="Markdown"
        )

@bot.callback_query_handler(func=lambda c: c.data.startswith("skip_skill_"))
def handle_skip_skill(call):
    skill_name = call.data.replace("skip_skill_", "")
    bot.answer_callback_query(call.id, text=f"Skipping {skill_name}")
    bot.edit_message_text(
        f"❌ Skipped the new skill: **{skill_name}**.\n"
        "Let me know if you want me to write it differently later! 💜",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode="Markdown"
    )
