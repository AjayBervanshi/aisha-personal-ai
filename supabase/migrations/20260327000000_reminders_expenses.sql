-- Migration: Create aisha_reminders and aisha_expenses tables
-- Applied: 2026-03-27

CREATE TABLE IF NOT EXISTS aisha_reminders (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id BIGINT,
  title TEXT NOT NULL,
  message TEXT,
  remind_at TIMESTAMPTZ NOT NULL,
  recurrence TEXT DEFAULT 'once' CHECK (recurrence IN ('once','daily','weekly','monthly')),
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending','sent','cancelled')),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_reminders_remind_at ON aisha_reminders(remind_at, status);

CREATE TABLE IF NOT EXISTS aisha_expenses (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  amount NUMERIC(12,2) NOT NULL,
  category TEXT DEFAULT 'misc',
  description TEXT NOT NULL,
  currency TEXT DEFAULT 'INR',
  paid_via TEXT,
  notes TEXT,
  expense_date DATE DEFAULT CURRENT_DATE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_expenses_date ON aisha_expenses(expense_date DESC);
