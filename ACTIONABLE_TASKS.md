# 🛠️ Actionable Task List

Convert these findings directly into GitHub issues or a working sprint.

### [CRITICAL] Security & Data Privacy
- [ ] **Fix SSRF in Workflow Engine:** Add IP/hostname sanitization to `workflow_engine.py` HTTP requests.
- [ ] **Stop Screen Text Data Leak:** Prevent raw `screen_text` from being shipped to public LLMs in `goal_engine.py`.
- [ ] **Refactor OAuth CSRF State:** Move `_oauth_states` out of memory into Supabase or use JWT signatures.

### [HIGH] Architecture & Performance
- [ ] **Cap Self-Healing Retries:** Add a maximum retry limit to `workflow_engine.py` error catching.
- [ ] **Fix O(N) Database Queries:** Append `.limit(MAX)` to all Supabase `.select()` calls that currently return unbounded lists (specifically in `goal_engine.py` and `bot.py`).
- [ ] **Offload Scheduler Thread:** Wrap long-running scheduled tasks in `autonomous_loop.py` inside `threading.Thread(target=...).start()` or a ThreadPoolExecutor to prevent head-of-line blocking.

### [MEDIUM] Code Quality & Debt
- [ ] **Refactor `bot.py` (God Object):** Split `src/telegram/bot.py` into:
  - `src/telegram/router.py` (Handlers)
  - `src/telegram/views.py` (Inline keyboards & formatting)
  - `src/core/scheduler.py` (Move background jobs entirely out of the telegram folder).
- [ ] **Implement Pydantic Validation:** Introduce schema validation for LLM outputs in `GoalEngine` and `WorkflowEngine` instead of relying entirely on `json.loads` and regex.
- [ ] **Fix Bare Exceptions:** Do a global search and replace for bare `except Exception:` and `except:` to ensure at minimum, stack traces are logged via `log.exception()`.

### [DEEP DIVE REMEDIATIONS]
- [ ] **Refactor Dependency Inversion:** Remove inline imports inside functions in `bot.py` by implementing an Event Bus or Dependency Injection framework for instantiating the `SelfEditor`, `SocialMediaEngine`, and `FeaturePipeline`.
- [ ] **Extract Daemon Thread Scheduling:** Move the `AutonomousLoop` registration entirely out of `bot.py` and into an independent worker service (`src/worker.py`) that can be scaled independently of the Telegram bot instance.
- [ ] **Migrate OAuth CSRF State to DB:** Deprecate the in-memory `_oauth_states` dictionary. Create a Supabase table `aisha_oauth_states(id UUID, state UUID, user_id BIGINT, expires_at TIMESTAMPTZ)` to support clustered deployments.
- [ ] **Rewrite LLM Error Handling:** Remove `except Exception: pass` from `ai_router.py` initialization blocks. Initialization failures should crash early or use specific `requests.exceptions.RequestException` traps.
