## 2024-05-24 - Single Query Updates Over `.in_()` Batching
 **Learning:** While `.in_()` batching is better than N+1 queries, single conditional updates (e.g. `.update().eq()`) are superior for simple conditional state updates as they eliminate the initial `.select()` completely. Supabase automatically returns updated rows by default in `.data`.
 **Action:** Refactored `_startup_recovery` in `src/core/autonomous_loop.py` to use a single conditional update query.
