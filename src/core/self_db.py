"""
self_db.py
==========
Aisha's self-healing database module.
Detects missing tables and auto-creates them via Supabase Management API.
Uses SUPABASE_PAT (project access token) for DDL operations.
"""

import os
import requests
import logging

log = logging.getLogger(__name__)

SUPABASE_URL  = os.getenv("SUPABASE_URL", "")
SERVICE_KEY   = os.getenv("SUPABASE_SERVICE_KEY", "")
PAT           = os.getenv("SUPABASE_PAT", "")
PROJECT_REF   = SUPABASE_URL.split(".supabase.co")[0].split("//")[-1] if SUPABASE_URL else ""

# ── Table schemas Aisha needs to function ──────────────────────────────────────

REQUIRED_TABLES: dict[str, str] = {
    "aisha_reminders": """
        CREATE TABLE IF NOT EXISTS aisha_reminders (
          id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
          user_id BIGINT,
          title TEXT NOT NULL,
          message TEXT,
          remind_at TIMESTAMPTZ NOT NULL,
          recurrence TEXT DEFAULT 'once',
          status TEXT DEFAULT 'pending',
          workspace_id UUID REFERENCES aisha_workspaces(id),
          created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_reminders_remind_at
          ON aisha_reminders(remind_at, status);
    """,
    "aisha_expenses": """
        CREATE TABLE IF NOT EXISTS aisha_expenses (
          id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
          amount NUMERIC(12,2) NOT NULL,
          category TEXT DEFAULT 'misc',
          description TEXT NOT NULL,
          currency TEXT DEFAULT 'INR',
          paid_via TEXT,
          notes TEXT,
          expense_date DATE DEFAULT CURRENT_DATE,
          workspace_id UUID REFERENCES aisha_workspaces(id),
          created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_expenses_date
          ON aisha_expenses(expense_date DESC);
    """,
    "aisha_system_log": """
        CREATE TABLE IF NOT EXISTS aisha_system_log (
          id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
          level TEXT NOT NULL DEFAULT 'INFO',
          module TEXT,
          message TEXT NOT NULL,
          details JSONB,
          created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_system_log_created
          ON aisha_system_log(created_at DESC);
    """,
    "aisha_message_queue": """
        CREATE TABLE IF NOT EXISTS aisha_message_queue (
          id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
          chat_id BIGINT NOT NULL,
          message TEXT NOT NULL,
          parse_mode TEXT DEFAULT 'Markdown',
          media_url TEXT,
          media_type TEXT,
          status TEXT DEFAULT 'pending',
          retry_count INT DEFAULT 0,
          scheduled_at TIMESTAMPTZ DEFAULT NOW(),
          sent_at TIMESTAMPTZ,
          created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_msg_queue_status
          ON aisha_message_queue(status, scheduled_at);
    """,
    "aisha_health": """
        CREATE TABLE IF NOT EXISTS aisha_health (
          id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
          date DATE NOT NULL DEFAULT CURRENT_DATE UNIQUE,
          water_ml INT DEFAULT 0,
          sleep_hours NUMERIC(4,2),
          sleep_quality INT,
          workout_done BOOLEAN DEFAULT FALSE,
          workout_type TEXT,
          workout_minutes INT,
          weight_kg NUMERIC(5,2),
          notes TEXT,
          created_at TIMESTAMPTZ DEFAULT NOW(),
          updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_health_date
          ON aisha_health(date DESC);
    """,
    "aisha_users": """
        CREATE TABLE IF NOT EXISTS aisha_users (
          telegram_user_id BIGINT PRIMARY KEY,
          role TEXT NOT NULL DEFAULT 'guest',
          first_name TEXT,
          username TEXT,
          permissions JSONB DEFAULT '{}'::JSONB,
          created_at TIMESTAMPTZ DEFAULT NOW(),
          updated_at TIMESTAMPTZ DEFAULT NOW(),
          active_workspace_id UUID REFERENCES aisha_workspaces(id),
          CONSTRAINT valid_role CHECK (role IN ('admin', 'guest'))
        );
    """,
    "aisha_workspaces": """
        CREATE TABLE IF NOT EXISTS aisha_workspaces (
          id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
          name TEXT NOT NULL,
          type TEXT NOT NULL CHECK (type IN ('vault', 'studio', 'lobby')),
          created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """,
    "aisha_memory": """
        CREATE TABLE IF NOT EXISTS aisha_memory (
          id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
          category TEXT NOT NULL,
          title TEXT NOT NULL,
          content TEXT NOT NULL,
          importance INTEGER DEFAULT 3,
          tags TEXT[] DEFAULT ARRAY[]::TEXT[],
          workspace_id UUID REFERENCES aisha_workspaces(id),
          is_active BOOLEAN DEFAULT TRUE,
          source TEXT DEFAULT 'conversation',
          embedding VECTOR(768),
          created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """,
    "aisha_conversations": """
        CREATE TABLE IF NOT EXISTS aisha_conversations (
          id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
          platform TEXT NOT NULL,
          role TEXT NOT NULL,
          message TEXT NOT NULL,
          language TEXT,
          mood_detected TEXT,
          workspace_id UUID REFERENCES aisha_workspaces(id),
          embedding VECTOR(768),
          created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """,
}


def _table_exists(table: str) -> bool:
    """Check if a table exists via Supabase REST API."""
    if not SUPABASE_URL or not SERVICE_KEY:
        return True  # can't check, assume exists
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/{table}?select=id&limit=0",
            headers={"apikey": SERVICE_KEY, "Authorization": f"Bearer {SERVICE_KEY}"},
            timeout=8,
        )
        return r.status_code in (200, 206)
    except Exception:
        return True  # assume OK on network error


def _run_sql(sql: str) -> tuple[bool, str]:
    """Execute DDL SQL via Supabase Management API using PAT."""
    if not PAT or not PROJECT_REF:
        return False, "SUPABASE_PAT not configured — cannot run DDL"
    try:
        r = requests.post(
            f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query",
            headers={"Authorization": f"Bearer {PAT}", "Content-Type": "application/json"},
            json={"query": sql},
            timeout=30,
        )
        if r.status_code in (200, 201):
            return True, "OK"
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)


def migrate_schema():
    """Apply migrations to existing tables (add columns, etc.)."""
    if not PAT or not PROJECT_REF:
        return

    migrations = [
        # Add permissions and active_workspace_id to aisha_users
        "ALTER TABLE aisha_users ADD COLUMN IF NOT EXISTS permissions JSONB DEFAULT '{}'::JSONB;",
        "ALTER TABLE aisha_users ADD COLUMN IF NOT EXISTS active_workspace_id UUID REFERENCES aisha_workspaces(id);",
        # Add workspace_id to core tables
        "ALTER TABLE aisha_memory ADD COLUMN IF NOT EXISTS workspace_id UUID REFERENCES aisha_workspaces(id);",
        "ALTER TABLE aisha_conversations ADD COLUMN IF NOT EXISTS workspace_id UUID REFERENCES aisha_workspaces(id);",
        "ALTER TABLE aisha_schedule ADD COLUMN IF NOT EXISTS workspace_id UUID REFERENCES aisha_workspaces(id);",
        "ALTER TABLE aisha_finance ADD COLUMN IF NOT EXISTS workspace_id UUID REFERENCES aisha_workspaces(id);",
        "ALTER TABLE aisha_reminders ADD COLUMN IF NOT EXISTS workspace_id UUID REFERENCES aisha_workspaces(id);",
    ]

    for sql in migrations:
        _run_sql(sql)


def check_and_repair() -> dict[str, str]:
    """
    Check all required tables. Create any that are missing.
    Returns {table_name: "ok" | "created" | "failed: <reason>"}.
    """
    # 1. Run migrations first to ensure columns exist on existing tables
    migrate_schema()

    # 2. Run standard table checks
    results: dict[str, str] = {}
    for table, ddl in REQUIRED_TABLES.items():
        if _table_exists(table):
            results[table] = "ok"
            continue
        log.warning(f"self_db: table '{table}' missing — auto-creating")
        ok, msg = _run_sql(ddl.strip())
        if ok:
            results[table] = "created"
            log.info(f"self_db: table '{table}' created successfully")
        else:
            results[table] = f"failed: {msg}"
            log.error(f"self_db: failed to create '{table}': {msg}")
    return results


def repair_report() -> str:
    """Human-readable report for Telegram /syscheck or Ajay."""
    results = check_and_repair()
    lines = ["🗄️ *DB Self-Repair Report*\n"]
    for table, status in results.items():
        if status == "ok":
            lines.append(f"✅ `{table}` — exists")
        elif status == "created":
            lines.append(f"🔧 `{table}` — auto-created!")
        else:
            lines.append(f"❌ `{table}` — {status}")
    return "\n".join(lines)
