# Aisha Project — Session Context

## Project
- **Name:** Aisha — Personal AI Assistant
- **Repo:** https://github.com/AjayBervanshi/aisha-personal-ai.git
- **Local:** `E:/VSCode/Aisha`
- **Deploy:** Render (https://aisha-bot-yudp.onrender.com)
- **Owner:** Ajay (Telegram ID: 1002381172)

## Tech Stack
- Python 3.11 + python-telegram-bot 20.x
- Supabase (PostgreSQL + Edge Functions)
- ElevenLabs TTS (Aisha + Riya voices)
- Gemini 2.5-flash via REST (primary AI)
- Groq llama-3.3-70b (fallback)
- xAI Grok (Riya adult channels)
- NVIDIA NIM pool (22 keys × 1000 credits)

## Key Env Vars (loaded from .env or Render)
- TELEGRAM_BOT_TOKEN
- SUPABASE_URL / SUPABASE_SERVICE_KEY
- GEMINI_API_KEY
- GROQ_API_KEY
- ELEVENLABS_API_KEY
- XAI_API_KEY
- GITHUB_TOKEN (also in Supabase api_keys table)

## Testing Rules
- ALL testing via web.telegram.org in browser (Playwright CDP)
- NEVER use webhook injection (curl POST to bot endpoint)
- Edge launched with: --remote-debugging-port=9222
- CDP: p.chromium.connect_over_cdp("http://localhost:9222")

## Active Issues (as of 2026-03-22)
- Groq API returning 401 (needs renewal at console.groq.com)
- Guest migration SQL pending (Supabase Dashboard → SQL Editor)
- PR #2 on GitHub open ("Acknowledging user instructions")
- xAI Grok 403 (no credits — Riya channels fall back to Groq)
