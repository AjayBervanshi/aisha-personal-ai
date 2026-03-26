---
name: aisha-content-pipeline
description: How Aisha's content pipeline works — from job to video to YouTube/Instagram post
type: project
---

# Aisha Content Pipeline

## Full Flow

```
AntigravityAgent.enqueue_job()
        ↓
content_jobs table (status: queued)
        ↓
AntigravityAgent._process_loop()
        ↓
YouTubeCrew.kickoff(inputs)
  ├── ResearchAgent   → trending topics + hooks
  ├── ScriptAgent     → Hindi Devanagari script (EP continuity via SeriesTracker)
  ├── VisualAgent     → scene descriptions + thumbnail brief
  ├── SEOAgent        → title, description, tags, hashtags
  └── VoiceAgent      → ElevenLabs narration + image_engine thumbnails
        ↓
VideoEngine.render_video()  → MP4 with Ken Burns effect
        ↓
SocialMediaEngine.upload_youtube_video()   → YouTube Data API
SocialMediaEngine.post_instagram_reel()    → Meta Graph API
  └── _upload_to_storage() → Supabase Storage (content-videos bucket)
        ↓
SeriesTracker.save_episode()  → aisha_episodes table
content_jobs table (status: completed)
```

## Key Inputs for `enqueue_job()`

```python
{
    "topic": "Ek Raat Ki Kahani",      # empty = crew auto-researches
    "channel": "Story With Aisha",      # or "Riya's Dark Whisper", etc.
    "content_format": "Short/Reel",     # or "Long Form Episode"
    "platforms": ["youtube", "instagram"],
    "auto_post": True,                  # False = render only, no post
    "series_id": "uuid-here",          # optional — for episodic content
    "render_video": True,              # always True for full pipeline
}
```

## Channel → AI Provider Mapping

| Channel | AI Provider | Voice ID |
|---------|------------|---------|
| Story With Aisha | Gemini 2.5-flash | `wdymxIQkYn7MJCYCQF2Q` |
| Aisha & Him | Gemini 2.5-flash | `wdymxIQkYn7MJCYCQF2Q` |
| Riya's Dark Whisper | xAI Grok → Groq | `BpjGufoPiobT79j2vtj4` |
| Riya's Dark Romance | xAI Grok → Groq | `BpjGufoPiobT79j2vtj4` |

## Series/Episodic Content

Use `SeriesTracker` for multi-episode story arcs:

```python
from src.core.series_tracker import get_or_create_series, get_next_episode_number

series = get_or_create_series("Raat Ka Raaz", "Story With Aisha", total_episodes=5)
ep_num = get_next_episode_number(series["id"])
# Pass series_id to enqueue_job so ScriptAgent gets continuity context
```

## Autonomous Schedule (autonomous_loop.py)

- Every 4 hours: studio session for each channel
- 8 AM: morning checkin + content planning
- 3 AM: memory compression + DB cleanup
- 6 AM daily: token health check (TokenManager)
