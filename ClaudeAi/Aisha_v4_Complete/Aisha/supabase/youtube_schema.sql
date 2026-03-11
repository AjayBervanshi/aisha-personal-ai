-- ============================================================
-- YOUTUBE EMPIRE — Database Schema
-- All agents communicate through these tables
-- Run AFTER aisha schema.sql
-- ============================================================

-- ── VIDEO JOBS (Central job tracker) ─────────────────────────
-- Every video starts here. Agents update this row as they work.
CREATE TABLE IF NOT EXISTS yt_jobs (
  id            UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  topic         TEXT NOT NULL,               -- "10 best street foods in Mumbai"
  status        TEXT DEFAULT 'queued' CHECK (status IN (
                  'queued','researching','scripting','reviewing',
                  'audio','video','thumbnail','syncing','captions',
                  'seo','uploading','published','failed','paused'
                )),
  created_by    TEXT DEFAULT 'ajay',
  priority      INT DEFAULT 3,               -- 1=urgent, 5=low
  error_msg     TEXT,
  retry_count   INT DEFAULT 0,
  started_at    TIMESTAMPTZ,
  completed_at  TIMESTAMPTZ,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ── RESEARCH (Riya's output) ──────────────────────────────────
CREATE TABLE IF NOT EXISTS yt_research (
  id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  job_id      UUID REFERENCES yt_jobs(id) ON DELETE CASCADE,
  topic       TEXT NOT NULL,
  findings    TEXT NOT NULL,                 -- Research summary
  sources     TEXT[],                        -- URLs used
  keywords    TEXT[],                        -- SEO keywords found
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── SCRIPTS (Lexi's output) ───────────────────────────────────
CREATE TABLE IF NOT EXISTS yt_scripts (
  id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  job_id      UUID REFERENCES yt_jobs(id) ON DELETE CASCADE,
  version     INT DEFAULT 1,                 -- Revision number
  content     TEXT NOT NULL,                 -- Full script text
  word_count  INT,
  duration_s  INT,                           -- Estimated seconds
  status      TEXT DEFAULT 'draft' CHECK (status IN (
                'draft','reviewing','approved','rejected'
              )),
  reviewer_notes TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── AUDIO (Aria's output) ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS yt_audio (
  id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  job_id      UUID REFERENCES yt_jobs(id) ON DELETE CASCADE,
  script_id   UUID REFERENCES yt_scripts(id),
  provider    TEXT DEFAULT 'edge_tts',       -- edge_tts / elevenlabs / coqui
  voice_id    TEXT,
  file_path   TEXT,                          -- Supabase storage path
  duration_s  NUMERIC,
  status      TEXT DEFAULT 'pending',
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── THUMBNAILS (Pixel's output) ───────────────────────────────
CREATE TABLE IF NOT EXISTS yt_thumbnails (
  id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  job_id      UUID REFERENCES yt_jobs(id) ON DELETE CASCADE,
  prompt      TEXT,                          -- Image gen prompt used
  file_path   TEXT,                          -- Supabase storage path
  provider    TEXT DEFAULT 'stable_diffusion',
  status      TEXT DEFAULT 'pending',
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── VIDEOS (Vex's output) ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS yt_videos (
  id           UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  job_id       UUID REFERENCES yt_jobs(id) ON DELETE CASCADE,
  audio_id     UUID REFERENCES yt_audio(id),
  raw_path     TEXT,                         -- Before sync
  synced_path  TEXT,                         -- After audio+video merge
  captions_path TEXT,
  final_path   TEXT,                         -- Upload-ready file
  resolution   TEXT DEFAULT '1920x1080',
  provider     TEXT DEFAULT 'huggingface',
  status       TEXT DEFAULT 'pending',
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ── SEO (Mia's output) ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS yt_seo (
  id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  job_id      UUID REFERENCES yt_jobs(id) ON DELETE CASCADE,
  title       TEXT NOT NULL,
  description TEXT,
  tags        TEXT[],
  hashtags    TEXT[],
  category    TEXT,
  thumbnail_text TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── PUBLISHED (Max's record) ──────────────────────────────────
CREATE TABLE IF NOT EXISTS yt_published (
  id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  job_id      UUID REFERENCES yt_jobs(id) ON DELETE CASCADE,
  youtube_id  TEXT,                          -- YouTube video ID
  youtube_url TEXT,
  published_at TIMESTAMPTZ DEFAULT NOW(),
  views_24h   INT DEFAULT 0,
  likes_24h   INT DEFAULT 0,
  comments_24h INT DEFAULT 0
);

-- ── AGENT LOGS (All agents log here) ─────────────────────────
CREATE TABLE IF NOT EXISTS yt_agent_logs (
  id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  job_id      UUID REFERENCES yt_jobs(id) ON DELETE CASCADE,
  agent_name  TEXT NOT NULL,                 -- "Riya", "Lexi", "Aria" etc.
  action      TEXT NOT NULL,                 -- What it did
  result      TEXT,                          -- Output summary
  duration_ms INT,
  success     BOOLEAN DEFAULT TRUE,
  error       TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── AGENT STATUS (Live heartbeat) ────────────────────────────
CREATE TABLE IF NOT EXISTS yt_agents (
  id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  name        TEXT NOT NULL UNIQUE,          -- "Riya", "Lexi" etc.
  role        TEXT NOT NULL,
  status      TEXT DEFAULT 'idle',           -- idle/busy/error/offline
  current_job UUID REFERENCES yt_jobs(id),
  jobs_done   INT DEFAULT 0,
  last_seen   TIMESTAMPTZ DEFAULT NOW()
);

-- ── TRENDING TOPICS (Neo's store) ─────────────────────────────
CREATE TABLE IF NOT EXISTS yt_trending (
  id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  topic       TEXT NOT NULL,
  category    TEXT,
  score       INT DEFAULT 0,                 -- Trending score
  used        BOOLEAN DEFAULT FALSE,
  found_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ── SEED AGENTS ───────────────────────────────────────────────
INSERT INTO yt_agents (name, role) VALUES
  ('Aisha',   'Commander — orchestrates all agents'),
  ('Riya',    'Topic Researcher'),
  ('Lexi',    'Script Writer'),
  ('Priya',   'Fact Checker'),
  ('Zara',    'Quality Reviewer'),
  ('Mia',     'SEO Specialist'),
  ('Tara',    'Title Generator'),
  ('Aria',    'Audio/Voice Bot'),
  ('Vex',     'Video Generator'),
  ('Pixel',   'Thumbnail Designer'),
  ('Cappy',   'Caption Creator'),
  ('Sync',    'AV Sync Bot'),
  ('Ivy',     'Social Media Bot'),
  ('Max',     'YouTube Upload Bot'),
  ('Echo',    'Comment Manager'),
  ('Lux',     'Analytics Tracker'),
  ('Neo',     'Trend Watcher'),
  ('Kai',     'Shorts/Reels Repurposer'),
  ('Rex',     'Review Coordinator'),
  ('Opus',    'Memory Archivist'),
  ('Dash',    'Scheduler')
ON CONFLICT (name) DO NOTHING;

-- ── REALTIME (enable for agent communication) ─────────────────
-- Enable realtime on jobs table so agents get instant notifications
ALTER TABLE yt_jobs REPLICA IDENTITY FULL;
ALTER TABLE yt_agent_logs REPLICA IDENTITY FULL;

-- ── INDEXES ───────────────────────────────────────────────────
CREATE INDEX idx_jobs_status   ON yt_jobs(status);
CREATE INDEX idx_logs_agent    ON yt_agent_logs(agent_name);
CREATE INDEX idx_logs_job      ON yt_agent_logs(job_id);
CREATE INDEX idx_scripts_job   ON yt_scripts(job_id);
CREATE INDEX idx_trending_used ON yt_trending(used, score DESC);

-- ── TRIGGER: auto-update updated_at ──────────────────────────
CREATE TRIGGER update_yt_jobs_updated_at
  BEFORE UPDATE ON yt_jobs
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

SELECT 'YouTube Empire schema created! 20 agents ready. 💜' AS status;
