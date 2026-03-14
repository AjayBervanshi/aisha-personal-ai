create extension if not exists "pgcrypto";

create table if not exists public.api_keys (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  secret text not null,
  description text,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_api_keys_updated_at on public.api_keys;
create trigger trg_api_keys_updated_at
before update on public.api_keys
for each row execute function public.set_updated_at();

alter table public.api_keys enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'api_keys'
      and policyname = 'service_role_only_api_keys'
  ) then
    create policy service_role_only_api_keys
      on public.api_keys
      for all
      to service_role
      using (true)
      with check (true);
  end if;
end $$;
