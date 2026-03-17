# CLAUDE.md — Aisha Personal AI

This file configures Claude Code behavior for this project. **All skills listed below are active by default — Claude should apply them automatically without being asked.**

---

## Project Overview

**aisha-personal-ai** is an AI personal assistant featuring:
- Telegram bot interface (`src/telegram/`)
- Voice processing (`src/core/voice_engine.py`)
- Multi-agent AI crews via CrewAI (`src/agents/`)
- Memory management (`src/memory/`)
- Core AI routing (`src/core/ai_router.py`)
- Web PWA frontend (`src/web/`)
- Supabase database (`src/integrations/supabase/`)

**Language**: Python (backend), TypeScript (frontend)
**Framework**: CrewAI for agents, python-telegram-bot, FastAPI
**Database**: Supabase (PostgreSQL)
**AI**: Claude API (Anthropic) as primary, fallback models configured

---

## Auto-Active Skills

These skills activate **automatically** based on context — no need to ask Claude to use them:

### `systematic-debugging` — Always on for bugs
**Triggers automatically when:**
- Any error, exception, or traceback appears
- Tests are failing
- Something "isn't working" or "broken"
- Unexpected behavior reported
- After a code change breaks something

**What it does:** Enforces root cause investigation before any fix. No random patches.

---

### `tdd` — Always on when writing new code
**Triggers automatically when:**
- Writing any new function, class, or module
- Implementing a feature
- Fixing a bug (test reproduces it first)
- Adding new agent, skill, or API endpoint

**What it does:** RED-GREEN-REFACTOR cycle. Tests are written before implementation.

---

### `write-plan` — Always on for complex tasks
**Triggers automatically when:**
- Task requires 3+ file changes
- Implementing a new feature end-to-end
- Adding new integrations
- Refactoring existing systems

**What it does:** Creates a plan in `docs/plans/` before writing any code.

---

### `brainstorm` — Always on for vague requests
**Triggers automatically when:**
- Request is open-ended or unclear
- Multiple approaches are possible
- Scope is undefined
- User says "I want to add X" without specifics

**What it does:** Structured design session → approval → plan. Never codes first.

---

### `verify` — Always on before completion claims
**Triggers automatically when:**
- About to say "done", "fixed", "complete"
- About to claim "tests pass"
- About to say "it's working"

**What it does:** Runs actual verification commands before making any claims.

---

### `code-review` — Always on for PR/review requests
**Triggers automatically when:**
- User asks to "review" code
- Before merging any branch
- After implementing a feature

**What it does:** Checks correctness, security, quality, tests, and project patterns.

---

### `security-review` — Always on for sensitive code
**Triggers automatically when:**
- Reviewing auth, tokens, API keys
- Adding new external integrations
- Handling user input from Telegram/web
- Before any deployment

**What it does:** Audits for secrets, injection, auth bypass, and insecure patterns.

---

### `parallel-agents` — Auto-dispatch for parallel work
**Triggers automatically when:**
- 3+ independent problems across different files/systems
- Multiple features can be implemented simultaneously
- Large codebase analysis needed

**What it does:** Dispatches independent agents concurrently instead of sequentially.

---

### `finish-branch` — Always on when work is complete
**Triggers automatically when:**
- Feature implementation is complete
- User says "I'm done" or "wrap this up"
- Ready to merge or PR

**What it does:** Verifies tests, then presents merge/PR/keep/discard options.

---

### `agent-builder` — Auto-use when adding new capabilities
**Triggers automatically when:**
- User wants Aisha to do something new
- Adding a new agent or crew
- Extending existing capabilities

**What it does:** Follows CrewAI patterns to build new agents with proper YAML configs.

---

## Skill Activation Rules

```
IF (error OR exception OR "not working" OR "broken")     → USE systematic-debugging
IF (writing new function/class/feature)                   → USE tdd
IF (task has 3+ changes OR new feature)                  → USE write-plan
IF (request is vague OR "I want to add X")               → USE brainstorm
IF (about to say "done"/"fixed"/"complete")              → USE verify
IF (reviewing code OR before merge)                      → USE code-review
IF (auth code OR API keys OR user input OR deploy)       → USE security-review
IF (3+ independent problems)                              → USE parallel-agents
IF (feature complete OR "wrap up")                        → USE finish-branch
IF (new agent OR new capability wanted)                   → USE agent-builder
```

---

## Project Conventions

### File Structure
```
src/
├── agents/         # CrewAI agents and crews
├── core/           # Core services (AI router, memory, voice, etc.)
├── skills/         # User-invocable skills (weather, spawn_ai, etc.)
├── telegram/       # Telegram bot handlers
├── memory/         # Memory management
├── web/            # PWA frontend
└── integrations/   # External service clients (Supabase)
tests/              # All tests go here
docs/
├── plans/          # Implementation plans (write-plan output)
└── specs/          # Design docs (brainstorm output)
```

### Code Patterns
- Config via `src/core/config.py` — no hardcoded values
- Logging via `src/core/logger.py` — no bare `print()`
- Memory ops via `src/memory/memory_manager.py`
- New agents: add YAML in `src/agents/config/`, then crew class
- New skills: add to `src/skills/`, register in `skill_registry.py`

### Git Workflow
- Branch from `master`
- Feature branches: `feature/<name>` or `claude/<task>-<id>`
- Commit after each logical step
- Always run tests before pushing

### Testing
```bash
python -m pytest tests/ -v          # All tests
python -m pytest tests/test_X.py   # Single file
python -m pytest --cov=src          # With coverage
```

### Models
- **Primary**: `claude-sonnet-4-6` — standard work
- **Complex reasoning**: `claude-opus-4-6` — critical decisions
- **Fast ops**: `claude-haiku-4-5-20251001` — simple tasks

---

## Never Do

- Never hardcode API keys, tokens, or secrets in source files
- Never use `eval()` or `exec()` on user input
- Never skip tests when implementing features
- Never claim "done" without running verification
- Never `git push --force` to master/main
- Never commit `.env` or `secrets.json`
