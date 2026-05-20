## 2024-03-22 - [Supabase Count Limit]
**Learning:** Supabase / PostgREST queries that calculate a count WITHOUT limiting rows returned will download all rows, leading to an O(N) performance bottleneck.
**Action:** When querying Supabase for a row count, always append `.limit(1)` to `.select('...', count='exact')` to prevent an O(N) PostgREST bottleneck. Extract the integer count directly from the `.count` attribute of the response object (e.g., `response.count`), rather than fetching all rows to compute `len(data)`.

## 2024-03-22 - [Supabase Existence vs Count]
**Learning:** Using `count="exact"` causes PostgREST to execute a full table scan. If the goal is merely to check if *any* matching row exists, `count="exact"` is unnecessarily expensive.
**Action:** For simple boolean existence checks, omit the `count` header. Instead, use `.select('id').limit(1)` and check `if data and len(data) > 0:`. Only use `count="exact"` with `.limit(1)` when the actual scalar count value is required.
