-- Series tracking for episodic YouTube Shorts
CREATE TABLE IF NOT EXISTS aisha_series (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    series_name     TEXT NOT NULL,
    channel         TEXT NOT NULL,
    total_episodes  INT  DEFAULT 5,
    current_episode INT  DEFAULT 0,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS aisha_episodes (
    id                UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    series_id         UUID REFERENCES aisha_series(id) ON DELETE CASCADE,
    episode_number    INT NOT NULL,
    title             TEXT,
    script_summary    TEXT,
    cliffhanger       TEXT,
    youtube_url       TEXT,
    instagram_post_id TEXT,
    content_job_id    UUID,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_episodes_series ON aisha_episodes(series_id, episode_number);
CREATE INDEX IF NOT EXISTS idx_series_channel  ON aisha_series(channel, is_active);
