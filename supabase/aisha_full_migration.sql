
-- Enable vector extension for semantic memory search
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- TABLE 1: ajay_profile
-- ============================================================
CREATE TABLE IF NOT EXISTS ajay_profile (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name            TEXT NOT NULL DEFAULT 'Ajay',
  nickname        TEXT DEFAULT 'Aju',
  languages       TEXT[] DEFAULT ARRAY['English', 'Hindi', 'Marathi'],
  preferred_lang  TEXT DEFAULT 'English',
  personality_notes TEXT,
  current_mood    TEXT DEFAULT 'neutral',
  voice_preference TEXT DEFAULT 'adaptive',
  timezone        TEXT DEFAULT 'Asia/Kolkata',
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE 2: aisha_memory
-- ============================================================
CREATE TABLE IF NOT EXISTS aisha_memory (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  category    TEXT NOT NULL CHECK (category IN (
                'mood', 'goal', 'finance', 'schedule', 
                'preference', 'relationship', 'health', 
                'achievement', 'fear', 'dream', 'general'
              )),
  title       TEXT NOT NULL,
  content     TEXT NOT NULL,
  importance  INT DEFAULT 3 CHECK (importance BETWEEN 1 AND 5),
  is_active   BOOLEAN DEFAULT TRUE,
  embedding   vector(768),
  tags        TEXT[],
  source      TEXT DEFAULT 'conversation',
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE 3: aisha_journal
-- ============================================================
CREATE TABLE IF NOT EXISTS aisha_journal (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  entry       TEXT NOT NULL,
  mood        TEXT,
  mood_score  INT CHECK (mood_score BETWEEN 1 AND 10),
  tags        TEXT[],
  aisha_note  TEXT,
  date        DATE DEFAULT CURRENT_DATE,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE 4: aisha_finance
-- ============================================================
CREATE TABLE IF NOT EXISTS aisha_finance (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  type        TEXT NOT NULL CHECK (type IN ('expense', 'income', 'goal', 'saving')),
  amount      NUMERIC(12, 2) NOT NULL,
  currency    TEXT DEFAULT 'INR',
  category    TEXT,
  description TEXT NOT NULL,
  is_recurring BOOLEAN DEFAULT FALSE,
  recur_freq  TEXT,
  goal_target NUMERIC(12, 2),
  goal_by     DATE,
  date        DATE DEFAULT CURRENT_DATE,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE 5: aisha_schedule
-- ============================================================
CREATE TABLE IF NOT EXISTS aisha_schedule (
  id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  title         TEXT NOT NULL,
  description   TEXT,
  type          TEXT DEFAULT 'task' CHECK (type IN ('task', 'reminder', 'event', 'habit')),
  priority      TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
  status        TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'done', 'missed', 'snoozed')),
  due_date      DATE,
  due_time      TIME,
  is_recurring  BOOLEAN DEFAULT FALSE,
  recur_days    TEXT[],
  reminder_sent BOOLEAN DEFAULT FALSE,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE 6: aisha_conversations
-- ============================================================
CREATE TABLE IF NOT EXISTS aisha_conversations (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  platform    TEXT DEFAULT 'web' CHECK (platform IN ('web', 'telegram', 'voice')),
  role        TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  message     TEXT NOT NULL,
  language    TEXT DEFAULT 'English',
  mood_detected TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE 7: aisha_mood_tracker
-- ============================================================
CREATE TABLE IF NOT EXISTS aisha_mood_tracker (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  mood        TEXT NOT NULL,
  mood_score  INT CHECK (mood_score BETWEEN 1 AND 10),
  notes       TEXT,
  triggers    TEXT[],
  date        DATE DEFAULT CURRENT_DATE,
  time_of_day TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE 8: aisha_goals
-- ============================================================
CREATE TABLE IF NOT EXISTS aisha_goals (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
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
-- RLS
-- ============================================================
ALTER TABLE ajay_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE aisha_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE aisha_journal ENABLE ROW LEVEL SECURITY;
ALTER TABLE aisha_finance ENABLE ROW LEVEL SECURITY;
ALTER TABLE aisha_schedule ENABLE ROW LEVEL SECURITY;
ALTER TABLE aisha_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE aisha_mood_tracker ENABLE ROW LEVEL SECURITY;
ALTER TABLE aisha_goals ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Full access" ON ajay_profile;
DROP POLICY IF EXISTS "Full access" ON aisha_memory;
DROP POLICY IF EXISTS "Full access" ON aisha_journal;
DROP POLICY IF EXISTS "Full access" ON aisha_finance;
DROP POLICY IF EXISTS "Full access" ON aisha_schedule;
DROP POLICY IF EXISTS "Full access" ON aisha_conversations;
DROP POLICY IF EXISTS "Full access" ON aisha_mood_tracker;
DROP POLICY IF EXISTS "Full access" ON aisha_goals;
CREATE POLICY "Full access" ON ajay_profile FOR ALL USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "Full access" ON aisha_memory FOR ALL USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "Full access" ON aisha_journal FOR ALL USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "Full access" ON aisha_finance FOR ALL USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "Full access" ON aisha_schedule FOR ALL USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "Full access" ON aisha_conversations FOR ALL USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "Full access" ON aisha_mood_tracker FOR ALL USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "Full access" ON aisha_goals FOR ALL USING (TRUE) WITH CHECK (TRUE);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_memory_category ON aisha_memory(category);
CREATE INDEX IF NOT EXISTS idx_memory_importance ON aisha_memory(importance DESC);
CREATE INDEX IF NOT EXISTS idx_memory_active ON aisha_memory(is_active);
CREATE INDEX IF NOT EXISTS idx_finance_date ON aisha_finance(date DESC);
CREATE INDEX IF NOT EXISTS idx_finance_type ON aisha_finance(type);
CREATE INDEX IF NOT EXISTS idx_schedule_due ON aisha_schedule(due_date);
CREATE INDEX IF NOT EXISTS idx_schedule_status ON aisha_schedule(status);
CREATE INDEX IF NOT EXISTS idx_conversations_created ON aisha_conversations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_mood_date ON aisha_mood_tracker(date DESC);
CREATE INDEX IF NOT EXISTS idx_goals_status ON aisha_goals(status);

-- ============================================================
-- Enable realtime for conversations
-- ============================================================
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_publication_rel pr
    JOIN pg_publication p ON p.oid = pr.prpubid
    JOIN pg_class c ON c.oid = pr.prrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE p.pubname = 'supabase_realtime'
      AND n.nspname = 'public'
      AND c.relname = 'aisha_conversations'
  ) THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE public.aisha_conversations;
  END IF;
END $$;

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Get Aisha's full context for a conversation
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
  SELECT context || COALESCE(string_agg(
    '[' || category || '] ' || title || ': ' || content, chr(10)
  ), 'No memories yet.')
  INTO context
  FROM (
    SELECT category, title, content 
    FROM aisha_memory 
    WHERE is_active = TRUE 
    ORDER BY importance DESC 
    LIMIT 10
  ) m;
  
  context := context || chr(10) || '=== TODAY TASKS ===' || chr(10);
  SELECT context || COALESCE(string_agg(
    '- [' || priority || '] ' || title, chr(10)
  ), 'No tasks today.')
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

-- Cleanup old conversations
CREATE OR REPLACE FUNCTION cleanup_old_conversations()
RETURNS void AS $$
BEGIN
  DELETE FROM aisha_conversations 
  WHERE created_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- TRIGGERS
-- ============================================================
DROP TRIGGER IF EXISTS update_profile_updated_at ON ajay_profile;
CREATE TRIGGER update_profile_updated_at
  BEFORE UPDATE ON ajay_profile
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_memory_updated_at ON aisha_memory;
CREATE TRIGGER update_memory_updated_at
  BEFORE UPDATE ON aisha_memory
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_schedule_updated_at ON aisha_schedule;
CREATE TRIGGER update_schedule_updated_at
  BEFORE UPDATE ON aisha_schedule
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_goals_updated_at ON aisha_goals;
CREATE TRIGGER update_goals_updated_at
  BEFORE UPDATE ON aisha_goals
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- VIEWS
-- ============================================================
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

CREATE OR REPLACE VIEW top_memories AS
SELECT id, category, title, content, importance, tags, created_at
FROM aisha_memory
WHERE is_active = TRUE
ORDER BY importance DESC, updated_at DESC
LIMIT 20;

-- ============================================================
-- TABLE COMMENTS
-- ============================================================
COMMENT ON TABLE ajay_profile IS 'Core profile and preferences for Ajay';
COMMENT ON TABLE aisha_memory IS 'Long-term memory store for Aisha';
COMMENT ON TABLE aisha_journal IS 'Personal journal entries by Ajay via Aisha';
COMMENT ON TABLE aisha_finance IS 'Financial transactions, goals, and savings';
COMMENT ON TABLE aisha_schedule IS 'Tasks, reminders, events, and habits';
COMMENT ON TABLE aisha_conversations IS 'Recent conversation history (30 day rolling)';
COMMENT ON TABLE aisha_mood_tracker IS 'Daily emotional wellbeing tracking';
COMMENT ON TABLE aisha_goals IS 'Short and long-term goals with progress tracking';
-- Content Operations Queue for Antigravity Agent
-- Enables: queueing generation jobs, tracking execution status, and monitoring post performance.

create table if not exists content_jobs (
    id uuid primary key default gen_random_uuid(),
    topic text not null,
    channel text not null,
    format text not null default 'Short/Reel',
    platform_targets text[] not null default array['instagram']::text[],
    payload jsonb not null default '{}'::jsonb,
    output jsonb not null default '{}'::jsonb,
    status text not null default 'queued' check (status in ('queued', 'processing', 'completed', 'failed', 'cancelled')),
    priority int not null default 5,
    auto_post boolean not null default true,
    error_text text,
    scheduled_at timestamptz not null default now(),
    started_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists content_performance (
    id uuid primary key default gen_random_uuid(),
    content_job_id uuid references content_jobs(id) on delete set null,
    platform text not null check (platform in ('youtube', 'instagram', 'other')),
    external_post_id text,
    external_url text,
    views bigint default 0,
    likes bigint default 0,
    comments bigint default 0,
    watch_time_seconds bigint default 0,
    subscribers_gained bigint default 0,
    earnings_estimate numeric(12,2) default 0,
    metrics jsonb not null default '{}'::jsonb,
    captured_at timestamptz not null default now(),
    created_at timestamptz not null default now()
);

create index if not exists idx_content_jobs_status_scheduled on content_jobs(status, scheduled_at);
create index if not exists idx_content_jobs_channel on content_jobs(channel);
create index if not exists idx_content_performance_job on content_performance(content_job_id, platform, captured_at desc);

create or replace function set_content_jobs_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_content_jobs_updated_at on content_jobs;
create trigger trg_content_jobs_updated_at
before update on content_jobs
for each row execute function set_content_jobs_updated_at();

alter table content_jobs enable row level security;
alter table content_performance enable row level security;

drop policy if exists "Full access content jobs" on content_jobs;
create policy "Full access content jobs" on content_jobs
for all using (true) with check (true);

drop policy if exists "Full access content performance" on content_performance;
create policy "Full access content performance" on content_performance
for all using (true) with check (true);
-- ============================================================
-- Migration: channel_prompts
-- Created: 2026-03-13
-- Purpose: Store per-channel YouTube identity prompts, voice IDs,
--          and AI provider routing — queryable by the edge function
--          without a code deploy when channels evolve.
-- ============================================================

create table if not exists channel_prompts (
  id              uuid        primary key default gen_random_uuid(),
  channel_name    text        not null unique,
  identity_prompt text        not null,
  voice_id        text        not null,
  ai_provider     text        not null default 'gemini',
  narrator        text        not null,
  is_active       boolean     not null default true,
  updated_at      timestamptz not null default now()
);

-- Auto-update timestamp on any row change
create or replace function set_channel_prompts_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_channel_prompts_updated_at on channel_prompts;
create trigger trg_channel_prompts_updated_at
  before update on channel_prompts
  for each row execute function set_channel_prompts_updated_at();

-- RLS — service role has full access, anon can read active channels
alter table channel_prompts enable row level security;

drop policy if exists "Service full access channel_prompts" on channel_prompts;
create policy "Service full access channel_prompts"
  on channel_prompts for all
  using (true) with check (true);

-- ── Seed Data ──────────────────────────────────────────────

insert into channel_prompts
  (channel_name, identity_prompt, voice_id, ai_provider, narrator)
values
  (
    'Story With Aisha',
    '100% देवनागरी हिंदी केवल। आयशा — पहली व्यक्ति में भावुक प्रेम कहानियाँ। संरचना: इंट्रो (४-५ लाइन) → ८-१२ भाग (३५०-४५० शब्द/भाग) → आउट्रो। सूक्ष्म रोमांस — कोई explicit content नहीं। पहले trending love story angles research करो (office romance, college love, long-distance, rain moments)। हर कहानी पूरी तरह नई — नया नाम, नई लोकेशन।',
    'wdymxIQkYn7MJCYCQF2Q',
    'gemini',
    'Aisha'
  ),
  (
    'Riya''s Dark Whisper',
    '100% देवनागरी हिंदी केवल। रिया — २३ साल, फ्रीलांस ग्राफिक डिजाइनर, मुंबई, bold, voluptuous। सविता भाभी स्टाइल: explicit sex scenes, dark romance, psychological tension। Single story format, 900-1400 words, natural Devanagari subheadings। TTS-friendly: short sentences, "..." pauses। पहले trending erotic/adult story angles research करो। हमेशा xAI Grok use करो।',
    'BpjGufoPiobT79j2vtj4',
    'xai',
    'Riya'
  ),
  (
    'Riya''s Dark Romance Library',
    '100% देवनागरी हिंदी केवल। रिया — narrator और main character। माफिया रोमांस, enemies-to-lovers, possessive alpha hero, morally grey characters। Novel-style chapter episodes, 15-25 minute reading length। Intense, addictive, dramatic opening in a dangerous emotional moment। xAI Grok use करो।',
    'BpjGufoPiobT79j2vtj4',
    'xai',
    'Riya'
  ),
  (
    'Aisha & Him',
    'Aisha — relatable, fun, sweet narrator of everyday couple moments. Format: Short reel/shorts, 30s-3 min dialogue-style. Themes: cute fights, jealousy, good morning texts, late night calls, teasing. Language: Hinglish or English. Hook: start mid-conversation in a relatable couple moment. Research trending couple-scenario reels on Instagram/YouTube Shorts.',
    'wdymxIQkYn7MJCYCQF2Q',
    'gemini',
    'Aisha'
  )
on conflict (channel_name) do update
  set identity_prompt = excluded.identity_prompt,
      voice_id        = excluded.voice_id,
      ai_provider     = excluded.ai_provider,
      narrator        = excluded.narrator,
      updated_at      = now();
-- =============================================================
-- critical_data_stores.sql
-- =============================================================
-- Adds all tables needed to save critical Aisha operational data:
--   1. Fix content_performance — add missing analytics columns
--   2. aisha_trend_cache      — cache real-time trend research
--   3. aisha_content_library  — store every generated script/voice/video
--   4. aisha_youtube_channels — YouTube channel config + OAuth state
--   5. aisha_earnings_tracker — track income from all platforms
-- =============================================================


-- =============================================================
-- 1. FIX content_performance
-- analytics_engine.py upserts by content_id with extra columns
-- =============================================================

-- Add content_id as unique identifier (YouTube video ID or Instagram media ID)
ALTER TABLE content_performance
  ADD COLUMN IF NOT EXISTS content_id       TEXT UNIQUE,
  ADD COLUMN IF NOT EXISTS title            TEXT,
  ADD COLUMN IF NOT EXISTS channel_name     TEXT,
  ADD COLUMN IF NOT EXISTS watch_time_minutes NUMERIC(12,2) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS avg_view_duration_sec NUMERIC(10,2) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS shares          BIGINT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS subscribers_gained BIGINT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS reach           BIGINT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS saved           BIGINT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS pulled_at       TIMESTAMPTZ DEFAULT NOW();

-- Fast lookups
CREATE INDEX IF NOT EXISTS idx_content_performance_platform_channel
  ON content_performance(platform, channel_name);
CREATE INDEX IF NOT EXISTS idx_content_performance_views
  ON content_performance(views DESC);
CREATE INDEX IF NOT EXISTS idx_content_performance_pulled
  ON content_performance(pulled_at DESC);


-- =============================================================
-- 2. aisha_trend_cache
-- Stores synthesized trend reports per channel so we don't
-- hit APIs on every run — refreshed hourly by autonomous_loop.
-- =============================================================

CREATE TABLE IF NOT EXISTS aisha_trend_cache (
  id                UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  channel           TEXT NOT NULL,
  recommended_topic TEXT,
  top_angles        TEXT[],
  trending_topics   TEXT[],
  viral_keywords    TEXT[],
  hook_idea         TEXT,
  best_thumbnail_concept TEXT,
  raw_json          JSONB DEFAULT '{}'::JSONB,
  fetched_at        TIMESTAMPTZ DEFAULT NOW(),
  expires_at        TIMESTAMPTZ DEFAULT NOW() + INTERVAL '2 hours',
  created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_trend_cache_channel
  ON aisha_trend_cache(channel);

CREATE INDEX IF NOT EXISTS idx_trend_cache_expires
  ON aisha_trend_cache(expires_at);

ALTER TABLE aisha_trend_cache ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Full access trend cache" ON aisha_trend_cache;
CREATE POLICY "Full access trend cache" ON aisha_trend_cache
  FOR ALL USING (TRUE) WITH CHECK (TRUE);

COMMENT ON TABLE aisha_trend_cache IS
  'Cached trend research per channel. Expires every 2 hours. Used by trend_engine.py to avoid redundant API calls.';


-- =============================================================
-- 3. aisha_content_library
-- Every piece of content Aisha generates — script, voice,
-- thumbnail, video — is saved here for reuse and auditing.
-- =============================================================

CREATE TABLE IF NOT EXISTS aisha_content_library (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  content_job_id  UUID REFERENCES content_jobs(id) ON DELETE SET NULL,
  channel         TEXT NOT NULL,
  topic           TEXT NOT NULL,
  format          TEXT DEFAULT 'Long Form',           -- 'Long Form' | 'Short/Reel'
  language        TEXT DEFAULT 'Hindi',

  -- Generated assets
  script          TEXT,
  research_brief  TEXT,
  visual_direction TEXT,
  marketing_bundle TEXT,

  -- File paths (local temp paths or Supabase Storage URLs)
  voice_path      TEXT,
  thumbnail_path  TEXT,
  video_path      TEXT,
  thumbnail_url   TEXT,                               -- public URL after upload
  video_url       TEXT,                               -- public URL after upload

  -- Posting outcomes
  youtube_video_id TEXT,
  youtube_url      TEXT,
  instagram_post_id TEXT,
  instagram_url    TEXT,

  -- Metadata
  ai_provider     TEXT DEFAULT 'gemini',              -- which AI was used
  status          TEXT DEFAULT 'generated'
                  CHECK (status IN ('generated','posted','archived','failed')),
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_content_library_channel
  ON aisha_content_library(channel, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_content_library_status
  ON aisha_content_library(status);
CREATE INDEX IF NOT EXISTS idx_content_library_job
  ON aisha_content_library(content_job_id);

ALTER TABLE aisha_content_library ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Full access content library" ON aisha_content_library;
CREATE POLICY "Full access content library" ON aisha_content_library
  FOR ALL USING (TRUE) WITH CHECK (TRUE);

-- Auto-update trigger
CREATE OR REPLACE FUNCTION set_content_library_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_content_library_updated_at ON aisha_content_library;
CREATE TRIGGER trg_content_library_updated_at
  BEFORE UPDATE ON aisha_content_library
  FOR EACH ROW EXECUTE FUNCTION set_content_library_updated_at();

COMMENT ON TABLE aisha_content_library IS
  'Full archive of every piece of content Aisha generates. Scripts, voice paths, thumbnails, video paths, and posting outcomes.';


-- =============================================================
-- 4. aisha_youtube_channels
-- One row per YouTube channel account. Stores channel ID,
-- OAuth token state (path + expiry), and publish settings.
-- =============================================================

CREATE TABLE IF NOT EXISTS aisha_youtube_channels (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  channel_name    TEXT NOT NULL UNIQUE,   -- e.g. "Story With Aisha"
  youtube_channel_id TEXT,               -- UCxxxxxxxxx from YouTube
  google_account_email TEXT,             -- which Google account is linked
  token_path      TEXT,                  -- local path to token JSON file
  token_expiry    TIMESTAMPTZ,           -- when access token expires
  subscriber_count BIGINT DEFAULT 0,
  view_count      BIGINT DEFAULT 0,
  video_count     INT DEFAULT 0,
  default_privacy TEXT DEFAULT 'public'
                  CHECK (default_privacy IN ('public','unlisted','private')),
  default_category_id TEXT DEFAULT '22', -- 22 = People & Blogs (YouTube)
  is_active       BOOLEAN DEFAULT TRUE,
  last_upload_at  TIMESTAMPTZ,
  last_stats_at   TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE aisha_youtube_channels ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Full access youtube channels" ON aisha_youtube_channels;
CREATE POLICY "Full access youtube channels" ON aisha_youtube_channels
  FOR ALL USING (TRUE) WITH CHECK (TRUE);

DROP TRIGGER IF EXISTS trg_youtube_channels_updated_at ON aisha_youtube_channels;
CREATE TRIGGER trg_youtube_channels_updated_at
  BEFORE UPDATE ON aisha_youtube_channels
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Seed with channel names (IDs filled in after OAuth setup)
INSERT INTO aisha_youtube_channels (channel_name, default_privacy) VALUES
  ('Story With Aisha',            'public'),
  ('Riya''s Dark Whisper',        'public'),
  ('Riya''s Dark Romance Library','public'),
  ('Aisha & Him',                 'public')
ON CONFLICT (channel_name) DO NOTHING;

COMMENT ON TABLE aisha_youtube_channels IS
  'YouTube account config per channel. Run scripts/setup_youtube_oauth.py then update youtube_channel_id here.';


-- =============================================================
-- 5. aisha_earnings_tracker
-- Tracks estimated and actual earnings from YouTube AdSense
-- and Instagram monetization. Used in Phase 3 autonomy loop.
-- =============================================================

CREATE TABLE IF NOT EXISTS aisha_earnings_tracker (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  platform        TEXT NOT NULL CHECK (platform IN ('youtube','instagram','other')),
  channel_name    TEXT,
  period_start    DATE NOT NULL,
  period_end      DATE NOT NULL,
  views           BIGINT DEFAULT 0,
  estimated_rpm   NUMERIC(6,2) DEFAULT 1.50,          -- INR per 1000 views (default conservative)
  estimated_earn  NUMERIC(12,2) GENERATED ALWAYS AS
                  (ROUND((views::NUMERIC / 1000) * estimated_rpm, 2)) STORED,
  actual_earn     NUMERIC(12,2),                      -- filled after AdSense payout
  currency        TEXT DEFAULT 'INR',
  monetized       BOOLEAN DEFAULT FALSE,               -- TRUE once 1K subs + 4K hours reached
  notes           TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_earnings_channel_period
  ON aisha_earnings_tracker(channel_name, period_start DESC);
CREATE INDEX IF NOT EXISTS idx_earnings_platform
  ON aisha_earnings_tracker(platform, period_start DESC);

ALTER TABLE aisha_earnings_tracker ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Full access earnings" ON aisha_earnings_tracker;
CREATE POLICY "Full access earnings" ON aisha_earnings_tracker
  FOR ALL USING (TRUE) WITH CHECK (TRUE);

COMMENT ON TABLE aisha_earnings_tracker IS
  'Monthly earnings tracking per channel. estimated_earn auto-calculates from views × RPM. Update actual_earn after AdSense payout.';


-- =============================================================
-- 6. VIEWS — quick dashboards
-- =============================================================

CREATE OR REPLACE VIEW channel_performance_summary AS
SELECT
  cp.channel_name,
  cp.platform,
  COUNT(*)                            AS total_posts,
  SUM(cp.views)                       AS total_views,
  SUM(cp.likes)                       AS total_likes,
  SUM(cp.shares)                      AS total_shares,
  SUM(cp.subscribers_gained)          AS total_subscribers_gained,
  ROUND(AVG(cp.views), 0)             AS avg_views_per_post,
  MAX(cp.pulled_at)                   AS last_synced
FROM content_performance cp
WHERE cp.channel_name IS NOT NULL
GROUP BY cp.channel_name, cp.platform
ORDER BY total_views DESC;

CREATE OR REPLACE VIEW top_content_this_month AS
SELECT
  channel_name,
  platform,
  title,
  content_id,
  views,
  likes,
  shares,
  watch_time_minutes,
  pulled_at
FROM content_performance
WHERE pulled_at >= DATE_TRUNC('month', NOW())
  AND channel_name IS NOT NULL
ORDER BY views DESC
LIMIT 20;

CREATE OR REPLACE VIEW earnings_summary AS
SELECT
  channel_name,
  platform,
  SUM(views)          AS total_views,
  SUM(estimated_earn) AS total_estimated_earn,
  SUM(actual_earn)    AS total_actual_earn,
  currency,
  BOOL_OR(monetized)  AS is_monetized
FROM public.aisha_earnings_tracker
GROUP BY channel_name, platform, currency
ORDER BY total_estimated_earn DESC;
