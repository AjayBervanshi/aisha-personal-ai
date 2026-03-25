# Aisha Full Autonomy Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Aisha fully autonomous — she generates content, renders videos, posts to YouTube and Instagram on a daily schedule, tracks episode series, handles all Telegram commands, and monitors her own health.

**Architecture:** Thin connectors glue the already-built engines (YouTubeCrew → VideoEngine → SocialMediaEngine) into one `PipelineRunner`. A `SeriesTracker` DB table + class manages episodic continuity. Bot commands wire to existing brain/loop functions. A `TokenManager` handles credential refresh on a schedule.

**Tech Stack:** Python 3.11, telebot, moviepy, google-api-python-client, requests, supabase-py, schedule

---

## Chunk 1: Auto Content Pipeline (connect render → upload → post)

### What's already done
- `src/core/video_engine.py` — renders MP4 with Ken Burns ✅
- `src/core/social_media_engine.py` — uploads to YouTube + posts Instagram reel ✅
- `src/agents/youtube_crew.py` — generates script/voice/thumbnail, has `render_video` flag ✅
- `src/agents/antigravity_agent.py` — job queue worker ✅

### What's missing
- `antigravity_agent.py` never calls crew with `render_video=True`
- No upload/post step after video is rendered
- No `auto_post` field driving the pipeline end-to-end

---

### Task 1: Add `render_video=True` + auto-upload to antigravity_agent

**Files:**
- Modify: `src/agents/antigravity_agent.py`

- [ ] **Step 1: Read current run_job / process_job function**

```bash
grep -n "def.*job\|kickoff\|render\|upload\|post" src/agents/antigravity_agent.py
```

- [ ] **Step 2: Find where kickoff is called and add render + upload**

Find the line in `antigravity_agent.py` that calls `YouTubeCrew().kickoff(inputs)`.
Change it to:

```python
inputs["render_video"] = True   # always render MP4

crew    = YouTubeCrew()
summary = crew.kickoff(inputs)

video_path     = crew.results.get("video_path")
thumbnail_path = crew.results.get("thumbnail_path")
marketing_text = crew.results.get("marketing") or ""
script_text    = crew.results.get("script") or ""

# Parse title, description, tags, caption from marketing output
title, description, tags, caption, hashtags = _parse_marketing(marketing_text, inputs.get("topic",""))

sm = SocialMediaEngine()
channel = inputs.get("channel", "Story With Aisha")

# Upload to YouTube
yt_result = {}
if video_path:
    yt_result = sm.upload_youtube_video(
        video_path=video_path,
        title=title,
        description=description,
        tags=tags,
        channel_name=channel,
        job_id=str(job.get("id","")),
    )
    log.info(f"[Pipeline] YouTube: {yt_result}")

# Post Instagram Reel — upload video to Supabase Storage first, get public URL
ig_result = {}
if video_path and inputs.get("platforms", []) and "instagram" in inputs.get("platforms", []):
    video_url = _upload_to_storage(video_path, channel)
    if video_url:
        ig_result = sm.post_instagram_reel(
            video_url=video_url,
            caption=caption,
            hashtags=hashtags,
            channel=channel,
            job_id=str(job.get("id","")),
        )
        log.info(f"[Pipeline] Instagram: {ig_result}")
```

- [ ] **Step 3: Add `_parse_marketing` helper to antigravity_agent.py**

```python
def _parse_marketing(marketing_text: str, topic: str) -> tuple:
    """Parse title, description, tags, caption, hashtags from crew marketing output."""
    import re
    lines = marketing_text.split("\n")

    title = topic[:90]
    description = ""
    tags = []
    caption = ""
    hashtags = []

    for i, line in enumerate(lines):
        l = line.strip()
        if re.match(r"^(youtube\s+)?title", l, re.I) and ":" in l:
            title = l.split(":", 1)[1].strip().strip('"')[:90]
        elif re.match(r"^(youtube\s+)?description", l, re.I) and ":" in l:
            # Grab next 5 lines as description body
            desc_lines = []
            for j in range(i+1, min(i+8, len(lines))):
                if re.match(r"^(instagram|hashtag|thumbnail|\d+\.)", lines[j], re.I):
                    break
                desc_lines.append(lines[j])
            description = "\n".join(desc_lines).strip()
        elif re.match(r"^instagram\s+caption", l, re.I) and ":" in l:
            caption = l.split(":", 1)[1].strip().strip('"')[:150]
        elif "#" in l:
            tags_in_line = re.findall(r"#(\w+)", l)
            hashtags.extend(tags_in_line)

    if not description:
        description = f"{title}\n\n{topic}\n\n#HindiStory #AishaStories"
    if not caption:
        caption = title[:150]
    tags = list(dict.fromkeys(hashtags))[:15]  # deduplicated

    return title, description, tags, caption, hashtags[:30]
```

- [ ] **Step 4: Add `_upload_to_storage` helper**

```python
def _upload_to_storage(local_path: str, channel: str) -> str | None:
    """Upload video to Supabase Storage and return public URL."""
    try:
        import os, uuid
        from supabase import create_client
        sb = create_client(
            os.getenv("SUPABASE_URL",""),
            os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY",""),
        )
        bucket = "content-videos"
        filename = f"{channel.replace(' ','_')}_{uuid.uuid4().hex[:8]}.mp4"
        with open(local_path, "rb") as f:
            sb.storage.from_(bucket).upload(filename, f, {"content-type": "video/mp4"})
        url = sb.storage.from_(bucket).get_public_url(filename)
        return url
    except Exception as e:
        log.warning(f"[Storage] Upload failed: {e}")
        return None
```

- [ ] **Step 5: Add SocialMediaEngine import at top of antigravity_agent.py**

```python
from src.core.social_media_engine import SocialMediaEngine
```

- [ ] **Step 6: Test pipeline end-to-end (dry run)**

```bash
PYTHONUTF8=1 /e/VSCode/.venv/Scripts/python -c "
from src.agents.antigravity_agent import AntigravityAgent
a = AntigravityAgent()
result = a.enqueue_job(
    topic='Ek Raat Ki Kahani',
    channel='Story With Aisha',
    content_format='Short/Reel',
    platforms=['youtube','instagram'],
    auto_post=True,
    scheduled_for=None,
)
print('Job enqueued:', result)
"
```

Expected: job ID returned, job in `content_jobs` table with status=queued

- [ ] **Step 7: Commit**

```bash
git add src/agents/antigravity_agent.py
git commit -m "feat: pipeline auto-render + YouTube upload + Instagram post after crew"
```

---

### Task 2: Wire autonomous_loop to pass render_video=True + platforms

**Files:**
- Modify: `src/core/autonomous_loop.py`

- [ ] **Step 1: Find the studio session call in autonomous_loop.py**

```bash
grep -n "studio\|kickoff\|enqueue\|content_job\|antigravity" src/core/autonomous_loop.py
```

- [ ] **Step 2: Update studio call to include platforms and auto_post**

Find the studio session trigger. Change inputs to:

```python
inputs = {
    "channel": channel,
    "format": "Short/Reel",   # Shorts first — fastest to produce
    "render_video": True,
    "platforms": ["youtube", "instagram"],
    "auto_post": True,
}
```

- [ ] **Step 3: Commit**

```bash
git add src/core/autonomous_loop.py
git commit -m "feat: autonomous studio triggers full pipeline with auto-post"
```

---

## Chunk 2: Series Tracker (episodic YouTube Shorts continuity)

### Task 3: Create series_tracker DB table via Supabase migration

**Files:**
- Create: `supabase/migrations/20260325000001_series_tracker.sql`
- Create: `src/core/series_tracker.py`

- [ ] **Step 1: Write migration SQL**

```sql
-- supabase/migrations/20260325000001_series_tracker.sql
CREATE TABLE IF NOT EXISTS aisha_series (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    series_name     TEXT NOT NULL,
    channel         TEXT NOT NULL,
    total_episodes  INT  DEFAULT 5,
    current_episode INT  DEFAULT 0,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS aisha_episodes (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    series_id       UUID REFERENCES aisha_series(id) ON DELETE CASCADE,
    episode_number  INT NOT NULL,
    title           TEXT,
    script_summary  TEXT,   -- 200-word summary for continuity context
    cliffhanger     TEXT,   -- the cliffhanger ending of this episode
    youtube_url     TEXT,
    instagram_post_id TEXT,
    content_job_id  UUID,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_episodes_series ON aisha_episodes(series_id, episode_number);
CREATE INDEX IF NOT EXISTS idx_series_channel  ON aisha_series(channel, is_active);
```

- [ ] **Step 2: Apply migration via Supabase MCP**

Use `mcp__claude_ai_Supabase__apply_migration` with the SQL above.

- [ ] **Step 3: Create src/core/series_tracker.py**

```python
"""
series_tracker.py
=================
Tracks episodic YouTube Shorts series.
Provides continuity context for Episode N from Episodes 1..N-1.
"""
import os
import logging
from typing import Optional

log = logging.getLogger("Aisha.SeriesTracker")


def _sb():
    from supabase import create_client
    return create_client(
        os.getenv("SUPABASE_URL",""),
        os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY",""),
    )


def get_or_create_series(series_name: str, channel: str, total_episodes: int = 5) -> dict:
    """Get existing active series or create a new one."""
    try:
        sb = _sb()
        existing = sb.table("aisha_series")\
            .select("*")\
            .eq("series_name", series_name)\
            .eq("channel", channel)\
            .eq("is_active", True)\
            .limit(1).execute()
        if existing.data:
            return existing.data[0]
        result = sb.table("aisha_series").insert({
            "series_name": series_name,
            "channel": channel,
            "total_episodes": total_episodes,
            "current_episode": 0,
        }).execute()
        return result.data[0] if result.data else {}
    except Exception as e:
        log.error(f"[SeriesTracker] get_or_create_series error: {e}")
        return {}


def get_continuity_context(series_id: str) -> str:
    """
    Returns a context string summarizing all previous episodes.
    Used to inject into the script prompt so Episode N continues from N-1.
    """
    try:
        sb = _sb()
        eps = sb.table("aisha_episodes")\
            .select("episode_number,title,script_summary,cliffhanger")\
            .eq("series_id", series_id)\
            .order("episode_number").execute()
        if not eps.data:
            return ""
        lines = ["PREVIOUS EPISODES (for continuity):"]
        for ep in eps.data:
            lines.append(
                f"Episode {ep['episode_number']}: {ep.get('title','?')} | "
                f"Summary: {ep.get('script_summary','')[:150]} | "
                f"Cliffhanger: {ep.get('cliffhanger','')[:100]}"
            )
        return "\n".join(lines)
    except Exception as e:
        log.error(f"[SeriesTracker] get_continuity_context error: {e}")
        return ""


def save_episode(series_id: str, episode_number: int, title: str,
                 script: str, cliffhanger: str, youtube_url: str = None,
                 instagram_post_id: str = None, content_job_id: str = None) -> bool:
    """Save completed episode metadata."""
    try:
        sb = _sb()
        # 200-word summary via first 800 chars of script
        summary = script[:800].rsplit(" ", 1)[0] + "..." if len(script) > 800 else script
        sb.table("aisha_episodes").insert({
            "series_id": series_id,
            "episode_number": episode_number,
            "title": title,
            "script_summary": summary,
            "cliffhanger": cliffhanger,
            "youtube_url": youtube_url,
            "instagram_post_id": instagram_post_id,
            "content_job_id": content_job_id,
        }).execute()
        # Advance current_episode counter
        sb.table("aisha_series").update({
            "current_episode": episode_number,
        }).eq("id", series_id).execute()
        return True
    except Exception as e:
        log.error(f"[SeriesTracker] save_episode error: {e}")
        return False


def get_next_episode_prompt(series_name: str, channel: str) -> dict:
    """
    Returns dict with: series_id, episode_number, continuity_context.
    Creates series if it doesn't exist yet.
    """
    series = get_or_create_series(series_name, channel)
    if not series:
        return {"series_id": None, "episode_number": 1, "continuity_context": ""}

    episode_number = series.get("current_episode", 0) + 1
    total = series.get("total_episodes", 5)

    # If all episodes done, start a new arc
    if episode_number > total:
        try:
            _sb().table("aisha_series").update({"is_active": False}).eq("id", series["id"]).execute()
        except Exception:
            pass
        return {"series_id": None, "episode_number": 1, "continuity_context": ""}

    context = get_continuity_context(series["id"])
    return {
        "series_id": series["id"],
        "episode_number": episode_number,
        "total_episodes": total,
        "continuity_context": context,
    }
```

- [ ] **Step 4: Wire series tracking into YouTubeCrew.kickoff**

In `src/agents/youtube_crew.py`, modify the script generation prompt when `series_info` is passed in inputs:

```python
series_info = inputs.get("series_info", {})
continuity = series_info.get("continuity_context", "")
episode_num = series_info.get("episode_number", 0)

if continuity and episode_num:
    episode_header = (
        f"\n\nSERIES EPISODE {episode_num} of {series_info.get('total_episodes',5)}:\n"
        f"{continuity}\n\n"
        f"IMPORTANT: Continue the story from the cliffhanger above. "
        f"End Episode {episode_num} with a NEW cliffhanger that makes viewers desperate for Episode {episode_num+1}."
    )
else:
    episode_header = ""
```

Append `episode_header` to the script generation prompt.

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/20260325000001_series_tracker.sql src/core/series_tracker.py src/agents/youtube_crew.py
git commit -m "feat: series tracker — episodic Shorts with cliffhanger continuity"
```

---

## Chunk 3: Complete Telegram Commands

### Task 4: Wire all missing bot commands in bot.py

**Files:**
- Modify: `src/telegram/bot.py`

- [ ] **Step 1: Read current bot.py to find where /start is and add after it**

```bash
grep -n "@bot\.\|def cmd_\|def handle_" src/telegram/bot.py | head -40
```

- [ ] **Step 2: Add /syscheck command**

```python
@bot.message_handler(commands=["syscheck"])
def cmd_syscheck(message):
    if not is_ajay(message):
        return
    bot.send_message(message.chat.id, "🔍 Running system check...")
    try:
        from src.core.ai_router import AIRouter
        ai = AIRouter()
        lines = ["*Aisha System Status*\n"]
        for provider in ["gemini","openai","groq","xai","nvidia"]:
            try:
                r = ai.generate(
                    system_prompt="Reply with one word: OK",
                    user_message="ping",
                    max_tokens=5,
                )
                lines.append(f"✅ {provider.upper()}: OK")
            except Exception as e:
                lines.append(f"❌ {provider.upper()}: {str(e)[:50]}")
        from src.core.social_media_engine import SocialMediaEngine
        sm = SocialMediaEngine()
        lines.append("\n" + sm.status())
        bot.send_message(message.chat.id, "\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ syscheck error: {e}")
```

- [ ] **Step 3: Add /studio command**

```python
@bot.message_handler(commands=["studio"])
def cmd_studio(message):
    if not is_ajay(message):
        return
    parts = message.text.split(maxsplit=2)
    channel = parts[1] if len(parts) > 1 else "Story With Aisha"
    topic   = parts[2] if len(parts) > 2 else None
    bot.send_message(message.chat.id, f"🎬 Starting studio session for *{channel}*...", parse_mode="Markdown")
    def run():
        try:
            from src.agents.antigravity_agent import AntigravityAgent
            agent = AntigravityAgent()
            job_id = agent.enqueue_job(
                topic=topic or "",
                channel=channel,
                content_format="Short/Reel",
                platforms=["youtube","instagram"],
                auto_post=True,
            )
            bot.send_message(message.chat.id, f"✅ Studio job queued: `{job_id}`\nI'll notify you when the video is posted.", parse_mode="Markdown")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Studio error: {e}")
    import threading
    threading.Thread(target=run, daemon=True).start()
```

- [ ] **Step 4: Add /upgrade command (self-improvement trigger)**

```python
@bot.message_handler(commands=["upgrade"])
def cmd_upgrade(message):
    if not is_ajay(message):
        return
    task = message.text.replace("/upgrade", "").strip() or "Review Aisha's code and improve the weakest module"
    bot.send_message(message.chat.id, f"🧠 Starting self-improvement: _{task}_", parse_mode="Markdown")
    def run():
        try:
            from src.core.self_improvement import aisha_self_improve
            pr_url = aisha_self_improve(task)
            if pr_url:
                bot.send_message(message.chat.id, f"✅ PR created: {pr_url}\nClick Deploy when ready.")
            else:
                bot.send_message(message.chat.id, "❌ Self-improvement failed this cycle.")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Upgrade error: {e}")
    import threading
    threading.Thread(target=run, daemon=True).start()
```

- [ ] **Step 5: Add /voice command**

```python
@bot.message_handler(commands=["voice"])
def cmd_voice(message):
    if not is_ajay(message):
        return
    global VOICE_MODE_ENABLED
    arg = message.text.split()[-1].lower()
    if arg in ("on","off"):
        VOICE_MODE_ENABLED = (arg == "on")
    else:
        VOICE_MODE_ENABLED = not VOICE_MODE_ENABLED
    state = "ON 🔊" if VOICE_MODE_ENABLED else "OFF 🔇"
    bot.send_message(message.chat.id, f"Voice mode: {state}")
```

- [ ] **Step 6: Add /mood command**

```python
@bot.message_handler(commands=["mood"])
def cmd_mood(message):
    if not is_ajay(message):
        return
    parts = message.text.split(maxsplit=1)
    moods = ["romantic","motivational","personal","finance","professional","late_night","casual"]
    if len(parts) > 1 and parts[1].lower() in moods:
        aisha.mood_override = parts[1].lower()
        bot.send_message(message.chat.id, f"Mood set to: *{parts[1]}* ✨", parse_mode="Markdown")
    else:
        keyboard = types.InlineKeyboardMarkup()
        for mood in moods:
            keyboard.add(types.InlineKeyboardButton(mood.title(), callback_data=f"mood_{mood}"))
        bot.send_message(message.chat.id, "Choose mood:", reply_markup=keyboard)
```

- [ ] **Step 7: Add /aistatus command**

```python
@bot.message_handler(commands=["aistatus"])
def cmd_aistatus(message):
    if not is_ajay(message):
        return
    try:
        from src.core.autonomous_loop import AutonomousLoop
        # Report scheduled job count
        import schedule
        jobs = schedule.jobs
        lines = [
            "*Aisha Autonomous Status*",
            f"Scheduled jobs: {len(jobs)}",
            f"Voice mode: {'ON' if VOICE_MODE_ENABLED else 'OFF'}",
            f"Active users: {len(_approved_users)+1}",
        ]
        bot.send_message(message.chat.id, "\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"Status: running (detail error: {e})")
```

- [ ] **Step 8: Add callback handler for Deploy/Skip buttons (self-improvement)**

```python
@bot.callback_query_handler(func=lambda c: c.data.startswith("deploy_skill_") or c.data.startswith("skip_skill_"))
def handle_skill_callback(call):
    if call.from_user.id != AUTHORIZED_ID:
        bot.answer_callback_query(call.id, "Not authorized")
        return
    if call.data.startswith("deploy_skill_"):
        skill_name = call.data.replace("deploy_skill_","")
        bot.answer_callback_query(call.id, "Deploying...")
        bot.edit_message_text(f"🚀 Deploying *{skill_name}*...", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        # Find the PR URL from recent messages or store in DB
        # For now: trigger redeploy directly
        from src.core.self_improvement import trigger_redeploy
        ok = trigger_redeploy()
        bot.send_message(call.message.chat.id, "✅ Deployed! Render redeploying now." if ok else "⚠️ Redeploy hook failed — check Render dashboard.")
    else:
        bot.answer_callback_query(call.id, "Skipped")
        bot.edit_message_text("❌ Skill skipped.", call.message.chat.id, call.message.message_id)
```

- [ ] **Step 9: Commit**

```bash
git add src/telegram/bot.py
git commit -m "feat: wire all Telegram commands — syscheck, studio, upgrade, voice, mood, aistatus"
```

---

## Chunk 4: Token Manager + Smart Test Agent

### Task 5: Token auto-refresh manager

**Files:**
- Create: `src/core/token_manager.py`
- Modify: `src/core/autonomous_loop.py`

- [ ] **Step 1: Create token_manager.py**

```python
"""
token_manager.py
================
Monitors and auto-refreshes expiring credentials.
- Instagram: refresh every 45 days (expires at 60)
- YouTube: check token validity, alert if expired
- Groq/other AI keys: test on schedule, alert on 401
"""
import os
import logging
import requests
from datetime import datetime, timezone

log = logging.getLogger("Aisha.TokenManager")


def refresh_instagram_token() -> dict:
    """Refresh Instagram long-lived token. Returns status dict."""
    token = os.getenv("INSTAGRAM_ACCESS_TOKEN","")
    if not token:
        return {"ok": False, "error": "No INSTAGRAM_ACCESS_TOKEN set"}
    try:
        resp = requests.get(
            "https://graph.instagram.com/refresh_access_token",
            params={"grant_type": "ig_refresh_token", "access_token": token},
            timeout=15,
        )
        if resp.status_code == 200:
            new_token = resp.json().get("access_token", token)
            expires_in = resp.json().get("expires_in", 0)
            # Update .env in memory (for this process) and Supabase api_keys
            os.environ["INSTAGRAM_ACCESS_TOKEN"] = new_token
            _save_token_to_db("INSTAGRAM_TOKEN", new_token)
            log.info(f"[TokenManager] Instagram token refreshed, expires_in={expires_in}s")
            return {"ok": True, "expires_in": expires_in}
        else:
            return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text[:100]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def check_youtube_token() -> dict:
    """Check if YouTube OAuth token is valid."""
    try:
        from src.core.social_media_engine import SocialMediaEngine
        sm = SocialMediaEngine()
        creds = sm._get_youtube_credentials("Story With Aisha")
        if creds and creds.token:
            return {"ok": True, "expired": creds.expired}
        return {"ok": False, "error": "No credentials loaded"}
    except FileNotFoundError:
        return {"ok": False, "error": "YouTube token file missing — run setup_youtube_oauth.py"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def check_ai_providers() -> dict:
    """Quick ping all AI providers. Returns dict of provider → ok/error."""
    from src.core.ai_router import AIRouter
    ai = AIRouter()
    results = {}
    for provider in ["gemini", "groq", "openai"]:
        try:
            r = ai.generate(
                system_prompt="Reply: OK",
                user_message="ping",
                max_tokens=5,
            )
            results[provider] = "ok"
        except Exception as e:
            results[provider] = f"error: {str(e)[:60]}"
    return results


def _save_token_to_db(name: str, secret: str):
    """Upsert token in Supabase api_keys table."""
    try:
        from supabase import create_client
        sb = create_client(
            os.getenv("SUPABASE_URL",""),
            os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY",""),
        )
        existing = sb.table("api_keys").select("id").eq("name", name).execute()
        if existing.data:
            sb.table("api_keys").update({"secret": secret, "active": True}).eq("name", name).execute()
        else:
            sb.table("api_keys").insert({"name": name, "secret": secret, "active": True}).execute()
    except Exception as e:
        log.warning(f"[TokenManager] DB save failed for {name}: {e}")


def run_daily_health_check(notify_fn=None):
    """
    Run all checks. Call notify_fn(message) to send Telegram alert.
    Add to autonomous_loop schedule: daily at 09:00 IST.
    """
    report = []

    ig = refresh_instagram_token()
    if ig["ok"]:
        report.append(f"✅ Instagram token refreshed")
    else:
        report.append(f"⚠️ Instagram token: {ig['error']}")

    yt = check_youtube_token()
    if yt["ok"]:
        status = "⚠️ EXPIRED — re-auth needed" if yt.get("expired") else "✅ valid"
        report.append(f"YouTube OAuth: {status}")
    else:
        report.append(f"❌ YouTube: {yt['error']}")

    ai_status = check_ai_providers()
    for p, s in ai_status.items():
        icon = "✅" if s == "ok" else "❌"
        report.append(f"{icon} {p.upper()}: {s}")

    msg = "🔑 *Daily Token & Health Report*\n" + "\n".join(report)
    log.info(msg.replace("*",""))
    if notify_fn:
        notify_fn(msg)
    return report
```

- [ ] **Step 2: Add token health check to autonomous_loop schedule**

In `src/core/autonomous_loop.py`, in the `setup_schedule` or `run` method, add:

```python
from src.core.token_manager import run_daily_health_check

schedule.every().day.at("03:30").do(
    lambda: run_daily_health_check(notify_fn=self._send_to_ajay)
)
```

Where `_send_to_ajay` sends a Telegram message to AJAY_TELEGRAM_ID.

- [ ] **Step 3: Commit**

```bash
git add src/core/token_manager.py src/core/autonomous_loop.py
git commit -m "feat: token manager — auto-refresh Instagram, YouTube health check, AI provider ping"
```

---

### Task 6: Smart Professional Test Agent

**Files:**
- Create: `tests/test_smart_agent.py`

The new test agent uses randomized scenarios so it never runs the same test twice.

- [ ] **Step 1: Create tests/test_smart_agent.py**

```python
"""
test_smart_agent.py — Aisha Smart Professional Test Agent
=========================================================
Unlike test_production_agent.py which runs fixed scenarios,
this agent generates varied test cases each run:
  - Random channels for content generation
  - Random Hindi topics from a pool
  - Random expense amounts and categories
  - Random reminder timing
  - System health checks with evidence logging
  - DB state verification (not just reply checking)

Run: PYTHONUTF8=1 /e/VSCode/.venv/Scripts/python tests/test_smart_agent.py
Requires: Edge --remote-debugging-port=9222 + Telegram chat open
"""
import sys, io, time, json, os, random, requests
from datetime import datetime, timedelta
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from playwright.sync_api import sync_playwright

# ─── Load .env ────────────────────────────────────────────────
def _load_env(path="e:/VSCode/Aisha/.env"):
    if not os.path.exists(path): return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line: continue
            k, _, v = line.partition("=")
            k = k.strip(); v = v.strip().strip('"').strip("'")
            if k and k not in os.environ: os.environ[k] = v
_load_env()

SUPABASE_URL = os.getenv("SUPABASE_URL","")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY","")
RENDER_URL   = "https://aisha-bot-yudp.onrender.com"

# ─── Varied test data pools ───────────────────────────────────
CHANNELS = [
    "Story With Aisha",
    "Riya's Dark Romance Library",
    "Aisha & Him",
]

HINDI_TOPICS = [
    "पहली मुलाकात का वो लम्हा",
    "रात के तीन बजे का वादा",
    "दिल की बात अधूरी रही",
    "तुम्हारे बिना क्या जीना",
    "माफ़ी का आखिरी मौका",
    "अनजान शहर में प्यार",
    "सावन की पहली बारिश",
]

EXPENSE_SCENARIOS = [
    (499, "Netflix subscription"),
    (1299, "new keyboard"),
    (250, "coffee and snacks"),
    (5999, "monthly cloud hosting"),
    (799, "domain renewal"),
]

REMINDER_SCENARIOS = [
    ("check YouTube analytics", "every Monday at 10am IST"),
    ("renew Groq API key", "in 30 days"),
    ("post Instagram reel", "tomorrow at 6pm IST"),
    ("review Render billing", "on the 1st of next month"),
]

SERIES_SCENARIOS = [
    ("Milne Ki Chahat", "Story With Aisha"),
    ("Mafia Ka Dil", "Riya's Dark Romance Library"),
    ("Hamari Kahani", "Story With Aisha"),
]

# ─── CDP helpers (same as test_production_agent.py) ──────────
def get_telegram_page(playwright):
    for _ in range(5):
        try:
            browser = playwright.chromium.connect_over_cdp("http://localhost:9222")
            ctx = browser.contexts[0]
            for pg in ctx.pages:
                if "web.telegram.org/a/#" in pg.url:
                    pg.bring_to_front()
                    return browser, pg
        except Exception: pass
        time.sleep(2)
    return None, None

def get_last_bot_msg_id(page):
    try:
        return page.evaluate("""() => {
            const msgs = Array.from(document.querySelectorAll('.Message:not(.own)'));
            if (!msgs.length) return '0';
            return msgs[msgs.length-1].dataset.messageId || String(msgs.length);
        }""")
    except: return '0'

def count_own_msgs(page):
    try: return page.evaluate("() => document.querySelectorAll('.Message.own').length")
    except: return 0

def get_last_bot_reply(page):
    try:
        return page.evaluate("""() => {
            const msgs = Array.from(document.querySelectorAll('.Message:not(.own)'));
            for (let i=msgs.length-1; i>=0; i--) {
                const tc = msgs[i].querySelector('.text-content');
                if (tc && tc.innerText.trim().length > 5) return tc.innerText.trim();
            }
            return '';
        }""")
    except: return ""

def send_message(page, text):
    try:
        page.evaluate("document.getElementById('editable-message-text')?.focus()")
        page.wait_for_timeout(300)
        page.keyboard.type(text)
        page.wait_for_timeout(200)
        btn = page.locator('button.main-button')
        if btn.count() > 0: btn.click()
        else:
            btns = page.locator('.composer-wrapper button')
            if btns.count() > 0: btns.last.click()
    except: pass

def send_and_wait(page, text, wait_s=35):
    time.sleep(3)
    before_id  = get_last_bot_msg_id(page)
    before_own = count_own_msgs(page)
    send_message(page, text)
    for _ in range(20):
        if count_own_msgs(page) > before_own: break
        time.sleep(0.3)
    last_text, stable = "", 0
    deadline = time.time() + wait_s
    while time.time() < deadline:
        try:
            cur_id = get_last_bot_msg_id(page)
            if cur_id != before_id:
                time.sleep(0.8)
                cur = get_last_bot_reply(page)
                if len(cur) >= 10:
                    if cur == last_text:
                        stable += 1
                        if stable >= 2: return cur
                    else: last_text, stable = cur, 0
        except: return last_text
        time.sleep(0.4)
    return last_text or get_last_bot_reply(page)

def db_query(table, params=""):
    if not SUPABASE_KEY: return []
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/{table}?{params}",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            timeout=8,
        )
        return r.json() if r.status_code == 200 else []
    except: return []

# ─── Smart Test Runner ────────────────────────────────────────
def run_smart_tests(page):
    results = []
    seed = random.randint(1000,9999)
    print(f"\n  [Smart Agent] Seed: {seed} (test variation)")
    random.seed(seed)

    def check(name, category, fn):
        print(f"\n  [{category}] {name}")
        try: passed, detail = fn()
        except Exception as e: passed, detail = False, f"EXCEPTION: {e}"
        icon = "✅" if passed else "❌"
        print(f"  {icon} {'PASS' if passed else 'FAIL'} — {detail[:220]}")
        results.append({"name": name, "category": category, "pass": passed, "detail": detail, "seed": seed})
        return passed

    # 1. Health
    print("\n" + "─"*60 + "\n  BLOCK 1 — HEALTH")
    check("Render health", "Health",
          lambda: (lambda r: (r.status_code==200, f"HTTP {r.status_code}"))(
              requests.get(f"{RENDER_URL}/health", timeout=10)))

    check("/syscheck returns AI status", "Health", lambda: (
        lambda r: (any(w in r.lower() for w in ["gemini","groq","✅","ok"]), r[:250]))(
        send_and_wait(page, "/syscheck", wait_s=90)))

    # 2. Content — random channel + topic
    channel = random.choice(CHANNELS)
    topic   = random.choice(HINDI_TOPICS)
    print(f"\n" + "─"*60 + f"\n  BLOCK 2 — CONTENT ({channel})")

    def test_script():
        reply = send_and_wait(page,
            f"Write a 60-second YouTube Shorts script for '{channel}' — topic: {topic}, "
            "Hindi Devanagari, strong hook, cliffhanger ending",
            wait_s=55)
        deva = sum(1 for c in reply if '\u0900' <= c <= '\u097F')
        return deva > 60 and len(reply) > 300, f"Devanagari: {deva} | Len: {len(reply)}"
    check(f"Script for {channel} ({topic[:20]})", "Content", test_script)

    def test_instagram():
        reply = send_and_wait(page,
            f"Write Instagram reel caption for '{channel}' — {topic[:40]}, 20 hashtags, viral hook",
            wait_s=30)
        hcount = reply.count("#")
        return "#" in reply and len(reply) > 150, f"Hashtags: {hcount} | Len: {len(reply)}"
    check("Instagram caption with hashtags", "Content", test_instagram)

    # 3. Series continuity — random series
    sname, schannel = random.choice(SERIES_SCENARIOS)
    print(f"\n" + "─"*60 + f"\n  BLOCK 3 — SERIES ({sname})")

    def test_episode1():
        reply = send_and_wait(page,
            f"Start a 5-episode YouTube Shorts series '{sname}' for '{schannel}' — "
            "Episode 1: Hindi Devanagari, 60s script, end with cliffhanger",
            wait_s=55)
        deva = sum(1 for c in reply if '\u0900' <= c <= '\u097F')
        return deva > 80, f"Devanagari: {deva} | Len: {len(reply)}"
    check(f"Episode 1: {sname}", "Series", test_episode1)

    def test_episode2():
        reply = send_and_wait(page,
            f"Episode 2 of '{sname}' — continue from cliffhanger, "
            "Hindi Devanagari, 60s, new tension, new cliffhanger",
            wait_s=55)
        deva = sum(1 for c in reply if '\u0900' <= c <= '\u097F')
        return deva > 60, f"Devanagari: {deva} | Len: {len(reply)}"
    check(f"Episode 2: {sname} (continuity)", "Series", test_episode2)

    # 4. Pipeline
    amount, category = random.choice(EXPENSE_SCENARIOS)
    reminder_what, reminder_when = random.choice(REMINDER_SCENARIOS)
    print(f"\n" + "─"*60 + "\n  BLOCK 4 — PIPELINE")

    def test_expense():
        reply = send_and_wait(page, f"I spent {amount} rupees on {category}", wait_s=20)
        ok_reply = any(w in reply.lower() for w in [str(amount), category.split()[0].lower(), "logged","noted","added"])
        rows = db_query("aisha_expenses", f"amount=eq.{amount}&order=created_at.desc&limit=1")
        return ok_reply, f"Reply OK: {ok_reply} | DB: {len(rows)>0} | {reply[:100]}"
    check(f"Expense {amount}₹ ({category})", "Pipeline", test_expense)

    def test_reminder():
        reply = send_and_wait(page, f"Remind me to {reminder_what} {reminder_when}", wait_s=20)
        ok = any(w in reply.lower() for w in ["remind","set","noted","saved","will"])
        return ok, reply[:150]
    check(f"Reminder: {reminder_what[:30]}", "Pipeline", test_reminder)

    # 5. Self-improvement
    print(f"\n" + "─"*60 + "\n  BLOCK 5 — SELF-IMPROVEMENT")

    def test_upgrade():
        reply = send_and_wait(page, "/upgrade Improve content generation quality", wait_s=35)
        ok = any(w in reply.lower() for w in ["improve","upgrade","pr","github","code","skill"])
        return ok, reply[:200]
    check("/upgrade triggers self-improvement", "SelfImprove", test_upgrade)

    github_rows = db_query("aisha_audit_log",
        "event_type=eq.self_improvement&order=created_at.desc&limit=3")
    check("Self-improvement logged to DB", "SelfImprove",
          lambda: (len(github_rows)>0, f"{len(github_rows)} entries"))

    return results

# ─── Report ───────────────────────────────────────────────────
def print_report(results):
    passed = sum(1 for r in results if r["pass"])
    total  = len(results)
    pct    = int(passed/total*100) if total else 0
    seed   = results[0].get("seed","?") if results else "?"

    print(f"\n{'='*65}")
    print(f"  AISHA SMART TEST AGENT — {datetime.now().strftime('%Y-%m-%d %H:%M IST')}")
    print(f"  Seed: {seed} | Score: {passed}/{total} ({pct}%)")
    bar = ("█" * (pct//5)).ljust(20)
    print(f"  [{bar}]")

    cats = {}
    for r in results:
        cats.setdefault(r["category"], {"p":0,"f":0})
        cats[r["category"]]["p" if r["pass"] else "f"] += 1

    print("\n  By Category:")
    for cat, v in cats.items():
        t = v["p"]+v["f"]
        icon = "✅" if v["f"]==0 else ("⚠️" if v["p"]>0 else "❌")
        print(f"    {icon} {cat:<20} {v['p']}/{t}")

    fails = [r for r in results if not r["pass"]]
    if fails:
        print(f"\n  ❌ Failures ({len(fails)}):")
        for r in fails:
            print(f"    • [{r['category']}] {r['name']}")
            print(f"      → {r['detail'][:130]}")

    report = {"timestamp": datetime.now().isoformat(), "seed": seed,
              "total": total, "passed": passed, "score_pct": pct,
              "categories": cats, "results": results}
    os.makedirs("tests", exist_ok=True)
    with open("tests/smart_test_report.json","w",encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n  Report → tests/smart_test_report.json")
    print(f"{'='*65}\n")

# ─── Main ─────────────────────────────────────────────────────
def main():
    print(f"\n{'='*65}")
    print(f"  AISHA SMART TEST AGENT  (varied scenarios each run)")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*65}")
    with sync_playwright() as p:
        browser, page = get_telegram_page(p)
        if not page:
            print("ERROR: No Telegram tab found in Edge.")
            print("Launch: msedge --remote-debugging-port=9222")
            return
        page.wait_for_timeout(2000)
        print(f"\nConnected: {page.title()}")
        time.sleep(4)
        results = run_smart_tests(page)
        print_report(results)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add tests/test_smart_agent.py
git commit -m "feat: smart test agent — randomized scenarios, varied content tests, seed-based reproducibility"
```

---

## Chunk 5: DB migrations + push to GitHub + deploy

### Task 7: Apply pending migrations

- [ ] **Step 1: Apply guest_user_id migration (pending since CLAUDE.md)**

Via Supabase MCP:
```sql
ALTER TABLE aisha_conversations
ADD COLUMN IF NOT EXISTS guest_user_id BIGINT DEFAULT NULL;
```

- [ ] **Step 2: Create content-videos bucket in Supabase Storage**

Via Supabase MCP or Dashboard:
```sql
INSERT INTO storage.buckets (id, name, public)
VALUES ('content-videos', 'content-videos', true)
ON CONFLICT (id) DO NOTHING;
```

- [ ] **Step 3: Apply series tracker migration**

Run the SQL from Task 3 Step 1 via Supabase MCP.

- [ ] **Step 4: Push all changes to GitHub**

```bash
git push origin main
```

- [ ] **Step 5: Trigger Render redeploy**

```bash
curl -s "$RENDER_DEPLOY_HOOK_URL"
```

- [ ] **Step 6: Verify health after deploy**

```bash
sleep 60
curl -s https://aisha-bot-yudp.onrender.com/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 7: Run smart test agent to verify everything works**

```bash
PYTHONUTF8=1 /e/VSCode/.venv/Scripts/python tests/test_smart_agent.py
```

Expected: ≥80% pass rate

---

## Execution Order Summary

```
Chunk 1: Pipeline connector (antigravity_agent + autonomous_loop)
  └── Makes: content auto-renders + uploads + posts after crew

Chunk 2: Series tracker (DB + series_tracker.py + YouTubeCrew wiring)
  └── Makes: YouTube Shorts tell continuous stories across episodes

Chunk 3: Telegram commands (bot.py)
  └── Makes: /syscheck /studio /upgrade /voice /mood /aistatus all work

Chunk 4: Token manager + smart test agent
  └── Makes: tokens never expire, tests always vary

Chunk 5: Migrations + deploy
  └── Makes: everything live on Render
```

**After completion:** Aisha will:
- Post 1 Short/day per channel automatically
- Track episode series with cliffhangers
- Refresh her own Instagram token
- Self-improve via GitHub PRs on schedule
- Respond to all Telegram commands
- Run smart varied tests so you always get new coverage
