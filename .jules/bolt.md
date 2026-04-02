## 2026-04-01 - Fix N+1 Query in Autonomous Loop Startup Recovery
**Learning:** Avoid N+1 query patterns by batching database requests (e.g., using Supabase `.in_()` filters) instead of querying inside loops. When using `.in_()`, chunk batches (e.g., 100 items per batch) to avoid PostgREST URL length limits.
**Action:** Replaced the loop in `src/core/autonomous_loop.py`'s `_startup_recovery` method that updated stuck jobs individually with a chunked bulk update using `.in_('id', chunk)`.
