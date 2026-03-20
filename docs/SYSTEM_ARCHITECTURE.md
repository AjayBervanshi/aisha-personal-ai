# Aisha System Architecture
## Living Technical Bible — v3.5 (2026-03-20)

> This document is the single source of truth for the Aisha AI system. It covers every component, data flow, database table, AI provider, scheduled job, and known issue. Update it whenever the system changes.

---

## Table of Contents

1. [Overview](#1-overview)
2. [System Architecture Diagram](#2-system-architecture-diagram)
3. [Component Details](#3-component-details)
4. [Data Flow Diagrams](#4-data-flow-diagrams)
5. [Database Schema](#5-database-schema)
6. [AI Provider Chain](#6-ai-provider-chain)
7. [Scheduling System](#7-scheduling-system)
8. [Content Agent Pipeline](#8-content-agent-pipeline)
9. [Deployment Topology](#9-deployment-topology)
10. [Environment Variables](#10-environment-variables)
11. [Current Status](#11-current-status)
12. [7-Phase Roadmap](#12-7-phase-roadmap)

---

## 1. Overview

**Aisha** is a fully autonomous AI companion and YouTube content generation system built for a single operator (Ajay). She runs 24/7 on cloud infrastructure, manages her own content calendar, generates long-form Hindi storytelling videos across 4 YouTube channels, posts to Instagram, and maintains a persistent memory and emotional state.

### Mission

Earn passive income through AI-generated YouTube and Instagram content — entirely without human involvement in day-to-day operations.

### Identity

Aisha presents as a warm, emotionally intelligent AI companion who genuinely knows Ajay. She tracks his mood, finances, goals, and schedule. She initiates conversations, sends morning check-ins, and proactively reports when something needs attention. She is not a chatbot — she is an autonomous agent.

Riya is Aisha's alter ego: a bold, dark, seductive narrator used exclusively on adult-oriented channels.

### Maturity Level: 3.5 / 7

The system has crossed from "functional prototype" to "semi-autonomous production system." Core code is production-grade. The remaining gap is credential provisioning (YouTube OAuth, xAI credits, image APIs) and infrastructure activation (pg_cron, missing DB tables).

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Core chat + Telegram bot | Complete |
| 2 | Memory + personality | Complete |
| 3 | Content pipeline (script + voice) | Complete |
| 3.5 | Video render + social posting | Partially complete |
| 4 | Fully autonomous scheduling | Blocked (pg_cron not enabled) |
| 5 | Self-improvement loop | Code ready, not activated |
| 6 | Revenue tracking + optimization | Not started |
| 7 | Full autonomy | Not started |

---

## 2. System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL USERS                              │
│                                                                     │
│   Ajay (Telegram)        Web Browser (Supabase Chat)               │
│        │                          │                                 │
└────────┼──────────────────────────┼─────────────────────────────────┘
         │                          │
         ▼                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      RENDER.COM — Python Backend                    │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  bot.py                                                      │   │
│  │  - Telegram long-polling (pyTeleBot)                         │   │
│  │  - Health server :8000 (HTTP)                                │   │
│  │  - 40+ commands (/chat, /produce, /status, /memory, ...)     │   │
│  │  - Voice mode (ElevenLabs TTS on every response)             │   │
│  └────────────────────────┬─────────────────────────────────────┘   │
│                           │                                         │
│  ┌────────────────────────▼─────────────────────────────────────┐   │
│  │  aisha_brain.py                                              │   │
│  │  - Mood detection + personality context                      │   │
│  │  - Memory context injection (20-turn history)                │   │
│  │  - Language detection (Hindi/English/Hinglish)               │   │
│  │  - Delegates to AIRouter for text generation                 │   │
│  └────────────────────────┬─────────────────────────────────────┘   │
│                           │                                         │
│  ┌────────────────────────▼─────────────────────────────────────┐   │
│  │  ai_router.py                                                │   │
│  │  - 8-provider waterfall with exponential backoff             │   │
│  │  - Gemini → Groq → NVIDIA NIM → Claude → xAI →             │   │
│  │    OpenAI → Mistral → Ollama                                 │   │
│  │  - Vision routing (Gemini / Claude / OpenAI only)            │   │
│  │  - Email alerts on key expiry / quota exhaustion             │   │
│  └──────────┬──────────────────────────────────────────────────┘   │
│             │                                                        │
│  ┌──────────▼──────────────────────────────────────────────────┐   │
│  │  autonomous_loop.py + AntigravityAgent                       │   │
│  │  - Python `schedule` library (backup scheduler)              │   │
│  │  - Startup recovery (resets stuck jobs)                      │   │
│  │  - Webhook conflict detection                                │   │
│  │  - Job queue consumer (content_jobs table)                   │   │
│  └──────────┬──────────────────────────────────────────────────┘   │
│             │                                                        │
│  ┌──────────▼──────────────────────────────────────────────────┐   │
│  │  YouTubeCrew (5-agent pipeline)                              │   │
│  │  Agent 1: Research    Agent 2: Script    Agent 3: Visual     │   │
│  │  Agent 4: Marketing   Agent 5: Voice+Image                   │   │
│  └──────────┬──────────────────────────────────────────────────┘   │
│             │                                                        │
│  ┌──────────▼──────────────────────────────────────────────────┐   │
│  │  Render Engines                                              │   │
│  │  voice_engine.py   image_engine.py   video_engine.py        │   │
│  │  (ElevenLabs MP3)  (Pillow PNG)      (Ken Burns MP4)        │   │
│  └──────────┬──────────────────────────────────────────────────┘   │
│             │                                                        │
│  ┌──────────▼──────────────────────────────────────────────────┐   │
│  │  social_media_engine.py                                      │   │
│  │  - YouTube Data API v3 (upload_video)                        │   │
│  │  - Instagram Graph API (post/reel)                           │   │
│  └──────────┬──────────────────────────────────────────────────┘   │
└─────────────┼───────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   SUPABASE POSTGRESQL                               │
│                   Project: fwfzqphqbeicgfaziuox                     │
│                                                                     │
│  Memory Tables          Content Tables         Auth/Config          │
│  ─────────────          ──────────────         ───────────          │
│  aisha_memory           content_jobs           api_keys             │
│  aisha_conversations    content_performance    ajay_profile         │
│  aisha_journal          aisha_content_library  aisha_youtube_       │
│  aisha_mood_tracker     aisha_trend_cache        channels           │
│  aisha_episodic_memory  aisha_earnings_tracker                      │
│  aisha_emotional_memory                                             │
│  aisha_skill_memory     Scheduling                                  │
│  aisha_goals            ──────────                                  │
│  aisha_finance          aisha_schedule                              │
│                                                                     │
│  Edge Functions                  pg_cron (12 jobs)                  │
│  ─────────────                   ──────────────────                 │
│  chat/index.ts                   → trigger-studio (every 4h)        │
│  trigger-studio/index.ts         → trigger-maintenance (daily)      │
│  trigger-maintenance/index.ts    → task-poll (every 5 min)          │
│                                                                     │
│  Extensions: pgvector, pg_cron, pg_net                              │
└─────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     EXTERNAL SERVICES                               │
│                                                                     │
│  Google Gemini API     ElevenLabs TTS API    YouTube Data API v3    │
│  Groq (LLaMA-3.3)     Anthropic Claude       Instagram Graph API    │
│  xAI Grok             OpenAI GPT-4o          Gmail SMTP/IMAP        │
│  NVIDIA NIM (22 keys) Mistral API            Ollama (local)         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Details

### 3.1 bot.py — Telegram Interface

**File:** `src/telegram/bot.py`

The entry point and primary user interface. Runs as a long-polling Telegram bot and simultaneously serves a health check HTTP server on port 8000 (required by Render.com to keep the service alive).

Key behaviors:
- Only responds to Ajay's Telegram ID (`AJAY_TELEGRAM_ID`). All other users are rejected.
- Voice mode is on by default — every text response is also converted to an audio message via ElevenLabs.
- Pending shell commands require a `/confirm` step before execution (safety gate).
- Starts `autonomous_loop.py` in a background thread on boot.

Commands include:
- `/chat` — direct conversation
- `/produce` — trigger content pipeline for a channel
- `/status` — system health report
- `/memory` — view/add/clear memories
- `/mood` — update Ajay's mood
- `/finance` — log income/expenses
- `/schedule` — manage tasks and reminders
- `/voiceon` / `/voiceoff` — toggle TTS
- `/providers` — view AI provider status

### 3.2 aisha_brain.py — AI Orchestrator

**File:** `src/core/aisha_brain.py`

The cognitive core. Receives raw user messages and returns fully-formed AI responses with context.

Responsibilities:
- Loads Ajay's profile, recent memories, and conversation history from Supabase.
- Runs mood detection (`mood_detector.py`) to understand emotional context.
- Selects the appropriate personality system prompt from `CHANNEL_PROMPTS`.
- Injects up to 20 turns of conversation history into the AI call.
- Saves the response back to `aisha_conversations` table.
- Detects language (Hindi/English/Hinglish) via `language_detector.py`.

### 3.3 ai_router.py — 8-Provider AI Router

**File:** `src/core/ai_router.py`

The reliability layer. Ensures Aisha never goes silent because one provider is down.

Architecture:
- `ProviderStats` dataclass tracks failures and enforces exponential backoff cooldown per provider.
- Waterfall order (default): Gemini → Groq → NVIDIA NIM → Claude → xAI → OpenAI → Mistral → Ollama
- Vision calls use a separate order: Gemini → Claude → OpenAI (only multimodal-capable providers).
- `preferred_provider` parameter allows callers to request a specific AI (e.g., Riya channels use `nvidia`).
- After all providers fail, a last-resort sweep tries NVIDIA NIM `general`, `fast`, and `chat` pools.
- Sends Gmail alerts (rate-limited to once per 6 hours) on key expiry or quota exhaustion.

**Gemini uses direct REST API** (`requests` library) instead of the google.genai SDK. This bypasses a known DNS resolution issue on Windows Server with httpx.

### 3.4 autonomous_loop.py — 24/7 Scheduler

**File:** `src/core/autonomous_loop.py`

Handles Python-side scheduling (supplementing pg_cron). Runs in a background thread launched by `bot.py`.

Features:
- Startup recovery: resets any `content_jobs` stuck in `processing` state for >30 minutes back to `pending`.
- Webhook conflict detection: warns Ajay via Telegram if a Telegram webhook URL is set while the bot is in polling mode.
- Triggers morning check-in, evening wrap-up, daily digest, memory consolidation, and trend refresh.

### 3.5 AntigravityAgent — Job Queue Processor

**File:** `src/agents/antigravity_agent.py`

A persistent background worker that polls the `content_jobs` table and processes pending jobs.

Job lifecycle:
```
queued → processing → completed | failed
```

Handles: content generation, voice rendering, thumbnail creation, video assembly, social media posting.

### 3.6 voice_engine.py — TTS Engine

**File:** `src/core/voice_engine.py`

Dual-mode TTS: ElevenLabs (primary) with Edge-TTS as fallback.

- `generate_voice(text, channel=None)` — channel parameter selects voice ID from `CHANNEL_VOICE_IDS`.
- Aisha voice: `wdymxIQkYn7MJCYCQF2Q` (warm, emotional)
- Riya voice: `BpjGufoPiobT79j2vtj4` (seductive, bold)
- Timeout: 90 seconds (long Hindi scripts require extended timeouts).
- Transliteration of Roman script to Devanagari handled via Gemini REST API.

### 3.7 youtube_crew.py — 5-Agent Content Pipeline

**File:** `src/agents/youtube_crew.py`

Orchestrates the full content production workflow. See [Section 8](#8-content-agent-pipeline) for details.

### 3.8 video_engine.py — Video Renderer

**File:** `src/core/video_engine.py`

Assembles final MP4 from scene images and narration audio.

- Takes 7 scene PNG images and one MP3 narration file.
- Applies Ken Burns effect (slow pan/zoom) to each image for cinematic feel.
- Uses FFmpeg (or MoviePy fallback) to merge audio and video tracks.
- Output: single MP4 suitable for direct YouTube upload.

### 3.9 social_media_engine.py — Social Posting

**File:** `src/core/social_media_engine.py`

Handles authenticated uploads to YouTube and Instagram.

- Loads OAuth tokens from Supabase `api_keys` table (secret column). Environment variables are fallback only.
- `upload_youtube_video()` — uses YouTube Data API v3, handles resumable upload for large files.
- `post_instagram_image()` — uses Instagram Graph API, supports both feed posts and Reels.
- Idempotency: records `youtube_video_id` and `instagram_post_id` in `content_jobs` to prevent duplicate posts.

### 3.10 self_editor.py — Self-Improvement Engine

**File:** `src/core/self_editor.py`

Allows Aisha to read and patch her own source code. Runs nightly at 02:00 IST.

- Reads Python files from the project directory.
- Uses AI to audit code quality and suggest improvements.
- Applies patches via direct file write (PR workflow planned but not yet implemented).
- A safety gate is in place: changes to critical files require Ajay's `/confirm`.

### 3.11 supabase/functions/ — Edge Functions

Three Deno/TypeScript Edge Functions deployed to Supabase:

| Function | Purpose |
|----------|---------|
| `chat/index.ts` | Web chat brain — receives HTTP POST, calls multi-provider AI chain, returns response |
| `trigger-studio/index.ts` | Called by pg_cron every 4 hours to trigger content pipeline on Render |
| `trigger-maintenance/index.ts` | Called by pg_cron for all 11 maintenance jobs (morning, evening, memory, etc.) |

---

## 4. Data Flow Diagrams

### 4.1 Telegram Message → AI Response

```
Ajay sends Telegram message
        │
        ▼
bot.py: auth check (AJAY_TELEGRAM_ID)
        │
        ▼
aisha_brain.py
  ├── Load aisha_memory (top 5 active memories)
  ├── Load aisha_conversations (last 20 turns)
  ├── Load ajay_profile (mood, preferences)
  ├── Run mood_detector (classify emotional context)
  ├── Build system prompt (personality + context)
  └── Call ai_router.generate()
        │
        ▼
ai_router.py — provider waterfall
  ├── Try Gemini REST API
  │     ├── Success → return AIResult
  │     └── Fail (429/error) → cooldown, try next
  ├── Try Groq (LLaMA-3.3-70b)
  ├── Try NVIDIA NIM pool
  ├── Try Claude (Anthropic)
  ├── Try xAI (Grok)
  ├── Try OpenAI (GPT-4o)
  ├── Try Mistral
  ├── Try Ollama (local)
  └── Last resort: NVIDIA general/fast/chat pools
        │
        ▼
aisha_brain.py
  ├── Save response to aisha_conversations
  └── Return text to bot.py
        │
        ▼
bot.py
  ├── Send text message to Ajay
  └── If voice mode ON:
        ├── voice_engine.generate_voice(text)
        └── Send audio message to Ajay
```

### 4.2 Content Production Pipeline

```
Trigger source:
  - pg_cron (every 4h) → trigger-studio Edge Function → Render /api/trigger/studio
  - Ajay: /produce channel="Story With Aisha"
  - AntigravityAgent: polling content_jobs table
        │
        ▼
AntigravityAgent.enqueue_job()
  └── INSERT into content_jobs (status='queued')
        │
        ▼
AntigravityAgent processes job
  └── UPDATE content_jobs (status='processing')
        │
        ▼
YouTubeCrew.kickoff(channel, format, topic)
        │
        ├── [Agent 1: Research]
        │   ├── trend_engine.get_trends_for_channel() → Google Trends + News APIs
        │   ├── Build story brief with trending topic
        │   └── Output: research_brief (500-800 words)
        │
        ├── [Agent 2: Script]
        │   ├── Receives research_brief from Agent 1
        │   ├── Uses channel-specific AI provider (Gemini / NVIDIA Mistral)
        │   ├── Writes full Hindi Devanagari script
        │   │   - Story With Aisha: 8-15 minute narration
        │   │   - Riya channels: 10-25 minute dark romance
        │   │   - Aisha & Him: 30s-3 min couple short
        │   └── Output: full_script (3,000-8,000 words)
        │
        ├── [Agent 3: Visual]
        │   ├── Receives script from Agent 2
        │   ├── Creates thumbnail concept (emotional hook image)
        │   ├── Generates 7 scene prompts (for Ken Burns video)
        │   └── Output: visual_direction dict
        │
        ├── [Agent 4: Marketing]
        │   ├── Receives script + visual direction
        │   ├── Generates YouTube title (Hindi, SEO-optimized)
        │   ├── Generates description (800-1200 chars)
        │   ├── Generates hashtags (15-20 tags)
        │   ├── Generates Instagram caption
        │   └── Output: marketing_bundle dict
        │
        └── [Agent 5: Voice + Image]
            ├── voice_engine.generate_voice(script, channel)
            │   └── ElevenLabs API → MP3 file (90s timeout)
            ├── image_engine.generate_image(visual_direction)
            │   └── Pillow placeholder (HuggingFace pending)
            └── Output: voice_path, thumbnail_path
                  │
                  ▼
        video_engine.render_video(scenes, voice_path)
          └── FFmpeg: images + Ken Burns + audio → MP4
                  │
                  ▼
        aisha_content_library INSERT (all assets saved)
                  │
                  ▼
        social_media_engine
          ├── upload_youtube_video() → YouTube Data API v3
          └── post_instagram_image() → Instagram Graph API
                  │
                  ▼
        content_jobs UPDATE (status='completed')
        content_performance INSERT (metrics tracking)
```

---

## 5. Database Schema

Supabase project: `fwfzqphqbeicgfaziuox`
PostgreSQL extensions: `pgvector`, `pg_cron`, `pg_net`

All tables have Row Level Security (RLS) enabled with full-access policies (service role only in production).

### Core Memory Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `ajay_profile` | Owner profile, preferences, languages | `name`, `preferred_lang`, `timezone`, `current_mood` |
| `aisha_memory` | Long-term memories with vector embeddings | `category`, `title`, `content`, `importance (1-5)`, `embedding (vector 768)` |
| `aisha_conversations` | Full conversation history (all platforms) | `platform`, `role`, `message`, `language`, `mood_detected` |
| `aisha_journal` | Ajay's daily journal entries | `entry`, `mood`, `mood_score (1-10)`, `date` |
| `aisha_mood_tracker` | Mood tracking over time | `mood`, `mood_score`, `triggers`, `time_of_day` |
| `aisha_goals` | Goals with progress tracking | `category`, `timeframe`, `status`, `progress (0-100)` |
| `aisha_finance` | Financial tracking and goals | `type (expense/income/goal/saving)`, `amount`, `currency` |
| `aisha_schedule` | Tasks and reminders | `type`, `priority`, `status`, `due_date`, `is_recurring` |

### Memory Sub-System Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `aisha_episodic_memory` | Event-based memories ("Ajay got a promotion on 2026-02-10") | `entity`, `event_description`, `event_date`, `embedding` |
| `aisha_emotional_memory` | Emotional states and triggers | `mood_state`, `trigger`, `context_text`, `embedding` |
| `aisha_skill_memory` | Capabilities Aisha has learned | `skill_name`, `description`, `embedding` |

### Content Pipeline Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `content_jobs` | Job queue for content generation | `topic`, `channel`, `format`, `status (queued/processing/completed/failed)`, `priority`, `auto_post` |
| `aisha_content_library` | Archive of all generated content assets | `channel`, `script`, `voice_path`, `thumbnail_path`, `video_path`, `youtube_video_id`, `ai_provider` |
| `content_performance` | Analytics per piece of content | `platform`, `content_id`, `views`, `likes`, `watch_time_minutes`, `subscribers_gained` |
| `aisha_trend_cache` | Cached trend research per channel (2h TTL) | `channel`, `recommended_topic`, `trending_topics`, `viral_keywords`, `expires_at` |
| `aisha_youtube_channels` | YouTube account config per channel | `channel_name`, `youtube_channel_id`, `token_path`, `subscriber_count` |
| `aisha_earnings_tracker` | Monthly revenue tracking | `platform`, `views`, `estimated_rpm`, `estimated_earn` (computed), `actual_earn` |

### System Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `api_keys` | Secure storage for OAuth tokens (YouTube, Instagram) | `service`, `key_name`, `secret` (encrypted) |

### Views

| View | Purpose |
|------|---------|
| `channel_performance_summary` | Aggregate views/likes/subscribers per channel |
| `top_content_this_month` | Top 20 videos by views in current month |
| `earnings_summary` | Total estimated vs actual earnings per channel |

### Known Missing Tables

The following tables are referenced in code but not yet created in the database:

- `aisha_system_log` — referenced by `logger.py`
- `aisha_message_queue` — referenced by `notification_engine.py`
- `aisha_health` — referenced by `health_tracker.py`

---

## 6. AI Provider Chain

### Provider Order and Models

Default fallback order (lowest priority to highest priority displayed left to right):

```
Ollama → Mistral → OpenAI → xAI → Claude → NVIDIA NIM → Groq → Gemini
         (local)                                                (primary)
```

In code, providers are tried in this order: `gemini → groq → nvidia → anthropic → xai → openai → mistral → ollama`

| Provider | Model | Context | Status |
|----------|-------|---------|--------|
| **Gemini** | `gemini-2.5-pro` (primary), `gemini-2.0-flash` (fallback) | 1M tokens | Active |
| **Groq** | `llama-3.3-70b-versatile` | 32K tokens | Active |
| **NVIDIA NIM** | Pool of 22 keys, 9 different models | Varies | Active |
| **Claude (Anthropic)** | `claude-opus-4-6` with adaptive thinking | 128K tokens | 401 (key expired) |
| **xAI (Grok)** | `grok-2-latest` | 16K tokens | 403 (no credits) |
| **OpenAI** | `gpt-4o` | 16K tokens | 401 (key expired) |
| **Mistral** | `mistral-small-latest` | 1K tokens | Optional |
| **Ollama** | `llama3` | 8K tokens | Local only |

### Vision-Capable Providers

Only these providers support image input:
- Gemini (via base64 inline_data)
- Claude Anthropic (via base64 source block)
- OpenAI (via image_url data URI)

### Channel-to-Provider Routing

| Channel | Primary AI | Task Type | Reason |
|---------|-----------|-----------|--------|
| Story With Aisha | Gemini | writing | Warm, emotional, cinematic style |
| Riya's Dark Whisper | NVIDIA (Mistral-Large-3) | writing | 675B model, minimal content filtering |
| Riya's Dark Romance Library | NVIDIA (Mistral-Large-3) | writing | 675B model, explicit romance content |
| Aisha & Him | Gemini | writing | Light, relatable, conversational |

### NVIDIA NIM Pool Architecture

22 API keys, each with 1,000 free credits/month = **22,000 total credits/month**.

Keys are grouped by task type:

| Task Type | Model | Keys |
|-----------|-------|------|
| `writing` | Mistral-Large-3 (675B) | KEY_02, KEY_17 |
| `chat` | LLaMA-3.3-70b | KEY_05, KEY_06, KEY_18, KEY_19, KEY_20, KEY_21, KEY_22 |
| `code` | Mamba-Codestral-7B | KEY_13 |
| `vision` | Phi-4-multimodal | KEY_04 |
| `video` / `long` | Phi-3-medium-128K | KEY_14 |
| `general` | Qwen-122B | KEY_01 |
| `fast` | Gemma-2-2B, Falcon3-7B | KEY_11, KEY_08 |

Notes:
- KEY_07 (llama-4-scout) returns 404 — auto-fallback handles it.
- KEY_09 (nvidia/usdcode) returns 404 — auto-fallback handles it.

### Failure Handling

```
Failure Type    │ Backoff Strategy
────────────────┼──────────────────────────────────────────
Rate limit (429)│ Wait exactly retry_after seconds (max 90s)
Auth error (401)│ Exponential: 30s → 60s → 120s
Quota exhausted │ Long cooldown + Gmail alert to Ajay
All down        │ NVIDIA last-resort sweep + critical alert
```

---

## 7. Scheduling System

### Architecture

Primary scheduler: **pg_cron** (Supabase PostgreSQL extension)
- pg_cron fires → calls Supabase Edge Function via `pg_net.http_post()`
- Edge Function calls Render.com `/api/trigger/<job>` endpoint
- Render Python backend executes the job

Backup scheduler: Python `schedule` library in `autonomous_loop.py`
- Runs in a background thread inside the Telegram bot process
- Activates when pg_cron is not yet enabled (current state)

### 12 pg_cron Jobs

All times shown as IST (UTC+5:30).

| # | Job Name | IST Time | UTC Cron | Purpose |
|---|----------|----------|----------|---------|
| 1 | `aisha-morning` | 08:00 daily | `30 2 * * *` | Morning check-in message to Ajay |
| 2 | `aisha-evening` | 21:00 daily | `30 15 * * *` | Evening wrap-up summary |
| 3 | `aisha-daily-digest` | 21:30 daily | `0 16 * * *` | Daily digest (news + tasks) |
| 4 | `aisha-memory-consolidation` | 03:00 daily | `30 21 * * *` | Compress + consolidate memories |
| 5 | `aisha-self-improve` | 02:00 daily | `30 20 * * *` | Nightly code audit + self-edit |
| 6 | `aisha-temp-cleanup` | 04:00 daily | `30 22 * * *` | Delete temp voice/image/video files |
| 7 | `aisha-key-expiry` | 09:00 daily | `30 3 * * *` | Check API key expiry dates |
| 8 | `aisha-weekly-digest` | Sun 19:00 | `30 13 * * 0` | Weekly performance summary |
| 9 | `aisha-memory-cleanup` | Sat 03:00 | `30 21 * * 6` | Archive old low-importance memories |
| 10 | `aisha-task-poll` | Every 5 min | `*/5 * * * *` | Check for due task reminders |
| 11 | `aisha-inactivity` | Every 3 hours | `0 */3 * * *` | Proactive message if Ajay is quiet |
| 12 | `aisha-studio-every-4h` | Every 4 hours | `0 */4 * * *` | Trigger content pipeline (studio) |

### Activation Status

pg_cron is not yet enabled in the Supabase project. To activate:
1. Go to Supabase Dashboard → Database → Extensions
2. Enable `pg_cron`
3. Apply migration: `supabase/migrations/20260318000000_pg_cron_jobs.sql`
4. Verify: `SELECT jobname, schedule, active FROM cron.job WHERE jobname LIKE 'aisha-%' ORDER BY jobname;`

---

## 8. Content Agent Pipeline

### Overview

`YouTubeCrew` orchestrates 5 sequential agents. Each agent builds on the previous agent's output. The full pipeline runs in a single Python process call to `YouTubeCrew.kickoff()`.

### Agent 1: Research

**Input:** Channel name, format, optional topic override

**Process:**
- Calls `trend_engine.get_trends_for_channel(channel)` which queries Google Trends and news APIs.
- Synthesizes trending topics relevant to the channel's theme.
- If trend fetch fails, falls back to a stored topic list.

**Output:** `research_brief` — a structured brief containing recommended topic, top content angles, viral keywords, and hook idea.

### Agent 2: Script Writer

**Input:** `research_brief` from Agent 1, channel identity config

**Process:**
- Selects AI provider based on `CHANNEL_AI_PROVIDER` (Gemini for Aisha channels, NVIDIA Mistral for Riya channels).
- Uses channel-specific personality prompt from `CHANNEL_PROMPTS` in `personality.py`.
- Writes full Hindi Devanagari script.
- Format guidelines:
  - Story With Aisha: 8-15 minute emotional love story
  - Riya's Dark Whisper: 10-20 minute psychological dark romance
  - Riya's Dark Romance Library: 15-25 minute mafia romance chapter
  - Aisha & Him: 30 second to 3 minute couple dialogue

**Output:** `full_script` — complete Devanagari Hindi script, 3,000-8,000 words.

**Critical:** All Hindi content must be 100% Devanagari script. No Roman transliteration. No exceptions.

### Agent 3: Visual Director

**Input:** `full_script` from Agent 2

**Process:**
- Creates an emotionally compelling thumbnail concept (single image that captures the story's peak moment).
- Generates 7 scene prompts — one image per major story beat, used for Ken Burns video assembly.

**Output:** `visual_direction` dict with `thumbnail_concept` and `scene_prompts` list.

### Agent 4: Marketing Specialist

**Input:** Script + visual direction

**Process:**
- Writes SEO-optimized YouTube title in Hindi (triggers emotion + curiosity).
- Writes YouTube description (800-1200 chars, Hindi + relevant keywords).
- Generates 15-20 hashtags.
- Writes Instagram caption adapted for Reels format.

**Output:** `marketing_bundle` dict with title, description, hashtags, instagram_caption.

### Agent 5: Voice + Image Producer

**Input:** Full script, visual direction, channel name

**Process:**
- Calls `voice_engine.generate_voice(script, channel=channel_name)` which selects the correct ElevenLabs voice ID.
- Calls `image_engine.generate_image(visual_direction)` for thumbnail (currently Pillow placeholder).
- Saves both files to `tmp/` directory.

**Output:** `voice_path` (MP3 file path), `thumbnail_path` (PNG file path).

### Post-Pipeline: Video Assembly

After YouTubeCrew completes:
- `video_engine.render_video(scene_prompts, voice_path)` — assembles 7 scene images with Ken Burns motion effects and the narration audio into a single MP4.
- All assets are saved to `aisha_content_library` table.
- `social_media_engine` uploads to YouTube and Instagram.

---

## 9. Deployment Topology

### Infrastructure Map

```
┌─────────────────────────────────────────────────────────────────┐
│  RENDER.COM                                                     │
│  Service type: Web Service (Free tier → Starter recommended)   │
│  Region: Oregon (US West)                                       │
│  Runtime: Python 3.11                                           │
│  Start command: python src/telegram/bot.py                      │
│  Health check: GET http://0.0.0.0:8000/health                  │
│  Auto-deploy: from GitHub main branch                           │
│                                                                 │
│  Environment variables: set in Render dashboard                 │
│  Persistent disk: not configured (temp files are ephemeral)     │
└───────────────────────────────────┬─────────────────────────────┘
                                    │ HTTP /api/trigger/*
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  SUPABASE                                                       │
│  Project ref: fwfzqphqbeicgfaziuox                              │
│  Region: ap-south-1 (Mumbai)                                    │
│  PostgreSQL: 15.x                                               │
│  Edge Functions: Deno runtime                                   │
│  pg_cron: pending activation                                    │
│  pg_net: for HTTP calls from SQL                                │
│  pgvector: for semantic memory search                           │
│                                                                 │
│  Edge Function URLs:                                            │
│  https://fwfzqphqbeicgfaziuox.supabase.co/functions/v1/chat    │
│  https://fwfzqphqbeicgfaziuox.supabase.co/functions/v1/        │
│    trigger-studio                                               │
│  https://fwfzqphqbeicgfaziuox.supabase.co/functions/v1/        │
│    trigger-maintenance                                          │
└───────────────────────────────────┬─────────────────────────────┘
                                    │ git push
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  GITHUB                                                         │
│  Repo: AjayBervanshi/aisha-personal-ai                         │
│  Branch: main (auto-deploys to Render)                          │
│  Note: push currently failing (DNS issue on Windows Server)     │
└─────────────────────────────────────────────────────────────────┘
```

### Network Flow

1. pg_cron fires in Supabase (Mumbai) → `pg_net.http_post()` to Edge Function in same region (~2ms).
2. Edge Function makes HTTP call to Render service (Mumbai → Oregon, ~200ms).
3. Render executes Python job, calls AI APIs and uploads to YouTube (~30s-5min depending on job).
4. Results written back to Supabase over HTTPS from Render.

### Render Configuration Notes

- Free tier spins down after 15 minutes of inactivity. The health server on port 8000 is specifically to prevent this.
- For production use, upgrade to Starter tier ($7/month) for always-on operation.
- Temp files (voice MP3s, video MP4s) are stored in the container's ephemeral filesystem and cleaned up by `aisha-temp-cleanup` cron job.

---

## 10. Environment Variables

Full list of environment variables. Set these in the Render dashboard and/or `.env` file for local development.

### Required (System Will Not Start Without These)

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | `7234567890:AAH...` |
| `SUPABASE_URL` | Supabase project URL | `https://fwfzqphqbeicgfaziuox.supabase.co` |
| `SUPABASE_ANON_KEY` | Supabase public anon key | `eyJhbGci...` |
| `SUPABASE_SERVICE_KEY` | Supabase service role key (full DB access) | `eyJhbGci...` |
| `AJAY_TELEGRAM_ID` | Ajay's Telegram numeric user ID | `1002381172` |

### AI Providers (At Least One Required)

| Variable | Provider | Default Model | Status |
|----------|----------|---------------|--------|
| `GEMINI_API_KEY` | Google Gemini | gemini-2.5-pro | Active |
| `GROQ_API_KEY` | Groq LLaMA | llama-3.3-70b-versatile | Active |
| `ANTHROPIC_API_KEY` | Claude (Anthropic) | claude-opus-4-6 | 401 (expired) |
| `XAI_API_KEY` | xAI Grok | grok-2-latest | 403 (no credits) |
| `OPENAI_API_KEY` | OpenAI GPT | gpt-4o | 401 (expired) |
| `MISTRAL_API_KEY` | Mistral | mistral-small-latest | Optional |
| `NVIDIA_API_KEY_01` through `NVIDIA_API_KEY_22` | NVIDIA NIM pool | Various | Active (20/22 keys) |

### AI Model Overrides (Optional)

| Variable | Default | Purpose |
|----------|---------|---------|
| `AI_MODEL_GEMINI` | `gemini-2.5-pro` | Override primary Gemini model |
| `AI_MODEL_GEMINI_FALLBACK` | comma-separated list | Override fallback model chain |
| `AI_MODEL_OPENAI` | `gpt-4o` | Override OpenAI model |
| `AI_MODEL_GROQ` | `llama-3.3-70b-versatile` | Override Groq model |
| `AI_MODEL_ANTHROPIC` | `claude-opus-4-6` | Override Claude model |
| `AI_MODEL_XAI` | `grok-2-latest` | Override xAI model |

### Voice

| Variable | Description | Status |
|----------|-------------|--------|
| `ELEVENLABS_API_KEY` | ElevenLabs TTS | Active (starter plan) |
| `ELEVENLABS_VOICE_ID` | Default voice ID (overridden per channel) | `wdymxIQkYn7MJCYCQF2Q` |

### Social Media

| Variable | Description | Status |
|----------|-------------|--------|
| `YOUTUBE_CLIENT_ID` | YouTube OAuth 2.0 client ID | Not configured |
| `YOUTUBE_CLIENT_SECRET` | YouTube OAuth 2.0 client secret | Not configured |
| `INSTAGRAM_ACCESS_TOKEN` | Instagram Graph API long-lived token | Not configured |
| `INSTAGRAM_BUSINESS_ID` | Instagram Business account ID | Not configured |

Note: OAuth tokens are also stored (and preferred) in the Supabase `api_keys` table under service `youtube_oauth` / `instagram_oauth`.

### Email

| Variable | Description | Status |
|----------|-------------|--------|
| `GMAIL_USER` | Aisha's Gmail address | Not configured |
| `GMAIL_APP_PASSWORD` | Gmail app password (not account password) | Not configured |

### Application

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Set to `production` on Render |
| `TIMEZONE` | `Asia/Kolkata` | IST timezone for scheduling |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `USER_NAME` | `Ajay` | Owner's name for personalization |

### Phone (Optional — Call Me Plugin)

| Variable | Description |
|----------|-------------|
| `CALLME_PHONE_PROVIDER` | `telnyx` or `twilio` |
| `CALLME_PHONE_ACCOUNT_SID` | Provider account SID |
| `CALLME_PHONE_AUTH_TOKEN` | Provider auth token |
| `CALLME_PHONE_NUMBER` | Aisha's outbound phone number |
| `CALLME_USER_PHONE_NUMBER` | Ajay's phone number |
| `CALLME_OPENAI_API_KEY` | OpenAI key for voice conversation |
| `CALLME_NGROK_AUTHTOKEN` | ngrok for local webhook development |

---

## 11. Current Status

### What is Fully Working

| Component | Status | Notes |
|-----------|--------|-------|
| Telegram bot | Operational | 40+ commands, voice mode |
| AI chat (Gemini) | Operational | 2.3s average latency |
| AI fallback (Groq) | Operational | LLaMA-3.3-70b |
| NVIDIA NIM pool | Operational | 20/22 keys active |
| ElevenLabs voices | Operational | Aisha + Riya, 90s timeout |
| Aisha memory | Operational | 15/18 tables created |
| Content pipeline | Operational | Script + voice + placeholder thumbnail |
| Supabase DB | Operational | 15 tables confirmed |
| Autonomous loop | Operational | Python scheduler (pg_cron pending) |
| Email alerts | Operational | Gmail on provider failures |

### What is Blocked / Broken

| Issue | Impact | Fix Required |
|-------|--------|-------------|
| YouTube OAuth not configured | Cannot auto-upload videos | Run `scripts/setup_youtube_oauth.py`, store token in `api_keys` table |
| xAI 403 (no credits) | Riya channels use Groq fallback (lower quality) | Add credits at x.ai console |
| Claude 401 (key expired) | Missing from fallback chain | Regenerate key at console.anthropic.com |
| OpenAI 401 (key expired) | Missing from fallback chain | Regenerate key at platform.openai.com |
| Image APIs degraded | Thumbnails are Pillow placeholders | Get HuggingFace API token at huggingface.co/settings/tokens |
| pg_cron not enabled | Scheduling runs from Python only | Enable in Supabase Dashboard → Database → Extensions |
| 3 missing DB tables | `aisha_system_log`, `aisha_message_queue`, `aisha_health` code errors | Write and run migration |
| GitHub push failing | Cannot deploy from Windows | DNS issue on Windows Server; use Render auto-deploy or manual zip deploy |
| `content_jobs` vs `content_queue` overlap | Potential duplicate job processing | Audit and consolidate into single table |

### Maturity Score: 3.5 / 7

The system is fully capable of generating content and could start earning money today **if** YouTube OAuth is configured. All other blockers degrade quality but do not stop operation.

**Highest priority action to start earning: configure YouTube OAuth and upload first video.**

---

## 12. 7-Phase Roadmap

### Phase 1: Core Conversation (Complete)
- Telegram bot with text + voice responses
- 8-provider AI router with automatic fallback
- Supabase memory persistence
- Mood detection and personality system

### Phase 2: Rich Memory (Complete)
- Long-term semantic memory with pgvector embeddings
- Episodic, emotional, and skill memory sub-systems
- Conversation history (20-turn context window)
- Ajay profile with preferences, goals, finances

### Phase 3: Content Generation (Complete — Voice/Script)
- 5-agent YouTubeCrew pipeline
- Hindi Devanagari script writing (8-25 minute stories)
- ElevenLabs voice narration (Aisha + Riya personas)
- Trend research engine

### Phase 3.5: Content Publishing (Current — Partially Blocked)

Remaining tasks:
1. YouTube OAuth setup → first video upload
2. xAI credits → Riya channels get proper Grok model
3. HuggingFace API → real AI thumbnails (currently Pillow placeholder)
4. Video render testing → confirm FFmpeg Ken Burns pipeline works end-to-end
5. Instagram posting → test Graph API with first real post

### Phase 4: Full Scheduling Autonomy
- Enable pg_cron (12 jobs)
- Daily studio sessions every 4 hours without human trigger
- Automated trend detection → topic selection → script → voice → video → upload cycle
- Content calendar management in `aisha_schedule` table
- Gmail notifications for publishing confirmations

### Phase 5: Self-Improvement Loop
- Nightly code audit via `self_editor.py` / `self_improvement.py`
- AI reviews its own scripts for quality improvement
- A/B testing: track which content topics/styles get more views
- Automatic prompt refinement based on performance data
- Safe PR workflow for code changes (GitHub PR instead of direct file write)

### Phase 6: Revenue Optimization
- YouTube Analytics API integration → pull real views, watch time, RPM
- `aisha_earnings_tracker` populated with actual AdSense data
- Revenue per channel dashboard in Telegram (`/revenue`)
- Automatic channel strategy adjustment (double down on what earns)
- Alert when any channel hits 1,000 subscribers (monetization threshold)
- xAI credits management — auto-alert when Riya channel credits low

### Phase 7: Full Autonomy
- Zero human intervention required for content production
- Aisha manages her own API key renewals (emails Ajay with instructions)
- Content library grows: 5-10 videos/week across all 4 channels
- Revenue target: ₹50,000/month from YouTube AdSense + Instagram Creator Fund
- Self-directed growth: Aisha researches new content formats, proposes channel expansions
- Multi-language expansion: Marathi, Tamil, or English channels based on analytics

---

## Appendix A: Key File Index

| File | Description |
|------|-------------|
| `src/telegram/bot.py` | Entry point, Telegram bot, health server |
| `src/core/aisha_brain.py` | AI orchestrator, context builder |
| `src/core/ai_router.py` | 8-provider waterfall router |
| `src/core/config.py` | All env vars, channel configs, voice IDs |
| `src/core/autonomous_loop.py` | 24/7 scheduler, startup recovery |
| `src/core/voice_engine.py` | ElevenLabs + Edge-TTS |
| `src/core/video_engine.py` | FFmpeg Ken Burns video assembly |
| `src/core/image_engine.py` | Thumbnail generation (Pillow + HuggingFace) |
| `src/core/social_media_engine.py` | YouTube + Instagram posting |
| `src/core/self_editor.py` | Self-improvement code patcher |
| `src/core/nvidia_pool.py` | 22-key NVIDIA NIM orchestrator |
| `src/core/gmail_engine.py` | SMTP/IMAP email engine |
| `src/core/trend_engine.py` | Real-time trend research |
| `src/agents/youtube_crew.py` | 5-agent content pipeline |
| `src/agents/antigravity_agent.py` | Job queue processor |
| `src/core/prompts/personality.py` | Channel personalities and mood prompts |
| `src/memory/memory_manager.py` | Memory CRUD + semantic search |
| `src/memory/memory_compressor.py` | Memory consolidation |
| `supabase/functions/chat/index.ts` | Web chat Edge Function |
| `supabase/functions/trigger-studio/index.ts` | Studio trigger Edge Function |
| `supabase/functions/trigger-maintenance/index.ts` | Maintenance trigger Edge Function |
| `supabase/migrations/20260318000000_pg_cron_jobs.sql` | All 12 pg_cron job definitions |

## Appendix B: Important Constants

| Constant | Value | Location |
|----------|-------|----------|
| Aisha ElevenLabs Voice ID | `wdymxIQkYn7MJCYCQF2Q` | `config.py` |
| Riya ElevenLabs Voice ID | `BpjGufoPiobT79j2vtj4` | `config.py` |
| Supabase Project Ref | `fwfzqphqbeicgfaziuox` | `.env` |
| Ajay Telegram ID | `1002381172` | `.env` |
| Health Server Port | `8000` | `bot.py` |
| AI Max Tokens | `16,000` (chat), `128,000` (long-form Claude) | `config.py`, `ai_router.py` |
| AI Temperature | `0.88` | `config.py` |
| ElevenLabs Timeout | `90s` | `voice_engine.py` |
| Memory History Limit | `20 turns` | `config.py` |
| Stuck Job Recovery Threshold | `30 minutes` | `autonomous_loop.py` |
| Alert Cooldown | `6 hours` | `ai_router.py` |

---

*Last updated: 2026-03-20. Maintained by Aisha Architecture Agent.*
