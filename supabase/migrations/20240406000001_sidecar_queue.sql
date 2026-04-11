-- =========================================================================
-- JARVIS UPGRADE: OS-Level Sidecar (Feature 2.1)
-- Uses Supabase as the message broker between the Cloud Brain and Local Laptop
-- =========================================================================

CREATE TABLE IF NOT EXISTS sidecar_commands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sidecar_id TEXT NOT NULL,
    command_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    status TEXT DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    result JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_sidecar_status ON sidecar_commands(sidecar_id, status);

-- Secure the table with Row Level Security (RLS)
ALTER TABLE sidecar_commands ENABLE ROW LEVEL SECURITY;

-- Only service_role can insert/update/read (meaning the Python server with SUPABASE_SERVICE_KEY)
-- Local sidecar must also run with SUPABASE_SERVICE_KEY to poll the queue
CREATE POLICY "Service Role Full Access"
ON sidecar_commands
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');
