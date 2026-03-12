-- Content Operations Queue for Antigravity Agent
-- Enables: queueing generation jobs, tracking execution status, and monitoring post performance.

create table if not exists content_jobs (
    id uuid primary key default gen_random_uuid(),
    topic text not null,
    channel text not null,
    format text not null default 'Short/Reel',
    platform_targets text[] not null default array['instagram']::text[],
    payload jsonb not null default '{}'::jsonb,
    output jsonb not null default '{}'::jsonb,
    status text not null default 'queued' check (status in ('queued', 'processing', 'completed', 'failed', 'cancelled')),
    priority int not null default 5,
    auto_post boolean not null default true,
    error_text text,
    scheduled_at timestamptz not null default now(),
    started_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists content_performance (
    id uuid primary key default gen_random_uuid(),
    content_job_id uuid references content_jobs(id) on delete set null,
    platform text not null check (platform in ('youtube', 'instagram', 'other')),
    external_post_id text,
    external_url text,
    views bigint default 0,
    likes bigint default 0,
    comments bigint default 0,
    watch_time_seconds bigint default 0,
    subscribers_gained bigint default 0,
    earnings_estimate numeric(12,2) default 0,
    metrics jsonb not null default '{}'::jsonb,
    captured_at timestamptz not null default now(),
    created_at timestamptz not null default now()
);

create index if not exists idx_content_jobs_status_scheduled on content_jobs(status, scheduled_at);
create index if not exists idx_content_jobs_channel on content_jobs(channel);
create index if not exists idx_content_performance_job on content_performance(content_job_id, platform, captured_at desc);

create or replace function set_content_jobs_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_content_jobs_updated_at on content_jobs;
create trigger trg_content_jobs_updated_at
before update on content_jobs
for each row execute function set_content_jobs_updated_at();

alter table content_jobs enable row level security;
alter table content_performance enable row level security;

drop policy if exists "Full access content jobs" on content_jobs;
create policy "Full access content jobs" on content_jobs
for all using (true) with check (true);

drop policy if exists "Full access content performance" on content_performance;
create policy "Full access content performance" on content_performance
for all using (true) with check (true);
