# AISHA BOSS AI TASK QUEUE

## Loophole Fixes & Enhancements

0. **[IN_PROGRESS] Install & Integrate Agent-Lightning & CallMe**
   - [x] Clone agent-lightning repository to workspace.
   - [x] Add it to Aisha's requirements.txt.
   - [x] Install package and test import.
   - [x] Set up CallMe plugin environment variables for Telnyx/Twilio.
   - [ ] Register `CallMe` capabilities with Aisha's brain.

1. **[IN_PROGRESS] Fix Deployment Pipeline**
   - [ ] Implement `merge_github_pr` in `src/core/self_improvement.py`.
   - [ ] Add Railway/Vercel redeploy webhook trigger.
   - [ ] Update Telegram handler in `src/telegram/bot.py` to call the real merge function.

2. **[QUEUED] CrewAI YouTube Tools**
   - [ ] Build `ElevenLabsTool` in `src/agents/tools/voice_tools.py`.
   - [ ] Build `HuggingFaceVideoTool` in `src/agents/tools/video_tools.py`.
   - [ ] Register tools with `Aria` and `Mia` in `src/agents/youtube_crew.py`.

3. **[QUEUED] AI Reliability (Embeddings)**
   - [ ] Add async/retry logic to `_generate_embedding` in `src/memory/memory_manager.py`.
   - [ ] Implement exponential backoff for rate limits.

4. **[QUEUED] Autonomous 3 AM Consolidation**
   - [ ] Implement `run_memory_consolidation` in `src/core/autonomous_loop.py`.
   - [ ] Extract facts/emotions from 24h history using Gemini.
   - [ ] Save to semantic/episodic memory tables.

5. **[QUEUED] Multi-Agent Refinement**
   - [ ] Test the "Boss Aisha" delegation flow.
   - [ ] Ensure `CrewAI` manager can spawn sub-crews correctly.

6. **[IN_PROGRESS] Antigravity Content Ops (Supabase Queue)**
   - [x] Add `content_jobs` + `content_performance` Supabase schema migration.
   - [x] Add queue worker: `src/agents/antigravity_agent.py`.
   - [x] Hook autonomous studio sessions to enqueue jobs first.
   - [ ] Add final video render step and pass `video_path` into queue payload.
   - [ ] Add YouTube + Instagram analytics pullback to populate `content_performance`.

7. **[DONE] Channel Identity System**
   - [x] Add `CHANNEL_PROMPTS` to `src/core/prompts/personality.py` (Story With Aisha, Riya's Dark Whisper, Riya's Dark Romance Library, Aisha & Him).
   - [x] Add `AISHA_ELEVENLABS_VOICE_ID`, `RIYA_ELEVENLABS_VOICE_ID`, `CHANNEL_VOICE_IDS` to `src/core/config.py`.
   - [x] Update `src/core/voice_engine.py` — `generate_voice(channel=)` picks ElevenLabs voice per channel.
   - [x] Update `src/agents/youtube_crew.py` — uses full CHANNEL_PROMPTS, trend research, correct voice per channel.
   - [x] Upgrade `supabase/functions/chat/index.ts` — Riya mode mood, channel routing, `preferredProvider` in `generateWithFallback`.
   - [x] New migration: `supabase/migrations/20260313000000_channel_prompts.sql`.

---

## Micro Earning Roadmap — 4 Phases

### Phase 1 — Foundation Setup (Day 1-3)
- [ ] Apply migration `20260313000000_channel_prompts.sql` to Supabase (`npx supabase db push`)
- [ ] Set all secrets in Supabase: `npx supabase secrets set --env-file .env --project-ref fwfzqphqbeicgfaziuox`
- [ ] Configure YouTube OAuth: set `YOUTUBE_CLIENT_ID` + `YOUTUBE_CLIENT_SECRET` in `.env`
- [ ] Complete YouTube OAuth flow → save token file → test upload with `social_media_engine.py`
- [ ] Configure Instagram Business API: set `INSTAGRAM_ACCESS_TOKEN` + `INSTAGRAM_BUSINESS_ID`
- [ ] Verify Aisha voice (`wdymxIQkYn7MJCYCQF2Q`) and Riya voice (`BpjGufoPiobT79j2vtj4`) work via ElevenLabs
- [ ] Verify `XAI_API_KEY` (Grok) works — run `/aistatus` on Telegram
- [ ] Deploy updated edge function: `npx supabase functions deploy chat --project-ref fwfzqphqbeicgfaziuox`
- [ ] Configure `GMAIL_USER` + `GMAIL_APP_PASSWORD` for Aisha email notifications

### Phase 2 — Content Machine (Week 1-2)
- [ ] Run first full pipeline: `python -m src.agents.run_youtube --channel "Story With Aisha" --topic "Office Romance"`
- [ ] Run first Riya pipeline: `python -m src.agents.run_youtube --channel "Riya's Dark Whisper" --topic "Mumbai Raat"`
- [ ] Verify voice files saved in `temp_voice/` with correct ElevenLabs voices
- [ ] Verify thumbnails saved in `temp_assets/` via HuggingFace
- [ ] Build video render step: combine `voice_path` + thumbnail into MP4 (use `moviepy` or `ffmpeg`)
- [ ] Add `video_path` to `content_jobs` queue payload in `antigravity_agent.py`
- [ ] Auto-post first video to YouTube via `social_media_engine.upload_youtube_video()`
- [ ] Auto-post reel to Instagram via `social_media_engine.post_instagram_reel()`
- [ ] Verify both posts appear live on respective platforms

### Phase 3 — Growth Loop (Month 1-2)
- [ ] Target: YouTube monetization threshold → 1,000 subscribers + 4,000 watch hours (Story With Aisha)
- [ ] Enable YouTube Partner Program on first eligible channel
- [ ] Pull YouTube Analytics into `content_performance` table (views, watch time, CTR, revenue estimate)
- [ ] Pull Instagram Insights into `content_performance` table (reach, saves, shares, profile visits)
- [ ] Build weekly analytics review: Aisha reads `content_performance`, identifies top 3 story types
- [ ] Auto-adjust `autonomous_loop.py` topic selection based on performance data
- [ ] Target 3-4 videos/week per channel using `autonomous_loop.py` 3AM cron

### Phase 4 — Scale (Month 2+)
- [ ] Activate all 4 channels simultaneously (Story With Aisha, Riya's Dark Whisper, Riya's Dark Romance Library, Aisha & Him)
- [ ] Schedule daily automated content via `autonomous_loop.py` (each channel gets 1 job/day)
- [ ] Implement performance-based topic selection: top-performing story types get 70% of new content
- [ ] Add A/B thumbnail testing: generate 2 thumbnails per video, pick winner after 48h CTR data
- [ ] Track total monthly revenue per channel in `aisha_finance` table
- [ ] Add Shorts strategy for "Aisha & Him" channel (30-60s clips → faster subscriber growth)
- [ ] Cross-promote: use Instagram Reels to drive YouTube subscribers
- [ ] Optimize ElevenLabs usage: cache repeated story intro/outro voice segments
