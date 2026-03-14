alter table if exists public.api_keys
  add column if not exists updated_at timestamptz not null default now();
