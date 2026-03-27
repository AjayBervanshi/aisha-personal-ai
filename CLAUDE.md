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

**RULE: ALL matching skills fire simultaneously — never stop at first match.**

### Core Development
| When working on... | Auto-use skill |
|--------------------|---------------|
| Any new Python file or function | `superpowers:test-driven-development` + `sc:implement` |
| Any DB migration or Supabase query | `supabase-postgres-best-practices` |
| Before committing code | `superpowers:verification-before-completion` → `commit` → `git-pushing` |
| After implementing a module | `coderabbit:code-review` + `owasp-security` + `sc:troubleshoot` (parallel) |
| Architecture decisions | `architecture-diagram-creator` + `sc:design` |
| Complex multi-file changes | `superpowers:dispatching-parallel-agents` |
| Bug or broken behavior | `superpowers:systematic-debugging` + `sc:troubleshoot` |
| Release / deploy | `owasp-security` + `release` + `verification-before-completion` |
| Documentation updates | `update-docs` + `sc:document` |
| Code quality improvement | `sc:improve` + `simplify` + `code-auditor` |

### Video & Content Pipeline
| When working on... | Auto-use skill |
|--------------------|---------------|
| YouTube video creation end-to-end | `remotion-production` + `content-creator` + `elevenlabs` + `imagen` |
| Voice narration (voice_engine.py) | `elevenlabs` + `remotion-production` |
| Thumbnail/image (image_engine.py) | `imagen` + `remotion-production` |
| YouTube upload (social_media_engine.py) | `remotion-production` (youtube upload mode) |
| Hindi story scripts | `content-creator` + `avoid-ai-writing` + `studio-producer` |
| YouTube SEO, titles, tags | `remotion-production` + `youtube-transcript` |
| Competitor research | `youtube-transcript` + `trend-researcher` |
| Instagram reel/post | `instagram-curator` + `content-creator` |
| TikTok content | `tiktok-strategist` + `create-viral-content` |
| Making content go viral | `create-viral-content` + `trend-researcher` + `growth-hacker` |
| Full video production session | `video-director` agent + `media-scout` agent + `post-producer` agent |

### AI Routing & Multi-Model
| When working on... | Auto-use skill |
|--------------------|---------------|
| ai_router.py changes | `claude-api` + `owasp-security` |
| Adding new AI provider | `claude-api` + `sc:design` + TDD |
| NVIDIA NIM pool (nvidia_pool.py) | `claude-api` (NVIDIA NIM mode) |
| Multi-model routing optimization | `claude-code-router` skill (if installed) |

### Autonomous Systems
| When working on... | Auto-use skill |
|--------------------|---------------|
| autonomous_loop.py (scheduler) | `sc:troubleshoot` + `superpowers:systematic-debugging` |
| self_editor.py / self_improvement.py | `owasp-security` + `coderabbit:code-review` |
| New autonomous job / pipeline | `superpowers:brainstorming` + `ln-400-story-executor` |
| Agent orchestration | `superpowers:dispatching-parallel-agents` + `loki-mode` |

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

## Slash Commands Available (All Auto-Activate — Use ALL Matching)

### Core Workflow
| Command | When to Auto-Use |
|---------|-----------------|
| `/commit` | Ready to commit changes |
| `/ultrathink` | Complex multi-step problem |
| `/pr-review` | Before merging any PR |
| `/analyze-codebase` | Full structural + security analysis |
| `/plan` | Feature needs planning |
| `/implement` | Implementing from plan |
| `/implement-tests` | Writing tests |
| `/execute` | Executing plan steps |
| `/cycle` | Full TDD cycle |
| `/review` | Code review vs acceptance |
| `/update-docs` | Docs need syncing |
| `/release` | Full release process |
| `/skip` | Skip current step |
| `/debug` | Something broken |
| `/refactor` | Cleanup existing code |
| `/security-audit` | Before any production deploy |
| `/ship` | Full PR pipeline: lint, commit, push |
| `/audit-project` | Full project health check |

### Content & Video
| Command | When to Auto-Use |
|---------|-----------------|
| `/content-creator` | YouTube/Instagram Hindi content |
| `/growth-hacker` | Channel growth strategy |
| `/instagram-curator` | Instagram content calendar |
| `/tiktok-strategist` | TikTok content strategy |

### SuperClaude (sc:*)
| Command | When to Auto-Use |
|---------|-----------------|
| `/sc:analyze` | Deep code analysis |
| `/sc:improve` | Quality improvement |
| `/sc:cleanup` | Remove dead code |
| `/sc:troubleshoot` | Diagnose runtime issues |
| `/sc:design` | Architecture design |
| `/sc:implement` | Feature implementation |
| `/sc:test` | Run tests with coverage |
| `/sc:document` | Generate docs |
| `/sc:spawn` | Multi-agent orchestration |
| `/sc:pm` | Full project manager mode |

---

## Active Issues (2026-03-25) — API Audit Results

### ❌ Keys to Renew
- **Groq** 401 Invalid → renew at console.groq.com
- **OpenAI** 401 Invalid → renew at platform.openai.com
- **Anthropic** 401 Invalid → renew at console.anthropic.com
- **xAI (Grok)** 403 BLOCKED — key was leaked & auto-revoked → get new key at console.x.ai
- **HuggingFace** 401 — looks like a placeholder key → get real token at huggingface.co/settings/tokens
- **Gemini** 429 Quota exceeded → wait for monthly reset or upgrade billing at aistudio.google.com

### 🚨 ElevenLabs CRITICAL
- Only **178 characters remaining** (starter plan, 50,140 limit)
- voice_engine.py already falls back to Edge-TTS on 422 (quota error) — SAFE
- Upgrade at elevenlabs.io before next YouTube story generation run

### ✅ Working Keys (as of 2026-03-25)
- **NVIDIA NIM**: 21/22 keys active (KEY_18 disabled — 403 forbidden)
- **YouTube API**: Working (AIzaSyD0rPY4...)
- **Instagram**: @story_with_aisha — token active
- **Gmail SMTP**: Working (aishaa1662001@gmail.com)
- **GitHub**: Working (AjayBervanshi)
- **Supabase PAT**: Working (Aisha-Brain-Cloud project)

### Other
- PR #2 on GitHub open — "Acknowledging user instructions"
- Guest migration SQL pending:
  `ALTER TABLE aisha_conversations ADD COLUMN IF NOT EXISTS guest_user_id BIGINT DEFAULT NULL;`

## Completed Implementations (2026-03-25)
- [x] `antigravity_agent.py` — render_video=True + auto upload/post (already wired)
- [x] `autonomous_loop.py` — platforms + auto_post to studio sessions (already wired)
- [x] `src/core/series_tracker.py` — episodic series DB + tracker class
- [x] `src/core/token_manager.py` — Instagram/YouTube token health
- [x] `src/telegram/bot.py` — /syscheck /studio /upgrade /voice /mood /aistatus all exist
- [x] `tests/test_smart_agent.py` — randomized smart test agent (5/5 passing)
- [x] Supabase `aisha_series` + `aisha_episodes` tables migration applied
- [x] Supabase Storage bucket `content-videos` created

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
