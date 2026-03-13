-- ============================================================
-- Migration: channel_prompts
-- Created: 2026-03-13
-- Purpose: Store per-channel YouTube identity prompts, voice IDs,
--          and AI provider routing — queryable by the edge function
--          without a code deploy when channels evolve.
-- ============================================================

create table if not exists channel_prompts (
  id              uuid        primary key default gen_random_uuid(),
  channel_name    text        not null unique,
  identity_prompt text        not null,
  voice_id        text        not null,
  ai_provider     text        not null default 'gemini',
  narrator        text        not null,
  is_active       boolean     not null default true,
  updated_at      timestamptz not null default now()
);

-- Auto-update timestamp on any row change
create or replace function set_channel_prompts_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_channel_prompts_updated_at on channel_prompts;
create trigger trg_channel_prompts_updated_at
  before update on channel_prompts
  for each row execute function set_channel_prompts_updated_at();

-- RLS — service role has full access, anon can read active channels
alter table channel_prompts enable row level security;

drop policy if exists "Service full access channel_prompts" on channel_prompts;
create policy "Service full access channel_prompts"
  on channel_prompts for all
  using (true) with check (true);

-- ── Seed Data ──────────────────────────────────────────────

insert into channel_prompts
  (channel_name, identity_prompt, voice_id, ai_provider, narrator)
values
  (
    'Story With Aisha',
    '100% देवनागरी हिंदी केवल। आयशा — पहली व्यक्ति में भावुक प्रेम कहानियाँ। संरचना: इंट्रो (४-५ लाइन) → ८-१२ भाग (३५०-४५० शब्द/भाग) → आउट्रो। सूक्ष्म रोमांस — कोई explicit content नहीं। पहले trending love story angles research करो (office romance, college love, long-distance, rain moments)। हर कहानी पूरी तरह नई — नया नाम, नई लोकेशन।',
    'wdymxIQkYn7MJCYCQF2Q',
    'gemini',
    'Aisha'
  ),
  (
    'Riya''s Dark Whisper',
    '100% देवनागरी हिंदी केवल। रिया — २३ साल, फ्रीलांस ग्राफिक डिजाइनर, मुंबई, bold, voluptuous। सविता भाभी स्टाइल: explicit sex scenes, dark romance, psychological tension। Single story format, 900-1400 words, natural Devanagari subheadings। TTS-friendly: short sentences, "..." pauses। पहले trending erotic/adult story angles research करो। हमेशा xAI Grok use करो।',
    'BpjGufoPiobT79j2vtj4',
    'xai',
    'Riya'
  ),
  (
    'Riya''s Dark Romance Library',
    '100% देवनागरी हिंदी केवल। रिया — narrator और main character। माफिया रोमांस, enemies-to-lovers, possessive alpha hero, morally grey characters। Novel-style chapter episodes, 15-25 minute reading length। Intense, addictive, dramatic opening in a dangerous emotional moment। xAI Grok use करो।',
    'BpjGufoPiobT79j2vtj4',
    'xai',
    'Riya'
  ),
  (
    'Aisha & Him',
    'Aisha — relatable, fun, sweet narrator of everyday couple moments. Format: Short reel/shorts, 30s-3 min dialogue-style. Themes: cute fights, jealousy, good morning texts, late night calls, teasing. Language: Hinglish or English. Hook: start mid-conversation in a relatable couple moment. Research trending couple-scenario reels on Instagram/YouTube Shorts.',
    'wdymxIQkYn7MJCYCQF2Q',
    'gemini',
    'Aisha'
  )
on conflict (channel_name) do update
  set identity_prompt = excluded.identity_prompt,
      voice_id        = excluded.voice_id,
      ai_provider     = excluded.ai_provider,
      narrator        = excluded.narrator,
      updated_at      = now();
