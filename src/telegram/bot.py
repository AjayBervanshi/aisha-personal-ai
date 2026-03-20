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

# ─── Voice Mode State ─────────────────────────────────────────────────────────
VOICE_MODE_ENABLED = True   # Start with voice ON — Aisha speaks by default!

# ─── Pending shell commands (for confirmation) ────────────────────────────────
_pending_shell: dict = {}  # message_id → command string

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
        "/skills — See all skills Aisha has learned\n\n"
        "⚡ *Power Commands (Claude Code Level):*\n"
        "/upload [channel] — Upload latest content to YouTube\n"
        "/queue — See content pipeline jobs\n"
        "/logs [n] — View last N lines of aisha.log\n"
        "/syscheck — Run full system test\n"
        "/shell <cmd> — Run shell command (with confirmation)\n"
        "/read <file> — Read any file\n"
        "/gitpull — Pull latest code from GitHub\n"
        "/restart — Restart Aisha bot\n"
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
    filepath = message.text.replace("/read", "").strip()
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
    """Pull latest code from GitHub."""
    if not is_ajay(message): return unauthorized_response(message)
    bot.send_message(message.chat.id, "🔄 Pulling latest code from GitHub...")
    try:
        import subprocess
        project_root = str(Path(__file__).parent.parent.parent)
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
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
    
    import subprocess
    project_root = str(Path(__file__).parent.parent.parent)
    subprocess.Popen(["python", "-m", "src.core.autonomous_loop", "--once"], cwd=project_root)


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

        bot.send_message(message.chat.id,
            f"Heard: \"{transcribed_text}\"",
            parse_mode="Markdown")

        bot.send_chat_action(message.chat.id, "typing")
        response = aisha.think(transcribed_text, platform="telegram")
        bot.send_message(message.chat.id, response)

        # Send voice reply back (voice-in = voice-out, respects VOICE_MODE_ENABLED)
        if VOICE_MODE_ENABLED and len(response) < 1000:
            try:
                bot.send_chat_action(message.chat.id, "record_voice")
                mood_res = detect_mood(transcribed_text)
                mood = mood_res.mood if hasattr(mood_res, "mood") else str(mood_res)
                lang_tuple = detect_language(transcribed_text)
                language = lang_tuple[0] if isinstance(lang_tuple, tuple) else "English"
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
            "Arre Ajay, I couldn't catch that voice message. Try typing it out?")
    finally:
        try:
            os.unlink(voice_path)
        except Exception:
            pass


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
                from src.core.mood_detector import detect_mood
                from src.core.language_detector import detect_language
                mood_res = detect_mood(user_text)
                mood = mood_res.mood if hasattr(mood_res, "mood") else str(mood_res)
                lang_tuple = detect_language(user_text)
                language = lang_tuple[0] if isinstance(lang_tuple, tuple) else "English"
                
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
                from src.core.mood_detector import detect_mood
                from src.core.language_detector import detect_language
                mood_res = detect_mood(user_text)
                mood = mood_res.mood if hasattr(mood_res, "mood") else str(mood_res)
                lang_tuple = detect_language(user_text)
                language = lang_tuple[0] if isinstance(lang_tuple, tuple) else "English"
                
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


# ─── Render Health + Trigger Server ──────────────────────────────────────────

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
        telebot.types.BotCommand("/syscheck", "Run full system test"),
        telebot.types.BotCommand("/shell",    "Run shell command with confirmation"),
        telebot.types.BotCommand("/read",     "Read any file (/read src/core/ai_router.py)"),
        telebot.types.BotCommand("/gitpull",  "Pull latest code from GitHub"),
        telebot.types.BotCommand("/restart",  "Restart Aisha bot process"),
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
            _schedule.every().day.at("08:00").do(_autonomous_loop.run_morning_checkin)
            _schedule.every().day.at("21:00").do(_autonomous_loop.run_evening_wrapup)
            _schedule.every().day.at("21:30").do(_autonomous_loop.run_daily_digest)
            _schedule.every().day.at("03:00").do(_autonomous_loop.run_memory_consolidation)
            _schedule.every().sunday.at("19:00").do(_autonomous_loop.run_weekly_digest)
            _schedule.every().sunday.at("03:00").do(_autonomous_loop.run_memory_cleanup)
            _schedule.every(5).minutes.do(_autonomous_loop.run_task_reminder_poll)
            _schedule.every(3).hours.do(_autonomous_loop.run_inactivity_check)
            _schedule.every(4).hours.do(_autonomous_loop.run_studio_session)
            _schedule.every().day.at("02:00").do(run_self_improvement, _autonomous_loop)
            _schedule.every().day.at("04:00").do(_autonomous_loop.run_temp_cleanup)
            _schedule.every().day.at("09:00").do(_autonomous_loop.run_key_expiry_check)
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
    
    from src.core.self_improvement import merge_github_pr, get_pr_number_from_url
    pr_number = get_pr_number_from_url(pr_url) if pr_url else 0
    
    if pr_number and merge_github_pr(pr_number):
        bot.edit_message_text(
            f"✅ Successfully deployed: *{skill_name}*!\n"
            "The PR has been merged. My brain is now more powerful! 💜",
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
