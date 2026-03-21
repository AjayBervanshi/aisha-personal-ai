-- Migration: Add youtube_status and instagram_status to content_jobs table
-- Date: 2026-03-21
-- Fixes: /upload crash "column content_jobs.youtube_status does not exist"

ALTER TABLE content_jobs
  ADD COLUMN IF NOT EXISTS youtube_status   TEXT DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS instagram_status TEXT DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS youtube_video_id TEXT,
  ADD COLUMN IF NOT EXISTS youtube_url      TEXT,
  ADD COLUMN IF NOT EXISTS instagram_post_id TEXT;

-- Also ensure content_queue has the same columns (idempotent)
ALTER TABLE content_queue
  ADD COLUMN IF NOT EXISTS youtube_status   TEXT DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS instagram_status TEXT DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS youtube_video_id TEXT,
  ADD COLUMN IF NOT EXISTS youtube_url      TEXT,
  ADD COLUMN IF NOT EXISTS instagram_post_id TEXT;

-- Unique indexes to prevent duplicate uploads
CREATE UNIQUE INDEX IF NOT EXISTS idx_content_jobs_youtube_video_id
  ON content_jobs (youtube_video_id)
  WHERE youtube_video_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_content_jobs_instagram_post_id
  ON content_jobs (instagram_post_id)
  WHERE instagram_post_id IS NOT NULL;

-- Check constraints for valid status values (content_jobs)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_jobs_youtube_status') THEN
    ALTER TABLE content_jobs
      ADD CONSTRAINT chk_jobs_youtube_status
      CHECK (youtube_status IN ('pending', 'processing', 'published', 'failed', 'skipped'));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_jobs_instagram_status') THEN
    ALTER TABLE content_jobs
      ADD CONSTRAINT chk_jobs_instagram_status
      CHECK (instagram_status IN ('pending', 'processing', 'published', 'failed', 'skipped'));
  END IF;
END $$;
