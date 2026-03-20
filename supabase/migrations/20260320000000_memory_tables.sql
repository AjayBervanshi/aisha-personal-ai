-- ============================================================
-- Memory Tables Migration
-- Creates aisha_emotional_memory, aisha_skill_memory,
-- and aisha_episodic_memory tables used by MemoryManager.
-- ============================================================

-- ── Emotional Memory ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS aisha_emotional_memory (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mood_state    TEXT NOT NULL,
    trigger       TEXT NOT NULL,
    context_text  TEXT,
    embedding     JSONB,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE aisha_emotional_memory ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_all_emotional" ON aisha_emotional_memory
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ── Skill Memory ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS aisha_skill_memory (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_name  TEXT NOT NULL,
    description TEXT,
    embedding   JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE aisha_skill_memory ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_all_skill" ON aisha_skill_memory
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ── Episodic Memory ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS aisha_episodic_memory (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity            TEXT NOT NULL,
    event_description TEXT NOT NULL,
    event_date        DATE,
    embedding         JSONB,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE aisha_episodic_memory ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_all_episodic" ON aisha_episodic_memory
    FOR ALL TO service_role USING (true) WITH CHECK (true);
