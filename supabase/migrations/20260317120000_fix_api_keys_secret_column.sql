-- Fix api_keys table: ensure secret column exists
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS secret TEXT;
