-- Fix api_keys table: ensure secret column exists
-- Run in Supabase SQL Editor if 'column api_keys.secret does not exist' error appears

-- Add secret column if missing
ALTER TABLE public.api_keys
  ADD COLUMN IF NOT EXISTS secret TEXT NOT NULL DEFAULT '';

-- If old 'key' column exists, migrate data then drop
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'api_keys'
      AND column_name = 'key'
  ) THEN
    UPDATE public.api_keys SET secret = key WHERE secret = '';
    ALTER TABLE public.api_keys DROP COLUMN IF EXISTS key;
  END IF;
END $$;

-- Remove DEFAULT '' now that data is migrated (enforce NOT NULL properly)
ALTER TABLE public.api_keys ALTER COLUMN secret DROP DEFAULT;
