-- Migration: Fix 4 DB schema gaps causing Render log spam
-- Date: 2026-03-21
-- Fixes:
--   1. aisha_memory.category_check missing 'other' value
--   2. match_memories() function missing (semantic search)

-- Fix 1: Add 'other' to aisha_memory category constraint
ALTER TABLE aisha_memory DROP CONSTRAINT IF EXISTS aisha_memory_category_check;
ALTER TABLE aisha_memory ADD CONSTRAINT aisha_memory_category_check
  CHECK (category IN (
    'mood', 'goal', 'finance', 'schedule',
    'preference', 'relationship', 'health',
    'achievement', 'fear', 'dream', 'general', 'other'
  ));

-- Fix 2: Create match_memories function for semantic memory search (pgvector)
CREATE OR REPLACE FUNCTION match_memories(
  query_embedding vector(768),
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  id uuid,
  category text,
  content text,
  importance int,
  is_active boolean,
  tags text[],
  source text,
  created_at timestamptz,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    m.id,
    m.category,
    m.content,
    m.importance,
    m.is_active,
    m.tags,
    m.source,
    m.created_at,
    1 - (m.embedding <=> query_embedding) AS similarity
  FROM aisha_memory m
  WHERE m.is_active = true
    AND m.embedding IS NOT NULL
    AND 1 - (m.embedding <=> query_embedding) > match_threshold
  ORDER BY m.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
