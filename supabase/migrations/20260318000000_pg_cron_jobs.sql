-- ============================================================
-- Aisha pg_cron Jobs Migration
-- All times in UTC (IST = UTC+5:30)
-- Primary scheduler: pg_cron → Edge Function → Render /api/trigger/<job>
-- ============================================================

-- Remove any existing Aisha jobs (idempotent re-run safety)
SELECT cron.unschedule(jobname)
FROM cron.job
WHERE jobname LIKE 'aisha-%';

-- Edge Function base URL: https://tgqerhkcbobtxqkgihps.supabase.co/functions/v1/<name>
-- Functions deployed with --no-verify-jwt, no Authorization header needed.

-- ── Daily Jobs ─────────────────────────────────────────────────────────────

-- 1. Morning check-in — 08:00 IST = 02:30 UTC
SELECT cron.schedule(
  'aisha-morning',
  '30 2 * * *',
  $$
  SELECT net.http_post(
    url     := 'https://tgqerhkcbobtxqkgihps.supabase.co/functions/v1/trigger-maintenance?job=morning',
    headers := '{"Content-Type":"application/json"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);

-- 2. Evening wrap-up — 21:00 IST = 15:30 UTC
SELECT cron.schedule(
  'aisha-evening',
  '30 15 * * *',
  $$
  SELECT net.http_post(
    url     := 'https://tgqerhkcbobtxqkgihps.supabase.co/functions/v1/trigger-maintenance?job=evening',
    headers := '{"Content-Type":"application/json"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);

-- 3. Daily digest — 21:30 IST = 16:00 UTC
SELECT cron.schedule(
  'aisha-daily-digest',
  '0 16 * * *',
  $$
  SELECT net.http_post(
    url     := 'https://tgqerhkcbobtxqkgihps.supabase.co/functions/v1/trigger-maintenance?job=digest',
    headers := '{"Content-Type":"application/json"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);

-- 4. Memory consolidation — 03:00 IST = 21:30 UTC
SELECT cron.schedule(
  'aisha-memory-consolidation',
  '30 21 * * *',
  $$
  SELECT net.http_post(
    url     := 'https://tgqerhkcbobtxqkgihps.supabase.co/functions/v1/trigger-maintenance?job=memory',
    headers := '{"Content-Type":"application/json"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);

-- 5. Self-improvement — 02:00 IST = 20:30 UTC
SELECT cron.schedule(
  'aisha-self-improve',
  '30 20 * * *',
  $$
  SELECT net.http_post(
    url     := 'https://tgqerhkcbobtxqkgihps.supabase.co/functions/v1/trigger-maintenance?job=self-improve',
    headers := '{"Content-Type":"application/json"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);

-- 6. Temp file cleanup — 04:00 IST = 22:30 UTC
SELECT cron.schedule(
  'aisha-temp-cleanup',
  '30 22 * * *',
  $$
  SELECT net.http_post(
    url     := 'https://tgqerhkcbobtxqkgihps.supabase.co/functions/v1/trigger-maintenance?job=temp-cleanup',
    headers := '{"Content-Type":"application/json"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);

-- 7. API key expiry check — 09:00 IST = 03:30 UTC
SELECT cron.schedule(
  'aisha-key-expiry',
  '30 3 * * *',
  $$
  SELECT net.http_post(
    url     := 'https://tgqerhkcbobtxqkgihps.supabase.co/functions/v1/trigger-maintenance?job=key-expiry',
    headers := '{"Content-Type":"application/json"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);

-- ── Weekly Jobs ────────────────────────────────────────────────────────────

-- 8. Weekly digest — Sunday 19:00 IST = Sunday 13:30 UTC
SELECT cron.schedule(
  'aisha-weekly-digest',
  '30 13 * * 0',
  $$
  SELECT net.http_post(
    url     := 'https://tgqerhkcbobtxqkgihps.supabase.co/functions/v1/trigger-maintenance?job=weekly-digest',
    headers := '{"Content-Type":"application/json"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);

-- 9. Memory cleanup — Sunday 03:00 IST = Saturday 21:30 UTC
SELECT cron.schedule(
  'aisha-memory-cleanup',
  '30 21 * * 6',
  $$
  SELECT net.http_post(
    url     := 'https://tgqerhkcbobtxqkgihps.supabase.co/functions/v1/trigger-maintenance?job=memory-cleanup',
    headers := '{"Content-Type":"application/json"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);

-- ── High-Frequency Jobs ────────────────────────────────────────────────────

-- 10. Task reminder poll — every 5 minutes
SELECT cron.schedule(
  'aisha-task-poll',
  '*/5 * * * *',
  $$
  SELECT net.http_post(
    url     := 'https://tgqerhkcbobtxqkgihps.supabase.co/functions/v1/trigger-maintenance?job=task-poll',
    headers := '{"Content-Type":"application/json"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);

-- 11. Inactivity check — every 3 hours
SELECT cron.schedule(
  'aisha-inactivity',
  '0 */3 * * *',
  $$
  SELECT net.http_post(
    url     := 'https://tgqerhkcbobtxqkgihps.supabase.co/functions/v1/trigger-maintenance?job=inactivity',
    headers := '{"Content-Type":"application/json"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);

-- ── Studio (heavy job — its own function) ─────────────────────────────────

-- 12. Studio session — every 4 hours
SELECT cron.schedule(
  'aisha-studio-every-4h',
  '0 */4 * * *',
  $$
  SELECT net.http_post(
    url     := 'https://tgqerhkcbobtxqkgihps.supabase.co/functions/v1/trigger-studio',
    headers := '{"Content-Type":"application/json"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);

-- ── Verify ────────────────────────────────────────────────────────────────
-- Run after applying to confirm all 12 jobs are registered:
-- SELECT jobname, schedule, active FROM cron.job WHERE jobname LIKE 'aisha-%' ORDER BY jobname;
