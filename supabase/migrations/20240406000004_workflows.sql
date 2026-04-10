-- =========================================================================
-- JARVIS UPGRADE: Visual/NLP Workflow Engine (Feature 4.2 & 4.3)
-- Stores workflow graph definitions (Nodes and Edges) and execution logs.
-- =========================================================================

-- 1. Workflow Definitions
CREATE TABLE IF NOT EXISTS aisha_workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    trigger_type TEXT NOT NULL, -- e.g., 'cron', 'webhook', 'email', 'manual'
    trigger_config JSONB DEFAULT '{}'::jsonb, -- e.g., {"schedule": "0 9 * * *"}
    nodes JSONB NOT NULL,       -- Array of node objects (id, type, config, position)
    edges JSONB NOT NULL,       -- Array of edge connections (source_node, target_node)
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 2. Workflow Execution History
CREATE TABLE IF NOT EXISTS aisha_workflow_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES aisha_workflows(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'running', -- running, completed, failed, self_healing
    started_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    finished_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    state_snapshot JSONB DEFAULT '{}'::jsonb -- The final output variables/state of the run
);

-- RLS Enforcement
ALTER TABLE aisha_workflows ENABLE ROW LEVEL SECURITY;
ALTER TABLE aisha_workflow_executions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service Role Full Access" ON aisha_workflows USING (auth.role() = 'service_role');
CREATE POLICY "Service Role Full Access" ON aisha_workflow_executions USING (auth.role() = 'service_role');
