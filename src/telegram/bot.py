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

import threading
import json as _json
from http.server import HTTPServer, BaseHTTPRequestHandler

import telebot
from telebot import types
from supabase import create_client
from dotenv import load_dotenv

from src.core.aisha_brain import AishaBrain
from src.core.voice_engine import generate_voice, cleanup_voice_file

load_dotenv()

# Ensure UTF-8 output on Windows (prevents UnicodeEncodeError with emoji/Hindi/Devanagari text)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ─── Rate-limited fallback message (max once per 10 min per chat) ─────────────
import time as _time
_last_fallback: dict[int, float] = {}

def _get_fallback_msg(chat_id: int) -> str | None:
    """Returns fallback message string, or None if rate-limited."""
    now = _time.time()
    if now - _last_fallback.get(chat_id, 0) < 600:  # 10 min cooldown
        return None
    _last_fallback[chat_id] = now
    return (
        "Ek second Ajay... mujhe kuch technical dikkat aa rahi hai. "
        "Ek baar aur try karo? Agar problem rahe toh /syscheck se check karo. 🔧"
    )

# ─── IST timezone helpers ─────────────────────────────────────────────────────
import pytz as _pytz
_IST = _pytz.timezone("Asia/Kolkata")

def get_ist_hour() -> int:
    """Returns current hour in IST (0-23)."""
    return datetime.now(_IST).hour

def get_greeting() -> str:
    h = get_ist_hour()
    if 5 <= h < 12:   return "Good morning"
    if 12 <= h < 17:  return "Good afternoon"
    if 17 <= h < 21:  return "Good evening"
    return "Good night"

# ─── Voice Mode State ─────────────────────────────────────────────────────────
VOICE_MODE_ENABLED = False  # Voice OFF by default — enable with /voice command

# ─── Per-chat processing lock + message correlation ───────────────────────────
# Prevents reply bleed when async/threaded tasks from previous messages
# finish late and send their replies into the current conversation turn.
_chat_locks: dict[int, threading.Lock] = {}
_chat_locks_mutex = threading.Lock()
_last_message_id: dict[int, int] = {}  # chat_id → most-recent message_id


def _get_chat_lock(chat_id: int) -> threading.Lock:
    """Return (creating if needed) the per-chat serialisation lock."""
    with _chat_locks_mutex:
        if chat_id not in _chat_locks:
            _chat_locks[chat_id] = threading.Lock()
        return _chat_locks[chat_id]


# ─── Pending shell commands (for confirmation) ────────────────────────────────
_pending_shell: dict = {}  # message_id → command string

# ─── User Approval System ─────────────────────────────────────────────────────
_approved_users: set = set()    # user_ids Ajay has approved this session
_pending_approvals: dict = {}   # user_id → {user, text, message}

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


# ─── Load approved users from Supabase on startup ─────────────────────────────

def load_approved_users_from_db():
    """Query aisha_approved_users and populate the in-memory _approved_users set."""
    try:
        rows = (
            db.table("aisha_approved_users")
            .select("telegram_user_id")
            .eq("is_active", True)
            .execute()
        ).data or []
        for row in rows:
            _approved_users.add(row["telegram_user_id"])
        log.info(f"load_approved_users count={len(rows)}")
    except Exception as e:
        log.error(f"load_approved_users error={e}")

load_approved_users_from_db()


# ─── Security: Only Ajay can use Aisha ────────────────────────────────────────

def is_ajay(message) -> bool:
    """Allow Ajay or any user Ajay has approved this session."""
    if AUTHORIZED_ID == 0:
        return True  # Not configured — allow all (dev mode)
    uid = getattr(message.from_user, "id", None) or getattr(message, "id", None)
    return uid == AUTHORIZED_ID or uid in _approved_users


def unauthorized_response(message):
    """Forward unknown user to Ajay for approve/deny decision."""
    user = message.from_user
    user_id = user.id
    name = user.first_name or "Unknown"
    username = f"@{user.username}" if user.username else "no username"
    text = getattr(message, "text", None) or "[media message]"

    # Tell the user to wait
    bot.reply_to(message, "🔒 Please wait, checking with the owner...")

    # Store their pending message
    _pending_approvals[user_id] = {"user": user, "text": text, "message": message}

    # Alert Ajay with Approve / Deny buttons
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_user_{user_id}"),
        types.InlineKeyboardButton("❌ Deny",    callback_data=f"deny_user_{user_id}")
    )
    try:
        bot.send_message(
            AUTHORIZED_ID,
            f"🔔 *New User Wants to Chat*\n\n"
            f"👤 Name: {name}\n"
            f"🆔 ID: `{user_id}`\n"
            f"🔗 Username: {username}\n\n"
            f"💬 Their message:\n_{text[:500]}_\n\n"
            f"Allow them to talk to me?",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
    except Exception as e:
        log.error(f"Could not alert Ajay about new user {user_id}: {e}")


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
    
    greeting = get_greeting()  # IST-aware greeting
    
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
        "/testpipeline [channel] — Dry-run pipeline test (no upload)\n"
        "/inbox — Check business email\n"
        "/aistatus — See active AI brains\n\n"
        "🧠 *Aisha Self-Improvement:*\n"
        "/upgrade — Full autonomous upgrade: audit → code → PR → deploy 🚀\n"
        "/selfaudit — Aisha audits her own code\n"
        "/addtool [description] — Aisha builds a new tool\n"
        "/skills — See all skills Aisha has learned\n\n"
        "⚡ *Power Commands (Claude Code Level):*\n"
        "/upload [channel] — Upload latest content to YouTube\n"
        "/queue — See content pipeline jobs\n"
        "/earnings — Revenue dashboard & monetization progress\n"
        "/calendar — Weekly content schedule (+ /calendar generate)\n"
        "/logs [n] — View last N lines of aisha.log\n"
        "/syscheck — Run full system test\n"
        "/shell <cmd> — Run shell command (with confirmation)\n"
        "/read <file> — Read any file\n"
        "/gitpull — Pull latest code from GitHub\n"
        "/restart — Restart Aisha bot\n"
        "/findapi <platform> — Search web for API key signup guide\n"
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")


@bot.message_handler(commands=["selfaudit"])
def cmd_selfaudit(message):
    """Trigger Aisha's self-improvement engine."""
    if not is_ajay(message): return unauthorized_response(message)
    bot.send_message(message.chat.id, "Starting self-audit now, Ajju! Reading my own code, finding bugs, fixing what I can. I'll report back in a few minutes. 💜🧠")
    import subprocess, sys as _sys
    project_root = str(Path(__file__).parent.parent.parent)
    subprocess.Popen([_sys.executable, "-c",
        f"import sys; sys.path.insert(0,'{project_root}'); from src.core.self_editor import SelfEditor; e=SelfEditor(); e.run_improvement_session()"
    ], cwd=project_root)


@bot.message_handler(commands=["upgrade"])
def cmd_upgrade(message):
    """
    Trigger Aisha's full autonomous self-improvement pipeline:
    Audit → Plan → Generate code → GitHub PR → Auto-merge → Render redeploy → Notify Ajay.
    Optional: /upgrade <target_file> to audit a specific file.
    """
    if not is_ajay(message): return unauthorized_response(message)

    args = message.text.replace("/upgrade", "").strip()
    target_file = args if args else None

    bot.send_message(
        message.chat.id,
        "🧠 Starting my full self-upgrade cycle, Ajay!\n\n"
        "Steps:\n"
        "1. Audit code for improvement opportunities\n"
        "2. Plan the best new skill\n"
        "3. Generate code with Gemini\n"
        "4. Create GitHub PR\n"
        "5. Auto-merge + Render redeploy\n"
        "6. I'll message you when I'm live! 💜\n\n"
        "This takes 2-5 minutes — I'll report back!"
    )

    def _run_upgrade():
        try:
            from src.core.self_editor import SelfEditor
            editor = SelfEditor()
            pr_url = editor.run_improvement_session(target_file=target_file)
            if not pr_url:
                bot.send_message(
                    message.chat.id,
                    "I tried to upgrade myself but the code generation failed this time. "
                    "Check the logs for details. 💜"
                )
        except Exception as exc:
            log.error(f"[/upgrade] Upgrade session crashed: {exc}")
            bot.send_message(message.chat.id, f"Upgrade crashed: {exc}")

    import threading
    threading.Thread(target=_run_upgrade, daemon=True).start()


@bot.message_handler(commands=["feature"])
def cmd_feature(message):
    """Request a new feature to be built autonomously by Aisha's 6-agent pipeline."""
    if not is_ajay(message): return unauthorized_response(message)
    feature_desc = message.text.replace("/feature", "").strip()
    if not feature_desc:
        bot.send_message(
            message.chat.id,
            "Usage: `/feature <description>`\n"
            "Example: `/feature Add weather widget to morning briefing`",
            parse_mode="Markdown",
        )
        return
    bot.send_message(
        message.chat.id,
        f"Launching Feature Pipeline for:\n_{feature_desc}_\n\n"
        "Agents: Research → Architecture → Code → Review → Test → Deploy\n"
        "I'll notify you when done!",
        parse_mode="Markdown",
    )

    def _run_pipeline():
        try:
            from src.core.feature_pipeline import run_feature_pipeline, notify_pipeline_result
            result = run_feature_pipeline(feature_desc)
            notify_pipeline_result(result)
        except Exception as exc:
            log.error(f"[/feature] Pipeline crashed: {exc}")
            bot.send_message(message.chat.id, f"Feature pipeline crashed: {exc}")

    import threading
    threading.Thread(target=_run_pipeline, daemon=True).start()


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
    
    import subprocess, sys as _sys
    project_root = str(Path(__file__).parent.parent.parent)
    fmt = "Short/Reel" if channel == "Aisha & Him" else "Long Form"
    subprocess.Popen([_sys.executable, "-m", "src.agents.run_youtube", "--channel", channel, "--format", fmt], cwd=project_root)


@bot.message_handler(commands=["upload"])
def cmd_upload(message):
    """Upload the latest produced content to YouTube."""
    if not is_ajay(message): return unauthorized_response(message)
    channel = message.text.replace("/upload", "").strip()
    bot.send_message(message.chat.id, "🎬 Checking for latest produced content...", parse_mode="Markdown")
    try:
        query = db.table("content_jobs") \
                  .select("*") \
                  .eq("status", "completed") \
                  .is_("youtube_status", "null") \
                  .order("created_at", desc=True) \
                  .limit(1)
        if channel:
            query = db.table("content_jobs") \
                      .select("*") \
                      .eq("status", "completed") \
                      .eq("channel", channel) \
                      .is_("youtube_status", "null") \
                      .order("created_at", desc=True) \
                      .limit(1)
        rows = query.execute().data
        if not rows:
            bot.send_message(message.chat.id,
                "No completed content found pending upload.\n"
                "Run `/produce <channel>` first to generate content.",
                parse_mode="Markdown")
            return
        job = rows[0]
        job_id = job["id"]
        ch = job.get("channel", "Unknown")
        bot.send_message(message.chat.id,
            f"📤 Uploading to YouTube...\n"
            f"Channel: *{ch}*\n"
            f"Job ID: `{job_id}`\n"
            "_This may take 1-3 minutes..._",
            parse_mode="Markdown")
        video_path = job.get("payload", {}).get("video_path") or job.get("video_path")
        title = job.get("payload", {}).get("title") or job.get("topic", "New Video")
        description = job.get("payload", {}).get("description", "")
        tags = job.get("payload", {}).get("tags") or []
        if not video_path:
            bot.send_message(message.chat.id,
                "❌ No video file found for this job.\n"
                "The video may not have been rendered yet. Job must have `render_video=True`.",
                parse_mode="Markdown")
            return
        try:
            from src.core.social_media_engine import SocialMediaEngine
            sm = SocialMediaEngine()
            r = sm.upload_youtube_video(
                video_path=video_path,
                title=title,
                description=description,
                tags=tags,
                channel_name=ch,
            )
            if r and r.get("success"):
                db.table("content_jobs").update(
                    {"youtube_status": "uploaded", "youtube_video_id": r.get("video_id")}
                ).eq("id", job_id).execute()
                bot.send_message(message.chat.id,
                    f"✅ *Uploaded to YouTube!*\n"
                    f"Channel: *{ch}*\n"
                    f"Video ID: `{r.get('video_id')}`\n"
                    f"Check YouTube Studio for the video. 🎉",
                    parse_mode="Markdown")
            else:
                err = str(r)[:400] if r else "Unknown error"
                bot.send_message(message.chat.id, f"❌ Upload failed:\n```{err}```", parse_mode="Markdown")
        except Exception as upload_err:
            bot.send_message(message.chat.id, f"❌ Upload error: {upload_err}")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Upload error: {e}")


@bot.message_handler(commands=["queue"])
def cmd_queue(message):
    """Show content pipeline queue status."""
    if not is_ajay(message): return unauthorized_response(message)
    try:
        rows = db.table("content_jobs") \
                 .select("id, channel, status, created_at, youtube_status") \
                 .order("created_at", desc=True) \
                 .limit(8) \
                 .execute().data or []
        if not rows:
            bot.send_message(message.chat.id, "📭 Content queue is empty. Use `/produce <channel>` to start!", parse_mode="Markdown")
            return
        status_emoji = {
            "pending": "⏳", "processing": "🔄", "completed": "✅",
            "failed": "❌", "uploaded": "🎬"
        }
        text = "📋 *Content Queue (last 8):*\n\n"
        for r in rows:
            s = r.get("status", "?")
            yt = r.get("youtube_status") or ""
            icon = status_emoji.get(s, "❓")
            yt_icon = " 📺" if yt == "uploaded" else (" ⬆️" if yt == "uploading" else "")
            ch = (r.get("channel") or "Unknown")[:25]
            ts = (r.get("created_at") or "")[:10]
            text += f"{icon}{yt_icon} `{r['id'][:8]}` {ch}\n   _{s}_ · {ts}\n\n"
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Queue error: {e}")


@bot.message_handler(commands=["logs"])
def cmd_logs(message):
    """Show last N lines from aisha.log."""
    if not is_ajay(message): return unauthorized_response(message)
    text = message.text.replace("/logs", "").strip()
    try:
        n = int(text) if text and text.isdigit() else 30
        n = min(n, 100)
    except ValueError:
        n = 30
    try:
        import subprocess
        project_root = str(Path(__file__).parent.parent.parent)
        result = subprocess.run(
            ["tail", f"-{n}", "aisha.log"],
            cwd=project_root, capture_output=True, text=True, timeout=10
        )
        log_text = result.stdout or "No log output."
        if len(log_text) > 3800:
            log_text = "...(truncated)\n" + log_text[-3800:]
        bot.send_message(message.chat.id,
            f"📋 *Last {n} lines of aisha.log:*\n```\n{log_text}\n```",
            parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Logs error: {e}")


@bot.message_handler(commands=["earnings"])
def cmd_earnings(message):
    """Show revenue dashboard: uploads, views, monetization progress."""
    if not is_ajay(message): return unauthorized_response(message)
    bot.send_message(message.chat.id, "📊 Pulling revenue data... ⏳")

    def _build_report():
        try:
            from datetime import datetime, timedelta
            week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()

            # Content jobs completed this week
            rows = db.table("content_jobs") \
                     .select("channel, status, youtube_status, youtube_video_id, created_at") \
                     .gte("created_at", week_ago) \
                     .execute().data or []

            uploaded = [r for r in rows if r.get("youtube_status") == "uploaded"]
            completed = [r for r in rows if r.get("status") == "completed"]

            # Channel breakdown
            channel_counts = {}
            for r in uploaded:
                ch = (r.get("channel") or "Unknown")[:20]
                channel_counts[ch] = channel_counts.get(ch, 0) + 1

            # All-time uploads
            all_uploaded = db.table("content_jobs") \
                             .select("id") \
                             .eq("youtube_status", "uploaded") \
                             .execute().data or []

            # Monetization progress (need 1000 subs + 4000 watch hours)
            total_videos = len(all_uploaded)
            # Rough estimate: each Short = ~0.5 watch-hour average
            est_watch_hours = total_videos * 0.5
            watch_pct = min(100, (est_watch_hours / 4000) * 100)

            lines = [
                "📊 *Aisha Revenue Dashboard*\n",
                f"_Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}_\n",
                "─────────────────────────",
                f"📹 Videos uploaded (7d): *{len(uploaded)}*",
                f"⚙️  Jobs completed (7d): *{len(completed)}*",
                f"🎬 Total uploads ever: *{total_videos}*",
            ]

            if channel_counts:
                lines.append("\n📺 *By channel (this week):*")
                for ch, cnt in sorted(channel_counts.items(), key=lambda x: -x[1]):
                    lines.append(f"  • {ch}: {cnt} video{'s' if cnt!=1 else ''}")

            lines += [
                "\n💰 *YouTube Monetization Progress:*",
                f"  ⏱️  Est. watch hours: ~{est_watch_hours:.0f} / 4,000 ({watch_pct:.1f}%)",
                f"  👥 Subscribers needed: 1,000 (check YouTube Studio)",
                f"  📈 At 2 uploads/day per channel → ~{max(1, int((4000-est_watch_hours)/2/4/0.5))} days to 4k hrs",
                "\n🚀 *Actions to accelerate:*",
                "  1. Run `/studio` now to queue content",
                "  2. Renew xAI key for Riya channels (higher watch time)",
                "  3. Upgrade ElevenLabs for premium voice quality",
            ]

            return "\n".join(lines)
        except Exception as e:
            log.error(f"[/earnings] Error: {e}")
            return f"❌ Could not load earnings data: {e}"

    report = _build_report()
    bot.send_message(message.chat.id, report, parse_mode="Markdown")


@bot.message_handler(commands=["calendar"])
def cmd_calendar(message):
    """Show or regenerate the weekly content calendar."""
    if not is_ajay(message): return unauthorized_response(message)
    arg = message.text.replace("/calendar", "").strip().lower()

    def _get_or_generate():
        try:
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            # Slots per channel per day
            slots = {
                "Story With Aisha":           ["11:00", "19:00"],
                "Riya's Dark Whisper":         ["12:00", "20:00"],
                "Riya's Dark Romance Library": ["13:00", "21:00"],
                "Aisha & Him":                 ["10:00", "18:00"],
            }

            if arg == "generate":
                # Queue one job per channel for today
                from src.agents.antigravity_agent import AntigravityAgent
                agent = AntigravityAgent()
                queued = 0
                for channel in slots:
                    try:
                        agent.enqueue_job(
                            topic=None,  # agent picks trending topic
                            channel=channel,
                            fmt="short",
                            platform_targets=["youtube", "instagram"],
                            auto_post=True,
                        )
                        queued += 1
                    except Exception as eq:
                        log.warning(f"[calendar] Failed to queue {channel}: {eq}")
                return f"✅ Queued *{queued}* jobs (one per channel). Check `/queue` for status."

            # Show upcoming schedule
            today = now.date()
            lines = ["📅 *Aisha Content Calendar (next 3 days):*\n"]
            for day_offset in range(3):
                day = today + timedelta(days=day_offset)
                day_label = day.strftime("%a %b %d")
                lines.append(f"\n*{day_label}*")
                for channel, times in slots.items():
                    ch_short = channel[:22]
                    for t in times:
                        lines.append(f"  {t} IST — {ch_short}")

            lines += [
                "\n─────────────────────────",
                "Run `/calendar generate` to queue today's content now.",
                "Run `/studio` to let Aisha pick a single topic herself.",
            ]
            return "\n".join(lines)
        except Exception as e:
            log.error(f"[/calendar] Error: {e}")
            return f"❌ Calendar error: {e}"

    bot.send_message(message.chat.id, _get_or_generate(), parse_mode="Markdown")


@bot.message_handler(commands=["syscheck"])
def cmd_syscheck(message):
    """Run full system health check and report results."""
    if not is_ajay(message): return unauthorized_response(message)
    loading_msg = bot.send_message(message.chat.id, "Running system checks... ⏳")
    try:
        from src.core.monitoring_engine import full_health_report
        report = full_health_report()
        bot.delete_message(message.chat.id, loading_msg.message_id)
        bot.send_message(message.chat.id, report, parse_mode="Markdown")
    except Exception as e:
        bot.edit_message_text(f"❌ System check error: {e}", message.chat.id, loading_msg.message_id)


@bot.message_handler(commands=["healthreport"])
def cmd_healthreport(message):
    """Run health check via monitoring_engine.run_health_check() and send result."""
    if not is_ajay(message): return unauthorized_response(message)
    loading_msg = bot.send_message(message.chat.id, "Running health report... ⏳")
    try:
        from src.core.monitoring_engine import run_health_check
        report = run_health_check()
        bot.delete_message(message.chat.id, loading_msg.message_id)
        bot.send_message(message.chat.id, report, parse_mode="Markdown")
    except Exception as e:
        bot.edit_message_text(f"❌ Health report error: {e}", message.chat.id, loading_msg.message_id)


@bot.message_handler(commands=["dbrepair"])
def cmd_dbrepair(message):
    """Manually trigger Aisha's DB self-repair — creates any missing Supabase tables."""
    if not is_ajay(message): return unauthorized_response(message)
    loading_msg = bot.send_message(message.chat.id, "Running DB self-repair... ⏳")
    try:
        from src.core.self_db import check_and_repair
        results = check_and_repair()
        lines = []
        for table, status in results.items():
            icon = "✅" if status == "ok" else "🆕" if status == "created" else "❌"
            lines.append(f"{icon} `{table}` — {status}")
        report = "*DB Self-Repair Report*\n\n" + "\n".join(lines)
        bot.delete_message(message.chat.id, loading_msg.message_id)
        bot.send_message(message.chat.id, report, parse_mode="Markdown")
    except Exception as e:
        bot.edit_message_text(f"❌ DB repair error: {e}", message.chat.id, loading_msg.message_id)


@bot.message_handler(commands=["drainqueue"])
def cmd_drainqueue(message):
    """Manually drain up to 5 stuck queued jobs — Ajay only."""
    if not is_ajay(message):
        return unauthorized_response(message)

    loading_msg = bot.send_message(message.chat.id, "Draining queue... checking for stuck jobs ⏳")

    import requests as _req

    base = os.getenv("SUPABASE_URL", "").rstrip("/")
    svc_key = os.getenv("SUPABASE_SERVICE_KEY", "")
    headers = {
        "apikey":        svc_key,
        "Authorization": f"Bearer {svc_key}",
        "Content-Type":  "application/json",
    }

    if not base or not svc_key:
        bot.edit_message_text("❌ SUPABASE_URL / SUPABASE_SERVICE_KEY not set.", message.chat.id, loading_msg.message_id)
        return

    # Fetch up to 5 queued jobs
    try:
        r = _req.get(
            f"{base}/rest/v1/content_jobs?status=eq.queued&select=*&limit=5&order=created_at.asc",
            headers=headers,
            timeout=10,
        )
        r.raise_for_status()
        jobs = r.json()
    except Exception as e:
        bot.edit_message_text(f"❌ Failed to fetch queued jobs: {e}", message.chat.id, loading_msg.message_id)
        return

    if not jobs:
        bot.edit_message_text("✅ No queued jobs found — queue is clear.", message.chat.id, loading_msg.message_id)
        return

    bot.edit_message_text(
        f"Found {len(jobs)} queued job(s). Processing with AntigravityAgent... ⚙️",
        message.chat.id,
        loading_msg.message_id,
    )

    results = []
    try:
        from src.agents.antigravity_agent import AntigravityAgent
        agent = AntigravityAgent()
        for job in jobs:
            job_id = job.get("id", "?")
            try:
                result = agent.process_job(job)
                status = result.get("status", "?") if isinstance(result, dict) else "done"
                results.append(f"✅ `{str(job_id)[:8]}` → {status}")
            except Exception as job_err:
                results.append(f"❌ `{str(job_id)[:8]}` → {job_err}")
    except ImportError:
        # AntigravityAgent not importable — reset jobs back to queued so scheduler retries
        log.warning("drainqueue: AntigravityAgent import failed; re-queuing %d jobs", len(jobs))
        for job in jobs:
            job_id = job.get("id")
            try:
                _req.patch(
                    f"{base}/rest/v1/content_jobs?id=eq.{job_id}",
                    json={"status": "queued", "error_text": "drainqueue: reset for retry"},
                    headers=headers,
                    timeout=8,
                )
                results.append(f"♻️ `{str(job_id)[:8]}` reset to queued")
            except Exception as patch_err:
                results.append(f"❌ `{str(job_id)[:8]}` patch failed: {patch_err}")

    summary = "\n".join(results) or "No results."
    bot.send_message(message.chat.id, f"*DrainQueue complete:*\n{summary}", parse_mode="Markdown")


@bot.message_handler(commands=["fixkeys"])
def cmd_fixkeys(message):
    """Check all API keys and report their live status — Ajay only."""
    if not is_ajay(message):
        return unauthorized_response(message)

    loading_msg = bot.send_message(message.chat.id, "🔑 Checking all API keys in parallel... ⏳")

    def _run():
        import requests as _req
        import concurrent.futures
        from pathlib import Path as _Path

        # ── Collect keys from environment (already loaded from .env) ──────────
        gemini_key      = os.getenv("GEMINI_API_KEY", "")
        groq_key        = os.getenv("GROQ_API_KEY", "")
        openai_key      = os.getenv("OPENAI_API_KEY", "")
        xai_key         = os.getenv("XAI_API_KEY", "")
        elevenlabs_key  = os.getenv("ELEVENLABS_API_KEY", "")

        # NVIDIA — count keys that start with "nvapi-"
        nvidia_keys = [
            v for k, v in os.environ.items()
            if k.startswith("NVIDIA_") and v.startswith("nvapi-")
        ]

        TIMEOUT = 5  # seconds per check

        # ── Individual key testers ─────────────────────────────────────────────

        def check_gemini():
            if not gemini_key:
                return "❌", "Gemini", "No key set"
            try:
                r = _req.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}",
                    json={"contents": [{"parts": [{"text": "hi"}]}]},
                    timeout=TIMEOUT,
                )
                if r.status_code == 200:
                    return "✅", "Gemini", "Working"
                elif r.status_code == 429:
                    return "⚠️", "Gemini", "429 Quota exceeded"
                elif r.status_code == 400:
                    return "⚠️", "Gemini", "400 Bad request (key may be OK)"
                else:
                    return "❌", "Gemini", f"{r.status_code} Error"
            except Exception as e:
                return "❌", "Gemini", f"Timeout/Error: {str(e)[:60]}"

        def check_groq():
            if not groq_key:
                return "❌", "Groq", "No key set"
            try:
                r = _req.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                    json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
                    timeout=TIMEOUT,
                )
                if r.status_code == 200:
                    return "✅", "Groq", "Working"
                elif r.status_code == 401:
                    return "❌", "Groq", "401 Invalid key"
                elif r.status_code == 429:
                    return "⚠️", "Groq", "429 Rate limited"
                else:
                    return "❌", "Groq", f"{r.status_code} Error"
            except Exception as e:
                return "❌", "Groq", f"Timeout/Error: {str(e)[:60]}"

        def check_openai():
            if not openai_key:
                return "❌", "OpenAI", "No key set"
            try:
                r = _req.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                    json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
                    timeout=TIMEOUT,
                )
                if r.status_code == 200:
                    return "✅", "OpenAI", "Working"
                elif r.status_code == 401:
                    return "❌", "OpenAI", "401 Invalid key"
                elif r.status_code == 429:
                    return "⚠️", "OpenAI", "429 Rate limited"
                else:
                    return "❌", "OpenAI", f"{r.status_code} Error"
            except Exception as e:
                return "❌", "OpenAI", f"Timeout/Error: {str(e)[:60]}"

        def check_xai():
            if not xai_key:
                return "❌", "xAI (Grok)", "No key set"
            try:
                r = _req.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {xai_key}", "Content-Type": "application/json"},
                    json={"model": "grok-3-mini", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
                    timeout=TIMEOUT,
                )
                if r.status_code == 200:
                    return "✅", "xAI (Grok)", "Working"
                elif r.status_code == 401:
                    return "❌", "xAI (Grok)", "401 Invalid key"
                elif r.status_code == 403:
                    return "❌", "xAI (Grok)", "403 Blocked / no credits"
                elif r.status_code == 429:
                    return "⚠️", "xAI (Grok)", "429 Rate limited"
                else:
                    return "❌", "xAI (Grok)", f"{r.status_code} Error"
            except Exception as e:
                return "❌", "xAI (Grok)", f"Timeout/Error: {str(e)[:60]}"

        def check_elevenlabs():
            if not elevenlabs_key:
                return "❌", "ElevenLabs", "No key set"
            try:
                r = _req.get(
                    "https://api.elevenlabs.io/v1/user",
                    headers={"xi-api-key": elevenlabs_key},
                    timeout=TIMEOUT,
                )
                if r.status_code == 200:
                    data = r.json()
                    sub = data.get("subscription", {})
                    used = sub.get("character_count", 0)
                    limit = sub.get("character_limit", 0)
                    remaining = limit - used
                    if remaining < 500:
                        return "⚠️", "ElevenLabs", f"{remaining:,} chars left (CRITICAL)"
                    elif remaining < 5000:
                        return "⚠️", "ElevenLabs", f"{remaining:,} chars left (low)"
                    else:
                        return "✅", "ElevenLabs", f"{remaining:,} chars left"
                elif r.status_code == 401:
                    return "❌", "ElevenLabs", "401 Invalid key"
                else:
                    return "❌", "ElevenLabs", f"{r.status_code} Error"
            except Exception as e:
                return "❌", "ElevenLabs", f"Timeout/Error: {str(e)[:60]}"

        def check_nvidia():
            if not nvidia_keys:
                return "❌", "NVIDIA NIM", "No nvapi- keys found in env"
            # Spot-check first key with a lightweight models list call
            key = nvidia_keys[0]
            try:
                r = _req.get(
                    "https://api.nvidia.com/v1/models",
                    headers={"Authorization": f"Bearer {key}"},
                    timeout=TIMEOUT,
                )
                if r.status_code in (200, 201):
                    return "✅", "NVIDIA NIM", f"{len(nvidia_keys)} keys in pool"
                elif r.status_code in (401, 403):
                    # Key format valid but may be expired — still count them
                    return "⚠️", "NVIDIA NIM", f"{len(nvidia_keys)} keys (spot-check {r.status_code})"
                else:
                    return "⚠️", "NVIDIA NIM", f"{len(nvidia_keys)} keys (spot-check {r.status_code})"
            except Exception:
                # Endpoint might not exist — fall back to format check
                return "✅", "NVIDIA NIM", f"{len(nvidia_keys)} keys (format OK)"

        # ── Run all checks in parallel ─────────────────────────────────────────
        checkers = [check_gemini, check_groq, check_openai, check_xai, check_elevenlabs, check_nvidia]
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            futures = {pool.submit(fn): fn.__name__ for fn in checkers}
            for future in concurrent.futures.as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as exc:
                    results.append(("❌", futures[future], f"Error: {exc}"))

        # Sort to a stable display order by service name
        display_order = ["Gemini", "Groq", "OpenAI", "xAI (Grok)", "ElevenLabs", "NVIDIA NIM"]
        results.sort(key=lambda x: display_order.index(x[1]) if x[1] in display_order else 99)

        # ── Build report ───────────────────────────────────────────────────────
        lines = ["*Key Status Report:*\n"]
        working_names = []
        broken_names  = []
        for icon, name, detail in results:
            lines.append(f"{icon} *{name}*: {detail}")
            if icon == "✅":
                working_names.append(name)
            elif icon == "❌":
                broken_names.append(name)

        # Active chain summary
        chain_parts = []
        for name in ["Gemini", "NVIDIA NIM", "Groq", "xAI (Grok)", "OpenAI"]:
            matched = next((r for r in results if r[1] == name), None)
            if matched:
                icon = matched[0]
                chain_parts.append(f"{name} {icon}" if icon != "✅" else name)
        lines.append(f"\n*Active chain:* {' → '.join(chain_parts)}")

        # Tips
        if broken_names:
            lines.append(f"\n*Tip:* Renew broken keys with `/updatekey KEY_NAME value`")
            for icon, name, detail in results:
                if icon == "❌":
                    if "Groq" in name:
                        lines.append("  • Groq: console.groq.com")
                    elif "OpenAI" in name:
                        lines.append("  • OpenAI: platform.openai.com")
                    elif "xAI" in name:
                        lines.append("  • xAI: console.x.ai")
                    elif "Gemini" in name:
                        lines.append("  • Gemini: aistudio.google.com")

        report = "\n".join(lines)

        try:
            bot.delete_message(message.chat.id, loading_msg.message_id)
        except Exception:
            pass
        bot.send_message(message.chat.id, report, parse_mode="Markdown")

    _fire_in_thread(_run)


@bot.message_handler(commands=["shell", "run"])
def cmd_shell(message):
    """Run a shell command with confirmation before execution."""
    if not is_ajay(message): return unauthorized_response(message)
    cmd = message.text.replace("/shell", "").replace("/run", "").strip()
    if not cmd:
        bot.send_message(message.chat.id,
            "Usage: `/shell <command>`\n"
            "Examples:\n"
            "`/shell ls -la`\n"
            "`/shell pip list`\n"
            "`/shell git status`",
            parse_mode="Markdown")
        return
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("✅ Run", callback_data=f"shell_confirm_{message.message_id}"),
        types.InlineKeyboardButton("❌ Cancel", callback_data=f"shell_cancel_{message.message_id}")
    )
    bot.send_message(message.chat.id,
        f"⚡ *Run this command?*\n```\n{cmd}\n```",
        parse_mode="Markdown",
        reply_markup=keyboard)
    _pending_shell[message.message_id] = cmd


@bot.callback_query_handler(func=lambda c: c.data.startswith("shell_confirm_") or c.data.startswith("shell_cancel_"))
def handle_shell_callback(call):
    if not is_ajay(call): return  # check call.from_user, not call.message
    parts = call.data.split("_", 2)
    action = parts[1]   # "confirm" or "cancel"
    msg_id = int(parts[2])
    cmd = _pending_shell.pop(msg_id, None)
    if action == "cancel" or cmd is None:
        bot.answer_callback_query(call.id, "Cancelled.")
        bot.edit_message_text("❌ Command cancelled.", call.message.chat.id, call.message.message_id)
        return
    bot.answer_callback_query(call.id, "Running...")
    bot.edit_message_text(f"⚡ Running: `{cmd}`...", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    try:
        import subprocess
        project_root = str(Path(__file__).parent.parent.parent)
        result = subprocess.run(
            cmd, shell=True, cwd=project_root,
            capture_output=True, text=True, timeout=120
        )
        output = (result.stdout + result.stderr).strip()
        if not output:
            output = "(no output)"
        if len(output) > 3500:
            output = output[-3500:] + "\n...(truncated)"
        icon = "✅" if result.returncode == 0 else "⚠️"
        bot.send_message(call.message.chat.id,
            f"{icon} *Exit code: {result.returncode}*\n```\n{output}\n```",
            parse_mode="Markdown")
    except subprocess.TimeoutExpired:
        bot.send_message(call.message.chat.id, "⏰ Command timed out after 120 seconds.")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Error: {e}")


@bot.message_handler(commands=["read"])
def cmd_read(message):
    """Read a file and send its contents."""
    if not is_ajay(message): return unauthorized_response(message)
    filepath = message.text.replace("/read", "").strip().splitlines()[0].strip()
    if filepath in (".env", ".env.local", ".env.production"):
        bot.send_message(message.chat.id, "🔒 `.env` is protected — I don't send secrets over chat.", parse_mode="Markdown")
        return
    if not filepath:
        bot.send_message(message.chat.id,
            "Usage: `/read <filepath>`\n"
            "Examples:\n"
            "`/read src/core/ai_router.py`\n"
            "`/read .env`\n"
            "`/read docs/AISHA_STATE_HANDOFF_2026-03-18.md`",
            parse_mode="Markdown")
        return
    try:
        project_root = Path(__file__).parent.parent.parent
        full_path = project_root / filepath
        if not full_path.exists():
            bot.send_message(message.chat.id, f"❌ File not found: `{filepath}`", parse_mode="Markdown")
            return
        content = full_path.read_text(encoding="utf-8", errors="replace")
        lines = len(content.splitlines())
        if len(content) > 3500:
            content = content[:3500] + f"\n\n...(truncated — {lines} total lines, showing first ~70)"
        ext = filepath.split(".")[-1] if "." in filepath else ""
        bot.send_message(message.chat.id,
            f"📄 `{filepath}` ({lines} lines)\n```{ext}\n{content}\n```",
            parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Read error: {e}")


@bot.message_handler(commands=["gitpull"])
def cmd_gitpull(message):
    """Pull latest code from GitHub (or trigger Render redeploy if git not available)."""
    if not is_ajay(message): return unauthorized_response(message)
    bot.send_message(message.chat.id, "🔄 Pulling latest code from GitHub...")
    try:
        import subprocess, shutil
        project_root = str(Path(__file__).parent.parent.parent)

        git_path = shutil.which("git") or "/usr/bin/git"
        if not shutil.which("git") and not Path(git_path).exists():
            # On Render, git may not be in PATH — trigger redeploy instead
            import requests
            deploy_hook = os.getenv("RENDER_DEPLOY_HOOK_URL") or os.getenv("RAILWAY_WEBHOOK_URL")
            if deploy_hook:
                r = requests.post(deploy_hook, timeout=15)
                bot.send_message(message.chat.id,
                    f"⚡ Git not found — triggered Render redeploy instead.\n"
                    f"Status: {r.status_code}")
            else:
                bot.send_message(message.chat.id,
                    "❌ Git not available on this host and no deploy hook configured.")
            return

        result = subprocess.run(
            [git_path, "pull", "origin", "main"],
            cwd=project_root, capture_output=True, text=True, timeout=60
        )
        output = (result.stdout + result.stderr).strip()
        icon = "✅" if result.returncode == 0 else "❌"
        bot.send_message(message.chat.id,
            f"{icon} *Git Pull Result:*\n```\n{output}\n```",
            parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Git pull failed: {e}")


@bot.message_handler(commands=["restart"])
def cmd_restart(message):
    """Restart the Aisha bot process (self-restart)."""
    if not is_ajay(message): return unauthorized_response(message)
    bot.send_message(message.chat.id, "🔄 Restarting Aisha... I'll be back in 10 seconds! 💜")
    import subprocess, sys, time
    time.sleep(2)
    project_root = str(Path(__file__).parent.parent.parent)
    subprocess.Popen(
        [sys.executable, "-m", "src.telegram.bot"],
        cwd=project_root
    )
    os._exit(0)


@bot.message_handler(commands=["studio"])
def cmd_studio(message):
    if not is_ajay(message): return unauthorized_response(message)
    bot.send_message(message.chat.id, "Starting my creative session! I'll pick the best channel and topic myself. Check your email in a few minutes! 💜🎬")

    import subprocess, sys as _sys
    project_root = str(Path(__file__).parent.parent.parent)
    subprocess.Popen([_sys.executable, "-m", "src.core.autonomous_loop", "--once"], cwd=project_root)


@bot.message_handler(commands=["testpipeline"])
def cmd_test_pipeline(message):
    """Test the full content pipeline with a dry run."""
    if not is_ajay(message): return unauthorized_response(message)
    channel_arg = message.text.replace("/testpipeline", "").strip()

    # Default to simplest channel for testing
    test_channel = channel_arg if channel_arg else "Aisha & Him"
    valid_channels = ["Story With Aisha", "Riya's Dark Whisper",
                      "Riya's Dark Romance Library", "Aisha & Him"]
    if test_channel not in valid_channels:
        test_channel = "Aisha & Him"

    bot.send_message(message.chat.id,
        f"🧪 Testing pipeline for *{test_channel}*...\n"
        f"This will generate a test script + voice (no upload). Takes 2-3 min. ⏳",
        parse_mode="Markdown")

    def run_test():
        try:
            from src.agents.antigravity_agent import AntigravityAgent
            agent = AntigravityAgent()
            job = agent.enqueue_job(
                topic="A beautiful sunset story",
                channel=test_channel,
                fmt="short",
                platform_targets=[],  # no actual posting
                auto_post=False,
                payload={"render_video": False, "test_mode": True}
            )
            job_id = job.get("id", "?")

            # Process it
            result = agent.process_job(job)

            if result and result.get("status") == "completed":
                output = result.get("output", {})
                script_preview = str(output.get("script", ""))[:200]
                bot.send_message(message.chat.id,
                    f"✅ *Pipeline test PASSED!*\n\n"
                    f"Channel: {test_channel}\n"
                    f"Job ID: `{job_id[:8]}`\n\n"
                    f"Script preview:\n_{script_preview}..._",
                    parse_mode="Markdown")
            else:
                error = result.get("error_text", result.get("error", "Unknown error")) if result else "No result returned"
                bot.send_message(message.chat.id,
                    f"❌ *Pipeline test FAILED*\n\nError: {str(error)[:300]}",
                    parse_mode="Markdown")
        except Exception as e:
            log.error(f"[testpipeline] Error: {e}")
            bot.send_message(message.chat.id,
                f"❌ *Pipeline test ERROR*\n\n`{str(e)[:300]}`",
                parse_mode="Markdown")

    threading.Thread(target=run_test, daemon=True, name="pipeline-test").start()


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
    # Support: /mood casual  /mood motivational  etc.
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) > 1:
        requested = parts[1].strip().lower()
        from src.core.prompts.personality import MOOD_INSTRUCTIONS
        if requested in MOOD_INSTRUCTIONS:
            aisha.mood_override = requested
            bot.send_message(
                message.chat.id,
                f"✅ Mood switched to *{requested}* mode, Ajay!",
                parse_mode="Markdown"
            )
        else:
            valid = ", ".join(MOOD_INSTRUCTIONS.keys())
            bot.send_message(
                message.chat.id,
                f"⚠️ Unknown mood *{requested}*. Available: {valid}",
                parse_mode="Markdown"
            )
        return
    # No argument — show keyboard picker
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

@bot.message_handler(commands=["addtask"])
def cmd_addtask(message):
    if not is_ajay(message): return unauthorized_response(message)
    task_text = message.text.replace("/addtask", "").strip()
    if not task_text:
        bot.send_message(message.chat.id,
            "📝 Tell me the task!\nUsage: `/addtask Buy groceries`\nOr add priority: `/addtask Fix bug @urgent`",
            parse_mode="Markdown")
        return
    # Parse optional priority tag
    priority = "medium"
    for tag in ["@urgent", "@high", "@low"]:
        if tag in task_text:
            priority = tag.lstrip("@")
            task_text = task_text.replace(tag, "").strip()
    try:
        db.table("aisha_schedule").insert({
            "title": task_text,
            "priority": priority,
            "status": "pending",
            "due_date": datetime.now().date().isoformat(),
            "created_by": "ajay",
        }).execute()
        bot.send_message(message.chat.id,
            f"✅ Task added!\n*{task_text}* [{priority}]",
            parse_mode="Markdown")
    except Exception as e:
        log.error(f"addtask error: {e}")
        bot.send_message(message.chat.id, "Sorry Aju, couldn't save the task 😔 Try again?")


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


@bot.message_handler(commands=["block"])
def cmd_block(message):
    """Block an approved user: /block <name_or_user_id>"""
    if not is_ajay(message): return unauthorized_response(message)
    query = message.text.replace("/block", "").strip().lower()
    if not query:
        bot.send_message(message.chat.id, "Usage: /block <name or user_id>")
        return
    _block_user_by_query(message.chat.id, query)


def _block_user_by_query(chat_id: int, query: str):
    """Find user by name or ID, remove from approved set and DB."""
    try:
        # Try to find in approved users table
        rows = db.table("aisha_approved_users").select("*").eq("is_active", True).execute().data or []
        target = None
        for row in rows:
            name  = (row.get("first_name") or "").lower()
            uname = (row.get("telegram_username") or "").lower()
            uid   = str(row.get("telegram_user_id", ""))
            if query in name or query in uname or query == uid:
                target = row
                break

        if not target:
            bot.send_message(chat_id, f"No approved user found matching '{query}'.")
            return

        user_id   = target["telegram_user_id"]
        user_name = target.get("first_name", f"User {user_id}")

        # 1. Remove from in-memory approved set
        _approved_users.discard(user_id)

        # 2. Mark inactive in DB
        db.table("aisha_approved_users").update({"is_active": False}).eq("telegram_user_id", user_id).execute()

        # 3. Notify the blocked user (optional — silent block)
        try:
            bot.send_message(user_id, "You have been removed from this bot's access list.")
        except Exception:
            pass

        bot.send_message(chat_id, f"✅ {user_name} ({user_id}) has been blocked and removed from approved users.")
        log.info(f"block_user user_id={user_id} name={user_name}")

    except Exception as e:
        log.error(f"block_user failed query={query} err={e}")
        bot.send_message(chat_id, f"Could not block user: {e}")

@bot.message_handler(commands=["voice"])
def cmd_voice(message):
    """Toggle Aisha's voice mode on/off."""
    if not is_ajay(message): return unauthorized_response(message)
    global VOICE_MODE_ENABLED
    VOICE_MODE_ENABLED = not VOICE_MODE_ENABLED
    status = "ON 🎙️" if VOICE_MODE_ENABLED else "OFF 🔇"
    voice_msg = "I'll speak to you with voice notes now! 💜" if VOICE_MODE_ENABLED else "Text only mode. Say /voice again to hear me! 💜"
    bot.send_message(
        message.chat.id,
        f"Voice mode is now *{status}*\n{voice_msg}",
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
    if not is_ajay(call):
        bot.answer_callback_query(call.id, text="Unauthorized", show_alert=True)
        return
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


# ─── User Approval Callbacks ───────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith("approve_user_") or c.data.startswith("deny_user_"))
def handle_user_approval(call):
    if not is_ajay(call):
        bot.answer_callback_query(call.id, "Unauthorized", show_alert=True)
        return

    parts   = call.data.split("_")
    user_id = int(parts[-1])
    pending = _pending_approvals.get(user_id)

    # Remove inline buttons from Ajay's notification
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception:
        pass

    if call.data.startswith("approve_user_"):
        _approved_users.add(user_id)
        _pending_approvals.pop(user_id, None)
        user_obj = pending["user"] if pending else None
        name     = user_obj.first_name if user_obj else f"User {user_id}"
        username = user_obj.username   if user_obj else None

        # Persist approval to Supabase
        try:
            db.table("aisha_approved_users").upsert({
                "telegram_user_id": user_id,
                "telegram_username": username,
                "first_name": name,
                "approved_by": AUTHORIZED_ID,
                "is_active": True,
            }, on_conflict="telegram_user_id").execute()
            log.info(f"approved_user user_id={user_id} persisted=True")
        except Exception as e:
            log.error(f"approved_user persist error user_id={user_id} err={e}")

        bot.answer_callback_query(call.id, "✅ Approved!")
        bot.send_message(AUTHORIZED_ID, f"✅ {name} ({user_id}) is now approved to chat with me.")
        bot.send_message(user_id, "✅ You've been approved by the owner! You can now chat with me 💜")

        # Process their waiting message through Aisha
        if pending:
            try:
                bot.send_chat_action(pending["message"].chat.id, "typing")
                pending_user   = pending.get("user")
                pending_name   = pending_user.first_name if pending_user else "Guest"
                response = aisha.think(
                    pending["text"],
                    platform="telegram",
                    caller_name=pending_name,
                    caller_id=user_id,
                    is_owner=False,
                )
                bot.send_message(pending["message"].chat.id, response)
            except Exception as e:
                log.error(f"Failed to process pending message for approved user {user_id}: {e}")

    else:  # deny
        _pending_approvals.pop(user_id, None)
        user_obj = pending["user"] if pending else None
        name     = user_obj.first_name if user_obj else f"User {user_id}"
        username = user_obj.username   if user_obj else None
        last_msg = pending["text"]     if pending else None

        # Persist denial to Supabase (upsert — increment rejection_count if already denied)
        try:
            existing = (
                db.table("aisha_rejected_users")
                .select("rejection_count")
                .eq("telegram_user_id", user_id)
                .execute()
            ).data
            count = (existing[0]["rejection_count"] + 1) if existing else 1
            db.table("aisha_rejected_users").upsert({
                "telegram_user_id": user_id,
                "telegram_username": username,
                "first_name": name,
                "rejected_at": datetime.utcnow().isoformat(),
                "rejection_count": count,
                "last_message": last_msg[:500] if last_msg else None,
            }, on_conflict="telegram_user_id").execute()
            log.info(f"denied_user user_id={user_id} rejection_count={count} persisted=True")
        except Exception as e:
            log.error(f"denied_user persist error user_id={user_id} err={e}")

        bot.answer_callback_query(call.id, "❌ Denied.")
        bot.send_message(AUTHORIZED_ID, f"❌ {name} ({user_id}) has been denied access.")
        try:
            bot.send_message(user_id, "🔒 The owner has declined your access request.")
        except Exception:
            pass


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

    chat_id    = message.chat.id
    message_id = message.message_id

    # Track the latest message per chat (voice counts as a message turn)
    _last_message_id[chat_id] = message_id

    # Acquire the per-chat lock — serialise against text messages in the same chat
    lock = _get_chat_lock(chat_id)
    if not lock.acquire(timeout=120):
        log.warning(f"handle_voice lock_timeout chat_id={chat_id} msg_id={message_id}")
        return

    voice_path = None
    try:
        # Drop if a newer message arrived while waiting for the lock
        if _last_message_id.get(chat_id) != message_id:
            log.info(f"handle_voice dropped_stale chat_id={chat_id} msg_id={message_id}")
            return

        # Download voice file
        file_info  = bot.get_file(message.voice.file_id)
        downloaded = bot.download_file(file_info.file_path)

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(downloaded)
            voice_path = f.name

        # Transcribe with Groq Whisper (reliable on Windows venv)
        try:
            from groq import Groq
            from src.core.mood_detector import detect_mood
            from src.core.language_detector import detect_language

            groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            with open(voice_path, "rb") as audio_file:
                transcript = groq_client.audio.transcriptions.create(
                    model="whisper-large-v3",
                    file=("voice.ogg", audio_file),
                )
            transcribed_text = transcript.text.strip()

            # Guard: still the current message?
            if _last_message_id.get(chat_id) != message_id:
                log.info(f"handle_voice reply_dropped_stale chat_id={chat_id} msg_id={message_id}")
                return

            bot.send_message(chat_id,
                f"Heard: \"{transcribed_text}\"",
                parse_mode="Markdown")

            bot.send_chat_action(chat_id, "typing")
            voice_caller_id   = message.from_user.id
            voice_caller_name = message.from_user.first_name or "Guest"
            voice_is_owner    = (voice_caller_id == AUTHORIZED_ID)
            response = aisha.think(
                transcribed_text,
                platform="telegram",
                caller_name=voice_caller_name,
                caller_id=voice_caller_id,
                is_owner=voice_is_owner,
            )

            # Guard before sending reply
            if _last_message_id.get(chat_id) != message_id:
                log.info(f"handle_voice think_reply_dropped chat_id={chat_id} msg_id={message_id}")
                return

            bot.send_message(chat_id, response)

            # Send voice reply back (voice-in = voice-out, respects VOICE_MODE_ENABLED)
            if VOICE_MODE_ENABLED and len(response) < 1000:
                try:
                    bot.send_chat_action(chat_id, "record_voice")
                    mood_res = detect_mood(transcribed_text)
                    mood = mood_res.mood if hasattr(mood_res, "mood") else str(mood_res)
                    lang_tuple = detect_language(transcribed_text)
                    language = lang_tuple[0] if isinstance(lang_tuple, tuple) else "English"
                    voice_reply = generate_voice(response, language=language, mood=mood)
                    if voice_reply:
                        if _last_message_id.get(chat_id) == message_id:
                            with open(voice_reply, "rb") as vf:
                                bot.send_voice(chat_id, vf)
                        cleanup_voice_file(voice_reply)
                except Exception as ve:
                    log.warning(f"Voice reply skipped: {ve}")

        except Exception as e:
            log.error(f"Voice transcription failed: {e}")
            bot.send_message(chat_id,
                "Arre Ajay, I couldn't catch that voice message. Try typing it out?")
    finally:
        lock.release()
        if voice_path:
            try:
                os.unlink(voice_path)
            except Exception:
                pass


# ─── Photo Message Handler ─────────────────────────────────────────────────────

@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    if not is_ajay(message): return unauthorized_response(message)

    chat_id    = message.chat.id
    message_id = message.message_id

    # Track the latest message per chat (photo counts as a message turn)
    _last_message_id[chat_id] = message_id

    # Acquire the per-chat lock — serialise against text/voice messages in the same chat
    lock = _get_chat_lock(chat_id)
    if not lock.acquire(timeout=120):
        log.warning(f"handle_photo lock_timeout chat_id={chat_id} msg_id={message_id}")
        return

    try:
        # Drop if a newer message arrived while waiting for the lock
        if _last_message_id.get(chat_id) != message_id:
            log.info(f"handle_photo dropped_stale chat_id={chat_id} msg_id={message_id}")
            return

        bot.send_chat_action(chat_id, "typing")

        try:
            # Get highest resolution photo
            raw_photo = message.photo[-1]
            file_info = bot.get_file(raw_photo.file_id)
            downloaded_bytes = bot.download_file(file_info.file_path)

            user_text = message.caption if message.caption else "I sent you a photo. What do you see?"

            # Pass image to Aisha's brain
            photo_caller_id   = message.from_user.id
            photo_caller_name = message.from_user.first_name or "Guest"
            photo_is_owner    = (photo_caller_id == AUTHORIZED_ID)
            response = aisha.think(
                user_text,
                platform="telegram",
                image_bytes=downloaded_bytes,
                caller_name=photo_caller_name,
                caller_id=photo_caller_id,
                is_owner=photo_is_owner,
            )

            # Guard: don't send if a newer message has already arrived
            if _last_message_id.get(chat_id) != message_id:
                log.info(f"handle_photo reply_dropped_stale chat_id={chat_id} msg_id={message_id}")
                return

            bot.reply_to(message, response)

            # Optional: Voice reply
            if VOICE_MODE_ENABLED and len(response) < 1000:
                try:
                    bot.send_chat_action(chat_id, "record_voice")
                    from src.core.mood_detector import detect_mood
                    from src.core.language_detector import detect_language
                    mood_res = detect_mood(user_text)
                    mood = mood_res.mood if hasattr(mood_res, "mood") else str(mood_res)
                    lang_tuple = detect_language(user_text)
                    language = lang_tuple[0] if isinstance(lang_tuple, tuple) else "English"

                    voice_reply = generate_voice(response, language=language, mood=mood)
                    if voice_reply:
                        if _last_message_id.get(chat_id) == message_id:
                            with open(voice_reply, "rb") as vf:
                                bot.send_voice(chat_id, vf)
                        cleanup_voice_file(voice_reply)
                except Exception as ve:
                    log.warning(f"Voice reply skipped for photo: {ve}")

        except Exception as e:
            log.error(f"Image processing failed: {e}")
            bot.reply_to(message, "Arre Ajay, I couldn't process that image 😔 Technical issue on my end!")
    finally:
        lock.release()

# ─── Main Text Handler ─────────────────────────────────────────────────────────

@bot.message_handler(func=lambda message: True)
def handle_text(message, override_text=None):
    if not is_ajay(message): return unauthorized_response(message)

    user_text = override_text or message.text
    if not user_text or not user_text.strip():
        return

    chat_id    = message.chat.id
    message_id = message.message_id

    # Track the latest message for this chat so we can detect stale replies
    _last_message_id[chat_id] = message_id

    # Acquire the per-chat lock — only one message processed at a time per chat
    lock = _get_chat_lock(chat_id)
    if not lock.acquire(timeout=120):
        # Could not acquire within 2 min — give up silently
        log.warning(f"handle_text lock_timeout chat_id={chat_id} msg_id={message_id}")
        return

    try:
        # After acquiring the lock, check whether this message is still current.
        # If a newer message arrived while we were waiting, drop this one.
        if _last_message_id.get(chat_id) != message_id:
            log.info(f"handle_text dropped_stale chat_id={chat_id} msg_id={message_id}")
            return

        # Identify who is talking so Aisha addresses them correctly
        caller_id   = message.from_user.id
        caller_name = message.from_user.first_name or "Guest"
        owner       = (caller_id == AUTHORIZED_ID)

        # ── "Share with owner" intent ─────────────────────────────────────────
        # If an approved non-owner user says "share this with Ajay/owner", forward it.
        if not owner and any(kw in user_text.lower() for kw in [
            "share with", "tell ajay", "tell your owner", "tell the owner",
            "forward to", "send to ajay", "notify ajay", "let ajay know"
        ]):
            forward_msg = (
                f"📨 *{caller_name}* wants you to know:\n\n"
                f"_{user_text[:800]}_"
            )
            try:
                bot.send_message(AUTHORIZED_ID, forward_msg, parse_mode="Markdown")
            except Exception:
                pass
            bot.send_message(
                chat_id,
                f"Done! I've flagged that for Ajay, {caller_name}. He'll see it shortly."
            )
            return

        # Show typing indicator
        bot.send_chat_action(chat_id, "typing")

        try:
            log.info(f"[{caller_name}] {user_text[:80]}")
            response = aisha.think(
                user_text,
                platform="telegram",
                caller_name=caller_name,
                caller_id=caller_id,
                is_owner=owner,
            )

            # Guard: don't send if a newer message has already arrived
            if _last_message_id.get(chat_id) != message_id:
                log.info(f"handle_text reply_dropped_stale chat_id={chat_id} msg_id={message_id}")
                return

            # Send text response
            if len(response) > 4000:
                chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
                for chunk in chunks:
                    bot.send_message(chat_id, chunk)
            else:
                bot.send_message(chat_id, response)

            # Send voice note if voice mode is enabled
            if VOICE_MODE_ENABLED and len(response) < 1000:
                try:
                    bot.send_chat_action(chat_id, "record_voice")

                    # Detect language and mood for voice tuning
                    from src.core.mood_detector import detect_mood
                    from src.core.language_detector import detect_language
                    mood_res = detect_mood(user_text)
                    mood = mood_res.mood if hasattr(mood_res, "mood") else str(mood_res)
                    lang_tuple = detect_language(user_text)
                    language = lang_tuple[0] if isinstance(lang_tuple, tuple) else "English"

                    voice_path = generate_voice(response, language=language, mood=mood)
                    if voice_path:
                        # Final guard before sending voice
                        if _last_message_id.get(chat_id) == message_id:
                            with open(voice_path, "rb") as voice_file:
                                bot.send_voice(chat_id, voice_file)
                        cleanup_voice_file(voice_path)
                except Exception as ve:
                    log.warning(f"Voice generation skipped: {ve}")

        except Exception as e:
            log.error(f"Error processing message: {e}")
            fallback_msg = _get_fallback_msg(chat_id)
            if fallback_msg:
                bot.send_message(chat_id, fallback_msg)
    finally:
        lock.release()


# ─── Health Tracking Commands ─────────────────────────────────────────────────

@bot.message_handler(commands=["water"])
def cmd_water(message):
    if not is_ajay(message): return unauthorized_response(message)
    text = message.text.replace("/water", "").strip()
    try:
        glasses = int(text) if text else 1
    except ValueError:
        glasses = 1
    from src.core.health_tracker import HealthTracker
    tracker = HealthTracker(aisha.supabase)
    if tracker.log_water(glasses):
        bot.send_message(message.chat.id, f"Logged {glasses} glass(es) of water! Stay hydrated, Ajay! 💧")
    else:
        bot.send_message(message.chat.id, "Couldn't log water right now — try again!")


@bot.message_handler(commands=["sleep"])
def cmd_sleep(message):
    if not is_ajay(message): return unauthorized_response(message)
    text = message.text.replace("/sleep", "").strip()
    parts = text.split() if text else []
    try:
        hours = float(parts[0]) if parts else 7.0
        quality = parts[1].lower() if len(parts) > 1 else "okay"
    except (ValueError, IndexError):
        hours, quality = 7.0, "okay"
    from src.core.health_tracker import HealthTracker
    tracker = HealthTracker(aisha.supabase)
    if tracker.log_sleep(hours, quality):
        bot.send_message(message.chat.id, f"Logged {hours}h sleep ({quality}). Rest well! 😴")
    else:
        bot.send_message(message.chat.id, "Couldn't log sleep right now — try again!")


@bot.message_handler(commands=["workout"])
def cmd_workout(message):
    if not is_ajay(message): return unauthorized_response(message)
    text = message.text.replace("/workout", "").strip()
    parts = text.split(maxsplit=1) if text else []
    workout_type = parts[0] if parts else "workout"
    details = parts[1] if len(parts) > 1 else ""
    from src.core.health_tracker import HealthTracker
    tracker = HealthTracker(aisha.supabase)
    if tracker.log_workout(workout_type, details):
        bot.send_message(message.chat.id, f"Workout logged: {workout_type} {details}. Crushing it! 💪")
    else:
        bot.send_message(message.chat.id, "Couldn't log workout — try again!")


@bot.message_handler(commands=["health"])
def cmd_health(message):
    if not is_ajay(message): return unauthorized_response(message)
    from src.core.health_tracker import HealthTracker
    tracker = HealthTracker(aisha.supabase)
    text = tracker.format_summary_text()
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


# ─── Digest Command ──────────────────────────────────────────────────────────

@bot.message_handler(commands=["digest"])
def cmd_digest(message):
    if not is_ajay(message): return unauthorized_response(message)
    bot.send_chat_action(message.chat.id, "typing")
    from src.core.digest_engine import DigestEngine
    digest = DigestEngine(aisha.memory, aisha.ai)
    text = digest.generate_daily_digest()
    bot.send_message(message.chat.id, text)


# ─── Retry Failed Message ─────────────────────────────────────────────────────

@bot.message_handler(commands=["retry"])
def cmd_retry(message):
    if not is_ajay(message): return unauthorized_response(message)
    try:
        rows = (
            aisha.supabase.table("aisha_message_queue")
            .select("*")
            .eq("status", "failed")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        ).data
        if not rows:
            bot.send_message(message.chat.id, "No failed messages to retry! All clear. 💜")
            return
        failed = rows[0]
        bot.send_message(message.chat.id, f"Retrying: _{failed['user_message'][:80]}..._", parse_mode="Markdown")
        response = aisha.think(failed["user_message"], platform=failed.get("platform", "telegram"))
        # Mark as retried
        aisha.supabase.table("aisha_message_queue").update({
            "status": "retried",
            "retry_count": (failed.get("retry_count") or 0) + 1,
        }).eq("id", failed["id"]).execute()
        bot.send_message(message.chat.id, response)
    except Exception as e:
        bot.send_message(message.chat.id, f"Retry failed too: {e}")


# ─── API Key Update Flow ─────────────────────────────────────────────────────

# Tracks pending key updates: {key_name: True} when Aisha is waiting for Ajay to send a new value
_pending_key_updates: dict = {}


@bot.message_handler(commands=["updatekey"])
def cmd_updatekey(message):
    """
    /updatekey GROQ_API_KEY gsk_newkeyhere
    Ajay sends the new key value, Aisha validates it and saves to DB.
    """
    if not is_ajay(message):
        return unauthorized_response(message)
    parts = message.text.strip().split(maxsplit=2)
    if len(parts) < 3:
        bot.send_message(
            message.chat.id,
            "Usage: `/updatekey KEY_NAME new_value`\nExample: `/updatekey GROQ_API_KEY gsk_abc123`",
            parse_mode="Markdown",
        )
        return
    key_name = parts[1].strip().upper()
    new_value = parts[2].strip()
    _apply_key_update(message.chat.id, key_name, new_value)


@bot.message_handler(commands=["keyhealth"])
def cmd_keyhealth(message):
    """Run credential health check and report all API key statuses."""
    if not is_ajay(message):
        return unauthorized_response(message)
    bot.send_message(message.chat.id, "Running key health check... this takes ~30 seconds.")

    def _run():
        try:
            from src.core.credential_manager import CredentialManager
            cm = CredentialManager()
            summary = cm.run_daily_health_check()
            bot.send_message(message.chat.id, summary, parse_mode="Markdown")
        except Exception as e:
            bot.send_message(message.chat.id, f"Key health check failed: {e}")

    _fire_in_thread(_run)


@bot.message_handler(commands=["findapi"])
def cmd_findapi(message):
    """Search web for how to get an API key for any platform and send Ajay a guide."""
    if not is_ajay(message):
        return unauthorized_response(message)
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        bot.send_message(
            message.chat.id,
            "🔍 *Find API Setup Guide*\n\n"
            "Usage: `/findapi <platform>`\n\n"
            "Examples:\n"
            "`/findapi tiktok`\n"
            "`/findapi huggingface`\n"
            "`/findapi elevenlabs`\n"
            "`/findapi openai`\n"
            "`/findapi groq`",
            parse_mode="Markdown",
        )
        return
    platform = parts[1].strip()
    bot.send_message(
        message.chat.id,
        f"🔍 Searching for *{platform}* API setup guide...\n_This takes 10-20 seconds_ ⏳",
        parse_mode="Markdown",
    )

    def _run():
        try:
            from src.core.api_discovery import APIDiscoveryAgent
            agent = APIDiscoveryAgent()
            sent = agent.notify_ajay_api_setup(platform)
            if not sent:
                bot.send_message(
                    message.chat.id,
                    f"⚠️ Found guide for *{platform}* but Telegram send failed. Check logs.",
                    parse_mode="Markdown",
                )
        except Exception as e:
            log.error(f"[/findapi] Error for platform={platform}: {e}")
            bot.send_message(message.chat.id, f"❌ Search failed for *{platform}*: `{str(e)[:200]}`", parse_mode="Markdown")

    _fire_in_thread(_run)


@bot.message_handler(commands=["instagram_setup", "instagram_auth"])
def cmd_instagram_setup(message):
    """Generate and send the Meta OAuth URL so Ajay can reconnect Instagram."""
    if not is_ajay(message):
        return unauthorized_response(message)

    app_id = os.getenv("INSTAGRAM_APP_ID", "")
    if not app_id:
        bot.send_message(message.chat.id, "❌ INSTAGRAM_APP_ID not set in env. Add it first.")
        return

    render_url = os.getenv("RENDER_EXTERNAL_URL", "https://aisha-bot-yudp.onrender.com")
    redirect_uri = f"{render_url}/instagram_callback"

    from urllib.parse import urlencode
    params = urlencode({
        "client_id": app_id,
        "redirect_uri": redirect_uri,
        "scope": "instagram_basic,instagram_content_publish,pages_read_engagement,pages_manage_posts,public_profile",
        "response_type": "code",
    })
    auth_url = f"https://www.facebook.com/v19.0/dialog/oauth?{params}"

    bot.send_message(
        message.chat.id,
        f"*Instagram OAuth Setup*\n\n"
        f"Your current token has expired. Click the link below to reconnect Instagram:\n\n"
        f"[Connect Instagram]({auth_url})\n\n"
        f"After you approve, Aisha will automatically save the new token and notify you here. ✅",
        parse_mode="Markdown",
        disable_web_page_preview=False,
    )


def _fire_in_thread(fn):
    """Run *fn* in a background daemon thread (fire-and-forget helper)."""
    threading.Thread(target=fn, daemon=True).start()


def _apply_key_update(chat_id: int, key_name: str, new_value: str):
    """Validate a new API key value and save it to Supabase api_keys table."""
    import requests as _req
    try:
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        # Check if key exists in DB
        r = _req.get(
            f"{supabase_url}/rest/v1/api_keys?name=eq.{key_name}&select=name",
            headers=headers, timeout=10,
        )
        if not r.json():
            bot.send_message(chat_id, f"Key `{key_name}` not found in DB. Please check the name and try again.", parse_mode="Markdown")
            return
        # Save to DB
        patch = _req.patch(
            f"{supabase_url}/rest/v1/api_keys?name=eq.{key_name}",
            json={"secret": new_value, "active": True},
            headers=headers, timeout=10,
        )
        if patch.status_code in (200, 204):
            # Also update local env var for this session
            os.environ[key_name] = new_value
            bot.send_message(
                chat_id,
                f"Updated `{key_name}` in DB. Aisha will use the new key immediately.\n\nRun `/keyhealth` to verify it works!",
                parse_mode="Markdown",
            )
            _pending_key_updates.pop(key_name, None)
        else:
            bot.send_message(chat_id, f"DB update failed ({patch.status_code}). Try again or update manually in Render.")
    except Exception as e:
        bot.send_message(chat_id, f"Key update error: {e}")


# ─── Render Health + Trigger Server ──────────────────────────────────────────

def _handle_instagram_oauth_callback(handler):
    """
    Handle Instagram/Facebook OAuth2 callback.
    Exchange the code for a short-lived token, then a long-lived token,
    save to Supabase api_keys and notify Ajay on Telegram.
    """
    from urllib.parse import urlparse, parse_qs
    import json as _j
    import requests as _r

    parsed = urlparse(handler.path)
    params = parse_qs(parsed.query)

    app_id     = os.getenv("INSTAGRAM_APP_ID", "")
    app_secret = os.getenv("INSTAGRAM_APP_SECRET", "")
    render_url = os.getenv("RENDER_EXTERNAL_URL", "https://aisha-bot-yudp.onrender.com")
    redirect_uri = f"{render_url}/instagram_callback"

    error = params.get("error", [None])[0]
    if error:
        msg = f"❌ Instagram OAuth denied: {params.get('error_description', ['unknown'])[0]}"
        log.error(f"[Instagram OAuth] {msg}")
        _notify_ajay(msg)
        body = f"<html><body>{msg}</body></html>".encode()
        handler.send_response(400)
        handler.send_header("Content-Type", "text/html")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)
        return

    code = params.get("code", [None])[0]
    if not code:
        body = b"<html><body>Missing code parameter.</body></html>"
        handler.send_response(400)
        handler.send_header("Content-Type", "text/html")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)
        return

    try:
        # Step 1: Exchange code for short-lived user token
        token_resp = _r.post(
            "https://graph.facebook.com/v19.0/oauth/access_token",
            data={
                "client_id": app_id,
                "client_secret": app_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            },
            timeout=15,
        ).json()

        short_token = token_resp.get("access_token")
        if not short_token:
            raise RuntimeError(f"Token exchange failed: {token_resp}")

        # Step 2: Exchange short-lived token for long-lived token (60 days)
        ll_resp = _r.get(
            "https://graph.facebook.com/v19.0/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": app_id,
                "client_secret": app_secret,
                "fb_exchange_token": short_token,
            },
            timeout=15,
        ).json()

        long_token = ll_resp.get("access_token", short_token)
        expires_in = ll_resp.get("expires_in", 5183944)  # ~60 days in seconds

        # Step 3: Get Facebook Pages to find Instagram Business Account
        pages_resp = _r.get(
            "https://graph.facebook.com/v19.0/me/accounts",
            params={"access_token": long_token, "fields": "id,name,instagram_business_account"},
            timeout=15,
        ).json()

        ig_biz_id = None
        page_token = long_token

        for page in pages_resp.get("data", []):
            ig = page.get("instagram_business_account")
            if ig:
                ig_biz_id = ig.get("id")
                # Use page-specific access token for posting
                page_token = _r.get(
                    f"https://graph.facebook.com/v19.0/{page['id']}",
                    params={"fields": "access_token", "access_token": long_token},
                    timeout=10,
                ).json().get("access_token", long_token)
                break

        if not ig_biz_id:
            ig_biz_id = os.getenv("INSTAGRAM_BUSINESS_ID", "")

        # Step 4: Save to Supabase api_keys table
        token_payload = _j.dumps({
            "access_token": page_token,
            "business_id": ig_biz_id,
            "expires_in": expires_in,
        })

        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        }
        _r.post(
            f"{supabase_url}/rest/v1/api_keys",
            json={"name": "INSTAGRAM_TOKEN", "secret": token_payload, "active": True},
            headers=headers,
            timeout=10,
        )

        # Also update env var for this session
        os.environ["INSTAGRAM_ACCESS_TOKEN"] = page_token
        if ig_biz_id:
            os.environ["INSTAGRAM_BUSINESS_ID"] = ig_biz_id

        msg = (
            f"✅ *Instagram Connected!*\n\n"
            f"Business Account ID: `{ig_biz_id or 'not found'}`\n"
            f"Token expires in: ~{expires_in // 86400} days\n\n"
            f"Aisha can now post Reels and images! Run `/syscheck` to verify."
        )
        _notify_ajay(msg)
        log.info(f"[Instagram OAuth] Connected. biz_id={ig_biz_id}, expires_in={expires_in}s")

        body = b"<html><body><h1>Instagram connected!</h1><p>You can close this tab. Aisha has been notified.</p></body></html>"
        handler.send_response(200)
        handler.send_header("Content-Type", "text/html")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)

    except Exception as e:
        log.error(f"[Instagram OAuth] Callback failed: {e}", exc_info=True)
        _notify_ajay(f"❌ Instagram OAuth callback failed: {str(e)[:300]}")
        body = f"<html><body>Error: {e}</body></html>".encode()
        handler.send_response(500)
        handler.send_header("Content-Type", "text/html")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)


def _notify_ajay(msg: str):
    """Send a message to Ajay's Telegram chat (fire and forget)."""
    try:
        bot.send_message(AUTHORIZED_ID, msg, parse_mode="Markdown")
    except Exception as e:
        log.warning(f"[_notify_ajay] Failed: {e}")


import time as _time_mod

_last_startup_msg_time: float = 0.0
STARTUP_MSG_COOLDOWN: int = 1800  # 30 minutes — prevents spam on Render restarts


def send_startup_message():
    """Send Aisha's wake-up notification to Ajay with a 30-minute cooldown.

    Render may restart the process multiple times in quick succession.
    This guard ensures Ajay only receives one startup ping per 30-minute window.
    """
    global _last_startup_msg_time
    now = _time_mod.time()
    if now - _last_startup_msg_time < STARTUP_MSG_COOLDOWN:
        log.info(
            f"startup_msg skipped — sent {int(now - _last_startup_msg_time)}s ago "
            f"(cooldown={STARTUP_MSG_COOLDOWN}s)"
        )
        return
    _last_startup_msg_time = now
    try:
        bot.send_message(
            AUTHORIZED_ID,
            "💜 Aisha is online and ready, Ajay! All systems initialised.",
        )
        log.info("startup_msg sent to Ajay")
    except Exception as e:
        log.warning(f"startup_msg send failed: {e}")


# Global reference to the AutonomousLoop instance (set during startup)
_autonomous_loop = None

TRIGGER_SECRET = os.getenv("TRIGGER_SECRET", "")


class _AishaHTTPHandler(BaseHTTPRequestHandler):
    """Minimal HTTP server for Render /health keep-alive and pg_cron /api/trigger/<job>."""

    def do_GET(self):
        if self.path in ('/', '/health', '/ping'):
            body = b'{"status":"ok","service":"aisha-bot"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path.startswith('/instagram_callback'):
            _handle_instagram_oauth_callback(self)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        # ── Telegram webhook endpoint ──────────────────────────────────────────
        if self.path == f"/{BOT_TOKEN}":
            tg_secret = self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
            if TRIGGER_SECRET and tg_secret != TRIGGER_SECRET:
                self.send_response(403)
                self.end_headers()
                return
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                update = telebot.types.Update.de_json(_json.loads(body.decode("utf-8")))
                threading.Thread(target=bot.process_new_updates, args=([update],), daemon=True).start()
            except Exception as e:
                log.error(f"webhook_parse err={e}")
            self.send_response(200)
            self.end_headers()
            return

        # ── pg_cron trigger endpoint ───────────────────────────────────────────
        secret = self.headers.get("X-Trigger-Secret", "")
        if TRIGGER_SECRET and secret != TRIGGER_SECRET:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b'{"error":"forbidden"}')
            return

        parts = self.path.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "trigger":
            job = parts[2]
            _dispatch_trigger(job)
            body = _json.dumps({"status": "accepted", "job": job}).encode()
            self.send_response(202)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Silence access logs


def _dispatch_trigger(job: str):
    """Fire an AutonomousLoop method in a background thread (non-blocking)."""
    global _autonomous_loop
    if _autonomous_loop is None:
        log.warning(f"trigger_dispatch job={job} status=no_loop_yet")
        return

    job_map = {
        "morning":        _autonomous_loop.run_morning_checkin,
        "evening":        _autonomous_loop.run_evening_wrapup,
        "digest":         _autonomous_loop.run_daily_digest,
        "memory":         _autonomous_loop.run_memory_consolidation,
        "weekly-digest":  _autonomous_loop.run_weekly_digest,
        "memory-cleanup": _autonomous_loop.run_memory_cleanup,
        "task-poll":      _autonomous_loop.run_task_reminder_poll,
        "inactivity":     _autonomous_loop.run_inactivity_check,
        "studio":         _autonomous_loop.run_studio_session,
        "self-improve":   lambda: __import__("src.core.autonomous_loop", fromlist=["run_self_improvement"]).run_self_improvement(_autonomous_loop),
        "temp-cleanup":   _autonomous_loop.run_temp_cleanup,
        "key-expiry":     _autonomous_loop.run_key_expiry_check,
    }

    fn = job_map.get(job)
    if fn is None:
        log.warning(f"trigger_dispatch job={job} status=unknown_job")
        return

    log.info(f"trigger_dispatch job={job} status=firing")
    t = threading.Thread(target=fn, daemon=True)
    t.start()


def start_health_server():
    """Start the HTTP health/trigger server on $PORT (Render injects this)."""
    port = int(os.getenv("PORT", "8000"))
    server = HTTPServer(('0.0.0.0', port), _AishaHTTPHandler)
    log.info(f"health_server port={port} status=starting")
    server.serve_forever()


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
        telebot.types.BotCommand("/health",  "Today's health summary"),
        telebot.types.BotCommand("/water",   "Log water intake (/water 3)"),
        telebot.types.BotCommand("/sleep",   "Log sleep (/sleep 7.5 good)"),
        telebot.types.BotCommand("/workout", "Log workout (/workout run 30min)"),
        telebot.types.BotCommand("/digest",  "Today's AI digest"),
        telebot.types.BotCommand("/retry",   "Retry last failed message"),
        telebot.types.BotCommand("/help",     "Help & commands"),
        telebot.types.BotCommand("/reset",    "Reset conversation"),
        telebot.types.BotCommand("/upload",   "Upload latest content to YouTube"),
        telebot.types.BotCommand("/queue",    "View content pipeline queue"),
        telebot.types.BotCommand("/logs",     "View last 30 log lines (/logs 50)"),
        telebot.types.BotCommand("/syscheck",   "Run full system test"),
        telebot.types.BotCommand("/drainqueue", "Drain stuck queued jobs (up to 5)"),
        telebot.types.BotCommand("/dbrepair",   "Create any missing Supabase tables"),
        telebot.types.BotCommand("/shell",    "Run shell command with confirmation"),
        telebot.types.BotCommand("/read",     "Read any file (/read src/core/ai_router.py)"),
        telebot.types.BotCommand("/gitpull",  "Pull latest code from GitHub"),
        telebot.types.BotCommand("/restart",  "Restart Aisha bot process"),
        telebot.types.BotCommand("/upgrade",  "Full self-upgrade: audit → PR → deploy"),
        telebot.types.BotCommand("/selfaudit","Audit code and propose improvements"),
        telebot.types.BotCommand("/feature",  "Build a new feature with 6-agent pipeline"),
        telebot.types.BotCommand("/keyhealth","Check all API keys health"),
        telebot.types.BotCommand("/updatekey","Update an API key (/updatekey KEY value)"),
        telebot.types.BotCommand("/findapi",        "Search web for API setup guide (/findapi tiktok)"),
        telebot.types.BotCommand("/instagram_setup", "Reconnect Instagram OAuth token"),
    ])
    
    # ── Health + Trigger HTTP server (required by Render + pg_cron) ──────────
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    log.info("health_server thread=started")

    # ── Self-ping every 30s to prevent Render free-tier spin-down ────────────
    def _self_ping():
        import time as _t
        import urllib.request as _ur
        # Use public URL on Render (external traffic prevents spin-down)
        # Fall back to loopback for local dev
        render_url = os.getenv("RENDER_BOT_URL", "").rstrip("/")
        if render_url:
            url = f"{render_url}/health"
        else:
            port = int(os.getenv("PORT", "8000"))
            url = f"http://127.0.0.1:{port}/health"
        while True:
            _t.sleep(30)
            try:
                _ur.urlopen(url, timeout=10)
            except Exception:
                pass  # silence — server may still be starting

    threading.Thread(target=_self_ping, daemon=True).start()
    log.info("self_ping thread=started interval=30s")

    # ── AutonomousLoop background thread (fallback scheduler) ────────────────
    def _start_autonomous_loop():
        global _autonomous_loop
        try:
            import schedule as _schedule
            import time as _time
            from src.core.autonomous_loop import AutonomousLoop, run_self_improvement
            _autonomous_loop = AutonomousLoop()
            log.info("autonomous_loop status=initialized")
            send_startup_message()
            # ── IST times converted to UTC (server runs UTC on Render) ────────
            # IST = UTC + 5:30 → subtract 5:30 from IST time to get UTC time
            _schedule.every().day.at("02:30").do(_autonomous_loop.run_morning_checkin)    # 8:00 AM IST
            _schedule.every().day.at("15:30").do(_autonomous_loop.run_evening_wrapup)     # 9:00 PM IST
            _schedule.every().day.at("16:00").do(_autonomous_loop.run_daily_digest)       # 9:30 PM IST
            _schedule.every().day.at("21:30").do(_autonomous_loop.run_memory_consolidation)  # 3:00 AM IST
            _schedule.every().sunday.at("13:30").do(_autonomous_loop.run_weekly_digest)   # 7:00 PM IST Sunday
            _schedule.every().sunday.at("21:30").do(_autonomous_loop.run_memory_cleanup)  # 3:00 AM IST Sunday
            _schedule.every(5).minutes.do(_autonomous_loop.run_task_reminder_poll)
            _schedule.every(3).hours.do(_autonomous_loop.run_inactivity_check)
            _schedule.every(4).hours.do(_autonomous_loop.run_studio_session)
            _schedule.every().day.at("20:30").do(run_self_improvement, _autonomous_loop)  # 2:00 AM IST
            _schedule.every().day.at("22:30").do(_autonomous_loop.run_temp_cleanup)       # 4:00 AM IST
            _schedule.every().day.at("03:30").do(_autonomous_loop.run_key_expiry_check)   # 9:00 AM IST
            log.info("autonomous_loop status=schedule_registered")
            while True:
                _schedule.run_pending()
                _time.sleep(60)
        except Exception as e:
            log.error(f"autonomous_loop status=crashed err={e}")

    loop_thread = threading.Thread(target=_start_autonomous_loop, daemon=True)
    loop_thread.start()
    log.info("autonomous_loop thread=started")

    RENDER_BOT_URL = os.getenv("RENDER_BOT_URL", "").rstrip("/")
    if RENDER_BOT_URL:
        # ── Webhook mode (Render production) ─────────────────────────────────
        webhook_url = f"{RENDER_BOT_URL}/{BOT_TOKEN}"
        bot.remove_webhook()
        import time as _wt; _wt.sleep(1)
        webhook_kwargs = {"url": webhook_url}
        if TRIGGER_SECRET:
            webhook_kwargs["secret_token"] = TRIGGER_SECRET
        bot.set_webhook(**webhook_kwargs)
        log.info(f"webhook mode=enabled url=https://aisha-bot-yudp.onrender.com/<token>")
        print("✅ Aisha is live on Telegram (webhook mode)! 💜")
        threading.Event().wait()  # Keep main thread alive forever
    else:
        # ── Polling mode (local dev — no RENDER_BOT_URL set) ─────────────────
        print("✅ Aisha is live on Telegram (polling mode)! 💜")
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

    from src.core.self_improvement import merge_github_pr, get_pr_number_from_url, trigger_redeploy
    pr_number = get_pr_number_from_url(pr_url) if pr_url else 0

    if pr_number and merge_github_pr(pr_number):
        # Trigger Render redeploy after successful merge
        redeployed = trigger_redeploy()
        status_line = "Deployed and live! 🚀" if redeployed else "Merged — Render will redeploy shortly."
        bot.edit_message_text(
            f"✅ I upgraded myself!\n\n"
            f"*Skill:* {skill_name}\n"
            f"*Status:* {status_line}\n"
            f"*PR:* {pr_url or 'N/A'}\n\n"
            "My brain is now more powerful! 💜",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="Markdown"
        )
    else:
        bot.edit_message_text(
            f"⚠️ Approved *{skill_name}*, but failed to auto-merge PR #{pr_number}.\n"
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
        f"❌ Skipped the new skill: *{skill_name}*.\n"
        "Let me know if you want me to write it differently later! 💜",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode="Markdown"
    )
