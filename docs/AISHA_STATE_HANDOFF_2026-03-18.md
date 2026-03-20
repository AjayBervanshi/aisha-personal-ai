# Aisha — Agent State & Handoff Document
**State: Phase 1 (MVP Validation) | Confidence: HIGH | Last runtime verification: 2026-03-18 — 17/17 tests passed**

> This document follows `AGENT_STATE_FLOW_STANDARD.md`.
> Purpose: Any agent or human picking up this project should read ONLY this file to understand current state, what works, what is blocked, and exactly what to do next.

---

## 1. Verified in Code

| Claim | Evidence |
|-------|---------|
| AI Router has 7-provider waterfall + NVIDIA 22-key pool | `src/core/ai_router.py:66` — `_stats` dict, `_init_clients()` |
| Continuous fallback: last-resort tries nvidia general/fast/chat pools before giving up | `src/core/ai_router.py` — added 2026-03-18, after main provider loop |
| Email alert on key expiry / quota hit / all-down | `src/core/ai_router.py` — `_notify_provider_failure()`, `_should_alert()`, 6h cooldown |
| NVIDIA pool: 22 keys, writing=Mistral-Large-3-675B, chat=7×LLaMA-3.3-70b | `src/core/nvidia_pool.py:115` — `_KEY_DEFINITIONS` |
| YouTube upload function exists with idempotency guard | `src/core/social_media_engine.py:247` — `upload_youtube_video(job_id=)` |
| YouTube OAuth token file exists | `tokens/youtube_token.json` — refresh_token=True (verified in test) |
| YouTube client secret exists | `tokens/youtube_client_secret.json` |
| Instagram token file exists | `tokens/instagram_token.json` |
| Content pipeline: 5-agent flow (Research→Script→Visual→SEO→Voice) | `src/agents/youtube_crew.py:80` — `kickoff()` |
| ElevenLabs voices: Aisha + Riya voice IDs in config | `src/core/config.py:92-93` |
| Memory embedding: gemini-embedding-001 + outputDimensionality=768 | `src/memory/memory_manager.py:108` |
| api_keys.secret fix migration written | `supabase/migrations/20260317120000_fix_api_keys_secret_column.sql` |
| Video engine exists | `src/core/video_engine.py` — uses HuggingFace FLUX.1-schnell |
| setup_youtube_oauth.py wizard exists | `scripts/setup_youtube_oauth.py` |
| Minor bug: duplicate `return False` on line 166 | `scripts/setup_youtube_oauth.py:166` — cosmetic, not blocking |

---

## 2. Verified in Runtime

| Claim | Evidence (test artifact) |
|-------|-------------------------|
| 17/17 system tests pass | `scripts/test_all_systems.py` output 2026-03-18, exit code 0 |
| Telegram bot live, polling mode | test output: `Bot identity: AishaAIforAjay_Bot` |
| Gemini REST working | test output: `gemini 2188ms` |
| NVIDIA Mistral-Large-3 working, generates Devanagari Hindi | test output: `nvidia 22018ms \| उस रात चाँदनी में...` |
| ElevenLabs Aisha voice: 31,391 bytes | test output: `[4] VOICE ENGINE ✅` |
| ElevenLabs Riya voice: 24,703 bytes | test output: `[4] VOICE ENGINE ✅` |
| YouTube token loaded from file fallback (refresh_token=True) | test output: `[5] SOCIAL MEDIA ✅` |
| Instagram token loaded: `IGAAVIVYsRNe...` | test output: `[5] SOCIAL MEDIA ✅` |
| Aisha pipeline generated 33,735 chars | test output: `[6] PIPELINE ✅ Story With Aisha` |
| Riya pipeline generated 15,116 chars via NVIDIA | test output: `[6] PIPELINE ✅ Riya's Dark Whisper` |
| NVIDIA pool imports correctly, 18 keys available | `python -c "from src.core.nvidia_pool import NvidiaPool..."` 2026-03-18 |
| AIRouter clients: gemini, openai, anthropic, groq, xai, nvidia | `python -c "ai = AIRouter(); print(ai._clients.keys())"` 2026-03-18 |
| Embedding: gemini-embedding-001 + outputDimensionality=768 → 768 dims | REST API test 2026-03-18, confirmed |

---

## 3. Unverified / Assumed

| Claim | Status | Risk |
|-------|--------|------|
| `api_keys.secret` column exists in Supabase | ❌ **NOT APPLIED** — migration written but SQL not yet run in Supabase Dashboard | HIGH — Instagram DB token load fails; YouTube uses file fallback |
| Full E2E video upload to YouTube (create → render → publish) | ❌ **NOT TESTED** — YouTube upload code exists and token exists, but upload not executed | HIGH — Phase 1 gate |
| Video render (MP4 from voice + images) | ❌ **NOT WORKING** — HuggingFace endpoints all 410 Gone, no image source for video | MEDIUM — pipeline works without video (audio-only format valid for YouTube) |
| GMAIL_USER / GMAIL_APP_PASSWORD set in .env | **UNKNOWN** — email alert system added but credential status unverified | MEDIUM — alerts silently fail if not set |
| Groq API key valid | ❌ **EXPIRED** — key `gsk_C6Lmx...` returns 401. NVIDIA chat pool covers this. | LOW — covered by NVIDIA fallback |
| AutonomousLoop daily cron running | **UNKNOWN** — loop code exists (`src/core/autonomous_loop.py`) but Railway deploy status unknown | MEDIUM — manual runs work |

---

## 4. Conflicts With Other Docs

| Conflict | Doc A | Doc B | Resolution |
|----------|-------|-------|------------|
| "Run setup_youtube_oauth.py to get token" | `CTO_RESPONSE_REVIEW_2026-03-18.md` | This doc | **Token already exists** at `tokens/youtube_token.json` with refresh_token=True. Skip OAuth setup unless token expires. Run `python scripts/setup_youtube_oauth.py --test` to verify. |
| "Purchase xAI / HuggingFace credits for Phase 1" | `CTO_ROADMAP_TO_REVENUE_2026-03-17.md` | This doc | **Incorrect** — NVIDIA NIM pool (22 free keys, Mistral-Large-3) is the solution. No spend needed for Riya channels. |
| "Phase 1 DONE (17/17 tests)" | `docs/SYSTEM_TEST_REPORT_2026-03-17.md` | `CTO_RESPONSE_REVIEW_2026-03-18.md` | **CTO is right** — Phase 1 gate = first YouTube upload. Tests pass but upload not yet verified. Use CTO definition. |
| "Gemini fallback models: gemini-2.5-flash-lite, gemini-3.1..." (invalid names) | Old `ai_router.py` | Current code | **Fixed** — fallback is now: `gemini-2.0-flash`, `gemini-2.0-flash-lite`, `gemini-1.5-flash`, `gemini-1.5-flash-8b` |

---

## 5. Current State Snapshot

```
Phase:     Phase 1 — MVP Validation (99% complete)
Gate:      First YouTube video successfully uploaded
Blocker:   api_keys.secret column missing in Supabase (SQL not yet run)
           Gmail credentials not set (alerts silent)

AI stack:
  Primary:     Gemini 2.5-flash (REST, 20 req/day free) → 2.0-flash fallback (1500/day)
  Riya/Dark:   NVIDIA Mistral-Large-3-675B (writing pool, 2 keys × 1000 credits/month)
  Fallback:    NVIDIA LLaMA-3.3-70b (chat pool, 7 keys)
  Last resort: NVIDIA general (Qwen-122B, Gemma-27B) → fast (Gemma-2B, Falcon3)
  Alerts:      Email on key_expired / quota_exhausted / all_down (6h cooldown)

Content:
  Aisha pipeline:  ✅ 33,735 chars, Gemini, warm romantic Hindi
  Riya pipeline:   ✅ 15,116 chars, Mistral-Large-3, explicit dark Hindi
  Voice:           ✅ ElevenLabs Aisha + Riya, both working
  Thumbnail:       ❌ HuggingFace 410, placeholder used
  Video render:    ❌ HuggingFace 410, no MP4 possible yet

Social Media:
  YouTube upload:  Code ready, token file valid, DB token load failing (secret column)
  Instagram post:  Code ready, token file valid, DB token load failing (secret column)
  Idempotency:     ✅ youtube_video_id + instagram_post_id unique indexes in DB

Memory:
  Embedding:       gemini-embedding-001, outputDimensionality=768, REST API, working
  Semantic search: ✅ pgvector match_memories RPC
```

---

## 6. Flow Snapshot

### Content Factory (Primary Revenue Flow)

```
Trigger:        Ajay sends /create [topic] [channel] via Telegram
                OR AutonomousLoop cron fires (daily studio session)
Entry point:    src/core/aisha_brain.py → handle_message()
                OR src/core/autonomous_loop.py → run_studio_session()
Orchestrator:   src/agents/youtube_crew.py → YouTubeCrew.kickoff()

Flow:
  [1] TrendEngine.get_trends_for_channel(channel)
        → pytrends + Gemini AI synthesis of viral angles
  [2] AIRouter.generate(preferred_provider="gemini"|"nvidia", task_type="writing")
        → Research brief (300 words, trending angles + story brief)
  [3] AIRouter.generate() → Full script (8-15 min narration, Devanagari Hindi)
  [4] AIRouter.generate() → Visual direction (thumbnail concept + 5 scene prompts)
  [5] AIRouter.generate() → SEO package (title + description + 30 hashtags)
  [6] VoiceEngine.generate_voice(text, channel=) → ElevenLabs MP3 via API
  [7] ImageEngine.generate_image(prompt) → Thumbnail PNG (currently placeholder)
  [8] [OPTIONAL] VideoEngine.render_video() → MP4 (blocked: needs HuggingFace)

External deps:  Gemini REST API, NVIDIA NIM, ElevenLabs API, pytrends
Persistence:    content_queue table (Supabase) — status=ready after generation
                voice file → temp_assets/
                thumbnail → temp_assets/

Success output: Full production package (script + voice + thumbnail + SEO)
                content_queue row with status="ready"
Failure path:   Each agent catches exception independently — partial results saved
                AIRouter has 20+ model fallback — never returns empty on generation

Upload flow (Phase 1 gate):
  Trigger:      content_queue row status="ready" + render_video=True + video_path set
  Entry:        SocialMediaEngine.upload_youtube_video(video_path, title, desc, tags, channel)
  Auth:         _get_youtube_credentials(channel) → DB api_keys.secret → file fallback
  Upload:       YouTube Data API v3 resumable upload
  Idempotency:  job_id check → skip if youtube_video_id already set
  Post-upload:  Update content_queue: youtube_video_id, youtube_url, youtube_status="published"
  Instagram:    SocialMediaEngine.post_instagram_reel(video_url, caption, hashtags, channel)
```

### AI Fallback Flow (Never-Down Pattern)

```
Request arrives → AIRouter.generate()

Tier 1 (fast, high quality):
  gemini → groq → nvidia(writing/chat) → anthropic → xai → openai → mistral → ollama

Tier 2 (last resort, only if ALL Tier 1 fail):
  nvidia general pool (Qwen-122B, Gemma-3-27B, Gemma-2-27B, Phi-3.5-Mini)
  → nvidia fast pool (Gemma-2-2B, ChatGLM3, Falcon3, Phi-3-Small)
  → nvidia chat pool (7 × LLaMA-3.3-70b)

Tier 3 (true failure — extremely unlikely):
  Return hardcoded fallback message
  + send email alert to GMAIL_USER

Alert emails (ai_router.py _notify_provider_failure()):
  - 401/invalid key    → "PROVIDER key expired, using FALLBACK, update .env"
  - 429/quota (>1h)   → "PROVIDER quota hit, using FALLBACK, resets midnight UTC"
  - All providers down → "CRITICAL: all AI down, status: [per-provider table]"
  Rate limit: same alert suppressed 6h to prevent spam
```

---

## 7. Next 3 Actions (Ordered by Revenue Impact)

### Action 1 — CRITICAL: Run SQL migration (5 minutes, unblocks Instagram DB token)
```sql
-- Paste in Supabase Dashboard → SQL Editor
-- File: supabase/migrations/20260317120000_fix_api_keys_secret_column.sql
ALTER TABLE public.api_keys ADD COLUMN IF NOT EXISTS secret TEXT NOT NULL DEFAULT '';
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns
    WHERE table_schema='public' AND table_name='api_keys' AND column_name='key')
  THEN
    UPDATE public.api_keys SET secret = key WHERE secret = '';
    ALTER TABLE public.api_keys DROP COLUMN IF EXISTS key;
  END IF;
END $$;
ALTER TABLE public.api_keys ALTER COLUMN secret DROP DEFAULT;
```

### Action 2 — HIGH: Run first end-to-end YouTube upload (validates Phase 1 gate)
```python
# Step 1: Verify YouTube token is still valid
python scripts/setup_youtube_oauth.py --test

# Step 2: Run full pipeline with video render
from src.agents.youtube_crew import YouTubeCrew
crew = YouTubeCrew()
result = crew.kickoff({
    "topic": "रात का राज़",
    "channel": "Riya's Dark Whisper",
    "format": "Long Form",
    "render_video": True,   # Set True to produce MP4
})
# NOTE: render_video=True requires HuggingFace key for images
# Without HuggingFace: use render_video=False, manually compile audio + static thumbnail

# Step 3: Upload
from src.core.social_media_engine import SocialMediaEngine
sme = SocialMediaEngine()
result = sme.upload_youtube_video(
    video_path="temp_videos/output.mp4",
    title="रात का राज़ | Riya की कहानी",
    description="...",
    tags=["hindi story", "riya", "dark romance"],
    channel_name="Riya's Dark Whisper",
    privacy="public",
)
print(result)  # Should contain youtube_url
```

### Action 3 — MEDIUM: Set Gmail credentials for alert emails
```
In .env:
GMAIL_USER=your_gmail@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx  (App Password, not regular password)

Generate App Password:
  myaccount.google.com → Security → 2-Step Verification → App passwords
  Select "Mail" + "Windows Computer" → Generate
```

---

## 8. Blockers

| Blocker | Severity | Owned by | Fix |
|---------|----------|----------|-----|
| `api_keys.secret` column not in Supabase | `CRITICAL` | Ajay | Run SQL migration (Action 1 above) |
| Full E2E upload not validated | `HIGH` | Ajay | Run upload test (Action 2 above) |
| HuggingFace 410 — no image generation | `HIGH` | Ajay | Get HF token at huggingface.co/settings/tokens OR use static thumbnail |
| Gmail credentials not set | `MEDIUM` | Ajay | Set GMAIL_USER + GMAIL_APP_PASSWORD in .env |
| Groq key expired | `LOW` | Ajay | Get new key at console.groq.com/keys (NVIDIA covers this in the meantime) |
| SelfEditor has direct write access | `MEDIUM` | Deferred | Post Phase 2 — PR-only workflow |

---

## 9. Owner + Timestamp

```
Updated by:   Claude Code (Engineering session)
Date/time:    2026-03-18
What changed:
  - ai_router.py: continuous fallback (Tier 2 last-resort NVIDIA pools)
  - ai_router.py: email alert system (_notify_provider_failure, _should_alert)
  - ai_router.py: default nvidia_task_type changed "writing" → "chat"
  - ai_router.py: Gemini fallback models fixed (real high-quota model names)
  - social_media_engine.py: line 126 syntax error fixed
  - memory_manager.py: embedding → gemini-embedding-001 REST API, 768 dims
  - scripts/test_all_systems.py: voice + memory test fixes
  - supabase/migrations/20260317120000_fix_api_keys_secret_column.sql: NEW
  - docs/CTO_REVIEW_RESPONSE_2026-03-18.md: CTO doc analysis + decisions

What remains:
  - Run SQL migration in Supabase SQL Editor
  - Set Gmail credentials in .env
  - Execute first YouTube upload (Phase 1 gate)
  - Get HuggingFace token for thumbnails/image generation

Next owner action:
  Read ONLY this file → execute Action 1 (SQL) → Action 2 (upload test) → Action 3 (Gmail)
  Do NOT start Phase 2 (batch Riya videos) until Action 2 succeeds.
```

---

## Quick Reference: Key Files & Entry Points

```
Content generation:   src/agents/youtube_crew.py        → YouTubeCrew.kickoff()
AI routing:           src/core/ai_router.py              → AIRouter.generate()
NVIDIA pool:          src/core/nvidia_pool.py            → NvidiaPool.generate()
Voice generation:     src/core/voice_engine.py           → generate_voice()
Social media upload:  src/core/social_media_engine.py    → upload_youtube_video()
Memory:               src/memory/memory_manager.py        → MemoryManager
Telegram bot:         src/core/aisha_brain.py            → AishaBrain
Autonomous scheduler: src/core/autonomous_loop.py        → AutonomousLoop
Email alerts:         src/core/gmail_engine.py           → GmailEngine.send_email()
Config (all keys):    src/core/config.py
Channel prompts:      src/core/prompts/personality.py    → CHANNEL_PROMPTS

Channels:
  Story With Aisha          → Gemini, Aisha voice (wdymxIQkYn7MJCYCQF2Q), warm Hindi romance
  Riya's Dark Whisper       → NVIDIA Mistral-Large-3, Riya voice (BpjGufoPiobT79j2vtj4), explicit dark
  Riya's Dark Romance Library → NVIDIA Mistral-Large-3, Riya voice, mafia/intense
  Aisha & Him               → Gemini, Aisha voice, couple shorts/reels

Revenue path:
  1K subs + 4K watch hours → YouTube Partner Program → ad revenue
  ~3 months at 1 video/day/channel
  Riya channels = highest RPM (adult niche)
```
