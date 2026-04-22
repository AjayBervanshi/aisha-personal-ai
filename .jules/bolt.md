## 2024-05-18 - [Batch Updates to Avoid N+1 Problem with Supabase]
**Learning:** O(N^2) memory analysis loops (like cosine similarity computations) with individual synchronous database updates for each match result in severe network IO overhead and N+1 query patterns. Supabase has PostgREST URL length limits, meaning batched `.in_()` statements should chunk requests.
**Action:** Always accumulate entity IDs inside loops and apply updates in batches outside the loop using `.in_()` (chunked at max 100 items) to prevent blocking the main thread and ensure scalability over time.
## 2024-04-09 - [Supabase Count Optimizations]
**Learning:** By default, calling `select("id", count="exact")` in Supabase without a limit fetches all matching rows into memory/network before returning the exact count. This is an O(N) operation and causes bottlenecks for large tables.
**Action:** Always append `.limit(1)` when doing exact count queries (e.g., `sb.table('table').select('id', count='exact').limit(1).execute()`) to only return the count metadata and max 1 row, avoiding massive memory overhead.
## 2024-05-18 - [GoalEngine Evening Review Update Batching]
**Learning:** `GoalEngine.evening_review` had an N+1 query vulnerability because it iterated through completed daily action IDs and performed a separate `self.supabase.table("aisha_daily_actions").update(...).eq("id", a_id)` call for each ID.
**Action:** Use `.in_("id", batch)` to batch updates instead of `.eq("id", id)` inside a loop. Make sure to batch the `.in_()` call in chunks of 100 to avoid PostgREST URL length limits if the payload is large.
## 2025-02-12 - [Supabase HTTP API Count Optimization]
**Learning:** Making REST HTTP queries to PostgREST using the `Prefer: count=exact` header without specifying `&limit=1` acts as an O(N) operation by bringing the matched records into memory or across the network.
**Action:** Always append `&limit=1` to exact count queries like `?select=id&limit=1` to prevent fetching unnecessary rows when only the count is needed.
