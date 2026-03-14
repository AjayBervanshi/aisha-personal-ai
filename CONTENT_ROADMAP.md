# AISHA CONTENT CREATION ROADMAP
## From Zero → YouTube Monetized + Instagram Active
### Created: 2026-03-14

---

## CURRENT STATE

```
Infrastructure:  ✅ READY
AI Brain:        ✅ Groq (primary) + Gemini 4-model fallback
TTS Voices:      ✅ Aisha (ElevenLabs wdymxIQkYn7MJCYCQF2Q)
                 ✅ Riya  (ElevenLabs BpjGufoPiobT79j2vtj4)
Supabase DB:     ✅ 15 tables live
Edge Functions:  ✅ chat + telegram-bot deployed
GitHub:          ✅ Pushed → Lovable auto-deploys
Telegram Bot:    ✅ @AishaAIforAjay_Bot (webhook active)

Missing (blocking content):
  ❌ HuggingFace key (scene images for video thumbnails)
  ❌ YouTube OAuth (upload videos)
  ❌ YouTube Data API key (trend research)
  ❌ Instagram Business token (auto-post reels)
  ❌ xAI/Grok credits (Riya's Dark Whisper channel needs Grok)
```

---

## PHASE 1 — UNBLOCK CONTENT (This Week)

### Step 1.1: Get Missing API Keys (30 min, manual)

| Key | Where to get | Priority |
|-----|-------------|----------|
| HuggingFace | huggingface.co/settings/tokens → New token (Read) | HIGH |
| YouTube Data API | console.cloud.google.com → YouTube Data API v3 → Create key | HIGH |
| YouTube OAuth | Same GCP project → OAuth 2.0 → Desktop app creds | HIGH |
| xAI credits | x.ai/api → Add payment method ($5 min) | MEDIUM |
| Instagram token | developers.facebook.com → Instagram Basic Display | LOW |

### Step 1.2: Run YouTube OAuth Setup (10 min)
```bash
cd E:/VSCode/Aisha
python scripts/setup_youtube_oauth.py
# Browser opens → sign in → grants upload permission
# Saves token to config/youtube_token.json
```

### Step 1.3: Test Full Pipeline (5 min)
```bash
python -c "
from src.agents.youtube_crew import YouTubeCrew
crew = YouTubeCrew()
result = crew.kickoff({
    'channel': 'Story With Aisha',
    'topic': 'Pehli Mulaqat - Ek Anjanee Si Shakhs Ki Kahaani',
    'render_video': False  # test without video render first
})
print(result)
"
```

---

## PHASE 2 — FIRST CONTENT DROP (Days 3-5)

### Channel Priority Order:
1. **Story With Aisha** (safest, family-friendly, fast to monetize)
2. **Aisha & Him** (Hinglish shorts, virality potential)
3. **Riya's Dark Whisper** (adult, needs xAI credits first)
4. **Riya's Dark Romance Library** (long-form, complex)

### Story With Aisha — First 10 Videos Plan:

| # | Title (Hindi) | Angle | Length |
|---|--------------|-------|--------|
| 1 | पहली मुलाक़ात | First meeting on a rainy evening | 8 min |
| 2 | दूर से प्यार | Long distance love letters | 10 min |
| 3 | वो आख़िरी बात | Last conversation before goodbye | 9 min |
| 4 | तुम्हारी याद में | Missing someone at 3AM | 8 min |
| 5 | एक अधूरी कहानी | Love that never got a chance | 11 min |
| 6 | सपनों का शहर | Strangers in Mumbai who fall in love | 9 min |
| 7 | बारिश और तुम | Monsoon romance | 8 min |
| 8 | वापस आ जाओ | She waits, he never returns | 10 min |
| 9 | नई शुरुआत | Moving on after heartbreak | 9 min |
| 10 | हमेशा के लिए | Forever — a wedding night story | 12 min |

### Upload Schedule: 1 video every 2 days

---

## PHASE 3 — AUTOMATION LOOP (Week 2-3)

### The Full Automated Pipeline:
```
Every day at 8AM IST (AutonomousLoop):
  1. TrendEngine.research('Story With Aisha') → trending topics
  2. YouTubeCrew.kickoff(topic) → script + SEO + voice
  3. VideoEngine.render() → MP4 with Ken Burns effect
  4. SocialMediaEngine.upload_youtube() → publish
  5. SocialMediaEngine.post_instagram_reel() → 60s clip
  6. GmailEngine.send_report() → email Ajay with stats
  7. AnalyticsEngine.pull() → track performance
```

### Files to activate:
- `src/core/autonomous_loop.py` — already built, needs `schedule` start
- `src/agents/youtube_crew.py` — needs render_video=True
- `src/core/video_engine.py` — needs HuggingFace key for thumbnails
- `src/core/social_media_engine.py` — needs YouTube + Instagram tokens

---

## PHASE 4 — MONETIZATION MILESTONES

### YouTube Monetization Requirements:
- 1,000 subscribers
- 4,000 watch hours (last 12 months)
- No community guideline strikes

### Estimated Timeline (Story With Aisha):
```
Week 1-2:   10 videos uploaded, SEO optimized
Week 3-4:   100+ subscribers (organic Hindi audience)
Month 2:    500+ subscribers, trending story reaches 10K views
Month 3:    1,000 subscribers → Apply for monetization
Month 4:    Monetization approved → First revenue
Month 6:    4,000 watch hours → Full YPP membership
```

### Revenue Projections (conservative):
```
Month 4:    ₹500-2,000/month (early monetization)
Month 6:    ₹2,000-8,000/month (2K subs, 4K hours)
Month 9:    ₹8,000-25,000/month (5K subs, consistent uploads)
Month 12:   ₹25,000-60,000/month (10K subs, all 4 channels)
```

### Additional Revenue Streams:
- Instagram Reels bonus (1M+ views needed)
- Brand deals (Hindi story niche pays well)
- Sponsored stories for regional brands

---

## PHASE 5 — SCALE (Month 3+)

### All 4 Channels Running:
```
Story With Aisha     → 1 video/day, Gemini, Aisha voice
Aisha & Him          → 2 shorts/day, Gemini, Aisha voice
Riya's Dark Whisper  → 3 videos/week, Grok (xAI), Riya voice
Riya's Romance Lib   → 2 videos/week, Grok (xAI), Riya voice
```

### Autonomous 24/7 Loop (AutonomousLoop):
```python
# Already built in src/core/autonomous_loop.py
# Just need to start it:
python -m src.core.autonomous_loop
```

---

## IMMEDIATE NEXT ACTIONS (TODAY)

```
Priority 1 (blocking everything):
  → Get real HuggingFace API key from huggingface.co/settings/tokens
  → Get YouTube Data API key from Google Cloud Console
  → Set up YouTube OAuth (python scripts/setup_youtube_oauth.py)

Priority 2 (starts production):
  → Test full pipeline: python -c "from src.agents.youtube_crew import..."
  → Upload first video manually to verify quality
  → Check thumbnail generation works

Priority 3 (scaling):
  → Add xAI credits ($5) → unlocks Riya channels
  → Set up Instagram Business token
  → Start autonomous_loop.py as a background service
```

---

## KEY FILES REFERENCE

| File | Purpose | Status |
|------|---------|--------|
| `src/agents/youtube_crew.py` | 5-agent content pipeline | ✅ Built |
| `src/core/video_engine.py` | Voice+images → MP4 | ✅ Built |
| `src/core/trend_engine.py` | Google Trends research | ✅ Built |
| `src/core/analytics_engine.py` | YouTube analytics | ✅ Built |
| `src/core/social_media_engine.py` | Upload to YouTube/Instagram | ✅ Built |
| `src/core/autonomous_loop.py` | 24/7 scheduler | ✅ Built |
| `src/core/voice_engine.py` | Aisha+Riya TTS | ✅ Working |
| `scripts/setup_youtube_oauth.py` | OAuth setup wizard | ✅ Built |
| `scripts/setup_instagram_token.py` | Instagram token guide | ✅ Built |

**Everything is built. Only missing: API keys to activate it.**
