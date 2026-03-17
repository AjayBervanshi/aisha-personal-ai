-- content_queue table
CREATE TABLE IF NOT EXISTS content_queue (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  channel TEXT NOT NULL,
  topic TEXT NOT NULL,
  script TEXT,
  seo_package TEXT,
  youtube_title TEXT,
  audio_url TEXT,
  thumbnail_url TEXT,
  video_url TEXT,
  status TEXT DEFAULT 'ready', -- ready | posted_youtube | posted_instagram | posted
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Storage bucket for audio files
INSERT INTO storage.buckets (id, name, public)
VALUES ('content-audio', 'content-audio', true)
ON CONFLICT (id) DO NOTHING;

-- Allow public read on content-audio
CREATE POLICY IF NOT EXISTS "Public read content-audio"
ON storage.objects FOR SELECT
USING (bucket_id = 'content-audio');

-- Allow service role to upload
CREATE POLICY IF NOT EXISTS "Service role upload content-audio"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'content-audio');
