-- =========================================================================
-- JARVIS UPGRADE: Knowledge Graph Vault (Feature 1.3)
-- Transforms flat memory into an Entity-Relationship Graph
-- =========================================================================

-- 1. Vault Entities (Things, People, Places, Concepts)
CREATE TABLE IF NOT EXISTS vault_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,          -- e.g., "Apple", "John Doe", "Project X"
    type TEXT NOT NULL,          -- e.g., "organization", "person", "project", "concept"
    description TEXT,            -- Summarized context about this entity
    aliases TEXT[] DEFAULT ARRAY[]::TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    UNIQUE(name, type)
);

-- 2. Vault Facts (Discrete, atomic pieces of knowledge tied to an entity)
CREATE TABLE IF NOT EXISTS vault_facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID REFERENCES vault_entities(id) ON DELETE CASCADE,
    fact TEXT NOT NULL,          -- e.g., "Was founded in 1976", "Is allergic to peanuts"
    confidence FLOAT DEFAULT 1.0,
    source TEXT DEFAULT 'conversation',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 3. Vault Relationships (How entities connect to each other)
CREATE TABLE IF NOT EXISTS vault_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_entity_id UUID REFERENCES vault_entities(id) ON DELETE CASCADE,
    target_entity_id UUID REFERENCES vault_entities(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL, -- e.g., "works_for", "is_interested_in", "owns"
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    UNIQUE(source_entity_id, target_entity_id, relationship_type)
);

-- Add indexes for fast graph traversal
CREATE INDEX IF NOT EXISTS idx_vault_facts_entity ON vault_facts(entity_id);
CREATE INDEX IF NOT EXISTS idx_vault_rel_source ON vault_relationships(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_vault_rel_target ON vault_relationships(target_entity_id);
