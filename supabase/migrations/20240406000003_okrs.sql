-- =========================================================================
-- JARVIS UPGRADE: Goal Pursuit (Feature 4.1)
-- Stores Objectives, Key Results, and Daily Actions
-- =========================================================================

-- 1. Objectives (High Level Goals)
CREATE TABLE IF NOT EXISTS aisha_objectives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    deadline TIMESTAMP WITH TIME ZONE,
    status TEXT DEFAULT 'active', -- active, achieved, failed, dropped
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 2. Key Results (Measurable outcomes for an objective)
CREATE TABLE IF NOT EXISTS aisha_key_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    objective_id UUID REFERENCES aisha_objectives(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    target_value FLOAT DEFAULT 1.0,
    current_value FLOAT DEFAULT 0.0,
    unit TEXT DEFAULT 'completion',
    score FLOAT GENERATED ALWAYS AS (
        CASE
            WHEN target_value = 0 THEN 0.0
            ELSE LEAST(current_value / target_value, 1.0)
        END
    ) STORED,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 3. Daily Actions (The habits required to hit Key Results)
CREATE TABLE IF NOT EXISTS aisha_daily_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_result_id UUID REFERENCES aisha_key_results(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    frequency TEXT DEFAULT 'daily', -- daily, weekly
    last_completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- RLS Enforcement
ALTER TABLE aisha_objectives ENABLE ROW LEVEL SECURITY;
ALTER TABLE aisha_key_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE aisha_daily_actions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service Role Full Access" ON aisha_objectives USING (auth.role() = 'service_role');
CREATE POLICY "Service Role Full Access" ON aisha_key_results USING (auth.role() = 'service_role');
CREATE POLICY "Service Role Full Access" ON aisha_daily_actions USING (auth.role() = 'service_role');
