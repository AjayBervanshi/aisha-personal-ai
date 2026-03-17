-- Migration: Add per-platform status + idempotency columns to content_queue
-- Date: 2026-03-17

ALTER TABLE content_queue
  ADD COLUMN IF NOT EXISTS youtube_status  TEXT DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS instagram_status TEXT DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS youtube_video_id TEXT,
  ADD COLUMN IF NOT EXISTS youtube_url      TEXT,
  ADD COLUMN IF NOT EXISTS instagram_post_id TEXT;

-- Guard: prevent duplicate YouTube uploads for the same job
CREATE UNIQUE INDEX IF NOT EXISTS idx_content_queue_youtube_video_id
  ON content_queue (youtube_video_id)
  WHERE youtube_video_id IS NOT NULL;

-- Guard: prevent duplicate Instagram posts for the same job
CREATE UNIQUE INDEX IF NOT EXISTS idx_content_queue_instagram_post_id
  ON content_queue (instagram_post_id)
  WHERE instagram_post_id IS NOT NULL;

-- Add check constraints for valid status values
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_youtube_status'
  ) THEN
    ALTER TABLE content_queue
      ADD CONSTRAINT chk_youtube_status
      CHECK (youtube_status IN ('pending', 'processing', 'published', 'failed', 'skipped'));
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_instagram_status'
  ) THEN
    ALTER TABLE content_queue
      ADD CONSTRAINT chk_instagram_status
      CHECK (instagram_status IN ('pending', 'processing', 'published', 'failed', 'skipped'));
  END IF;
END $$;
