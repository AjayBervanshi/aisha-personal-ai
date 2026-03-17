CREATE TABLE IF NOT EXISTS content_queue (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  channel TEXT NOT NULL,
  topic TEXT NOT NULL,
  script TEXT,
  seo_package TEXT,
  youtube_title TEXT,
  audio_url TEXT,
  thumbnail_url TEXT,
  status TEXT DEFAULT 'ready',
  created_at TIMESTAMPTZ DEFAULT NOW()
);