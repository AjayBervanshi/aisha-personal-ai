## 2026-03-31 - Supabase O(N) Network Count Overhead
**Learning:** In PostgREST/Supabase, calculating row counts by selecting IDs (`.select("id")`) and calling `len()` in Python triggers significant memory and network overhead as tables scale, as it requires downloading thousands of rows.
**Action:** When querying only to ascertain total record volume, always use `.select("id", count="exact").limit(1)` and parse the `.count` attribute. This delegates counting exclusively to the Postgres engine in O(1) network transfer.
