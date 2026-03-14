# AI_HANDOFF.md — Aisha Project State
# Format: paste this file to any AI (Claude or Codex) to resume exactly where we left off.
# Updated: 2026-03-14

---

## PROJECT OVERVIEW

**Aisha** — Personal AI system for Ajay (Telegram: @AishaAIforAjay_Bot)
- YouTube content automation: 4 channels, Hindi stories, ElevenLabs TTS, MP4 render
- Telegram bot + autonomous 24/7 loop
- Supabase cloud database (project: tgqerhkcbobtxqkgihps)
- Local path: `E:\VSCode\Aisha`
- GitHub: https://github.com/AjayBervanshi/aisha-personal-ai

---

## CURRENT STATE (as of 2026-03-14)

### Working ✅
| System | Status |
|--------|--------|
| Telegram Bot (@AishaAIforAjay_Bot) | Connected |
| AIRouter — Gemini (gemini-2.5-flash) | **WORKING** — REST API via requests, 2.3s latency |
| AIRouter — Groq (llama-3.3-70b) | Working |
| AIRouter — xAI Grok | 403 Permission denied (no model credits) |
| ElevenLabs — Aisha voice | 31K bytes/request, starter plan |
| ElevenLabs — Riya voice | Configured |
| Voice Engine (voice_engine.py) | edge-tts fallback + ElevenLabs |
| Trend Engine (trend_engine.py) | Google Trends working, Gemini synthesis falls back |
| AishaBrain (aisha_brain.py) | Loads, routes via AIRouter — Gemini primary |
| Supabase — All 15 tables | Created and seeded |
| YouTubeCrew (youtube_crew.py) | 5-agent pipeline loaded |
| AntigravityAgent | Loads, orchestrates pipeline |
| AutonomousLoop | Loads (needs `schedule` package) |
| GmailEngine | Loaded (needs GMAIL_USER + APP_PASSWORD) |
| SocialMediaEngine | Loaded (needs YouTube OAuth) |

### Broken ❌
| System | Problem | Fix |
|--------|---------|-----|
| Gemini API | Key invalid (400) | Get new key: console.cloud.google.com |
| Anthropic API | Key invalid (401) | Get new key: console.anthropic.com |
| OpenAI API | Key invalid (401) | Get new key: platform.openai.com |
| HuggingFace | Placeholder key | Get free key: huggingface.co/settings/tokens |
| Image Engine | HF key missing → no images | Fix HF key first |
| Video Engine | Images don't generate → no video | Fix image engine first |
| Supabase DB | 0/10 tables exist | Apply migration (see below) |
| YouTube OAuth | Not set up | Run scripts/setup_youtube_oauth.py |
| Instagram | Token not set | Run scripts/setup_instagram_token.py |

---

## PENDING ACTIONS (in order)

### 1. Apply Supabase Migration (CRITICAL)
Go to: https://supabase.com/dashboard/project/tgqerhkcbobtxqkgihps/sql/new
Paste the full contents of: `supabase/aisha_full_migration.sql`
This creates all 10 tables: ajay_profile, aisha_memory, aisha_journal, aisha_finance,
aisha_schedule, aisha_conversations, aisha_mood_tracker, aisha_goals,
content_jobs, content_performance, channel_prompts, aisha_trend_cache,
aisha_content_library, aisha_youtube_channels, aisha_earnings_tracker

### 2. Fix API Keys in .env
```
GEMINI_API_KEY=<get from console.cloud.google.com>
ANTHROPIC_API_KEY=<get from console.anthropic.com>
OPENAI_API_KEY=<get from platform.openai.com>
HUGGINGFACE_API_KEY=<get from huggingface.co/settings/tokens>
GMAIL_USER=<your gmail>
GMAIL_APP_PASSWORD=<gmail app password>
YOUTUBE_API_KEY=<get from Google Cloud Console>
```

### 3. YouTube OAuth Setup
```bash
cd E:\VSCode\Aisha
python scripts/setup_youtube_oauth.py
```
Repeat for each of 4 channels. Tokens saved to `tokens/` directory.

### 4. Instagram Token Setup
```bash
python scripts/setup_instagram_token.py
```
Sets INSTAGRAM_ACCESS_TOKEN in .env

### 5. Test Full Pipeline
```bash
python -c "
import sys; sys.path.insert(0,'.')
from src.agents.youtube_crew import YouTubeCrew
crew = YouTubeCrew()
crew.kickoff({'topic':'Office love story','channel':'Story With Aisha','format':'Long Form'})
print(crew.results.get('script','')[:200])
"
```

### 6. Run Telegram Bot
```bash
python -m src.core.aisha_brain
```

---

## KEY FILES

```
src/core/config.py           — All env vars, models, CHANNEL_VOICE_IDS
src/core/ai_router.py        — 5-provider waterfall: Gemini→Claude→Groq→xAI→OpenAI
src/core/aisha_brain.py      — Telegram bot brain + AishaBrain.think()
src/core/voice_engine.py     — generate_voice(text, channel=) — ElevenLabs + edge-tts
src/core/image_engine.py     — generate_image(prompt) — HuggingFace FLUX.1-schnell
src/core/video_engine.py     — render_video(voice_path, script, channel, topic)
src/core/trend_engine.py     — get_trends_for_channel(channel) — Google Trends + DDG + Gemini
src/core/analytics_engine.py — YouTube + Instagram analytics pullback
src/core/gmail_engine.py     — SMTP email (Aisha can email Ajay)
src/core/social_media_engine.py — YouTube upload + Instagram post
src/core/autonomous_loop.py  — 24/7 cron: 8AM checkin, 3AM memory, every 4h studio
src/agents/youtube_crew.py   — 5-agent pipeline: Research→Script→Visual→SEO→Voice+Video
src/agents/antigravity_agent.py — Orchestrates: trends→crew→voice→video→upload
src/core/prompts/personality.py — MOOD_INSTRUCTIONS + CHANNEL_PROMPTS (full Hindi identities)
supabase/functions/chat/index.ts — Edge function: web chat, multi-provider fallback
supabase/aisha_full_migration.sql — ALL migrations in one file (paste in SQL editor)
```

---

## CHANNEL CONFIGURATION

| Channel | AI | Voice | Narrator | Content |
|---------|-----|-------|---------|---------|
| Story With Aisha | Gemini | Aisha (wdymxIQkYn7MJCYCQF2Q) | First-person warm love stories | 8-15 min Hindi Devanagari |
| Riya's Dark Whisper | xAI Grok | Riya (BpjGufoPiobT79j2vtj4) | Bold adult dark romance | 10-20 min Hindi Devanagari |
| Riya's Dark Romance Library | xAI Grok | Riya (same) | Mafia romance novel-style | 15-25 min Hindi Devanagari |
| Aisha & Him | Gemini | Aisha (same) | Couple reels | 30s-3 min Hinglish |

---

## RECENT CODE CHANGES (2026-03-14)

1. **ai_router.py** — Added load_dotenv at top, fixed Gemini to use `google.genai` (new SDK), added `available_providers` property, added `chat()` wrapper, fixed streaming text block extraction
2. **trend_engine.py** — Updated Gemini call to use `google.genai` with old SDK fallback
3. **requirements.txt** — Added: `google-genai`, `anthropic`, `edge-tts`
4. **voice_engine.py** — `generate_voice(text, channel=)` selects ElevenLabs voice by channel
5. **youtube_crew.py** — Uses CHANNEL_PROMPTS + trend research + video render step
6. **supabase/aisha_full_migration.sql** — All 15 tables in one file for manual SQL paste

---

## ENVIRONMENT

- Python 3.13 (Windows Server 2022)
- Shell: bash (PowerShell also works)
- Packages installed: groq, supabase, elevenlabs, edge-tts, moviepy, Pillow, numpy, pytrends, google-auth-oauthlib, google-api-python-client, schedule, google-genai
- Missing packages to install: `pip install -r requirements.txt`

---

## NEXT MILESTONE (Phase 1 Complete = First Video Posted)

1. Apply DB migration → tables exist
2. Fix Gemini API key → script generation works for Aisha channels
3. Fix HuggingFace key → image generation works → video render works
4. YouTube OAuth for "Story With Aisha" → upload enabled
5. Run `AntigravityAgent.run_next_job()` → first auto-generated video on YouTube

Expected result: YouTube video uploaded with:
- Hindi Devanagari story script (Gemini)
- Aisha voice narration (ElevenLabs)
- AI scene images (HuggingFace FLUX)
- Rendered MP4 (moviepy)
- Auto-uploaded to YouTube

---

## HOW TO USE THIS FILE

**To give to Claude:**
1. Copy this entire file
2. Start a new Claude conversation
3. Paste as first message with: "Continue Aisha development from this handoff"

**To give to Codex/GitHub Copilot:**
1. Open this file in VS Code
2. Open Copilot Chat
3. Type: "@workspace Continue from AI_HANDOFF.md"
4. Codex reads the workspace context including this file

**Updating this file:**
After each work session, update the CURRENT STATE and RECENT CODE CHANGES sections.
