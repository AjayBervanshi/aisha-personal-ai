
-- Enable vector extension for semantic memory search
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- TABLE 1: ajay_profile
-- ============================================================
CREATE TABLE IF NOT EXISTS ajay_profile (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name            TEXT NOT NULL DEFAULT 'Ajay',
  nickname        TEXT DEFAULT 'Aju',
  languages       TEXT[] DEFAULT ARRAY['English', 'Hindi', 'Marathi'],
  preferred_lang  TEXT DEFAULT 'English',
  personality_notes TEXT,
  current_mood    TEXT DEFAULT 'neutral',
  voice_preference TEXT DEFAULT 'adaptive',
  timezone        TEXT DEFAULT 'Asia/Kolkata',
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE 2: aisha_memory
-- ============================================================
CREATE TABLE IF NOT EXISTS aisha_memory (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  category    TEXT NOT NULL CHECK (category IN (
                'mood', 'goal', 'finance', 'schedule', 
                'preference', 'relationship', 'health', 
                'achievement', 'fear', 'dream', 'general'
              )),
  title       TEXT NOT NULL,
  content     TEXT NOT NULL,
  importance  INT DEFAULT 3 CHECK (importance BETWEEN 1 AND 5),
  is_active   BOOLEAN DEFAULT TRUE,
  embedding   vector(768),
  tags        TEXT[],
  source      TEXT DEFAULT 'conversation',
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE 3: aisha_journal
-- ============================================================
CREATE TABLE IF NOT EXISTS aisha_journal (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  entry       TEXT NOT NULL,
  mood        TEXT,
  mood_score  INT CHECK (mood_score BETWEEN 1 AND 10),
  tags        TEXT[],
  aisha_note  TEXT,
  date        DATE DEFAULT CURRENT_DATE,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE 4: aisha_finance
-- ============================================================
CREATE TABLE IF NOT EXISTS aisha_finance (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  type        TEXT NOT NULL CHECK (type IN ('expense', 'income', 'goal', 'saving')),
  amount      NUMERIC(12, 2) NOT NULL,
  currency    TEXT DEFAULT 'INR',
  category    TEXT,
  description TEXT NOT NULL,
  is_recurring BOOLEAN DEFAULT FALSE,
  recur_freq  TEXT,
  goal_target NUMERIC(12, 2),
  goal_by     DATE,
  date        DATE DEFAULT CURRENT_DATE,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE 5: aisha_schedule
-- ============================================================
CREATE TABLE IF NOT EXISTS aisha_schedule (
  id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  title         TEXT NOT NULL,
  description   TEXT,
  type          TEXT DEFAULT 'task' CHECK (type IN ('task', 'reminder', 'event', 'habit')),
  priority      TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
  status        TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'done', 'missed', 'snoozed')),
  due_date      DATE,
  due_time      TIME,
  is_recurring  BOOLEAN DEFAULT FALSE,
  recur_days    TEXT[],
  reminder_sent BOOLEAN DEFAULT FALSE,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE 6: aisha_conversations
-- ============================================================
CREATE TABLE IF NOT EXISTS aisha_conversations (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  platform    TEXT DEFAULT 'web' CHECK (platform IN ('web', 'telegram', 'voice')),
  role        TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  message     TEXT NOT NULL,
  language    TEXT DEFAULT 'English',
  mood_detected TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE 7: aisha_mood_tracker
-- ============================================================
CREATE TABLE IF NOT EXISTS aisha_mood_tracker (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  mood        TEXT NOT NULL,
  mood_score  INT CHECK (mood_score BETWEEN 1 AND 10),
  notes       TEXT,
  triggers    TEXT[],
  date        DATE DEFAULT CURRENT_DATE,
  time_of_day TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE 8: aisha_goals
-- ============================================================
CREATE TABLE IF NOT EXISTS aisha_goals (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  title       TEXT NOT NULL,
  description TEXT,
  category    TEXT CHECK (category IN (
                'career', 'finance', 'health', 'relationship', 
                'personal', 'learning', 'travel', 'other'
              )),
  timeframe   TEXT CHECK (timeframe IN ('daily', 'weekly', 'monthly', 'yearly', 'life')),
  status      TEXT DEFAULT 'active' CHECK (status IN ('active', 'achieved', 'abandoned', 'paused')),
  progress    INT DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
  target_date DATE,
  achieved_at TIMESTAMPTZ,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- RLS
-- ============================================================
ALTER TABLE ajay_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE aisha_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE aisha_journal ENABLE ROW LEVEL SECURITY;
ALTER TABLE aisha_finance ENABLE ROW LEVEL SECURITY;
ALTER TABLE aisha_schedule ENABLE ROW LEVEL SECURITY;
ALTER TABLE aisha_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE aisha_mood_tracker ENABLE ROW LEVEL SECURITY;
ALTER TABLE aisha_goals ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Full access" ON ajay_profile FOR ALL USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "Full access" ON aisha_memory FOR ALL USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "Full access" ON aisha_journal FOR ALL USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "Full access" ON aisha_finance FOR ALL USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "Full access" ON aisha_schedule FOR ALL USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "Full access" ON aisha_conversations FOR ALL USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "Full access" ON aisha_mood_tracker FOR ALL USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "Full access" ON aisha_goals FOR ALL USING (TRUE) WITH CHECK (TRUE);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX idx_memory_category ON aisha_memory(category);
CREATE INDEX idx_memory_importance ON aisha_memory(importance DESC);
CREATE INDEX idx_memory_active ON aisha_memory(is_active);
CREATE INDEX idx_finance_date ON aisha_finance(date DESC);
CREATE INDEX idx_finance_type ON aisha_finance(type);
CREATE INDEX idx_schedule_due ON aisha_schedule(due_date);
CREATE INDEX idx_schedule_status ON aisha_schedule(status);
CREATE INDEX idx_conversations_created ON aisha_conversations(created_at DESC);
CREATE INDEX idx_mood_date ON aisha_mood_tracker(date DESC);
CREATE INDEX idx_goals_status ON aisha_goals(status);

-- ============================================================
-- Enable realtime for conversations
-- ============================================================
ALTER PUBLICATION supabase_realtime ADD TABLE public.aisha_conversations;

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Get Aisha's full context for a conversation
CREATE OR REPLACE FUNCTION get_aisha_context()
RETURNS TEXT AS $$
DECLARE
  context TEXT := '';
  profile_row ajay_profile%ROWTYPE;
BEGIN
  SELECT * INTO profile_row FROM ajay_profile LIMIT 1;
  
  context := context || '=== AJAY PROFILE ===' || chr(10);
  context := context || 'Name: ' || profile_row.name || chr(10);
  context := context || 'Current Mood: ' || COALESCE(profile_row.current_mood, 'unknown') || chr(10);
  context := context || 'Preferred Language: ' || COALESCE(profile_row.preferred_lang, 'English') || chr(10);
  context := context || chr(10);
  
  context := context || '=== KEY MEMORIES ===' || chr(10);
  SELECT context || COALESCE(string_agg(
    '[' || category || '] ' || title || ': ' || content, chr(10)
  ), 'No memories yet.')
  INTO context
  FROM (
    SELECT category, title, content 
    FROM aisha_memory 
    WHERE is_active = TRUE 
    ORDER BY importance DESC 
    LIMIT 10
  ) m;
  
  context := context || chr(10) || '=== TODAY TASKS ===' || chr(10);
  SELECT context || COALESCE(string_agg(
    '- [' || priority || '] ' || title, chr(10)
  ), 'No tasks today.')
  INTO context
  FROM (
    SELECT priority, title
    FROM aisha_schedule
    WHERE due_date = CURRENT_DATE AND status = 'pending'
    ORDER BY 
      CASE priority WHEN 'urgent' THEN 1 WHEN 'high' THEN 2 
                    WHEN 'medium' THEN 3 ELSE 4 END
  ) t;
  
  RETURN context;
END;
$$ LANGUAGE plpgsql;

-- Cleanup old conversations
CREATE OR REPLACE FUNCTION cleanup_old_conversations()
RETURNS void AS $$
BEGIN
  DELETE FROM aisha_conversations 
  WHERE created_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- TRIGGERS
-- ============================================================
CREATE TRIGGER update_profile_updated_at
  BEFORE UPDATE ON ajay_profile
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_memory_updated_at
  BEFORE UPDATE ON aisha_memory
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_schedule_updated_at
  BEFORE UPDATE ON aisha_schedule
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_goals_updated_at
  BEFORE UPDATE ON aisha_goals
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- VIEWS
-- ============================================================
CREATE OR REPLACE VIEW today_summary AS
SELECT
  (SELECT COUNT(*) FROM aisha_schedule 
   WHERE due_date = CURRENT_DATE AND status = 'pending') AS pending_tasks,
  (SELECT COUNT(*) FROM aisha_schedule 
   WHERE due_date = CURRENT_DATE AND status = 'done') AS completed_tasks,
  (SELECT COALESCE(SUM(amount), 0) FROM aisha_finance 
   WHERE type = 'expense' AND date = CURRENT_DATE) AS todays_spending,
  (SELECT mood FROM aisha_mood_tracker 
   ORDER BY created_at DESC LIMIT 1) AS last_mood,
  (SELECT COUNT(*) FROM aisha_goals 
   WHERE status = 'active') AS active_goals;

CREATE OR REPLACE VIEW monthly_finance AS
SELECT
  DATE_TRUNC('month', date) AS month,
  SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) AS total_income,
  SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) AS total_expense,
  SUM(CASE WHEN type = 'saving' THEN amount ELSE 0 END) AS total_saved,
  COUNT(CASE WHEN type = 'expense' THEN 1 END) AS expense_count
FROM aisha_finance
GROUP BY DATE_TRUNC('month', date)
ORDER BY month DESC;

CREATE OR REPLACE VIEW top_memories AS
SELECT id, category, title, content, importance, tags, created_at
FROM aisha_memory
WHERE is_active = TRUE
ORDER BY importance DESC, updated_at DESC
LIMIT 20;

-- ============================================================
-- TABLE COMMENTS
-- ============================================================
COMMENT ON TABLE ajay_profile IS 'Core profile and preferences for Ajay';
COMMENT ON TABLE aisha_memory IS 'Long-term memory store for Aisha';
COMMENT ON TABLE aisha_journal IS 'Personal journal entries by Ajay via Aisha';
COMMENT ON TABLE aisha_finance IS 'Financial transactions, goals, and savings';
COMMENT ON TABLE aisha_schedule IS 'Tasks, reminders, events, and habits';
COMMENT ON TABLE aisha_conversations IS 'Recent conversation history (30 day rolling)';
COMMENT ON TABLE aisha_mood_tracker IS 'Daily emotional wellbeing tracking';
COMMENT ON TABLE aisha_goals IS 'Short and long-term goals with progress tracking';
