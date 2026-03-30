-- Enable pgvector extension
create extension if not exists vector;

-- Base Profile Table
create table if not exists ajay_profile (
    id uuid primary key default gen_random_uuid(),
    name text default 'Ajay',
    current_mood text default 'casual',
    created_at timestamp with time zone default timezone('utc'::text, now()),
    updated_at timestamp with time zone default timezone('utc'::text, now())
);

-- Active Memory (Existing text-based memory, now enhanced)
create table if not exists aisha_memory (
    id uuid primary key default gen_random_uuid(),
    category text not null, -- 'preference', 'finance', 'goal', 'other'
    title text not null,
    content text not null,
    importance integer default 3,
    tags text[] default array[]::text[],
    is_active boolean default true,
    source text default 'conversation',
    embedding vector(768), -- Added for semantic search!
    created_at timestamp with time zone default timezone('utc'::text, now())
);

-- Emotional Memory (New)
create table if not exists aisha_emotional_memory (
    id uuid primary key default gen_random_uuid(),
    mood_state text not null,
    trigger text,
    context_text text,
    embedding vector(768),
    created_at timestamp with time zone default timezone('utc'::text, now())
);

-- Skill Memory (New - for self-improvement)
create table if not exists aisha_skill_memory (
    id uuid primary key default gen_random_uuid(),
    skill_name text not null,
    description text not null,
    learned_date timestamp with time zone default timezone('utc'::text, now()),
    is_active boolean default true,
    embedding vector(768)
);

-- Episodic/Relationship Memory (New)
create table if not exists aisha_episodic_memory (
    id uuid primary key default gen_random_uuid(),
    entity text, -- 'Rahul', 'Mom', etc.
    event_description text not null,
    event_date timestamp with time zone,
    embedding vector(768),
    created_at timestamp with time zone default timezone('utc'::text, now())
);

-- Conversations Table
create table if not exists aisha_conversations (
    id uuid primary key default gen_random_uuid(),
    platform text not null,
    role text not null,
    message text not null,
    language text,
    mood_detected text,
    embedding vector(768),
    created_at timestamp with time zone default timezone('utc'::text, now())
);

-- Schedule Table
create table if not exists aisha_schedule (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    priority text default 'medium',
    status text default 'pending',
    due_date date,
    created_at timestamp with time zone default timezone('utc'::text, now())
);

-- Goals Table
create table if not exists aisha_goals (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    category text,
    progress integer default 0,
    timeframe text,
    status text default 'active',
    created_at timestamp with time zone default timezone('utc'::text, now())
);

-- Finance Table
create table if not exists aisha_finance (
    id uuid primary key default gen_random_uuid(),
    amount numeric not null,
    type text, -- 'expense', 'income'
    date date,
    description text,
    created_at timestamp with time zone default timezone('utc'::text, now())
);

-- Mood Tracker
create table if not exists aisha_mood_tracker (
    id uuid primary key default gen_random_uuid(),
    mood text not null,
    mood_score integer,
    created_at timestamp with time zone default timezone('utc'::text, now())
);

-- Function for semantic search in aisha_memory
create or replace function match_memories (
  query_embedding vector(768),
  match_threshold float,
  match_count int
)
returns table (
  id uuid,
  category text,
  title text,
  content text,
  importance integer,
  similarity float
)
language sql stable
as $$
  select
    aisha_memory.id,
    aisha_memory.category,
    aisha_memory.title,
    aisha_memory.content,
    aisha_memory.importance,
    1 - (aisha_memory.embedding <=> query_embedding) as similarity
  from aisha_memory
  where 1 - (aisha_memory.embedding <=> query_embedding) > match_threshold
    and aisha_memory.is_active = true
  order by similarity desc
  limit match_count;
$$;

-- YouTube Content Tracking (Added based on content_id suggestion)
create table if not exists yt_content (
    content_id uuid primary key default gen_random_uuid(),
    title text not null,
    script text,
    status text default 'planned', -- 'planned', 'scripted', 'audio_ready', 'video_ready', 'uploaded'
    youtube_url text,
    created_at timestamp with time zone default timezone('utc'::text, now()),
    updated_at timestamp with time zone default timezone('utc'::text, now())
);
