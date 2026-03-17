# Architecture Review - AISHA
Date: 2026-03-17
Source reviewed: E:/VSCode/Aisha/docs/ARCHITECTURE.md

## Step 1 - Architecture Understanding
- System: A single-user autonomous AI platform for Ajay that combines personal assistant behavior with automated content production.
- Purpose: personal companionship/productivity + revenue generation via YouTube (4 channels) and Instagram.
- Major components: Telegram bot, Lovable web app, Supabase Edge Functions, Python core backend on Railway, Supabase Postgres + pgvector, CrewAI agent pipelines, AI provider router, voice engines, social media publishing engines.
- Interaction model: user enters via Telegram/web; edge functions route to Python core; core orchestrates memory + model calls + agent workflows; outputs sent back to user or published to social platforms after approval.
- Technologies: Python 3.11/FastAPI/CrewAI/pyTelegramBotAPI, TypeScript+Deno edge functions, Supabase Postgres+pgvector, Railway hosting, external APIs (Gemini/Groq/NVIDIA/Claude/xAI/OpenAI/YouTube/Instagram/ElevenLabs).
- Style: modular monolith core + serverless edge adapters + event-driven/scheduled automation + sequential multi-agent pipelines.

## Step 2 - Major Architecture Components
- Frontend Layer: Telegram interface and Lovable web SPA for chat, voice, and controls.
- Edge/API Layer: Supabase Edge Functions (`/chat`, `/telegram-bot`, `/content-pipeline`, `/memory_search`, `/store-api-keys`) as ingress and orchestration glue.
- Core Application Layer: `AishaBrain`, `AutonomousLoop`, `YouTubeCrew`, `SelfEditor`, `SocialMediaEngine`, `FastAPI server`.
- AI Routing Layer: `AIRouter` with waterfall fallback and `NvidiaPool` key distribution.
- Agent Orchestration Layer: CrewAI agents for YouTube pipeline and DevCrew self-improvement flow.
- Memory/Data Layer: Supabase tables (15), vector memory (`aisha_memory`), conversation store, schedule/finance/health/content state.
- Storage Layer: local ephemeral directories (`temp_voice`, `temp_videos`, `tokens`) plus partially adopted Supabase Storage.
- External Integration Layer: AI model vendors, Telegram API, YouTube Data API + OAuth, Instagram Graph API, Google Trends, TTS providers.
- Infrastructure/DevOps Layer: Railway runtime, GitHub Actions deploy workflow, environment-secret management.

## Step 3 - Architecture Flow Analysis
1. User request flow:
- Ajay sends text/voice via Telegram (or web chat via edge function).
- Security gate checks `AJAY_TELEGRAM_ID`.
- Voice is transcribed, context/mood/language/memory loaded, prompt assembled.
- `AIRouter` calls providers in priority order; response returned as text/voice.
- Conversation and extracted memory persisted.

2. Content pipeline flow:
- `/create` command triggers `telegram-bot` edge function, then `content-pipeline`.
- CrewAI 5-agent chain produces script, visuals prompts, SEO metadata, voice audio.
- Result inserted into `content_queue` with `ready` status.
- Telegram inline approval drives publish decision.
- Callback publishes to YouTube/Instagram and sends confirmation.

3. Autonomous/background flow:
- `AutonomousLoop` runs scheduled jobs (briefings, reminders, inactivity checks, memory cleanup, production checks).
- Notifications delivered via Telegram; memory maintenance performed weekly.

4. Failure handling flow:
- LLM waterfall fallback across 8 providers.
- Voice fallback: ElevenLabs -> Edge-TTS -> text only.

Unclear/missing in flow:
- No explicit idempotency model for callback publish actions.
- No described queue executor despite `aisha_message_queue` existing.
- No clear transactional boundary between content generation, DB write, and publish trigger.
- Two Telegram entrypoints (long polling bot + edge webhook) create path ambiguity.

## Step 4 - Detailed Architecture Questions
- What is the single source of truth for Telegram ingestion: `src/telegram/bot.py` or `supabase/functions/telegram-bot`?
- Are both Telegram paths active in production today? If yes, how do you prevent duplicate processing?
- How are edge functions authenticated when calling Railway/FastAPI internals?
- Is there a service-to-service auth mechanism beyond shared secrets?
- What retry policy exists per external API (Gemini, Groq, YouTube, Instagram, ElevenLabs)?
- How do you prevent duplicate YouTube uploads if Telegram callback is retried?
- Is `content_queue` state machine formally defined (`queued/processing/ready/published/failed`)?
- Are publish actions idempotent with unique external operation keys?
- How do you handle partial success (YouTube success, Instagram failure)?
- What are the timeout budgets per stage (LLM generation, Crew run, TTS, upload)?
- How is backpressure handled if `/create` is triggered multiple times quickly?
- Are scheduled jobs single-instance guaranteed on Railway, or can multiple workers trigger duplicate jobs?
- What is the recovery process after Railway restart during in-flight pipelines?
- How are OAuth refresh failures detected and auto-remediated?
- Where are encryption-at-rest and key-rotation controls for tokens/API keys?
- Is `aisha_api_keys` encrypted with KMS/PGP or plain text in DB?
- How is `SelfEditor` execution sandboxed to avoid destructive patches?
- Is there a kill switch for self-editing and autonomous deployment actions?
- What approvals are required before `SelfEditor` changes production code?
- How are memory retention, deletion, and privacy lifecycle policies defined?
- What is the max payload/input size accepted from Telegram/web?
- What abuse protections exist for prompt injection through fetched external content?
- Is there model output validation before passing content to social publishing APIs?
- What SLOs are defined (availability, response latency, schedule reliability)?
- Which metrics are mandatory per component (request rate, error rate, fallback frequency, queue depth)?
- How do you correlate logs across edge function -> Railway -> Supabase operations?
- What is the disaster recovery plan for Supabase outage or data corruption?
- Is there PITR/backups validation for the 15-table schema + vector data?
- What are deployment rollback steps when GitHub Actions deploy breaks runtime?
- Is there a staging environment with test tokens and sandbox social accounts?
- How are NVIDIA key quotas monitored in near real time to avoid hard cutoff events?
- How will India timezone behavior be validated across DST differences in hosting region settings?

## Step 5 - Gaps / Risks
- Dual Telegram architecture: high risk of divergence, duplicate processing, and inconsistent security behavior.
- Weak security posture on data plane: wide-open RLS and plaintext token file materially increase compromise impact.
- Single-instance runtime: Railway single process is a clear availability and scheduling SPOF.
- No automated tests: changes to routing, agents, or integrations can silently break core workflows.
- Incomplete resilience: missing queue-based retries/circuit breakers/idempotency threatens reliability under transient failures.
- Operational blind spots: minimal observability means delayed detection of outages, quota exhaustion, token expiry.
- Ephemeral/local artifact dependence: temp files + local token storage are fragile across restarts/deploys.
- Self-modifying code path without robust guardrails: high blast-radius risk (security + stability).

## Step 6 - Improvement Suggestions
- Consolidate Telegram ingress to one production path and formalize an anti-duplication contract.
- Define explicit workflow state machines for content jobs and publish lifecycle with idempotent transitions.
- Move all secrets/tokens into managed secure storage with encryption and rotation policies.
- Enforce least-privilege RLS/service roles; eliminate permissive TRUE policies.
- Add queue-based async workers for retries, dead-letter handling, and backoff for external API operations.
- Introduce health checks, uptime probes, error tracking, and structured metrics with correlation IDs.
- Split `AishaBrain` into bounded services/modules (chat orchestration, memory orchestration, channel/content orchestration).
- Add staging + rollback-ready deployment pipeline, including edge-function CI/CD and migration safety checks.
- Put `SelfEditor` behind strict governance: signed patch validation, dry-run tests, manual approval gate, rollback hooks.
- Implement artifact lifecycle management (auto-cleanup and durable storage for required outputs).

## Step 7 - Architecture Maturity Evaluation
- Classification: Intermediate architecture.
- Why: strong functional breadth and thoughtful modular decomposition, but production-hardening controls are incomplete (testing, security hardening, reliability engineering, observability, deployment safety).

## Step 8 - Prioritized Improvement List
1. High Priority
- Security hardening: RLS tightening, token/key secure storage, self-editor guardrails.
- Reliability baseline: idempotency, retries/queue activation, single Telegram path, failure-state machine.
- Operational readiness: monitoring/alerting, token/quota expiry alarms, uptime checks.
- Delivery safety: automated tests, staging environment, rollback procedures, edge deploy in CI/CD.

2. Medium Priority
- Service boundary refactor of `AishaBrain`.
- Persistent artifact strategy (Supabase Storage adoption) and temp file lifecycle cleanup.
- Performance optimizations (async memory writes, targeted caching).

3. Low Priority
- Code hygiene debt (duplicate SDK imports, unclear agents like `antigravity_agent.py`).
- Non-critical architecture refinements after reliability/security baseline is complete.

## Step 9 - Final Architect Review Summary
- Strengths: ambitious and coherent end-to-end platform; strong AI fallback strategy; rich memory architecture; clear product intent; good modular file organization; practical automation workflows.
- Weaknesses: architecture is functionally advanced but operationally under-governed; security and reliability controls lag feature scope.
- Major concerns: dual Telegram runtime model, permissive data access posture, lack of strong deployment/testing safety nets, and unmanaged risk in self-editing/autonomous code changes.
- Most important next steps: lock down security and ingress boundaries first, implement resilient job/idempotency model second, then establish observability + CI/CD hardening so feature growth does not increase failure rate.
