-- ============================================================
-- AISHA DATABASE SCHEMA
-- Supabase PostgreSQL Schema for Aisha - Ajay's Personal AI
-- Run this in Supabase → SQL Editor → New Query
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- Enable vector extension for semantic memory search
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- TABLE 1: ajay_profile
-- Stores Ajay's core identity and preferences
-- ============================================================
CREATE TABLE IF NOT EXISTS ajay_profile (
  id              UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  name            TEXT NOT NULL DEFAULT 'Ajay',
  nickname        TEXT DEFAULT 'Aju',
  languages       TEXT[] DEFAULT ARRAY['English', 'Hindi', 'Marathi'],
  preferred_lang  TEXT DEFAULT 'English',
  personality_notes TEXT,           -- Things Aisha has learned about Ajay
  current_mood    TEXT DEFAULT 'neutral',
  voice_preference TEXT DEFAULT 'adaptive',  -- calm/energetic/adaptive
  timezone        TEXT DEFAULT 'Asia/Kolkata',
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE 2: aisha_memory
-- Long-term memory store — everything Aisha remembers about Ajay
-- ============================================================
CREATE TABLE IF NOT EXISTS aisha_memory (
  id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  category    TEXT NOT NULL CHECK (category IN (
                'mood', 'goal', 'finance', 'schedule', 
                'preference', 'relationship', 'health', 
                'achievement', 'fear', 'dream', 'general'
              )),
  title       TEXT NOT NULL,          -- Short label: "Ajay's dream job"
  content     TEXT NOT NULL,          -- Full memory content
  importance  INT DEFAULT 3 CHECK (importance BETWEEN 1 AND 5),
                                      -- 1=trivial, 5=critical
  is_active   BOOLEAN DEFAULT TRUE,   -- FALSE = Ajay said to forget it
  embedding   vector(768),            -- For semantic search (optional)
  tags        TEXT[],                 -- e.g. ['finance', 'goal', '2024']
  source      TEXT DEFAULT 'conversation', -- where did we learn this
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE 3: aisha_journal
-- Ajay's personal journal entries (via Aisha)
-- ============================================================
CREATE TABLE IF NOT EXISTS aisha_journal (
  id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  entry       TEXT NOT NULL,
  mood        TEXT,                   -- 'happy', 'sad', 'anxious', 'excited', etc.
  mood_score  INT CHECK (mood_score BETWEEN 1 AND 10),
                                      -- 1=very bad, 10=amazing
  tags        TEXT[],
  aisha_note  TEXT,                   -- Aisha's reflection/response to the entry
  date        DATE DEFAULT CURRENT_DATE,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE 4: aisha_finance
-- Financial tracking — expenses, income, goals
-- ============================================================
CREATE TABLE IF NOT EXISTS aisha_finance (
  id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  type        TEXT NOT NULL CHECK (type IN ('expense', 'income', 'goal', 'saving')),
  amount      NUMERIC(12, 2) NOT NULL,
  currency    TEXT DEFAULT 'INR',
  category    TEXT,                   -- 'food', 'transport', 'entertainment', etc.
  description TEXT NOT NULL,
  is_recurring BOOLEAN DEFAULT FALSE,
  recur_freq  TEXT,                   -- 'daily', 'weekly', 'monthly'
  goal_target NUMERIC(12, 2),         -- For type='goal', what's the target?
  goal_by     DATE,                   -- Target date for goal
  date        DATE DEFAULT CURRENT_DATE,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE 5: aisha_schedule
-- Ajay's schedule, tasks, and reminders
-- ============================================================
CREATE TABLE IF NOT EXISTS aisha_schedule (
  id            UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  title         TEXT NOT NULL,
  description   TEXT,
  type          TEXT DEFAULT 'task' CHECK (type IN ('task', 'reminder', 'event', 'habit')),
  priority      TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
  status        TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'done', 'missed', 'snoozed')),
  due_date      DATE,
  due_time      TIME,
  is_recurring  BOOLEAN DEFAULT FALSE,
  recur_days    TEXT[],               -- ['monday', 'wednesday'] for habits
  reminder_sent BOOLEAN DEFAULT FALSE,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE 6: aisha_conversations
-- Conversation history (last 30 days kept for context)
-- ============================================================
CREATE TABLE IF NOT EXISTS aisha_conversations (
  id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  platform    TEXT DEFAULT 'web' CHECK (platform IN ('web', 'telegram', 'voice')),
  role        TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  message     TEXT NOT NULL,
  language    TEXT DEFAULT 'English',
  mood_detected TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE 7: aisha_mood_tracker
-- Daily mood log for tracking Ajay's emotional wellbeing
-- ============================================================
CREATE TABLE IF NOT EXISTS aisha_mood_tracker (
  id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  mood        TEXT NOT NULL,
  mood_score  INT CHECK (mood_score BETWEEN 1 AND 10),
  notes       TEXT,
  triggers    TEXT[],                 -- What caused this mood?
  date        DATE DEFAULT CURRENT_DATE,
  time_of_day TEXT,                   -- 'morning', 'afternoon', 'evening', 'night'
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE 8: aisha_goals
-- Ajay's short and long term goals
-- ============================================================
CREATE TABLE IF NOT EXISTS aisha_goals (
  id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  title       TEXT NOT NULL,
  description TEXT,
  category    TEXT CHECK (category IN (
                'career', 'finance', 'health', 'relationship', 
                'personal', 'learning', 'travel', 'other'
              )),
  timeframe   TEXT CHECK (timeframe IN ('daily', 'weekly', 'monthly', 'yearly', 'life')),
  status      TEXT DEFAULT 'active' CHECK (status IN ('active', 'achieved', 'abandoned', 'paused')),
  progress    INT DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
  target_date DATE,
  achieved_at TIMESTAMPTZ,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- VIEWS
-- ============================================================

-- View: Today's summary for Aisha's morning briefing
CREATE OR REPLACE VIEW today_summary AS
SELECT
  (SELECT COUNT(*) FROM aisha_schedule 
   WHERE due_date = CURRENT_DATE AND status = 'pending') AS pending_tasks,
  (SELECT COUNT(*) FROM aisha_schedule 
   WHERE due_date = CURRENT_DATE AND status = 'done') AS completed_tasks,
  (SELECT COALESCE(SUM(amount), 0) FROM aisha_finance 
   WHERE type = 'expense' AND date = CURRENT_DATE) AS todays_spending,
  (SELECT mood FROM aisha_mood_tracker 
   ORDER BY created_at DESC LIMIT 1) AS last_mood,
  (SELECT COUNT(*) FROM aisha_goals 
   WHERE status = 'active') AS active_goals;

-- View: Monthly finance summary
CREATE OR REPLACE VIEW monthly_finance AS
SELECT
  DATE_TRUNC('month', date) AS month,
  SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) AS total_income,
  SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) AS total_expense,
  SUM(CASE WHEN type = 'saving' THEN amount ELSE 0 END) AS total_saved,
  COUNT(CASE WHEN type = 'expense' THEN 1 END) AS expense_count
FROM aisha_finance
GROUP BY DATE_TRUNC('month', date)
ORDER BY month DESC;

-- View: Top memories (high importance, active)
CREATE OR REPLACE VIEW top_memories AS
SELECT id, category, title, content, importance, tags, created_at
FROM aisha_memory
WHERE is_active = TRUE
ORDER BY importance DESC, updated_at DESC
LIMIT 20;

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Function: Get Aisha's full context for a conversation
CREATE OR REPLACE FUNCTION get_aisha_context()
RETURNS TEXT AS $$
DECLARE
  context TEXT := '';
  profile_row ajay_profile%ROWTYPE;
BEGIN
  SELECT * INTO profile_row FROM ajay_profile LIMIT 1;
  
  context := context || '=== AJAY PROFILE ===' || chr(10);
  context := context || 'Name: ' || profile_row.name || chr(10);
  context := context || 'Current Mood: ' || COALESCE(profile_row.current_mood, 'unknown') || chr(10);
  context := context || 'Preferred Language: ' || COALESCE(profile_row.preferred_lang, 'English') || chr(10);
  context := context || chr(10);
  
  context := context || '=== KEY MEMORIES ===' || chr(10);
  SELECT context || string_agg(
    '[' || category || '] ' || title || ': ' || content, chr(10)
  )
  INTO context
  FROM (
    SELECT category, title, content 
    FROM aisha_memory 
    WHERE is_active = TRUE 
    ORDER BY importance DESC 
    LIMIT 10
  ) m;
  
  context := context || chr(10) || '=== TODAY TASKS ===' || chr(10);
  SELECT context || string_agg(
    '- [' || priority || '] ' || title, chr(10)
  )
  INTO context
  FROM (
    SELECT priority, title
    FROM aisha_schedule
    WHERE due_date = CURRENT_DATE AND status = 'pending'
    ORDER BY 
      CASE priority WHEN 'urgent' THEN 1 WHEN 'high' THEN 2 
                    WHEN 'medium' THEN 3 ELSE 4 END
  ) t;
  
  RETURN context;
END;
$$ LANGUAGE plpgsql;

-- Function: Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- TRIGGERS
-- ============================================================

CREATE TRIGGER update_profile_updated_at
  BEFORE UPDATE ON ajay_profile
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_memory_updated_at
  BEFORE UPDATE ON aisha_memory
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_schedule_updated_at
  BEFORE UPDATE ON aisha_schedule
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_goals_updated_at
  BEFORE UPDATE ON aisha_goals
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- ROW LEVEL SECURITY (RLS)
-- Ensures only your app can access this data
-- ============================================================

ALTER TABLE ajay_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE aisha_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE aisha_journal ENABLE ROW LEVEL SECURITY;
ALTER TABLE aisha_finance ENABLE ROW LEVEL SECURITY;
ALTER TABLE aisha_schedule ENABLE ROW LEVEL SECURITY;
ALTER TABLE aisha_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE aisha_mood_tracker ENABLE ROW LEVEL SECURITY;
ALTER TABLE aisha_goals ENABLE ROW LEVEL SECURITY;

-- Allow full access with the service role key (your backend)
CREATE POLICY "Service role full access" ON ajay_profile
  USING (TRUE) WITH CHECK (TRUE);

CREATE POLICY "Service role full access" ON aisha_memory
  USING (TRUE) WITH CHECK (TRUE);

CREATE POLICY "Service role full access" ON aisha_journal
  USING (TRUE) WITH CHECK (TRUE);

CREATE POLICY "Service role full access" ON aisha_finance
  USING (TRUE) WITH CHECK (TRUE);

CREATE POLICY "Service role full access" ON aisha_schedule
  USING (TRUE) WITH CHECK (TRUE);

CREATE POLICY "Service role full access" ON aisha_conversations
  USING (TRUE) WITH CHECK (TRUE);

CREATE POLICY "Service role full access" ON aisha_mood_tracker
  USING (TRUE) WITH CHECK (TRUE);

CREATE POLICY "Service role full access" ON aisha_goals
  USING (TRUE) WITH CHECK (TRUE);

-- ============================================================
-- INDEXES (for performance)
-- ============================================================

CREATE INDEX idx_memory_category ON aisha_memory(category);
CREATE INDEX idx_memory_importance ON aisha_memory(importance DESC);
CREATE INDEX idx_memory_active ON aisha_memory(is_active);
CREATE INDEX idx_finance_date ON aisha_finance(date DESC);
CREATE INDEX idx_finance_type ON aisha_finance(type);
CREATE INDEX idx_schedule_due ON aisha_schedule(due_date);
CREATE INDEX idx_schedule_status ON aisha_schedule(status);
CREATE INDEX idx_conversations_created ON aisha_conversations(created_at DESC);
CREATE INDEX idx_mood_date ON aisha_mood_tracker(date DESC);
CREATE INDEX idx_goals_status ON aisha_goals(status);

-- ============================================================
-- AUTO-CLEANUP: Delete conversations older than 30 days
-- (keeps the DB lean while preserving important memories)
-- ============================================================
CREATE OR REPLACE FUNCTION cleanup_old_conversations()
RETURNS void AS $$
BEGIN
  DELETE FROM aisha_conversations 
  WHERE created_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- NOTE: Schedule this via Supabase cron (pg_cron extension)
-- SELECT cron.schedule('cleanup-conversations', '0 2 * * *', 
--   'SELECT cleanup_old_conversations()');

COMMENT ON TABLE ajay_profile IS 'Core profile and preferences for Ajay';
COMMENT ON TABLE aisha_memory IS 'Long-term memory store for Aisha';
COMMENT ON TABLE aisha_journal IS 'Personal journal entries by Ajay via Aisha';
COMMENT ON TABLE aisha_finance IS 'Financial transactions, goals, and savings';
COMMENT ON TABLE aisha_schedule IS 'Tasks, reminders, events, and habits';
COMMENT ON TABLE aisha_conversations IS 'Recent conversation history (30 day rolling)';
COMMENT ON TABLE aisha_mood_tracker IS 'Daily emotional wellbeing tracking';
COMMENT ON TABLE aisha_goals IS 'Short and long-term goals with progress tracking';

-- ============================================================
-- MIGRATION: Add session tracking to conversations
-- Needed for per-platform context isolation (web vs telegram)
-- and conversation compression (is_summary flag)
-- ============================================================

ALTER TABLE aisha_conversations
  ADD COLUMN IF NOT EXISTS session_id TEXT,
  ADD COLUMN IF NOT EXISTS is_summary  BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS token_estimate INT;

CREATE INDEX IF NOT EXISTS idx_conversations_session
  ON aisha_conversations(session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_conversations_summary
  ON aisha_conversations(is_summary)
  WHERE is_summary = TRUE;

-- ============================================================
-- TABLE: aisha_health
-- Physical wellbeing tracking (water, sleep, workouts)
-- Populated via /water, /sleep, /workout Telegram commands
-- ============================================================

CREATE TABLE IF NOT EXISTS aisha_health (
  id                    UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  date                  DATE DEFAULT CURRENT_DATE,
  water_glasses         INT DEFAULT 0,
  sleep_hours           NUMERIC(3, 1),
  sleep_quality         TEXT CHECK (sleep_quality IN ('poor', 'okay', 'good', 'great')),
  workout_type          TEXT,
  workout_duration_mins INT,
  weight_kg             NUMERIC(5, 2),
  steps                 INT,
  notes                 TEXT,
  created_at            TIMESTAMPTZ DEFAULT NOW(),
  updated_at            TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (date)         -- one record per day, upserted
);

CREATE TRIGGER update_health_updated_at
  BEFORE UPDATE ON aisha_health
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

ALTER TABLE aisha_health ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access" ON aisha_health
  USING (TRUE) WITH CHECK (TRUE);

CREATE INDEX idx_health_date ON aisha_health(date DESC);

COMMENT ON TABLE aisha_health IS 'Daily physical wellbeing log for Ajay';

-- ============================================================
-- TABLE: aisha_system_log
-- Structured error/event log for observability
-- Written by src/core/logger.py SupabaseSinkHandler
-- ============================================================

CREATE TABLE IF NOT EXISTS aisha_system_log (
  id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  level       TEXT NOT NULL CHECK (level IN ('info', 'warning', 'error', 'critical')),
  module      TEXT NOT NULL,
  event       TEXT NOT NULL,
  context     JSONB DEFAULT '{}',
  error_trace TEXT,
  session_id  TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE aisha_system_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access" ON aisha_system_log
  USING (TRUE) WITH CHECK (TRUE);

CREATE INDEX idx_syslog_level   ON aisha_system_log(level, created_at DESC);
CREATE INDEX idx_syslog_module  ON aisha_system_log(module, created_at DESC);
CREATE INDEX idx_syslog_created ON aisha_system_log(created_at DESC);

COMMENT ON TABLE aisha_system_log IS 'Structured observability log — errors written by logger.py';

-- ============================================================
-- TABLE: aisha_message_queue
-- Failed messages saved for retry via /retry Telegram command
-- Written by AishaBrain.think() on exception
-- ============================================================

CREATE TABLE IF NOT EXISTS aisha_message_queue (
  id           UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  platform     TEXT NOT NULL,
  user_message TEXT NOT NULL,
  error_reason TEXT,
  retry_count  INT DEFAULT 0,
  status       TEXT DEFAULT 'failed' CHECK (status IN ('failed', 'retried', 'resolved')),
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE aisha_message_queue ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access" ON aisha_message_queue
  USING (TRUE) WITH CHECK (TRUE);

CREATE INDEX idx_msgqueue_status ON aisha_message_queue(status, created_at DESC);

COMMENT ON TABLE aisha_message_queue IS 'Failed messages pending retry — written on brain exceptions';

-- ============================================================
-- VIEW: aisha_daily_summary
-- Used by DigestEngine and NotificationEngine morning briefing
-- ============================================================

CREATE OR REPLACE VIEW aisha_daily_summary AS
SELECT
  CURRENT_DATE                                                             AS date,
  (SELECT COUNT(*) FROM aisha_schedule
   WHERE due_date = CURRENT_DATE AND status = 'done')                      AS tasks_done,
  (SELECT COUNT(*) FROM aisha_schedule
   WHERE due_date = CURRENT_DATE AND status = 'pending')                   AS tasks_pending,
  (SELECT COUNT(*) FROM aisha_schedule
   WHERE due_date = CURRENT_DATE AND status = 'missed')                    AS tasks_missed,
  (SELECT COALESCE(SUM(amount), 0) FROM aisha_finance
   WHERE date = CURRENT_DATE AND type = 'expense')                         AS today_spending,
  (SELECT mood FROM aisha_mood_tracker
   ORDER BY created_at DESC LIMIT 1)                                       AS last_mood,
  (SELECT mood_score FROM aisha_mood_tracker
   ORDER BY created_at DESC LIMIT 1)                                       AS last_mood_score,
  (SELECT water_glasses FROM aisha_health
   WHERE date = CURRENT_DATE LIMIT 1)                                      AS water_glasses,
  (SELECT sleep_hours FROM aisha_health
   WHERE date = CURRENT_DATE LIMIT 1)                                      AS sleep_hours,
  (SELECT COUNT(*) FROM aisha_goals WHERE status = 'active')               AS active_goals;

-- ============================================================
-- AUTO-CLEANUP: Also purge old system logs (keep 7 days)
-- ============================================================

CREATE OR REPLACE FUNCTION cleanup_old_system_logs()
RETURNS void AS $$
BEGIN
  DELETE FROM aisha_system_log
  WHERE created_at < NOW() - INTERVAL '7 days'
    AND level IN ('info', 'warning');
  -- Keep errors for 30 days for debugging
  DELETE FROM aisha_system_log
  WHERE created_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;
