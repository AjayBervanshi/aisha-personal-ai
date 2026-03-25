# Aisha — Claude Code Project Instructions

## Project Overview
Aisha is a personal AI assistant deployed on Render, communicating via Telegram.
She autonomously generates YouTube content, manages expenses, sends reminders,
and improves her own code via GitHub PRs.

**Owner:** Ajay (Telegram ID: 1002381172)
**Repo:** https://github.com/AjayBervanshi/aisha-personal-ai.git
**Deploy:** https://aisha-bot-yudp.onrender.com

---

## Critical Rules

### Testing — Telegram Web ONLY
- ALL Aisha testing MUST be done via `web.telegram.org` in a browser (Playwright)
- Connect to Edge via CDP: `p.chromium.connect_over_cdp("http://localhost:9222")`
- Edge launched with: `--remote-debugging-port=9222`
- NEVER use webhook injection (curl POST to `/webhook`) for testing
- Test script: `PYTHONUTF8=1 /e/VSCode/.venv/Scripts/python tests/test_full_audit.py`

### No Secrets in Code
- All API keys must come from `os.getenv()` or Supabase `api_keys` table
- GitHub token: `GITHUB_TOKEN` env var OR Supabase `api_keys` where `name='GITHUB_TOKEN'`
- Never commit `.env` file

### Python Environment
- Always use: `/e/VSCode/.venv/Scripts/python`
- Activate: `source /e/VSCode/.venv/Scripts/activate`
- Shell: bash syntax (not PowerShell), forward slashes

### AI Routing
- Primary: Gemini 2.5-flash via REST requests (NOT google.genai SDK — DNS fails)
- Fallback: Groq llama-3.3-70b
- Riya channels: xAI Grok (adult content, currently 403 — falls back to Groq)

---

## Key Source Files

| File | Purpose |
|------|---------|
| `src/telegram/bot.py` | Telegram bot + health server + autonomous loop thread |
| `src/core/ai_router.py` | 8-provider AI fallback chain |
| `src/core/autonomous_loop.py` | 24/7 scheduler (12+ jobs) |
| `src/core/self_editor.py` | Aisha patches her own code (PR-gated) |
| `src/core/self_improvement.py` | GitHub PR creation/merge for self-improvement |
| `src/core/self_repair.py` | File integrity monitor + auto-restore from GitHub |
| `src/core/voice_engine.py` | ElevenLabs + Edge-TTS voice generation |
| `src/core/video_engine.py` | Ken Burns MP4 rendering (MoviePy) |
| `src/core/social_media_engine.py` | YouTube upload + Instagram Reel posting |
| `src/core/series_tracker.py` | Episodic YouTube Shorts series continuity tracker |
| `src/core/token_manager.py` | Instagram + YouTube OAuth token health + refresh |
| `src/agents/youtube_crew.py` | 5-agent content pipeline (Research→Script→Visual→SEO→Voice) |
| `src/agents/antigravity_agent.py` | Job queue processor → render → upload → post |
| `src/core/image_engine.py` | Image generation (Gemini → DALL-E → Pollinations) |
| `src/core/config.py` | All env vars, CHANNEL_VOICE_IDS, CHANNEL_AI_PROVIDER |
| `src/core/prompts/personality.py` | MOOD_INSTRUCTIONS + CHANNEL_PROMPTS |

---

## Skills Claude Should Auto-Use When Working on Aisha

| When working on... | Auto-use skill |
|--------------------|---------------|
| Any new Python file or function | `superpowers:test-driven-development` |
| Any DB migration or Supabase query | `supabase-postgres-best-practices` |
| Before committing code | `superpowers:verification-before-completion` then `commit` |
| After implementing a module | `coderabbit:code-review` + `owasp-security` |
| Voice/audio generation code | `elevenlabs` skill |
| Thumbnail/image generation code | `imagen` skill |
| YouTube competitor analysis | `youtube-transcript` skill |
| Content scripts (Hindi stories) | `content-creator` + `avoid-ai-writing` |
| Architecture decisions | `architecture-diagram-creator` |
| Complex multi-file changes | `superpowers:dispatching-parallel-agents` |
| Release / deploy | `release` + `owasp-security` |
| Documentation updates | `update-docs` + `sc:document` |

---

## Aisha's Extended API Capabilities (use all .env keys)

| Capability | API / Method | File |
|-----------|-------------|------|
| Voice narration | ElevenLabs (`ELEVENLABS_API_KEY`) | `voice_engine.py` |
| Voice fallback | Edge-TTS (free) | `voice_engine.py` |
| Image generation | Gemini imagen (`GEMINI_API_KEY`) | `image_engine.py` |
| Image fallback | DALL-E (`OPENAI_API_KEY`) → Pollinations (free) | `image_engine.py` |
| Video rendering | MoviePy (local) | `video_engine.py` |
| YouTube upload | Google Data API v3 (`tokens/youtube_token.json`) | `social_media_engine.py` |
| Instagram post | Meta Graph API (`tokens/instagram_token.json`) | `social_media_engine.py` |
| HuggingFace inference | `HUGGINGFACE_API_KEY` — sentiment, classification, NLP | (future: `hf_engine.py`) |
| Competitor video analysis | YouTube transcript + AI summary | (future: `competitor_analyzer.py`) |
| Email/Gmail | Gmail API (`GMAIL_APP_PASSWORD`) | (reminders) |

---

## Supabase
- Project ref: `tgqerhkcbobtxqkgihps`
- URL: `https://tgqerhkcbobtxqkgihps.supabase.co`
- MCP available: use `mcp__supabase__*` tools directly

Key tables: `aisha_conversations`, `aisha_memories`, `aisha_expenses`,
`aisha_reminders`, `content_jobs`, `api_keys`, `aisha_audit_log`

---

## NVIDIA NIM Pool
- 22 API keys × 1,000 credits/month = 22,000 total
- File: `src/core/nvidia_pool.py`
- Task routing: writing→Mistral-Large-3, chat→LLaMA-3.3, code→Codestral,
  vision→Phi-4, video→Phi-3-128K, fast→Gemma-2B/Falcon3

---

## YouTube Channels

| Channel | Language | AI | Voice |
|---------|----------|----|-------|
| Story With Aisha | Hindi Devanagari, love stories | Gemini | Aisha `wdymxIQkYn7MJCYCQF2Q` |
| Riya's Dark Whisper | Hindi Devanagari, explicit adult | Grok→Groq | Riya `BpjGufoPiobT79j2vtj4` |
| Riya's Dark Romance Library | Hindi Devanagari, mafia romance | Grok→Groq | Riya `BpjGufoPiobT79j2vtj4` |
| Aisha & Him | Hinglish/English, couple shorts | Gemini | Aisha `wdymxIQkYn7MJCYCQF2Q` |

**Hindi content: 100% Devanagari script — NEVER Roman transliteration**

---

## Slash Commands Available

| Command | Description |
|---------|-------------|
| `/commit` | Stage + conventional commit + push |
| `/ultrathink` | Deep analysis mode for complex problems |
| `/pr-review` | Review open GitHub PRs before merging |
| `/analyze-codebase` | Full structural + security analysis |
| `/content-creator` | Generate YouTube/Instagram content |
| `/growth-hacker` | Growth strategy for channels |
| `/instagram-curator` | Instagram content calendar |
| `/tiktok-strategist` | TikTok content strategy |
| `/plan` | Doc-driven feature planning |
| `/implement` | Implement from plan doc |
| `/implement-tests` | Write tests for a feature |
| `/execute` | Execute next plan steps |
| `/cycle` | Full TDD cycle (plan→test→implement→verify→commit) |
| `/review` | Comprehensive code review |
| `/update-docs` | Sync documentation with code |
| `/release` | Full release process |
| `/skip` | Skip current plan step |

---

## Active Issues (2026-03-25)
- Groq API 401 — renew at console.groq.com
- xAI Grok 403 — no credits (Riya falls back to Groq)
- PR #2 on GitHub open — "Acknowledging user instructions"
- Guest migration SQL pending:
  `ALTER TABLE aisha_conversations ADD COLUMN IF NOT EXISTS guest_user_id BIGINT DEFAULT NULL;`

## Pending Implementations (2026-03-25 — parallel agents executing)
- [ ] `antigravity_agent.py` — wire render_video=True + auto upload/post
- [ ] `autonomous_loop.py` — pass platforms + auto_post to studio sessions
- [ ] `src/core/series_tracker.py` — episodic series DB + tracker class (NEW)
- [ ] `src/core/token_manager.py` — Instagram/YouTube token health (NEW)
- [ ] `src/telegram/bot.py` — missing commands: /syscheck /studio /upgrade /voice /mood /aistatus
- [ ] `tests/test_smart_agent.py` — randomized smart test agent (NEW)
- [ ] Supabase `aisha_series` + `aisha_episodes` tables migration
- [ ] Supabase Storage bucket `content-videos` (for Instagram Reel video hosting)

---

## MCP Servers
- **filesystem**: Read/write Aisha project files
- **memory**: Persistent cross-session memory
- **context7**: Up-to-date library docs
- **playwright**: Browser automation (Telegram testing)
- **chrome-devtools**: CDP to running Edge
- **github**: PR/issue management (PAT configured)
- **supabase**: Direct DB management (token configured)
- **render**: Deploy management + health checks
