# Render + Supabase Deploy: 24/7 Aisha Bot Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the Aisha Telegram bot to Render.com with 24/7 uptime via UptimeRobot keep-alive, and migrate all 12 scheduled jobs to Supabase pg_cron so they run independently of Render's sleep cycle.

**Architecture:** `bot.py` gains two additions — a tiny threading HTTP server for `/health` and `/api/trigger/<job>` endpoints, and a background thread that starts `AutonomousLoop` as a fallback scheduler. Render hosts the bot process; UptimeRobot pings `/health` every 5 minutes to prevent free-tier sleep. Supabase pg_cron becomes the primary scheduler: it calls `/api/trigger/<job>` on the Render URL to fire each job, so even if Render does sleep between pings, pg_cron will wake it back up on the next scheduled tick.

**Tech Stack:** Python 3.11, pyTeleBot (`telebot`), `http.server` (stdlib, no new deps), Render.com free web service, UptimeRobot free account, Supabase pg_cron extension, Supabase `net` extension (for HTTP calls from SQL), Deno/TypeScript Edge Functions (for heavy trigger logic), Docker (optional reliability layer)

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `src/telegram/bot.py` | Modify (lines 1126-1158) | Add health server thread + trigger endpoint + autonomous loop thread |
| `Dockerfile` | Create | Optional container build for Render reliability |
| `supabase/functions/trigger-studio/index.ts` | Create | Edge Function called by pg_cron for studio sessions |
| `supabase/functions/trigger-maintenance/index.ts` | Create | Edge Function called by pg_cron for all maintenance jobs |
| `supabase/migrations/20260318000000_pg_cron_jobs.sql` | Create | All 12 pg_cron schedule entries |

---

## Chunk 1: Render Bot Changes

### Task 1: Add `/health` HTTP server to bot.py

**Files:**
- Modify: `src/telegram/bot.py` — `if __name__ == "__main__":` block starting at line 1126

The health server is a minimal stdlib `HTTPServer` running in a daemon thread. It must bind to `$PORT` (Render sets this env var; local default 8000). It also handles `POST /api/trigger/<job>` so pg_cron can fire jobs remotely (that endpoint is wired up in Task 11). For now Task 1 only adds GET health responses.

- [ ] **Step 1: Locate the exact insertion point in bot.py**

Open `src/telegram/bot.py`. The `if __name__ == "__main__":` block begins at line 1126. The final line is:
```
bot.infinity_polling(timeout=60, long_polling_timeout=60)
```
All new code goes **before** `bot.infinity_polling(...)`.

- [ ] **Step 2: Add imports at the top of bot.py (after existing imports, around line 27)**

Add after the existing `import telebot` block:
```python
import threading
import json as _json
from http.server import HTTPServer, BaseHTTPRequestHandler
```

- [ ] **Step 3: Add the HealthHandler class and start_health_server function**

Insert this block immediately before the `# ─── Health Tracking Commands ─────` section (around line 1022), so it's defined before `__main__` uses it:

```python
# ─── Render Health + Trigger Server ───────────────────────────────────────────

# Global reference to the AutonomousLoop instance (set during startup)
_autonomous_loop = None

TRIGGER_SECRET = os.getenv("TRIGGER_SECRET", "")


class _AishaHTTPHandler(BaseHTTPRequestHandler):
    """Minimal HTTP server for Render /health keep-alive and pg_cron /api/trigger/<job>."""

    def do_GET(self):
        if self.path in ('/', '/health', '/ping'):
            body = b'{"status":"ok","service":"aisha-bot"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        # Validate shared secret to prevent unauthorized triggers
        secret = self.headers.get("X-Trigger-Secret", "")
        if TRIGGER_SECRET and secret != TRIGGER_SECRET:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b'{"error":"forbidden"}')
            return

        parts = self.path.strip("/").split("/")
        # Expected: /api/trigger/<job>
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "trigger":
            job = parts[2]
            _dispatch_trigger(job)
            body = _json.dumps({"status": "accepted", "job": job}).encode()
            self.send_response(202)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Silence access logs to keep Render log output clean


def _dispatch_trigger(job: str):
    """Fire an AutonomousLoop method in a background thread (non-blocking)."""
    global _autonomous_loop
    if _autonomous_loop is None:
        log.warning(f"trigger_dispatch job={job} status=no_loop_yet")
        return

    job_map = {
        "morning":       _autonomous_loop.run_morning_checkin,
        "evening":       _autonomous_loop.run_evening_wrapup,
        "digest":        _autonomous_loop.run_daily_digest,
        "memory":        _autonomous_loop.run_memory_consolidation,
        "weekly-digest": _autonomous_loop.run_weekly_digest,
        "memory-cleanup":_autonomous_loop.run_memory_cleanup,
        "task-poll":     _autonomous_loop.run_task_reminder_poll,
        "inactivity":    _autonomous_loop.run_inactivity_check,
        "studio":        _autonomous_loop.run_studio_session,
        "self-improve":  lambda: __import__("src.core.autonomous_loop", fromlist=["run_self_improvement"]).run_self_improvement(_autonomous_loop),
        "temp-cleanup":  _autonomous_loop.run_temp_cleanup,
        "key-expiry":    _autonomous_loop.run_key_expiry_check,
    }

    fn = job_map.get(job)
    if fn is None:
        log.warning(f"trigger_dispatch job={job} status=unknown_job")
        return

    log.info(f"trigger_dispatch job={job} status=firing")
    t = threading.Thread(target=fn, daemon=True)
    t.start()


def start_health_server():
    """Start the HTTP health/trigger server on $PORT (Render injects this)."""
    port = int(os.getenv("PORT", "8000"))
    server = HTTPServer(('0.0.0.0', port), _AishaHTTPHandler)
    log.info(f"health_server port={port} status=starting")
    server.serve_forever()
```

- [ ] **Step 4: Verify the file is syntactically valid**

```bash
cd /e/VSCode/Aisha && python -c "import ast; ast.parse(open('src/telegram/bot.py').read()); print('syntax OK')"
```
Expected output: `syntax OK`

---

### Task 2: Start AutonomousLoop and health server threads in bot.py `__main__`

**Files:**
- Modify: `src/telegram/bot.py` — `if __name__ == "__main__":` block (line 1126+)

- [ ] **Step 1: Replace the current `__main__` block**

Find the existing block (lines 1126-1158):
```python
if __name__ == "__main__":
    log.info("💜 Aisha Telegram Bot starting...")
    log.info(f"Authorized user ID: {AUTHORIZED_ID or 'ALL (dev mode)'}")

    bot.set_my_commands([
        ...
    ])

    print("✅ Aisha is live on Telegram! 💜")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
```

Replace with:
```python
if __name__ == "__main__":
    log.info("💜 Aisha Telegram Bot starting...")
    log.info(f"Authorized user ID: {AUTHORIZED_ID or 'ALL (dev mode)'}")

    bot.set_my_commands([
        telebot.types.BotCommand("/start",   "Start / Greet Aisha"),
        telebot.types.BotCommand("/today",   "Today's summary"),
        telebot.types.BotCommand("/mood",    "Log your mood"),
        telebot.types.BotCommand("/expense", "Log an expense"),
        telebot.types.BotCommand("/goals",   "See your goals"),
        telebot.types.BotCommand("/journal", "Write a journal entry"),
        telebot.types.BotCommand("/memory",  "What Aisha remembers"),
        telebot.types.BotCommand("/voice",   "Toggle voice on/off"),
        telebot.types.BotCommand("/health",  "Today's health summary"),
        telebot.types.BotCommand("/water",   "Log water intake (/water 3)"),
        telebot.types.BotCommand("/sleep",   "Log sleep (/sleep 7.5 good)"),
        telebot.types.BotCommand("/workout", "Log workout (/workout run 30min)"),
        telebot.types.BotCommand("/digest",  "Today's AI digest"),
        telebot.types.BotCommand("/retry",   "Retry last failed message"),
        telebot.types.BotCommand("/help",    "Help & commands"),
        telebot.types.BotCommand("/reset",   "Reset conversation"),
        telebot.types.BotCommand("/upload",  "Upload latest content to YouTube"),
        telebot.types.BotCommand("/queue",   "View content pipeline queue"),
        telebot.types.BotCommand("/logs",    "View last 30 log lines (/logs 50)"),
        telebot.types.BotCommand("/syscheck","Run full system test"),
        telebot.types.BotCommand("/shell",   "Run shell command with confirmation"),
        telebot.types.BotCommand("/read",    "Read any file (/read src/core/ai_router.py)"),
        telebot.types.BotCommand("/gitpull", "Pull latest code from GitHub"),
        telebot.types.BotCommand("/restart", "Restart Aisha bot process"),
    ])

    # ── Health + Trigger HTTP server (required by Render + pg_cron) ──────────
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    log.info("health_server thread=started")

    # ── AutonomousLoop background thread (fallback scheduler) ────────────────
    def _start_autonomous_loop():
        global _autonomous_loop
        try:
            from src.core.autonomous_loop import AutonomousLoop, start_loop
            _autonomous_loop = AutonomousLoop()
            log.info("autonomous_loop status=initialized")
            # Run the schedule loop (blocks forever in its own thread)
            import schedule, time as _time
            import os as _os
            schedule.every().day.at("08:00").do(_autonomous_loop.run_morning_checkin)
            schedule.every().day.at("21:00").do(_autonomous_loop.run_evening_wrapup)
            schedule.every().day.at("21:30").do(_autonomous_loop.run_daily_digest)
            schedule.every().day.at("03:00").do(_autonomous_loop.run_memory_consolidation)
            schedule.every().sunday.at("19:00").do(_autonomous_loop.run_weekly_digest)
            schedule.every().sunday.at("03:00").do(_autonomous_loop.run_memory_cleanup)
            schedule.every(5).minutes.do(_autonomous_loop.run_task_reminder_poll)
            schedule.every(3).hours.do(_autonomous_loop.run_inactivity_check)
            schedule.every(4).hours.do(_autonomous_loop.run_studio_session)
            from src.core.autonomous_loop import run_self_improvement
            schedule.every().day.at("02:00").do(run_self_improvement, _autonomous_loop)
            schedule.every().day.at("04:00").do(_autonomous_loop.run_temp_cleanup)
            schedule.every().day.at("09:00").do(_autonomous_loop.run_key_expiry_check)
            log.info("autonomous_loop status=schedule_registered")
            while True:
                schedule.run_pending()
                _time.sleep(60)
        except Exception as e:
            log.error(f"autonomous_loop status=crashed err={e}")

    loop_thread = threading.Thread(target=_start_autonomous_loop, daemon=True)
    loop_thread.start()
    log.info("autonomous_loop thread=started")

    print("✅ Aisha is live on Telegram! 💜")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
```

- [ ] **Step 2: Syntax check**

```bash
cd /e/VSCode/Aisha && python -c "import ast; ast.parse(open('src/telegram/bot.py').read()); print('syntax OK')"
```
Expected: `syntax OK`

- [ ] **Step 3: Smoke test health server locally**

In one terminal:
```bash
cd /e/VSCode/Aisha && PORT=8001 python src/telegram/bot.py &
```
In another (wait 3 seconds for startup):
```bash
curl -s http://localhost:8001/health
```
Expected output: `{"status":"ok","service":"aisha-bot"}`

Kill the background process after confirming.

- [ ] **Step 4: Commit**

```bash
cd /e/VSCode/Aisha
git add src/telegram/bot.py
git commit -m "feat: add health server + autonomous loop thread for Render deploy"
```

---

### Task 3: Add Dockerfile

**Files:**
- Create: `Dockerfile`

Render can use either `Procfile` (existing) or `Dockerfile`. The Dockerfile gives Render a fixed Python version and avoids build environment drift. It is optional but recommended.

- [ ] **Step 1: Create Dockerfile at project root**

```dockerfile
FROM python:3.11-slim

# Install system deps for pyaudio / edge-tts if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render injects $PORT; our health server reads it
ENV PORT=8000

CMD ["python", "src/telegram/bot.py"]
```

- [ ] **Step 2: Verify Docker build locally (if Docker Desktop is installed)**

```bash
cd /e/VSCode/Aisha
docker build -t aisha-bot:local .
```
Expected: Build completes with `Successfully built ...`

If Docker is not installed, skip this step — Render will build it.

- [ ] **Step 3: Commit**

```bash
cd /e/VSCode/Aisha
git add Dockerfile
git commit -m "feat: add Dockerfile for Render deployment"
```

---

### Task 4: Environment variables checklist for Render dashboard

**Files:** None — this is a configuration checklist.

When creating the Render web service, go to **Environment** tab and add these vars:

| Variable | Source | Notes |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | BotFather | Required |
| `AJAY_TELEGRAM_ID` | `1002381172` | Hardcode from memory |
| `SUPABASE_URL` | Supabase → Settings → API | `https://fwfzqphqbeicgfaziuox.supabase.co` |
| `SUPABASE_SERVICE_KEY` | Supabase → Settings → API → service_role | Required |
| `GEMINI_API_KEY` | `AIzaSyCSXuVYFZIFjuhCdH0VcZoMICBhvHIuPy8` | Primary AI |
| `GROQ_API_KEY` | Groq console | Fallback AI |
| `ELEVENLABS_API_KEY` | ElevenLabs console | Voice synthesis |
| `XAI_API_KEY` | x.ai console | Riya channels (when credits restored) |
| `TRIGGER_SECRET` | Generate a random string, e.g. `openssl rand -hex 24` | Shared with Supabase pg_cron |
| `NVIDIA_API_KEY_01` through `_22` | From `src/core/nvidia_pool.py` | Optional — only needed if NVIDIA pool is used |

- [ ] **Step 1: Generate TRIGGER_SECRET**

```bash
python -c "import secrets; print(secrets.token_hex(24))"
```
Save this value — you will use it in both Render and Supabase secrets.

- [ ] **Step 2: Add TRIGGER_SECRET to Supabase secrets**

In Supabase Dashboard → Edge Functions → Secrets, add:
```
TRIGGER_SECRET=<the value from step 1>
RENDER_BOT_URL=https://<your-render-service-name>.onrender.com
```

You get the Render URL after deploying in Task 5.

- [ ] **Step 3: Commit a `.env.example` for documentation**

```bash
cd /e/VSCode/Aisha
```

Create `render.env.example` (not `.env` — never commit real secrets):
```
TELEGRAM_BOT_TOKEN=
AJAY_TELEGRAM_ID=1002381172
SUPABASE_URL=https://fwfzqphqbeicgfaziuox.supabase.co
SUPABASE_SERVICE_KEY=
GEMINI_API_KEY=
GROQ_API_KEY=
ELEVENLABS_API_KEY=
XAI_API_KEY=
TRIGGER_SECRET=
```

```bash
git add render.env.example
git commit -m "docs: add render.env.example for deployment checklist"
```

---

**End of Chunk 1. Commit checkpoint: 3 commits total.**

---

## Chunk 2: Render Infrastructure (Deploy + UptimeRobot)

### Task 5: Deploy to Render via dashboard

**Prerequisites:** Tasks 1–4 complete. Code pushed to GitHub main branch.

- [ ] **Step 1: Push all changes to GitHub**

```bash
cd /e/VSCode/Aisha
git push origin main
```

- [ ] **Step 2: Create Render web service**

1. Go to https://dashboard.render.com → **New** → **Web Service**
2. Connect GitHub → select `AjayBervanshi/aisha-personal-ai`
3. Settings:
   - **Name:** `aisha-bot`
   - **Region:** `Singapore` (closest to India for Telegram latency)
   - **Branch:** `main`
   - **Runtime:** `Docker` (if Dockerfile exists) OR `Python 3` (Render auto-detects Procfile)
   - **Build Command:** (leave blank — Render uses Dockerfile or auto-detects)
   - **Start Command:** (leave blank — Dockerfile CMD or Procfile handles this)
   - **Plan:** `Free`
4. Add all environment variables from Task 4 checklist.
5. Click **Create Web Service**.

- [ ] **Step 3: Wait for first deploy to complete**

Expected in Render logs:
```
health_server port=10000 status=starting
autonomous_loop thread=started
✅ Aisha is live on Telegram!
```

Note: Render free tier assigns port 10000 (not 8000). The service reads `$PORT` so this is automatic.

- [ ] **Step 4: Note your Render service URL**

It will be: `https://aisha-bot.onrender.com` (or similar).

Go to Render → Settings → confirm the URL.

- [ ] **Step 5: Test health endpoint from browser or curl**

```bash
curl -s https://aisha-bot.onrender.com/health
```
Expected: `{"status":"ok","service":"aisha-bot"}`

- [ ] **Step 6: Update RENDER_BOT_URL in Supabase secrets** (now that you have the real URL)

Supabase Dashboard → Edge Functions → Secrets:
```
RENDER_BOT_URL=https://aisha-bot.onrender.com
```

---

### Task 6: Set up UptimeRobot to ping /health every 5 minutes

UptimeRobot's free tier pings every 5 minutes. Render free tier sleeps after 15 minutes of inactivity. Five-minute pings keep it permanently awake.

- [ ] **Step 1: Create UptimeRobot account**

Go to https://uptimerobot.com → Sign up for free.

- [ ] **Step 2: Add new monitor**

1. Click **Add New Monitor**
2. Monitor Type: **HTTP(s)**
3. Friendly Name: `Aisha Bot - Render`
4. URL: `https://aisha-bot.onrender.com/health`
5. Monitoring Interval: **5 minutes**
6. Click **Create Monitor**

- [ ] **Step 3: Verify first ping succeeds**

UptimeRobot dashboard should show green status within 5 minutes.

- [ ] **Step 4: (Optional) Add alert contact**

Add your email or Telegram for downtime alerts:
UptimeRobot → My Settings → Alert Contacts → Add Alert Contact.

---

**End of Chunk 2.**

---

## Chunk 3: Supabase pg_cron Scheduled Jobs

### Task 7: Enable pg_cron and net extensions in Supabase

Both extensions must be active before any cron jobs or HTTP-from-SQL calls will work.

- [ ] **Step 1: Enable pg_cron**

In Supabase Dashboard → Database → Extensions, search `pg_cron` → Enable.

OR run in SQL Editor:
```sql
CREATE EXTENSION IF NOT EXISTS pg_cron;
```

- [ ] **Step 2: Enable pg_net (for HTTP calls from SQL)**

```sql
CREATE EXTENSION IF NOT EXISTS pg_net;
```

Verify both are active:
```sql
SELECT name, default_version FROM pg_available_extensions
WHERE name IN ('pg_cron', 'pg_net') ORDER BY name;
```
Expected: Two rows, both with a version number.

---

### Task 8: Create Edge Function `trigger-studio`

**Files:**
- Create: `supabase/functions/trigger-studio/index.ts`

This Edge Function is a thin proxy. pg_cron calls it via `net.http_post`, and it forwards to the Render bot's `/api/trigger/studio` endpoint. Having an Edge Function as the intermediary means pg_cron does not need to know the Render URL directly — only the Edge Function does, via Supabase secrets. This also means if the Render URL changes, only the secret needs updating.

- [ ] **Step 1: Create the function directory and file**

```bash
mkdir -p /e/VSCode/Aisha/supabase/functions/trigger-studio
```

Create `supabase/functions/trigger-studio/index.ts`:

```typescript
// trigger-studio/index.ts
// Called by pg_cron every 4 hours.
// Forwards to Render bot's /api/trigger/studio endpoint.
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const RENDER_BOT_URL = Deno.env.get("RENDER_BOT_URL")!;
const TRIGGER_SECRET = Deno.env.get("TRIGGER_SECRET") ?? "";

serve(async (_req) => {
  try {
    const res = await fetch(`${RENDER_BOT_URL}/api/trigger/studio`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Trigger-Secret": TRIGGER_SECRET,
      },
      body: JSON.stringify({ source: "pg_cron" }),
    });

    const body = await res.text();
    console.log(`trigger-studio → Render: ${res.status} ${body}`);

    return new Response(
      JSON.stringify({ status: res.status, body }),
      { headers: { "Content-Type": "application/json" } }
    );
  } catch (err) {
    console.error("trigger-studio error:", err);
    return new Response(
      JSON.stringify({ error: String(err) }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
});
```

- [ ] **Step 2: Deploy the Edge Function**

```bash
cd /e/VSCode/Aisha
npx supabase functions deploy trigger-studio --project-ref fwfzqphqbeicgfaziuox
```
Expected: `Deployed Function trigger-studio`

- [ ] **Step 3: Test the function manually**

```bash
npx supabase functions invoke trigger-studio \
  --project-ref fwfzqphqbeicgfaziuox \
  --no-verify-jwt
```
Expected: `{"status":202,"body":"{\"status\":\"accepted\",\"job\":\"studio\"}"}`

(This will only succeed if Render is already deployed from Task 5.)

- [ ] **Step 4: Commit**

```bash
cd /e/VSCode/Aisha
git add supabase/functions/trigger-studio/
git commit -m "feat: add trigger-studio edge function for pg_cron"
```

---

### Task 9: Create Edge Function `trigger-maintenance`

**Files:**
- Create: `supabase/functions/trigger-maintenance/index.ts`

This single function handles all 11 non-studio jobs. The caller passes `?job=<name>` in the URL query string. pg_cron will call this with different `job` values on different schedules.

- [ ] **Step 1: Create the function**

```bash
mkdir -p /e/VSCode/Aisha/supabase/functions/trigger-maintenance
```

Create `supabase/functions/trigger-maintenance/index.ts`:

```typescript
// trigger-maintenance/index.ts
// Called by pg_cron for all non-studio scheduled jobs.
// Usage: POST /trigger-maintenance?job=<job-name>
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const RENDER_BOT_URL = Deno.env.get("RENDER_BOT_URL")!;
const TRIGGER_SECRET = Deno.env.get("TRIGGER_SECRET") ?? "";

const VALID_JOBS = new Set([
  "morning", "evening", "digest", "memory",
  "weekly-digest", "memory-cleanup", "task-poll",
  "inactivity", "self-improve", "temp-cleanup", "key-expiry",
]);

serve(async (req) => {
  const url = new URL(req.url);
  const job = url.searchParams.get("job") ?? "";

  if (!VALID_JOBS.has(job)) {
    return new Response(
      JSON.stringify({ error: `unknown job: ${job}` }),
      { status: 400, headers: { "Content-Type": "application/json" } }
    );
  }

  try {
    const res = await fetch(`${RENDER_BOT_URL}/api/trigger/${job}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Trigger-Secret": TRIGGER_SECRET,
      },
      body: JSON.stringify({ source: "pg_cron" }),
    });

    const body = await res.text();
    console.log(`trigger-maintenance job=${job} → Render: ${res.status} ${body}`);

    return new Response(
      JSON.stringify({ job, status: res.status, body }),
      { headers: { "Content-Type": "application/json" } }
    );
  } catch (err) {
    console.error(`trigger-maintenance job=${job} error:`, err);
    return new Response(
      JSON.stringify({ error: String(err) }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
});
```

- [ ] **Step 2: Deploy**

```bash
cd /e/VSCode/Aisha
npx supabase functions deploy trigger-maintenance --project-ref fwfzqphqbeicgfaziuox
```
Expected: `Deployed Function trigger-maintenance`

- [ ] **Step 3: Test with morning job**

```bash
npx supabase functions invoke trigger-maintenance \
  --project-ref fwfzqphqbeicgfaziuox \
  --no-verify-jwt \
  -- '?job=morning'
```
Expected: `{"job":"morning","status":202,...}`

- [ ] **Step 4: Commit**

```bash
cd /e/VSCode/Aisha
git add supabase/functions/trigger-maintenance/
git commit -m "feat: add trigger-maintenance edge function for pg_cron"
```

---

### Task 10: Add all 12 pg_cron SQL entries

**Files:**
- Create: `supabase/migrations/20260318000000_pg_cron_jobs.sql`

The pg_cron syntax requires the `net.http_post` function from `pg_net`. All cron times are UTC. India Standard Time (IST) is UTC+5:30, so:
- `08:00 IST` = `02:30 UTC`
- `09:00 IST` = `03:30 UTC`
- `21:00 IST` = `15:30 UTC`
- `21:30 IST` = `16:00 UTC`
- `03:00 IST` = `21:30 UTC` (previous day boundary, use `21:30`)
- `02:00 IST` = `20:30 UTC`
- `04:00 IST` = `22:30 UTC`
- `19:00 IST Sunday` = `13:30 UTC Sunday`
- `03:00 IST Sunday` = `21:30 UTC Saturday`

The Edge Function URLs follow the pattern:
`https://fwfzqphqbeicgfaziuox.supabase.co/functions/v1/<function-name>`

- [ ] **Step 1: Create the migration file**

Create `supabase/migrations/20260318000000_pg_cron_jobs.sql`:

```sql
-- ============================================================
-- Aisha pg_cron Jobs Migration
-- All times in UTC (IST = UTC+5:30)
-- Primary scheduler: pg_cron → Edge Function → Render /api/trigger/<job>
-- ============================================================

-- Remove any existing Aisha jobs (idempotent re-run safety)
SELECT cron.unschedule(jobname)
FROM cron.job
WHERE jobname LIKE 'aisha-%';

-- Helper: Edge Function base URL
-- NOTE: Replace with actual Supabase project URL if different
-- Functions URL pattern: https://<ref>.supabase.co/functions/v1/<name>

-- ── Daily Jobs ─────────────────────────────────────────────────────────────

-- 1. Morning check-in — 08:00 IST = 02:30 UTC
SELECT cron.schedule(
  'aisha-morning',
  '30 2 * * *',
  $$
  SELECT net.http_post(
    url     := 'https://fwfzqphqbeicgfaziuox.supabase.co/functions/v1/trigger-maintenance?job=morning',
    headers := '{"Content-Type":"application/json","Authorization":"Bearer ' || current_setting('app.supabase_anon_key', true) || '"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);

-- 2. Evening wrap-up — 21:00 IST = 15:30 UTC
SELECT cron.schedule(
  'aisha-evening',
  '30 15 * * *',
  $$
  SELECT net.http_post(
    url     := 'https://fwfzqphqbeicgfaziuox.supabase.co/functions/v1/trigger-maintenance?job=evening',
    headers := '{"Content-Type":"application/json","Authorization":"Bearer ' || current_setting('app.supabase_anon_key', true) || '"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);

-- 3. Daily digest — 21:30 IST = 16:00 UTC
SELECT cron.schedule(
  'aisha-daily-digest',
  '0 16 * * *',
  $$
  SELECT net.http_post(
    url     := 'https://fwfzqphqbeicgfaziuox.supabase.co/functions/v1/trigger-maintenance?job=digest',
    headers := '{"Content-Type":"application/json","Authorization":"Bearer ' || current_setting('app.supabase_anon_key', true) || '"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);

-- 4. Memory consolidation — 03:00 IST = 21:30 UTC (previous calendar day)
SELECT cron.schedule(
  'aisha-memory-consolidation',
  '30 21 * * *',
  $$
  SELECT net.http_post(
    url     := 'https://fwfzqphqbeicgfaziuox.supabase.co/functions/v1/trigger-maintenance?job=memory',
    headers := '{"Content-Type":"application/json","Authorization":"Bearer ' || current_setting('app.supabase_anon_key', true) || '"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);

-- 5. Self-improvement — 02:00 IST = 20:30 UTC
SELECT cron.schedule(
  'aisha-self-improve',
  '30 20 * * *',
  $$
  SELECT net.http_post(
    url     := 'https://fwfzqphqbeicgfaziuox.supabase.co/functions/v1/trigger-maintenance?job=self-improve',
    headers := '{"Content-Type":"application/json","Authorization":"Bearer ' || current_setting('app.supabase_anon_key', true) || '"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);

-- 6. Temp file cleanup — 04:00 IST = 22:30 UTC
SELECT cron.schedule(
  'aisha-temp-cleanup',
  '30 22 * * *',
  $$
  SELECT net.http_post(
    url     := 'https://fwfzqphqbeicgfaziuox.supabase.co/functions/v1/trigger-maintenance?job=temp-cleanup',
    headers := '{"Content-Type":"application/json","Authorization":"Bearer ' || current_setting('app.supabase_anon_key', true) || '"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);

-- 7. API key expiry check — 09:00 IST = 03:30 UTC
SELECT cron.schedule(
  'aisha-key-expiry',
  '30 3 * * *',
  $$
  SELECT net.http_post(
    url     := 'https://fwfzqphqbeicgfaziuox.supabase.co/functions/v1/trigger-maintenance?job=key-expiry',
    headers := '{"Content-Type":"application/json","Authorization":"Bearer ' || current_setting('app.supabase_anon_key', true) || '"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);

-- ── Weekly Jobs ────────────────────────────────────────────────────────────

-- 8. Weekly digest — Sunday 19:00 IST = Sunday 13:30 UTC
SELECT cron.schedule(
  'aisha-weekly-digest',
  '30 13 * * 0',
  $$
  SELECT net.http_post(
    url     := 'https://fwfzqphqbeicgfaziuox.supabase.co/functions/v1/trigger-maintenance?job=weekly-digest',
    headers := '{"Content-Type":"application/json","Authorization":"Bearer ' || current_setting('app.supabase_anon_key', true) || '"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);

-- 9. Memory cleanup — Sunday 03:00 IST = Saturday 21:30 UTC (day 6 = Saturday)
SELECT cron.schedule(
  'aisha-memory-cleanup',
  '30 21 * * 6',
  $$
  SELECT net.http_post(
    url     := 'https://fwfzqphqbeicgfaziuox.supabase.co/functions/v1/trigger-maintenance?job=memory-cleanup',
    headers := '{"Content-Type":"application/json","Authorization":"Bearer ' || current_setting('app.supabase_anon_key', true) || '"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);

-- ── High-Frequency Jobs ────────────────────────────────────────────────────

-- 10. Task reminder poll — every 5 minutes
SELECT cron.schedule(
  'aisha-task-poll',
  '*/5 * * * *',
  $$
  SELECT net.http_post(
    url     := 'https://fwfzqphqbeicgfaziuox.supabase.co/functions/v1/trigger-maintenance?job=task-poll',
    headers := '{"Content-Type":"application/json","Authorization":"Bearer ' || current_setting('app.supabase_anon_key', true) || '"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);

-- 11. Inactivity check — every 3 hours
SELECT cron.schedule(
  'aisha-inactivity',
  '0 */3 * * *',
  $$
  SELECT net.http_post(
    url     := 'https://fwfzqphqbeicgfaziuox.supabase.co/functions/v1/trigger-maintenance?job=inactivity',
    headers := '{"Content-Type":"application/json","Authorization":"Bearer ' || current_setting('app.supabase_anon_key', true) || '"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);

-- ── Studio (heavy job — its own function) ─────────────────────────────────

-- 12. Studio session — every 4 hours
SELECT cron.schedule(
  'aisha-studio-every-4h',
  '0 */4 * * *',
  $$
  SELECT net.http_post(
    url     := 'https://fwfzqphqbeicgfaziuox.supabase.co/functions/v1/trigger-studio',
    headers := '{"Content-Type":"application/json","Authorization":"Bearer ' || current_setting('app.supabase_anon_key', true) || '"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);

-- ── Verify ────────────────────────────────────────────────────────────────
-- Run this after applying the migration to confirm all 12 jobs are registered:
-- SELECT jobname, schedule, active FROM cron.job WHERE jobname LIKE 'aisha-%' ORDER BY jobname;
```

**Note on Authorization header:** The Edge Functions need a valid JWT to be called externally. The SQL above uses `current_setting('app.supabase_anon_key', true)`. Alternatively, since we own the functions, deploy them with `--no-verify-jwt` and remove the Authorization header — simpler and avoids the JWT complexity. See Task 11 for this decision.

- [ ] **Step 2: Redeploy Edge Functions with --no-verify-jwt for simplicity**

```bash
cd /e/VSCode/Aisha
npx supabase functions deploy trigger-studio \
  --project-ref fwfzqphqbeicgfaziuox \
  --no-verify-jwt

npx supabase functions deploy trigger-maintenance \
  --project-ref fwfzqphqbeicgfaziuox \
  --no-verify-jwt
```

This allows pg_cron to call the Edge Functions without managing JWTs. Security is handled by `TRIGGER_SECRET` passed through to Render.

- [ ] **Step 3: Update the SQL to remove Authorization header (since --no-verify-jwt)**

Update `supabase/migrations/20260318000000_pg_cron_jobs.sql` — replace all `headers` lines with:
```sql
    headers := '{"Content-Type":"application/json"}'::jsonb,
```

(Remove the `Authorization` field from all 12 `net.http_post` calls.)

- [ ] **Step 4: Apply migration in Supabase SQL Editor**

In Supabase Dashboard → SQL Editor → paste the contents of `supabase/migrations/20260318000000_pg_cron_jobs.sql` → Run.

Expected: 12 `SELECT` results returned (one per `cron.schedule` call), each showing a job ID integer.

- [ ] **Step 5: Verify all 12 jobs are registered**

```sql
SELECT jobname, schedule, active FROM cron.job WHERE jobname LIKE 'aisha-%' ORDER BY jobname;
```
Expected: 12 rows, all `active = true`.

- [ ] **Step 6: Commit**

```bash
cd /e/VSCode/Aisha
git add supabase/migrations/20260318000000_pg_cron_jobs.sql
git commit -m "feat: add pg_cron schedule for all 12 Aisha autonomous jobs"
```

---

### Task 11: Add `/api/trigger/<job>` endpoint — already done in Task 1

The `_AishaHTTPHandler.do_POST` and `_dispatch_trigger` function added in Task 1 already implement this endpoint. No additional file changes are needed.

This task is a **verification step** to confirm the endpoint is correctly wired to all 12 job names.

- [ ] **Step 1: Confirm all 12 job keys are in `_dispatch_trigger`'s `job_map`**

Open `src/telegram/bot.py` and find `_dispatch_trigger`. Verify `job_map` contains all 12 keys:
- `morning`, `evening`, `digest`, `memory`
- `weekly-digest`, `memory-cleanup`, `task-poll`
- `inactivity`, `studio`, `self-improve`
- `temp-cleanup`, `key-expiry`

- [ ] **Step 2: Test trigger endpoint locally**

Start bot locally with `PORT=8001`:
```bash
PORT=8001 python /e/VSCode/Aisha/src/telegram/bot.py &
sleep 3
curl -s -X POST http://localhost:8001/api/trigger/morning \
  -H "Content-Type: application/json" \
  -H "X-Trigger-Secret: test-secret" \
  -d '{}'
```
Expected: `{"status":"accepted","job":"morning"}`

(The actual job will fire in a background thread — check logs for `trigger_dispatch job=morning status=firing`.)

- [ ] **Step 3: Test unknown job returns 404-class**

```bash
curl -s -X POST http://localhost:8001/api/trigger/nonexistent \
  -H "X-Trigger-Secret: test-secret" \
  -d '{}'
```
Expected: `{"status":"accepted","job":"nonexistent"}` — the endpoint accepts it, but `_dispatch_trigger` logs `status=unknown_job`. This is intentional (202 accept, non-blocking).

---

**End of Chunk 3. Running commit total: 6 commits.**

---

## Chunk 4: Verification

### Task 12: Verify bot responds on Telegram

- [ ] **Step 1: Open Telegram and find the bot**

Search for `@<your_bot_username>` (the one connected to `TELEGRAM_BOT_TOKEN`).

- [ ] **Step 2: Send `/start`**

Expected: Aisha responds with her greeting message within 5 seconds.

- [ ] **Step 3: Send a plain text message**

Expected: Aisha responds with an AI-generated reply. Render logs should show:
```
[Ajay] <first 80 chars of message>
```

- [ ] **Step 4: Check Render logs for errors**

Render Dashboard → aisha-bot → Logs. Look for any `ERROR` or stack traces. Common issues and fixes:
- `ModuleNotFoundError`: A dependency is missing from `requirements.txt`
- `TELEGRAM_BOT_TOKEN not set`: Missing env var in Render dashboard
- `Connection refused` on Supabase: `SUPABASE_URL` or `SUPABASE_SERVICE_KEY` wrong

---

### Task 13: Verify /health returns 200 OK

- [ ] **Step 1: Direct curl test**

```bash
curl -v https://aisha-bot.onrender.com/health
```
Expected:
```
< HTTP/2 200
{"status":"ok","service":"aisha-bot"}
```

- [ ] **Step 2: Verify all three health paths**

```bash
curl -s https://aisha-bot.onrender.com/
curl -s https://aisha-bot.onrender.com/health
curl -s https://aisha-bot.onrender.com/ping
```
All three should return `{"status":"ok","service":"aisha-bot"}`.

- [ ] **Step 3: Verify unknown path returns 404**

```bash
curl -s -o /dev/null -w "%{http_code}" https://aisha-bot.onrender.com/unknown
```
Expected: `404`

---

### Task 14: Verify pg_cron jobs are scheduled in Supabase

- [ ] **Step 1: Check job list in SQL Editor**

```sql
SELECT jobname, schedule, active, nodename
FROM cron.job
WHERE jobname LIKE 'aisha-%'
ORDER BY jobname;
```
Expected: 12 rows, all `active = true`.

- [ ] **Step 2: Manually trigger one job via the Edge Function**

```bash
npx supabase functions invoke trigger-maintenance \
  --project-ref fwfzqphqbeicgfaziuox \
  --no-verify-jwt \
  --body '{}' \
  -- '?job=key-expiry'
```
Expected: `{"job":"key-expiry","status":202,...}`

Check Render logs for: `trigger_dispatch job=key-expiry status=firing`

- [ ] **Step 3: Check cron job run history (after waiting for next scheduled run)**

```sql
SELECT jobname, runid, job_pid, start_time, end_time, status
FROM cron.job_run_details
WHERE jobname LIKE 'aisha-%'
ORDER BY start_time DESC
LIMIT 20;
```
Expected: Rows appearing as each job fires on its schedule.

- [ ] **Step 4: Manually trigger studio via its dedicated function**

```bash
npx supabase functions invoke trigger-studio \
  --project-ref fwfzqphqbeicgfaziuox \
  --no-verify-jwt
```
Expected: `{"status":202,...}` and Render logs show `trigger_dispatch job=studio status=firing`.

---

### Task 15: Verify UptimeRobot is pinging successfully

- [ ] **Step 1: Check UptimeRobot dashboard**

Go to https://dashboard.uptimerobot.com. The `Aisha Bot - Render` monitor should show:
- Status: **Up** (green)
- Response time: under 2000ms
- Uptime: 100% (since it was just created)

- [ ] **Step 2: Check Render keeps-alive across a 10-minute window**

Wait 10 minutes. During this time, UptimeRobot sends 2 pings. Check Render logs — you should NOT see any `Starting...` messages (which would indicate the service woke from sleep). If you see them, the service is sleeping between pings — verify UptimeRobot interval is set to 5 minutes.

- [ ] **Step 3: Simulate what happens if Render does sleep**

This is theoretical — but pg_cron + Edge Functions provide a safety net. If Render sleeps and UptimeRobot wakes it, the `/health` ping will reboot the bot process. The `_start_autonomous_loop` thread will re-register schedules. The `_startup_recovery` in `AutonomousLoop.__init__` will reset any stuck `processing` jobs in Supabase. This is already handled.

- [ ] **Step 4: Final integration smoke test**

Send a Telegram message. Verify:
1. Aisha responds (Telegram bot working)
2. `/health` returns 200 (HTTP server working)
3. UptimeRobot shows green (keep-alive working)
4. SQL: 12 pg_cron jobs active (scheduler working)
5. Render logs: no crash errors

---

**End of Chunk 4. All 15 tasks complete.**

---

## Summary of All 15 Tasks

| Task | File(s) | What it Does |
|---|---|---|
| 1 | `src/telegram/bot.py` | Health server class + trigger dispatcher |
| 2 | `src/telegram/bot.py` | Main block: start health thread + autonomous loop thread |
| 3 | `Dockerfile` | Container build for Render reliability |
| 4 | `render.env.example` | Env vars checklist for Render dashboard |
| 5 | — | Push code, create Render web service, note URL |
| 6 | — | UptimeRobot free account, 5-min /health ping |
| 7 | — | Enable pg_cron + pg_net extensions in Supabase |
| 8 | `supabase/functions/trigger-studio/index.ts` | Edge Function proxy for studio job |
| 9 | `supabase/functions/trigger-maintenance/index.ts` | Edge Function proxy for all 11 other jobs |
| 10 | `supabase/migrations/20260318000000_pg_cron_jobs.sql` | 12 pg_cron schedule entries (UTC times) |
| 11 | `src/telegram/bot.py` | Verification: confirm all 12 job keys in dispatch map |
| 12 | — | Verify Telegram bot responds |
| 13 | — | Verify /health returns 200 on all 3 paths |
| 14 | — | Verify 12 pg_cron jobs active + manual trigger test |
| 15 | — | Verify UptimeRobot green + end-to-end smoke test |

## Key Decisions

1. **Stdlib `http.server`, not Flask/FastAPI** — Zero new dependencies. The health server is too small to justify a framework.

2. **AutonomousLoop runs in bot.py, not as a separate process** — Render free tier gives 1 process. The loop runs as a daemon thread alongside `infinity_polling`. If the process dies, both restart together.

3. **pg_cron → Edge Function → Render** — pg_cron cannot easily call Render directly with auth headers. The Edge Function layer handles the secret injection and provides a stable, version-controlled call site.

4. **`--no-verify-jwt` for trigger functions** — The trigger functions are internal-only (called from pg_cron, not browser). JWT verification adds complexity without security benefit here since `TRIGGER_SECRET` in the Render endpoint provides the equivalent protection.

5. **UTC time conversion** — All IST times are explicitly converted. Sunday 03:00 IST maps to Saturday 21:30 UTC (day boundary crossing).

6. **`task-poll` (every 5 min) via pg_cron** — This fires 288 times/day. pg_net calls are lightweight; Edge Function cold starts may add 1-2s latency. This is acceptable for task reminders (not real-time critical).

7. **Dual scheduler (pg_cron primary + schedule library fallback)** — If Supabase pg_cron has an outage, the in-process `schedule` library still fires jobs. Belt and suspenders.
