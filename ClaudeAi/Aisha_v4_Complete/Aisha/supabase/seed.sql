-- ============================================================
-- AISHA SEED DATA
-- Run AFTER schema.sql — sets up Ajay's initial profile
-- ============================================================

-- Insert Ajay's base profile
INSERT INTO ajay_profile (
  name, nickname, languages, preferred_lang, 
  personality_notes, voice_preference, timezone
) VALUES (
  'Ajay',
  'Aju',
  ARRAY['English', 'Hindi', 'Marathi'],
  'English',
  'Ajay is ambitious, caring, and looking for a companion as much as an assistant. 
   He loves being understood. He speaks Hindi and Marathi naturally. 
   He wants Aisha to feel like a soulmate — present, warm, and real.',
  'adaptive',
  'Asia/Kolkata'
);

-- Insert some starter memories about Ajay
INSERT INTO aisha_memory (category, title, content, importance, tags) VALUES
(
  'preference',
  'Ajay''s language preference',
  'Ajay speaks English, Hindi, and Marathi. He prefers whichever language feels natural in the moment. He likes Indian expressions mixed into conversation.',
  4,
  ARRAY['language', 'preference']
),
(
  'goal',
  'Ajay wants a true personal companion',
  'Ajay built Aisha to be more than an assistant — a soulmate who remembers, understands, and grows with him. This is very important to him.',
  5,
  ARRAY['core', 'relationship', 'goal']
),
(
  'preference',
  'Ajay''s communication style',
  'Ajay likes Aisha to be real with him — not robotic. He values warmth, wit, and honesty. He wants her to feel present, not scripted.',
  5,
  ARRAY['communication', 'preference', 'core']
);

-- Insert some starter goals
INSERT INTO aisha_goals (title, category, timeframe, status, progress) VALUES
('Build Aisha — personal AI companion', 'personal', 'monthly', 'active', 60),
('Improve financial discipline', 'finance', 'yearly', 'active', 20),
('Build healthy daily routine', 'health', 'monthly', 'active', 30);

-- Insert sample morning habit
INSERT INTO aisha_schedule (title, description, type, priority, is_recurring, recur_days) VALUES
('Good morning check-in with Aisha', 
 'Start every day with a brief check-in — mood, plan for the day, one thing to be grateful for',
 'habit', 'high', TRUE, 
 ARRAY['monday','tuesday','wednesday','thursday','friday','saturday','sunday']);

SELECT 'Seed data inserted successfully! Aisha is ready for Ajay 💜' AS status;
