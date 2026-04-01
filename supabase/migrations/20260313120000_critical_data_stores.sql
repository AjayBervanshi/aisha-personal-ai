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
  MAX(monetized)      AS is_monetized
FROM aisha_earnings_tracker
GROUP BY channel_name, platform, currency
ORDER BY total_estimated_earn DESC;
