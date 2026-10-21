-- Migration: Create render_jobs table for asynchronous background queue
-- Designed for FOR UPDATE SKIP LOCKED concurrency

CREATE TABLE public.render_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    status TEXT NOT NULL DEFAULT 'pending',
    intent TEXT NOT NULL,
    
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    result JSONB DEFAULT '{}'::jsonb,
    
    chat_id BIGINT,
    
    priority INT DEFAULT 0,
    
    retry_count INT NOT NULL DEFAULT 0,
    last_error TEXT,
    
    locked_at TIMESTAMP WITH TIME ZONE,
    worker_id TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Index for efficient polling
CREATE INDEX idx_render_jobs_status_created 
ON public.render_jobs (status, created_at);

-- Index for processing jobs (useful for monitoring and zombies)
CREATE INDEX idx_render_jobs_processing 
ON public.render_jobs (status, locked_at);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_render_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_render_jobs_updated_at
BEFORE UPDATE ON public.render_jobs
FOR EACH ROW
EXECUTE FUNCTION update_render_jobs_updated_at();

-- RLS Policies (Allow authenticated server to access queue)
ALTER TABLE public.render_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable read/write for service_role only" 
ON public.render_jobs 
USING (auth.jwt() ->> 'role' = 'service_role')
WITH CHECK (auth.jwt() ->> 'role' = 'service_role');


-- RPC Function for atomic dequeue
CREATE OR REPLACE FUNCTION dequeue_render_job(req_worker_id TEXT)
RETURNS TABLE(
    id UUID,
    status TEXT,
    intent TEXT,
    payload JSONB,
    result JSONB,
    chat_id BIGINT,
    priority INT,
    retry_count INT,
    last_error TEXT,
    locked_at TIMESTAMP WITH TIME ZONE,
    worker_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    UPDATE public.render_jobs
    SET status = 'processing',
        locked_at = NOW(),
        updated_at = NOW(),
        worker_id = req_worker_id
    WHERE public.render_jobs.id = (
        SELECT r.id
        FROM public.render_jobs r
        WHERE r.status = 'pending'
           OR (r.status = 'processing' AND r.locked_at < NOW() - INTERVAL '10 minutes')
        ORDER BY r.priority DESC, r.created_at ASC
        FOR UPDATE SKIP LOCKED
        LIMIT 1
    )
    RETURNING *;
END;
$$;
