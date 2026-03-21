-- Migration: Add guest_user_id to aisha_conversations for per-user data isolation
-- Date: 2026-03-21
-- Fixes: Jash's conversation data bleeding into Ajay's context (and vice versa)
--
-- guest_user_id is NULL  → message belongs to the owner (Ajay)
-- guest_user_id = <id>   → message belongs to that approved guest

ALTER TABLE aisha_conversations
  ADD COLUMN IF NOT EXISTS guest_user_id BIGINT DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_conversations_guest_user_id
  ON aisha_conversations (guest_user_id);
