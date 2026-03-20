# Telegram Power Commands Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Claude Code-level power commands to Aisha's Telegram bot so Ajay can fully control, monitor, and operate the Aisha system from Telegram without needing a laptop.

**Architecture:** Add 8 new command handlers to `src/telegram/bot.py`. Shell commands use an inline keyboard confirmation step (Option B) — Ajay sees the command and taps [Run ✅] or [Cancel ❌] before execution. All handlers are protected by the existing `is_ajay()` guard.

**Tech Stack:** Python, telebot (pyTelegramBotAPI), subprocess, pathlib — all already in project

---

## Chunk 1: Test scaffolding + /upload command

### Task 1: Write failing tests for /upload command

**Files:**
- Create: `scripts/test_telegram_commands.py`

- [ ] **Step 1: Create test file with /upload test**

```python
# scripts/test_telegram_commands.py
"""
Tests for Telegram power commands.
Run: cd E:/VSCode/Aisha && python scripts/test_telegram_commands.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_upload_command_exists():
    """Verify /upload handler is registered in bot.py."""
    with open("src/telegram/bot.py") as f:
        content = f.read()
    assert "commands=[\"upload\"]" in content or 'commands=["upload"]' in content, \
        "/upload command not found in bot.py"
    print("✅ /upload command exists")

def test_queue_command_exists():
    assert 'commands=["queue"]' in open("src/telegram/bot.py").read() or \
           "commands=['queue']" in open("src/telegram/bot.py").read(), \
        "/queue command not found"
    print("✅ /queue command exists")

def test_logs_command_exists():
    content = open("src/telegram/bot.py").read()
    assert '"logs"' in content, "/logs command not found"
    print("✅ /logs command exists")

def test_shell_command_exists():
    content = open("src/telegram/bot.py").read()
    assert '"shell"' in content, "/shell command not found"
    print("✅ /shell command exists")

def test_shell_confirmation_callback_exists():
    content = open("src/telegram/bot.py").read()
    assert "shell_confirm_" in content, "Shell confirmation callback not found"
    print("✅ Shell confirmation callback exists")

def test_read_command_exists():
    content = open("src/telegram/bot.py").read()
    assert '"read"' in content or "commands=[\"read\"]" in content, "/read command not found"
    print("✅ /read command exists")

def test_gitpull_command_exists():
    content = open("src/telegram/bot.py").read()
    assert '"gitpull"' in content, "/gitpull command not found"
    print("✅ /gitpull command exists")

def test_restart_command_exists():
    content = open("src/telegram/bot.py").read()
    assert '"restart"' in content, "/restart command not found"
    print("✅ /restart command exists")

def test_syscheck_command_exists():
    content = open("src/telegram/bot.py").read()
    assert '"syscheck"' in content, "/syscheck command not found"
    print("✅ /syscheck command exists")

if __name__ == "__main__":
    tests = [
        test_upload_command_exists,
        test_queue_command_exists,
        test_logs_command_exists,
        test_shell_command_exists,
        test_shell_confirmation_callback_exists,
        test_read_command_exists,
        test_gitpull_command_exists,
        test_restart_command_exists,
        test_syscheck_command_exists,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test.__name__} ERROR: {e}")
            failed += 1
    print(f"\n{'='*40}")
    print(f"Results: {passed}/{passed+failed} passed")
    if failed > 0:
        sys.exit(1)
```

- [ ] **Step 2: Run tests to confirm they ALL fail (expected)**

```bash
cd E:/VSCode/Aisha && python scripts/test_telegram_commands.py
```

Expected output: All 9 tests fail with "command not found" AssertionErrors.

---

### Task 2: Implement /upload command

**Files:**
- Modify: `src/telegram/bot.py` — add after the `/studio` command handler (line ~351)

- [ ] **Step 3: Add /upload command handler to bot.py**

Find the line `@bot.message_handler(commands=["studio"])` in bot.py and add the following BEFORE it:

```python
@bot.message_handler(commands=["upload"])
def cmd_upload(message):
    """Upload the latest produced content to YouTube."""
    if not is_ajay(message): return unauthorized_response(message)
    channel = message.text.replace("/upload", "").strip()
    bot.send_message(message.chat.id, "🎬 Checking for latest produced content...", parse_mode="Markdown")
    try:
        from supabase import create_client
        db = create_client(SUPABASE_URL, SUPABASE_KEY)
        # Find latest completed job pending upload
        query = db.table("content_queue") \
                  .select("*") \
                  .eq("status", "completed") \
                  .is_("youtube_status", "null") \
                  .order("created_at", desc=True) \
                  .limit(1)
        if channel:
            query = db.table("content_queue") \
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
        import subprocess
        project_root = str(Path(__file__).parent.parent.parent)
        result = subprocess.run(
            ["python", "-c",
             f"import sys; sys.path.insert(0,'{project_root}'); "
             f"from src.core.social_media_engine import SocialMediaEngine; "
             f"sm = SocialMediaEngine(); "
             f"r = sm.upload_youtube_video('{job_id}'); "
             f"print('SUCCESS:' + str(r))"],
            cwd=project_root, capture_output=True, text=True, timeout=300
        )
        if "SUCCESS:" in result.stdout:
            bot.send_message(message.chat.id,
                f"✅ *Uploaded to YouTube!*\n"
                f"Channel: *{ch}*\n"
                f"Check YouTube Studio for the video. 🎉",
                parse_mode="Markdown")
        else:
            err = (result.stderr or result.stdout)[:500]
            bot.send_message(message.chat.id,
                f"❌ Upload failed:\n```{err}```",
                parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Upload error: {e}")
```

- [ ] **Step 4: Run tests — upload test should pass now**

```bash
cd E:/VSCode/Aisha && python scripts/test_telegram_commands.py
```

Expected: 1/9 passed (upload), 8 still failing.

- [ ] **Step 5: Commit**

```bash
cd E:/VSCode/Aisha && git add src/telegram/bot.py scripts/test_telegram_commands.py && git commit -m "feat(telegram): add /upload command for YouTube publishing"
```

---

## Chunk 2: /queue, /logs, /syscheck commands

### Task 3: Implement /queue command

**Files:**
- Modify: `src/telegram/bot.py`

- [ ] **Step 6: Add /queue handler after /upload**

```python
@bot.message_handler(commands=["queue"])
def cmd_queue(message):
    """Show content pipeline queue status."""
    if not is_ajay(message): return unauthorized_response(message)
    try:
        from supabase import create_client
        db = create_client(SUPABASE_URL, SUPABASE_KEY)
        rows = db.table("content_queue") \
                 .select("id, channel, status, created_at, youtube_status") \
                 .order("created_at", desc=True) \
                 .limit(8) \
                 .execute().data or []
        if not rows:
            bot.send_message(message.chat.id, "📭 Content queue is empty. Use `/produce <channel>` to start!")
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
```

### Task 4: Implement /logs command

- [ ] **Step 7: Add /logs handler**

```python
@bot.message_handler(commands=["logs"])
def cmd_logs(message):
    """Show last N lines from aisha.log."""
    if not is_ajay(message): return unauthorized_response(message)
    text = message.text.replace("/logs", "").strip()
    try:
        n = int(text) if text and text.isdigit() else 30
        n = min(n, 100)  # cap at 100 lines
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
        # Truncate to Telegram's 4096 char limit
        if len(log_text) > 3800:
            log_text = "...(truncated)\n" + log_text[-3800:]
        bot.send_message(message.chat.id,
            f"📋 *Last {n} lines of aisha.log:*\n```\n{log_text}\n```",
            parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Logs error: {e}")
```

### Task 5: Implement /syscheck command

- [ ] **Step 8: Add /syscheck handler**

```python
@bot.message_handler(commands=["syscheck"])
def cmd_syscheck(message):
    """Run full system test and report results."""
    if not is_ajay(message): return unauthorized_response(message)
    bot.send_message(message.chat.id, "🔬 Running system tests... (30-60 seconds)")
    try:
        import subprocess
        project_root = str(Path(__file__).parent.parent.parent)
        result = subprocess.run(
            ["python", "scripts/test_all_systems.py"],
            cwd=project_root, capture_output=True, text=True, timeout=180
        )
        output = result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout
        passed = output.count("✅")
        failed = output.count("❌")
        total = passed + failed
        status = "✅ ALL PASSING" if failed == 0 else f"⚠️ {failed} FAILING"
        bot.send_message(message.chat.id,
            f"🔬 *System Check: {status}*\n"
            f"Results: {passed}/{total} passed\n\n"
            f"```\n{output[-2000:]}\n```",
            parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ System check error: {e}")
```

- [ ] **Step 9: Run tests — queue, logs, syscheck should pass**

```bash
cd E:/VSCode/Aisha && python scripts/test_telegram_commands.py
```

Expected: 4/9 passed, 5 still failing.

- [ ] **Step 10: Commit**

```bash
cd E:/VSCode/Aisha && git add src/telegram/bot.py && git commit -m "feat(telegram): add /queue, /logs, /syscheck commands"
```

---

## Chunk 3: /shell with confirmation, /read, /gitpull, /restart

### Task 6: Implement /shell with Option B (confirmation-required)

**Files:**
- Modify: `src/telegram/bot.py`

- [ ] **Step 11: Add pending shell commands dict + /shell handler**

Add this dict near the top of bot.py, after `VOICE_MODE_ENABLED = True`:

```python
# ─── Pending shell commands (for confirmation) ────────────────────────────────
_pending_shell: dict = {}  # message_id → command string
```

Then add these handlers:

```python
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
    # Show confirmation
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("✅ Run", callback_data=f"shell_confirm_{message.message_id}"),
        types.InlineKeyboardButton("❌ Cancel", callback_data=f"shell_cancel_{message.message_id}")
    )
    sent = bot.send_message(message.chat.id,
        f"⚡ *Run this command?*\n```\n{cmd}\n```",
        parse_mode="Markdown",
        reply_markup=keyboard)
    _pending_shell[message.message_id] = cmd


@bot.callback_query_handler(func=lambda c: c.data.startswith("shell_confirm_") or c.data.startswith("shell_cancel_"))
def handle_shell_callback(call):
    if not is_ajay(call.message): return
    parts = call.data.split("_", 2)
    action = parts[1]  # "confirm" or "cancel"
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
        return_code = result.returncode
        icon = "✅" if return_code == 0 else "⚠️"
        bot.send_message(call.message.chat.id,
            f"{icon} *Exit code: {return_code}*\n```\n{output}\n```",
            parse_mode="Markdown")
    except subprocess.TimeoutExpired:
        bot.send_message(call.message.chat.id, "⏰ Command timed out after 120 seconds.")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Error: {e}")
```

### Task 7: Implement /read command

- [ ] **Step 12: Add /read handler**

```python
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
```

### Task 8: Implement /gitpull and /restart

- [ ] **Step 13: Add /gitpull handler**

```python
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
```

- [ ] **Step 14: Run tests — all 9 should pass**

```bash
cd E:/VSCode/Aisha && python scripts/test_telegram_commands.py
```

Expected: 9/9 passed ✅

- [ ] **Step 15: Commit**

```bash
cd E:/VSCode/Aisha && git add src/telegram/bot.py && git commit -m "feat(telegram): add /shell (with confirmation), /read, /gitpull, /restart"
```

---

## Chunk 4: Update /help + register BotCommands

### Task 9: Update /help and register all new commands with BotFather

**Files:**
- Modify: `src/telegram/bot.py` — update `cmd_help()` and `bot.set_my_commands()`

- [ ] **Step 16: Update the /help text**

In `cmd_help()`, add to the existing help text after the `🎬 *YouTube Studio:*` section:

```python
        "⚡ *Power Commands (Claude Code Level):*\n"
        "/upload [channel] — Upload latest content to YouTube\n"
        "/queue — See content pipeline jobs\n"
        "/logs [n] — View last N lines of aisha.log\n"
        "/syscheck — Run full system test\n"
        "/shell <cmd> — Run shell command (with confirmation)\n"
        "/read <file> — Read any file\n"
        "/gitpull — Pull latest code from GitHub\n"
        "/restart — Restart Aisha bot\n\n"
```

- [ ] **Step 17: Add new commands to bot.set_my_commands() at bottom of file**

In the `if __name__ == "__main__":` block, add to `bot.set_my_commands([...])`:

```python
        telebot.types.BotCommand("/upload",   "Upload latest content to YouTube"),
        telebot.types.BotCommand("/queue",    "View content pipeline queue"),
        telebot.types.BotCommand("/logs",     "View last 30 log lines (/logs 50)"),
        telebot.types.BotCommand("/syscheck", "Run full system test"),
        telebot.types.BotCommand("/shell",    "Run shell command with confirmation"),
        telebot.types.BotCommand("/read",     "Read any file (/read src/core/ai_router.py)"),
        telebot.types.BotCommand("/gitpull",  "Pull latest code from GitHub"),
        telebot.types.BotCommand("/restart",  "Restart Aisha bot process"),
```

- [ ] **Step 18: Run final test suite**

```bash
cd E:/VSCode/Aisha && python scripts/test_telegram_commands.py
```

Expected: 9/9 passed ✅

- [ ] **Step 19: Syntax check**

```bash
cd E:/VSCode/Aisha && python -c "import ast; ast.parse(open('src/telegram/bot.py').read()); print('✅ Syntax OK')"
```

- [ ] **Step 20: Final commit**

```bash
cd E:/VSCode/Aisha && git add src/telegram/bot.py && git commit -m "feat(telegram): update /help + register power commands with BotFather"
```

---

## Summary

After all 4 chunks:

| Command | What it does |
|---|---|
| `/upload [channel]` | Upload last completed content job to YouTube |
| `/queue` | Show last 8 content pipeline jobs with status |
| `/logs [n]` | Tail last N lines of aisha.log (default 30) |
| `/syscheck` | Run `scripts/test_all_systems.py` and report |
| `/shell <cmd>` | Show command → [Run ✅] [Cancel ❌] → execute |
| `/read <file>` | Read any file from project root, send contents |
| `/gitpull` | `git pull origin main` and report result |
| `/restart` | Self-restart bot process |

**Verification command:** `cd E:/VSCode/Aisha && python scripts/test_telegram_commands.py`
**Expected:** 9/9 passed
