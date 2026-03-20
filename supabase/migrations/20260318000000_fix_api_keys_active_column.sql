-- Fix api_keys table: ensure active column exists
-- The create_api_keys_table migration defines active boolean, but if the table
-- was created by an older script that omitted it, this patch adds it.

ALTER TABLE public.api_keys
  ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE;
