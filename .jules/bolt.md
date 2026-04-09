## 2024-05-18 - [Batch Updates to Avoid N+1 Problem with Supabase]
**Learning:** O(N^2) memory analysis loops (like cosine similarity computations) with individual synchronous database updates for each match result in severe network IO overhead and N+1 query patterns. Supabase has PostgREST URL length limits, meaning batched `.in_()` statements should chunk requests.
**Action:** Always accumulate entity IDs inside loops and apply updates in batches outside the loop using `.in_()` (chunked at max 100 items) to prevent blocking the main thread and ensure scalability over time.
## 2024-04-09 - [Supabase Count Optimizations]
**Learning:** By default, calling `select("id", count="exact")` in Supabase without a limit fetches all matching rows into memory/network before returning the exact count. This is an O(N) operation and causes bottlenecks for large tables.
**Action:** Always append `.limit(1)` when doing exact count queries (e.g., `sb.table('table').select('id', count='exact').limit(1).execute()`) to only return the count metadata and max 1 row, avoiding massive memory overhead.
