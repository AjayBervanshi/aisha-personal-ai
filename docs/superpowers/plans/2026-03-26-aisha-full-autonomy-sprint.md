# Aisha Full Autonomy Sprint — 2-Day Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Aisha fully autonomous — she generates, publishes, and earns from YouTube + Instagram 24/7 without any human intervention.

**Architecture:** Fix all blockers → wire full content pipeline (script→voice→video→upload) → activate autonomous scheduler → deploy → monitor first live publish.

**Tech Stack:** Python, Telegram Bot API, ElevenLabs/Edge-TTS, MoviePy, YouTube Data API v3, Instagram Graph API, Supabase, NVIDIA NIM, Render

**Deadline:** 2 days (by 2026-03-28)

---

## PRIORITY MATRIX

| # | Task | Impact | Effort | Status |
|---|------|--------|--------|--------|
| P0 | Fix ElevenLabs quota blocker | CRITICAL | 30min | ⏳ |
| P0 | Run Supabase migrations | CRITICAL | 15min | ⏳ |
| P1 | Test Aisha on Telegram | HIGH | 2h | ⏳ |
| P1 | Wire antigravity render_video + auto_post | HIGH | 2h | ⏳ |
| P1 | Wire autonomous_loop auto_post=True | HIGH | 1h | ⏳ |
| P2 | Add /earnings revenue tracker | MEDIUM | 1h | ⏳ |
| P2 | Add content calendar (self-scheduled) | MEDIUM | 2h | ⏳ |
| P3 | Test full pipeline end-to-end | HIGH | 1h | ⏳ |
| P3 | Deploy + verify Render | HIGH | 30min | ⏳ |

---

## DAY 1 — Fix Blockers + Wire Pipeline

### Task 1: Fix ElevenLabs Quota (P0 — 30 min)

**Files:**
- Modify: `src/core/voice_engine.py`
- Modify: `src/core/config.py`

**Problem:** Only 178 ElevenLabs characters remain. A single Hindi story script = 2000–4000 chars. Pipeline will silently fail or fall back mid-generation.

**Fix:** Make Edge-TTS the default for content pipeline. Reserve ElevenLabs only for short Telegram voice replies (≤500 chars) AND when `force_elevenlabs=True`.

- [ ] Read `src/core/voice_engine.py` — understand current fallback logic
- [ ] Add config flag `VOICE_ENGINE_DEFAULT = os.getenv("VOICE_ENGINE_DEFAULT", "edge_tts")`
- [ ] In `generate_voice()`, check `if len(text) > 500 or config.VOICE_ENGINE_DEFAULT == "edge_tts":` → skip ElevenLabs, go straight to Edge-TTS
- [ ] Add `force_elevenlabs=False` param to `generate_voice()` — when True, always try ElevenLabs first
- [ ] Test: `python -c "from src.core.voice_engine import VoiceEngine; v=VoiceEngine(); v.generate_voice('नमस्ते', channel='story_with_aisha')"`
- [ ] Commit: `fix: default voice to edge_tts, reserve elevenlabs for short replies`

---

### Task 2: Run Supabase Migrations (P0 — 15 min)

**Files:**
- Read: `supabase/migrations/20260325000001_series_tracker.sql`

- [ ] Read migration file to confirm SQL
- [ ] Apply via Supabase MCP: `mcp__supabase__execute_sql` with migration SQL
- [ ] Apply guest_user_id column: `ALTER TABLE aisha_conversations ADD COLUMN IF NOT EXISTS guest_user_id BIGINT DEFAULT NULL;`
- [ ] Verify: `SELECT table_name FROM information_schema.tables WHERE table_name IN ('aisha_series','aisha_episodes');`

---

### Task 3: Test Aisha on Telegram (P1 — 2 hours)

**Approach:** Launch Edge browser with remote debugging → send test messages → review responses → patch.

**Launch Edge:**
```bash
"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" \
  --remote-debugging-port=9222 \
  --user-data-dir="C:\Users\Admin\EdgeDebug"
```

Then open `web.telegram.org` and navigate to Aisha bot chat.

**Test messages to send (in order):**

| # | Message | Expected | Pass Criteria |
|---|---------|----------|---------------|
| 1 | "नमस्ते Aisha" | Hindi greeting back | >50 Devanagari chars |
| 2 | "How are you today?" | English reply, warm tone | >30 chars, no error |
| 3 | "मुझे एक प्रेम कहानी सुनाओ" | Hindi love story | >200 Devanagari chars |
| 4 | "/syscheck" | Full system report | Lists providers, >100 chars |
| 5 | "What's trending on YouTube today?" | Trend analysis | Mentions channel names |
| 6 | "/mood creative" | Mood confirmation | Confirms creative mode |
| 7 | "Plan my content for Story With Aisha" | Content ideas | Avoids NLP router trap |
| 8 | "/studio" | Pipeline acknowledgement | "queuing" message |

**For each failing test:**
- [ ] Identify root cause (NLP router? AI provider? Language detection?)
- [ ] Patch `src/core/aisha_brain.py` or `src/telegram/bot.py`
- [ ] Re-test on Telegram

**Run test script:**
```bash
cd /e/VSCode/Aisha
PYTHONUTF8=1 /e/VSCode/.venv/Scripts/python tests/test_production_agent.py
```

---

### Task 4: Wire antigravity_agent.py (P1 — 2 hours)

**Files:**
- Modify: `src/agents/antigravity_agent.py`
- Modify: `src/core/video_engine.py` (verify API)
- Modify: `src/core/social_media_engine.py` (verify upload API)

**Current state:** antigravity_agent processes content_jobs but render_video and auto_post are not connected.

**Target flow:**
```
content_job (DB)
  → script (done)
  → voice MP3 (done)
  → thumbnail PNG (done)
  → render MP4 [NEW: video_engine.render_video()]
  → upload YouTube [NEW: social_media_engine.upload_youtube()]
  → post Instagram [NEW: social_media_engine.post_instagram()]
  → update job status in DB
```

- [ ] Read `src/agents/antigravity_agent.py` — find where voice/thumbnail are assembled
- [ ] Read `src/core/video_engine.py` — find `render_video()` signature
- [ ] Read `src/core/social_media_engine.py` — find `upload_to_youtube()` and `post_instagram()` signatures
- [ ] Add `render_video=True` and `auto_post=True` flags to `process_job()` method
- [ ] Wire: after voice + thumbnail ready → `video_engine.render_video(voice_path, thumbnail_path, title)` → returns `mp4_path`
- [ ] Wire: if `auto_post` and `mp4_path` → `social_media_engine.upload_to_youtube(mp4_path, title, description, tags, channel)`
- [ ] Wire: if Instagram channel → `social_media_engine.post_instagram(mp4_path, caption)`
- [ ] Update DB job status to `completed` with `video_url` and `post_url`
- [ ] Test: enqueue one job, run `python -m src.agents.antigravity_agent --test`
- [ ] Commit: `feat: wire render_video + auto_post into antigravity pipeline`

---

### Task 5: Wire autonomous_loop.py (P1 — 1 hour)

**Files:**
- Modify: `src/core/autonomous_loop.py`

**Current state:** Every 4h studio session calls `_run_studio_session()` but doesn't pass `auto_post=True`.

- [ ] Read `src/core/autonomous_loop.py` — find `_run_studio_session()` call
- [ ] Read how studio sessions are dispatched — find what params are accepted
- [ ] Add `platforms=["youtube", "instagram"]` and `auto_post=True` to studio session dispatch
- [ ] Ensure error handling: if upload fails → log + Telegram alert to Ajay, don't crash loop
- [ ] Test: trigger manual studio session via `/studio` command in Telegram, verify content job is created with `auto_post=True`
- [ ] Commit: `feat: autonomous loop passes auto_post=True to studio sessions`

---

## DAY 2 — Revenue Tracking + Full Pipeline Test + Deploy

### Task 6: Add /earnings Command (P2 — 1 hour)

**Files:**
- Modify: `src/telegram/bot.py`
- Modify: `src/core/analytics_engine.py` (or create `src/core/revenue_tracker.py`)

**What /earnings shows:**
```
📊 Aisha Revenue Dashboard — 2026-03-26

YouTube:
  📹 Videos uploaded (7 days): 3
  👁️  Total views (7 days): ~1,200
  ⏱️  Estimated watch hours: ~48h
  🎯  Monetization progress: 48/4000h (1.2%)
  👥  Subscribers needed: 950/1000

Instagram:
  📸 Posts this week: 5
  ❤️  Avg engagement: 4.2%
  👥  Followers: 234

💡 At current pace: monetization in ~83 days
🚀 To accelerate: post 2x/day per channel
```

- [ ] Add `/earnings` command handler in `bot.py`
- [ ] Query YouTube Analytics API for view/watch-hour data (or use stored DB data from `content_jobs`)
- [ ] Query Instagram API for follower count + engagement
- [ ] Calculate monetization ETA based on pace
- [ ] Format and send as Telegram message
- [ ] Commit: `feat: add /earnings revenue dashboard command`

---

### Task 7: Add Content Calendar (P2 — 2 hours)

**Files:**
- Create: `src/core/content_calendar.py`
- Modify: `src/core/autonomous_loop.py`
- Modify: `src/telegram/bot.py` (add `/calendar` command)

**Logic:**
- Each channel gets 2 slots/day: morning (11AM IST) + evening (7PM IST)
- Aisha uses `trend_engine.py` to pick trending topics for each slot
- Calendar is stored in Supabase `content_jobs` with `scheduled_at` timestamps
- `/calendar` command shows the week's planned content

```python
class ContentCalendar:
    SLOTS = {
        "story_with_aisha":         ["11:00", "19:00"],
        "riya_dark_whisper":        ["12:00", "20:00"],
        "riya_dark_romance":        ["13:00", "21:00"],
        "aisha_and_him":            ["10:00", "18:00"],
    }

    async def generate_week_plan(self):
        """For each channel, for each slot, pick trending topic and queue job."""
        ...

    async def get_calendar_summary(self) -> str:
        """Return formatted Telegram message with this week's content plan."""
        ...
```

- [ ] Create `src/core/content_calendar.py` with `ContentCalendar` class
- [ ] Implement `generate_week_plan()` — uses trend_engine per channel, queues content_jobs
- [ ] Implement `get_calendar_summary()` — formatted weekly view
- [ ] Add `/calendar` command to `bot.py`
- [ ] Add daily calendar generation to `autonomous_loop.py` (runs at 6AM IST)
- [ ] Test: `/calendar` shows upcoming content plan in Telegram
- [ ] Commit: `feat: add content calendar with auto topic selection`

---

### Task 8: Test Full Pipeline End-to-End (P3 — 1 hour)

**Test in Telegram:**
```
/produce story_with_aisha "एक प्यारी प्रेम कहानी"
```

**Verify each stage:**
- [ ] Script generated (Hindi Devanagari, >500 chars)
- [ ] Voice rendered (MP3 file, >10 seconds)
- [ ] Thumbnail created (PNG, 1280×720)
- [ ] MP4 rendered (Ken Burns effect)
- [ ] YouTube upload initiated (returns video ID or queued)
- [ ] Instagram post created (if channel has Instagram)
- [ ] DB job marked `completed`
- [ ] Aisha sends Telegram message: "Video published: [link]"

**If any stage fails:** fix the specific component and re-run.

---

### Task 9: Deploy + Verify Render (P3 — 30 min)

- [ ] Run all unit tests: `PYTHONUTF8=1 /e/VSCode/.venv/Scripts/python -m pytest tests/ -x -q`
- [ ] Commit all remaining changes
- [ ] Push to GitHub: `git push origin main`
- [ ] Check Render deploy via MCP: `mcp__render__list_deploys`
- [ ] Watch logs: `mcp__render__list_logs` — verify no crash on startup
- [ ] Wait for first scheduled studio session (next 4h boundary)
- [ ] Confirm Telegram message from Aisha about content being queued
- [ ] Verify YouTube/Instagram post appears

---

## SUCCESS CRITERIA

Aisha is "done" when she can:

- [ ] Respond naturally in Hindi/English on Telegram without any failures
- [ ] Generate and publish 2 YouTube Shorts per channel per day — automatically
- [ ] Post 2 Instagram reels/stories per day — automatically
- [ ] Send Ajay a daily summary of what was published and views/engagement
- [ ] Handle API failures gracefully (fallback to next provider, no crash)
- [ ] Report `/earnings` with monetization progress
- [ ] Show `/calendar` with the week's planned content

**Money making milestone:** YouTube monetization requires 1000 subscribers + 4000 watch hours.
At 4 videos/day across 4 channels = ~112 videos/week. Realistic timeline: monetization in 60–90 days of consistent publishing.

---

## WHAT REQUIRES AJAY (Manual — Cannot Be Automated)

| Item | Why Manual | Where |
|------|-----------|-------|
| Groq API renewal | Account login required | console.groq.com → API Keys |
| xAI API new key | Key was revoked (leaked) | console.x.ai → API Keys |
| ElevenLabs upgrade | Billing action | elevenlabs.io → Subscription |
| Instagram OAuth refresh | 2FA + browser OAuth flow | `/instagram-auth` flow |
| YouTube OAuth (first time) | Browser consent screen | `/youtube-auth` flow |
| OpenAI/Anthropic renewal | Account login | platform.openai.com / console.anthropic.com |

---

## NOTES

- **Content quality > quantity** — each video must be compelling or YouTube won't recommend it
- **Hindi Devanagari only** — never Roman script for Story With Aisha / Riya channels
- **Riya channels = xAI Grok** — once xAI key is renewed, Riya gets uncensored adult content quality back
- **ElevenLabs is brand identity** — Aisha's voice IS ElevenLabs. Upgrade to Creator plan ($22/mo) as soon as first revenue arrives
- **NVIDIA NIM** = free 22k credits/month — this is the backbone until paid APIs are restored
