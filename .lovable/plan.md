

## Plan: Create Shared Database Schema in Lovable Cloud

### Context
Your project has a Python backend (Telegram bot) and a vanilla HTML/JS web frontend. The database schema defined in `supabase/schema.sql` needs to be created in Lovable Cloud so both platforms can share the same data. Currently, no tables exist in the Cloud database.

### What We'll Do

**Step 1: Create all 8 tables via database migration**

Recreate the full schema from `schema.sql` in Lovable Cloud:
- `ajay_profile` — Ajay's identity and preferences
- `aisha_memory` — Long-term memory store (with vector embedding support)
- `aisha_journal` — Personal journal entries
- `aisha_finance` — Financial tracking
- `aisha_schedule` — Tasks, reminders, habits
- `aisha_conversations` — Chat history (30-day rolling)
- `aisha_mood_tracker` — Emotional wellbeing tracking
- `aisha_goals` — Short/long-term goals with progress

**Step 2: Create database views**
- `today_summary` — Morning briefing data
- `monthly_finance` — Monthly income/expense summary
- `top_memories` — High-importance active memories

**Step 3: Create functions and triggers**
- `get_aisha_context()` — Builds full context string for AI conversations
- `update_updated_at_column()` — Auto-updates timestamps
- `cleanup_old_conversations()` — Deletes conversations older than 30 days
- Triggers on `ajay_profile`, `aisha_memory`, `aisha_schedule`, `aisha_goals`

**Step 4: Set up RLS policies**

All tables get RLS enabled with policies allowing:
- **Anon/authenticated full access** — since this is a personal AI (single user, no multi-tenancy), and the Python backend uses the service role key
- Policies mirror the existing `schema.sql` approach ("Service role full access" with `USING (TRUE)`)

**Step 5: Create indexes for performance**

All indexes from the original schema for fast queries on categories, dates, statuses, etc.

**Step 6: Seed initial data**

Insert Ajay's base profile, starter memories, goals, and morning habit from `seed.sql`.

**Step 7: Update the web frontend to use Lovable Cloud**

Modify `index.html` to:
- Replace the hardcoded `YOUR_SUPABASE_URL` / `YOUR_SUPABASE_ANON_KEY` placeholders with the actual Lovable Cloud credentials
- Store conversations to `aisha_conversations` table after each message
- Load recent conversation history on page load
- Route AI calls through a new edge function (instead of direct Gemini API key exposure in the frontend)

**Step 8: Create a `chat` edge function**

A backend function that:
- Loads Aisha's context from the database (profile, memories, today's tasks)
- Calls Lovable AI (Gemini) with full personality and memory context
- Stores the conversation in `aisha_conversations`
- Returns the AI response (streaming)

### What Won't Change
- Your Python backend code stays untouched
- Telegram bot continues working as-is
- The existing `schema.sql` file remains for reference
- All table structures match exactly what your Python `memory_manager.py` expects

### Technical Note
The `vector(768)` extension for semantic memory search will be enabled. Your Python backend's existing Supabase connection will work with the same tables once you point it to the Lovable Cloud database URL.

