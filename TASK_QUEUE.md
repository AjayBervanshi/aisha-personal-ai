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
