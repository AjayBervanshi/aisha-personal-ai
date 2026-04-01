## 2026-04-01 - Fix N+1 Query in Autonomous Loop
**Learning:** Supabase queries should be batched to minimize network round trips, but when using `.in_()`, queries with too many items (e.g. hundreds) can hit PostgREST URL length limits.
**Action:** Implemented chunking (batches of 100) along with the `.in_()` clause for batched updates. This avoids both N+1 query latency and URL length limit errors.
