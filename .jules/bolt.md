## 2026-04-02 - [Optimize get_top_performing_topics query]
 **Learning:** In Supabase, retrieving records from a table based on a value in a related table (foreign key) can be done with a single database roundtrip using an inner join via `select('..., related_table!inner(column)')` and `.eq('related_table.column', value)` instead of fetching IDs first and then using an `in_()` filter.
 **Action:** Refactored `get_top_performing_topics` in `src/core/performance_tracker.py` to use a single inner join query, eliminating an extra query round-trip.
