## 2026-03-29 - Optimize notification_engine row count retrieval
**Learning:** Found N+1 inefficiency where pulling row counts used full `.select()` and `len()`. Supabase `.select("id", count="exact").limit(1)` + `.count` fixes this to avoid overhead.
**Action:** Replaced full selects in `NotificationEngine._build_daily_context()` with exact count limits, bypassing network delay in count retrieval.
