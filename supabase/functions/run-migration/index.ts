/**
 * run-migration — one-shot DDL runner. Deploy, invoke once, delete.
 */
import postgres from "https://deno.land/x/postgresjs@v3.4.4/mod.js";

const MIGRATION_SQL = `
-- Create content_queue if not exists (with all columns including idempotency)
CREATE TABLE IF NOT EXISTS content_queue (
  id                  UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  channel             TEXT        NOT NULL,
  topic               TEXT        NOT NULL,
  script              TEXT,
  seo_package         TEXT,
  youtube_title       TEXT,
  audio_url           TEXT,
  thumbnail_url       TEXT,
  status              TEXT        DEFAULT 'ready',
  youtube_status      TEXT        DEFAULT 'pending',
  instagram_status    TEXT        DEFAULT 'pending',
  youtube_video_id    TEXT,
  youtube_url         TEXT,
  instagram_post_id   TEXT,
  updated_at          TIMESTAMPTZ DEFAULT NOW(),
  created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Add any missing columns to existing table
ALTER TABLE content_queue
  ADD COLUMN IF NOT EXISTS youtube_status    TEXT DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS instagram_status  TEXT DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS youtube_video_id  TEXT,
  ADD COLUMN IF NOT EXISTS youtube_url       TEXT,
  ADD COLUMN IF NOT EXISTS instagram_post_id TEXT,
  ADD COLUMN IF NOT EXISTS updated_at        TIMESTAMPTZ DEFAULT NOW();

-- Auto-update updated_at trigger
CREATE OR REPLACE FUNCTION set_content_queue_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_content_queue_updated_at ON content_queue;
CREATE TRIGGER trg_content_queue_updated_at
  BEFORE UPDATE ON content_queue
  FOR EACH ROW EXECUTE FUNCTION set_content_queue_updated_at();

-- Unique indexes for idempotency
CREATE UNIQUE INDEX IF NOT EXISTS idx_cq_youtube_video_id
  ON content_queue (youtube_video_id)
  WHERE youtube_video_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_cq_instagram_post_id
  ON content_queue (instagram_post_id)
  WHERE instagram_post_id IS NOT NULL;

-- Check constraints
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_youtube_status') THEN
    ALTER TABLE content_queue ADD CONSTRAINT chk_youtube_status
      CHECK (youtube_status IN ('pending','processing','published','failed','skipped'));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_instagram_status') THEN
    ALTER TABLE content_queue ADD CONSTRAINT chk_instagram_status
      CHECK (instagram_status IN ('pending','processing','published','failed','skipped'));
  END IF;
END $$;

-- Enable RLS
ALTER TABLE content_queue ENABLE ROW LEVEL SECURITY;

-- RLS policy (service role only)
DROP POLICY IF EXISTS "service_only_content_queue" ON content_queue;
CREATE POLICY "service_only_content_queue" ON content_queue
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Also ensure api_keys table exists (created by earlier migration but verify)
CREATE TABLE IF NOT EXISTS api_keys (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT        NOT NULL UNIQUE,
  secret      TEXT        NOT NULL,
  description TEXT,
  active      BOOLEAN     NOT NULL DEFAULT true,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "service_role_only_api_keys" ON api_keys;
CREATE POLICY "service_role_only_api_keys" ON api_keys
  FOR ALL TO service_role USING (true) WITH CHECK (true);
`;

Deno.serve(async (_req) => {
  const dbUrl = Deno.env.get("SUPABASE_DB_URL");
  if (!dbUrl) {
    return new Response(JSON.stringify({ error: "SUPABASE_DB_URL not injected" }), { status: 500 });
  }
  try {
    const sql = postgres(dbUrl, { max: 1 });
    await sql.unsafe(MIGRATION_SQL);
    await sql.end();
    return new Response(JSON.stringify({ success: true, message: "Migration applied successfully" }), {
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: String(err) }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
});
