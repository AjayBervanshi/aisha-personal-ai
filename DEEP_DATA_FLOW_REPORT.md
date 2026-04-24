# Deep Data Flow Report: Aisha Personal AI

## 1. Interface & Routing (`src/telegram/bot.py`)
**Role:** Main entry point and orchestration layer (God Object).

### A. Initialization & Environment
- Loads environment variables and initializes core clients: `telebot`, `Supabase`, and `AishaBrain`.
- Implements custom role-based access control (RBAC). It queries `aisha_users` and falls back to `aisha_approved_users` to load an in-memory dictionary `_user_roles`.
- Hardcodes the owner access using the `AJAY_TELEGRAM_ID`.
- Uses global dicts for locks (`_chat_locks`), OAuth states (`_oauth_states`), and fallback rate limiting (`_last_fallback`), introducing severe scaling issues.

### B. Message Routing
- Handles commands using standard `@bot.message_handler(commands=[...])`.
- Example command flow (`/upgrade`):
  1. Validates `is_admin()`.
  2. Spawns an inline detached thread: `threading.Thread(target=_run_upgrade, daemon=True).start()`.
  3. Inside `_run_upgrade()`, it lazy imports `SelfEditor` to avoid circular dependencies.
  4. Calls `editor.run_improvement_session()`.

### C. Background Scheduling (`autonomous_loop`)
- A background daemon thread is started at the bottom of `bot.py` via `_start_autonomous_loop()`.
- Uses the `schedule` library to register heavy synchronous jobs (e.g., `run_morning_checkin`, `run_content_publisher`).
- Runs `schedule.run_pending()` every 60 seconds.

### D. Webhook Server (`BaseHTTPRequestHandler`)
- Starts a custom HTTP server (`health_thread`) running on `PORT` (or 8000).
- Handles basic `/health` checks.
- Handles `/instagram_callback` for OAuth, popping global state strings from `_oauth_states`.
- Handles `/{BOT_TOKEN}` for Telegram webhooks.

## 2. Core AI & Logic (`src/core/`)

### A. AI Router (`ai_router.py`)
**Role:** Facade for external LLM API calls.
- Contains an internal mapping of `_stats` (success/failures/cooldowns) for various providers (Gemini, Anthropic, Mistral, OpenAI, NVIDIA, etc.).
- When `generate()` is called, it iterates through a prioritized list of providers.
- It instantiates SDK clients dynamically within `_init_clients()`. Many initialization failures are swallowed via `except Exception: pass`.
- Automatically shifts to fallback providers on rate limits (429) or timeouts, and logs failovers via `GmailEngine`.

### B. Workflow Engine (`workflow_engine.py`)
**Role:** NLP-to-DAG orchestration.
- Parses NLP commands into AST representations.
- Evaluates Logic Nodes via `_safe_eval(cond)` which parses AST using `ast.parse`.
- Handles `action.http_request` by blindly invoking `urllib.request.urlopen(config.get("url"))`, causing an unauthenticated SSRF vulnerability.
- Implements a naive retry loop (`self_healing` phase) when a node fails. The LLM is given the node's JSON and asked to rewrite it, and it immediately retries without bounding.

### C. Goal Engine (`goal_engine.py`)
**Role:** OKR generation and habit tracking.
- Breaks text into JSON structures (`Objective`, `Key Results`, `Daily Actions`).
- Extracts `aisha_awareness_logs` using `gte` (fetching all day's logs at once) and feeds them into the LLM prompt to automatically resolve habits.

## 3. Storage & Integration (Supabase)
- Connects using `create_client` instantiated globally in `bot.py` and passed into core engines.
- Schema utilizes PostgreSQL extensions and relies on the backend `service_role` key to bypass RLS policies.
- Direct row modifications occur inline throughout `bot.py` (violating separation of concerns).
