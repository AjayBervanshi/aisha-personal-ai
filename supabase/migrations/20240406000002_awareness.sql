-- =========================================================================
-- JARVIS UPGRADE: Continuous Awareness (Feature 3.1)
-- Stores the latest screen OCR and active window context from the sidecar
-- =========================================================================

CREATE TABLE IF NOT EXISTS aisha_awareness_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sidecar_id TEXT NOT NULL,
    active_window TEXT,
    screen_text TEXT,
    has_visual_change BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- We only really care about the last 10 minutes of awareness for context injection.
-- We can add a pg_cron job or Supabase Edge Function to prune old logs later to save space.
CREATE INDEX IF NOT EXISTS idx_awareness_time ON aisha_awareness_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_awareness_sidecar ON aisha_awareness_logs(sidecar_id);

-- Enforce RLS so only the service role (Aisha and Sidecar) can access
ALTER TABLE aisha_awareness_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service Role Full Access" ON aisha_awareness_logs
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');
