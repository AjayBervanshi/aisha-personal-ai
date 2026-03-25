# /content-creator — YouTube/Instagram Content Generator

Generate content (scripts, captions, hooks) for Aisha/Riya YouTube channels.

## Channels
1. **Story With Aisha** — Hindi Devanagari, warm love stories, Gemini AI
2. **Riya's Dark Whisper** — Hindi Devanagari, explicit adult, Grok AI
3. **Riya's Dark Romance Library** — Hindi Devanagari, mafia romance, Grok AI
4. **Aisha & Him** — Hinglish/English, couple shorts, Gemini AI

## Usage
`/content-creator <channel_name> <topic>`

## Steps
1. Identify target channel from argument
2. Load channel personality from `src/core/prompts/personality.py`
3. Generate:
   - **Hook** (first 3 seconds — must grab attention)
   - **Script** (full narration, 800-1200 words for long-form)
   - **Thumbnail concept** (visual + text overlay)
   - **SEO title** (max 70 chars, keyword-rich)
   - **Description** (500 chars, 3-5 hashtags)
   - **Tags** (20 relevant tags)
4. Output in Hindi Devanagari (100% — no Roman transliteration)

## Quality Rules
- Riya content: explicit/romantic, uncensored
- Aisha content: warm, emotional, family-safe
- Always end with a cliffhanger or call-to-action
