# Aisha State Handoff — Phase 2 Start
`State: Phase 2 (Content Production) | Confidence: HIGH | Last runtime verification: 2026-03-18 — YouTube E2E upload CONFIRMED (video_id: a175vEVOBiU)`

**Reviewed against:** `docs/AGENT_STATE_FLOW_STANDARD.md`
**Supersedes:** `docs/AISHA_STATE_HANDOFF_2026-03-18.md`

---

## 1. Verified in Code

| Claim | Evidence |
|-------|----------|
| Channel identity prompts exist for all 4 channels | `src/core/prompts/personality.py:62-160` — CHANNEL_PROMPTS dict |
| Channel voice IDs configured | `src/core/config.py:91-100` — AISHA + RIYA IDs + CHANNEL_VOICE_IDS dict |
| Voice engine uses channel-aware voice selection | `src/core/voice_engine.py:114` — `_generate_elevenlabs(channel=)` param |
| youtube_crew uses CHANNEL_PROMPTS + trend research | `src/agents/youtube_crew.py:123-154` — CHANNEL_PROMPTS.get(channel) priority |
| Edge function has Riya mode + channel routing | `supabase/functions/chat/index.ts:62,102-108,507-509` |
| AI router has 20+ model waterfall + last-resort NVIDIA | `src/core/ai_router.py` — Tier1→Tier2→Tier3 |
| Email alerts on model failure | `src/core/ai_router.py` — `_notify_provider_failure()` with 6h cooldown |
| YouTube upload uses idempotency guard | `src/core/social_media_engine.py:258-266` — checks youtube_video_id before upload |
| Instagram upload uses idempotency guard | `src/core/social_media_engine.py:139-147` — checks instagram_post_id |
| Token refresh handled automatically | `tokens/youtube_token.json` — refreshed 2026-03-18, valid |
| gmail_engine.py functional (SMTP + IMAP) | `src/core/gmail_engine.py:32-39` — SMTP_SSL port 465 |
| Telegram bot has /produce command | `src/telegram/bot.py:311-340` — spawns run_youtube subprocess |
| `api_keys.secret` column migration exists | `supabase/migrations/20260317120000_fix_api_keys_secret_column.sql` |
| `api_keys.active` column migration exists | `supabase/migrations/20260318000000_fix_api_keys_active_column.sql` |

---

## 2. Verified in Runtime

| Claim | Evidence |
|-------|----------|
| 17/17 system tests pass | `docs/SYSTEM_TEST_REPORT_2026-03-17.md` — Gemini 2.2s, Mistral-Large-3 working |
| **YouTube E2E upload CONFIRMED** | `video_id: a175vEVOBiU` — unlisted test video uploaded 2026-03-18 |
| YouTube token valid + auto-refresh working | `Credentials.refresh(Request())` succeeded — `expiry` updated |
| `moviepy 2.1.2` installed and working | Test video created: `temp_assets/test_upload.mp4` (508KB, 30s) |
| `google-api-python-client` + `google-auth` installed | Import test passed 2026-03-18 |
| Token file fallback works when DB is missing column | `[YouTube] Using token file fallback: tokens/youtube_token.json` |
| Aisha voice (ElevenLabs): working | `temp_voice/aisha_voice_*.mp3` files present |
| Riya voice (ElevenLabs): working | Test report 2026-03-17 — 24K bytes |
| NVIDIA Mistral-Large-3 (Riya pipeline): working | Riya script 15,116 chars generated |
| Gemini 2.5-flash (Aisha pipeline): working | Aisha script 33,735 chars generated |
| `api_keys.secret` column migration: APPLIED | Confirmed by Ajay — 2026-03-18 |

---

## 3. Unverified / Assumed

| Item | Reason Not Verified |
|------|---------------------|
| `api_keys.active` column migration NOT YET APPLIED | Created 2026-03-18 — needs Ajay to run in SQL Editor |
| DB token loading for YouTube (`YOUTUBE_OAUTH_TOKEN` row) | `api_keys.active` column missing → DB load fails → falls back to file (works but suboptimal) |
| Instagram token/posting working | No Instagram test run yet; token file exists but not verified |
| Video render MP4 from full pipeline (not just test) | Only tested with pre-existing voice file, not fresh pipeline output |
| Gmail email alerts working end-to-end | `GMAIL_USER` + `GMAIL_APP_PASSWORD` not yet set in `.env` |
| Telegram `/produce` → YouTube auto-upload | No `/approve` or `/upload` command in bot — **GAP: bot can produce but cannot upload** |
| xAI Grok working for Riya channels | Still 403 (no credits) — NVIDIA Mistral-Large-3 substituting |

---

## 4. Conflicts With Other Docs

| Conflict | Resolution |
|----------|------------|
| `CTO_REVIEW_RESPONSE_2026-03-18.md` says "Phase 1 DONE = 17/17 tests" | CTO correctly refined: Phase 1 = one YouTube upload. **Now DONE.** |
| `TASK_QUEUE.md` Phase 2 Step 1: "apply migration" | `secret` column: DONE. `active` column: still needs applying. |
| `CTO_RESPONSE_REVIEW_2026-03-18.md`: "run setup_youtube_oauth.py" | **Outdated** — token already existed, just needed `client_id` injected from `youtube_client_secret.json`. Do NOT re-run OAuth flow (will break existing token). |
| `docs/AGENT_STATE_FLOW_STANDARD.md` has no versioning field | Suggestion: add `Version: N` to canonical state line for doc evolution tracking |

---

## 5. Current State Snapshot

```
Phase:          Phase 2 — Content Production (STARTED)
Phase 1 Gate:   ✅ PASSED — YouTube E2E upload confirmed (video_id: a175vEVOBiU)
Revenue Status: 0 subs, 0 watch hours — first video uploaded unlisted as test
AI Stack:       Gemini 2.5-flash → NVIDIA Mistral-Large-3 → LLaMA-3.3 → 20+ fallbacks
Voice:          ElevenLabs Aisha (wdymxIQkYn7MJCYCQF2Q) + Riya (BpjGufoPiobT79j2vtj4)
YouTube Token:  ✅ Valid (refreshed 2026-03-18, scopes: upload + readonly + analytics)
DB Status:      secret column ✅ | active column ❌ (migration written, not applied)
Gmail Alerts:   ❌ GMAIL_USER + GMAIL_APP_PASSWORD not set
Telegram Bot:   ✅ /produce (generates) | ❌ NO /upload command (gap — see Section 8)
```

---

## 6. Flow Snapshot

### Content Factory Flow (full path to revenue)
```
Trigger:            Ajay sends /produce Story With Aisha  (or autonomous_loop cron)
Entry point:        src/telegram/bot.py:cmd_produce()
Orchestrator:       src/agents/youtube_crew.py:YouTubeCrew.kickoff()
  → Research:       TrendEngine → AI (Gemini/NVIDIA)
  → Script:         15,000+ char Devanagari story
  → Visuals:        Thumbnail prompt + 5 scene prompts
  → SEO:            Title + description + 30 hashtags
  → Voice:          ElevenLabs (channel-specific voice ID)
  → Thumbnail:      PNG via image_engine
  → Video:          MP4 if render_video=True (moviepy: image+audio)
Persistence:        content_queue table (status=ready)
Upload path:        SocialMediaEngine.upload_youtube_video(video_path, ...)
                    → _get_youtube_credentials() → token file fallback
                    → google-api-python-client → YouTube Data API v3
Success output:     {'success': True, 'video_id': '...', 'url': 'https://youtube.com/watch?v=...'}
Failure path:       Exception logged, content_queue.youtube_status = 'failed'
```

### AI Fallback Flow
```
Tier 1 (named providers):  Gemini → Groq → NVIDIA-writing → Anthropic → xAI → OpenAI → Mistral
Tier 2 (NVIDIA last-resort): general pool → fast pool → chat pool
Tier 3:                      Hardcoded fallback message + critical email alert
Alert types:                 key_expired (401) | quota_hit (429) | all_providers_down
Anti-spam:                   6-hour cooldown per alert type
```

### YouTube Token Flow (fixed 2026-03-18)
```
youtube_token.json had empty client_id/client_secret
  → Fixed: injected from youtube_client_secret.json
  → Token refreshed via google.auth.transport.requests.Request()
  → Saved back to tokens/youtube_token.json
  → Credentials.from_authorized_user_file() now works
```

---

## 7. Next 3 Actions

### Action 1 — Apply `api_keys.active` migration (MEDIUM, 2 min)
Run in Supabase SQL Editor:
```sql
ALTER TABLE public.api_keys ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE;
```
Full script: `supabase/migrations/20260318000000_fix_api_keys_active_column.sql`
**Why:** Enables token loading from DB instead of file fallback. Required for multi-channel token management.

### Action 2 — Add `/upload` command to Telegram bot (HIGH, 30 min)
Gap: `/produce` generates content but there's no Telegram command to upload the result to YouTube.
After `/produce` completes, Ajay must currently run Python manually to upload.
Fix: Add `/upload <job_id>` command to `src/telegram/bot.py` that calls `SocialMediaEngine.upload_youtube_video()`.
Or: make `/produce` auto-upload after generation (simpler for Phase 2).

### Action 3 — Set Gmail credentials and start real content production (HIGH)
Set in `.env`:
```
GMAIL_USER=aishaa1662001@gmail.com
GMAIL_APP_PASSWORD=<app password from Google Account settings>
```
Then run first real production pipeline:
```bash
python -m src.agents.run_youtube --channel "Story With Aisha" --topic "Office Romance" --upload
```

---

## 8. Blockers

| Severity | Blocker | Fix |
|----------|---------|-----|
| `MEDIUM` | `api_keys.active` column missing in DB | Run `20260318000000_fix_api_keys_active_column.sql` in SQL Editor |
| `MEDIUM` | No `/upload` Telegram command — Ajay can produce but not upload from phone | Add `/upload` or auto-upload after `/produce` |
| `MEDIUM` | Gmail not set up — no email alerts on model failure | Set `GMAIL_USER` + `GMAIL_APP_PASSWORD` in `.env` |
| `LOW` | xAI Grok 403 (no credits) — Riya uses NVIDIA Mistral as substitute | Get xAI credits at x.ai console (or keep NVIDIA) |
| `LOW` | SelfEditor has direct file write — safety risk | Deferred to Phase 3 (post-first-revenue) |

---

## 9. Owner + Timestamp

### Handoff Footer
- **Updated by:** Claude Code (Engineering Lead session)
- **Date/time:** 2026-03-18
- **What changed:**
  - Phase 1 Gate PASSED — YouTube E2E upload confirmed (`video_id: a175vEVOBiU`)
  - `youtube_token.json` fixed — `client_id` + `client_secret` injected from `youtube_client_secret.json`
  - Token refreshed and saved (was expired since 2026-03-16)
  - `moviepy 2.1.2` installed — video render capability confirmed
  - New migration written: `20260318000000_fix_api_keys_active_column.sql`
  - Gmail question answered (see companion doc below)
  - Telegram capability gap identified: no `/upload` command
- **What remains:**
  - Apply `active` column migration in Supabase
  - Add `/upload` Telegram command
  - Set Gmail credentials
  - Run first real (non-test) content production pipeline
  - Make first video public on YouTube (currently unlisted test)
- **Next owner action:** Apply the `active` migration, then add `/upload` to bot.py, then run `/produce Story With Aisha` from Telegram

---

## Appendix A — Answers to Ajay's Questions

### Q1: Gmail — Aisha's email or mine?

**Use Aisha's Gmail:** `aishaa1662001@gmail.com`

Evidence: `run_youtube.py:37` already hardcodes this as the RECIPIENT for production notifications. So set:
```
GMAIL_USER=aishaa1662001@gmail.com
GMAIL_APP_PASSWORD=<16-char app password>
```

**How to get App Password:**
1. Go to Google Account → Security → 2-Step Verification (must be ON)
2. Scroll to "App Passwords" at bottom
3. Create one for "Mail" + "Windows Computer"
4. Copy the 16-char password into `.env`

This email is ONLY for:
- Sending AI model failure alerts TO Ajay
- Sending production completion notifications TO Ajay (`aishaa1662001@gmail.com` sends TO itself in test, real usage should send to Ajay's email)

**YouTube does NOT use Gmail.** YouTube uses OAuth tokens (`tokens/youtube_token.json`). These are completely separate.

### Q2: Can Aisha via Telegram do everything Claude Code can do?

**Short answer: NO. They serve different purposes.**

| Capability | Telegram (Aisha Bot) | Claude Code (this session) |
|------------|---------------------|---------------------------|
| Chat with Aisha, personal support | ✅ Full | ✅ Yes |
| Generate YouTube script + voice + thumbnail | ✅ `/produce` | ✅ Yes |
| Run autonomous studio session | ✅ `/studio` | ✅ Yes |
| **Upload video to YouTube** | ❌ **NO COMMAND** (gap) | ✅ Direct Python |
| Post to Instagram | ❌ No command | ✅ Direct Python |
| Check AI provider status | ✅ `/aistatus` | ✅ Yes |
| **Edit/fix Aisha's code** | ⚠️ `/selfaudit` (risky) | ✅ Safe + reviewed |
| Run database migrations | ❌ No | ✅ Yes |
| Debug errors, read logs | ❌ No | ✅ Full access |
| Install Python packages | ❌ No | ✅ Yes |
| Refresh OAuth tokens | ❌ No | ✅ Done today |
| Create new Telegram commands | ❌ No | ✅ Yes |

**Architecture gap to fix:**
Telegram bot has `/produce` but no `/upload`. After `/produce` finishes, the content sits in `temp_voice/` and `temp_assets/` but cannot be uploaded from Telegram.

**Recommended fix:** Add to `bot.py`:
```
/upload Story With Aisha  →  uploads last produced content for that channel
```
This would make Telegram a complete production-to-publish console.

**What Telegram will NEVER replace:**
Code maintenance, debugging, migrations, and architectural changes need Claude Code. Telegram is the production console; Claude Code is the engineering workbench.

---

## Appendix B — Review of AGENT_STATE_FLOW_STANDARD.md

### Strengths ✅
- 9-section structure enforces consistent, evidence-based handoffs
- Evidence rules prevent vague claims ("migration applied" without proof)
- Severity labels (`CRITICAL/HIGH/MEDIUM/LOW`) make triage instant
- Flow Snapshot template captures the full pipeline in one readable block
- Handoff footer prevents context loss between sessions

### Gaps / Suggested Improvements

| Gap | Suggestion |
|----|------------|
| No versioning field | Add `Version: N` to canonical state line: `State: Phase 2 | Version: 2 | Confidence: HIGH | ...` |
| No "doc update frequency" guidance | Add rule: create new `_VN.md` when phase changes; update in-place for minor updates |
| Handoff footer has no confidence per item | Add `[HIGH/LOW confidence]` marker to each "What remains" bullet |
| No "Discovered This Session" section | Add Section 2b: items found true during this session that weren't in prior docs |
| Flow Snapshot has no "last tested" timestamp | Add `Last tested:` field to each flow |
| No guidance on max doc age | Add: "Any handoff doc older than 7 days without runtime verification must be flagged as STALE" |

### Verdict
The standard is production-grade for a solo operation. The 6 gaps are LOW priority — the existing structure successfully prevented multiple misunderstandings in this session (e.g., flagging the OAuth re-run as unnecessary when the token existed). Keep using as-is; implement versioning when Phase 3 begins.
