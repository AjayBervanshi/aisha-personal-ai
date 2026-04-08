## 2024-05-18 - [Batch Updates to Avoid N+1 Problem with Supabase]
**Learning:** O(N^2) memory analysis loops (like cosine similarity computations) with individual synchronous database updates for each match result in severe network IO overhead and N+1 query patterns. Supabase has PostgREST URL length limits, meaning batched `.in_()` statements should chunk requests.
**Action:** Always accumulate entity IDs inside loops and apply updates in batches outside the loop using `.in_()` (chunked at max 100 items) to prevent blocking the main thread and ensure scalability over time.
## 2025-04-08 - O(1) Supabase Count Optimization
**Learning:** In Supabase, executing `.select("id", count="exact").execute()` fetches all matching rows (row IDs) over the network just to get the count, causing O(N) memory and network overhead.
**Action:** Always append `.limit(1)` to `.select(..., count="exact")` queries to avoid downloading unnecessary row data when only the count is needed.
