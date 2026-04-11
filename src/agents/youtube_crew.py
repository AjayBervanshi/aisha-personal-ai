"""
youtube_crew.py
==============
Aisha's YouTube Content Production Engine.
Handles all channels with unique identity and generates core assets.
"""

import os
import logging
from src.core.ai_router import AIRouter
from src.core.voice_engine import generate_voice
from src.core.image_engine import generate_image
from src.core.video_engine import render_video, VideoSettings
from src.core.trend_engine import get_trends_for_channel
from src.core.prompts.personality import CHANNEL_PROMPTS
from src.core.config import CHANNEL_VOICE_IDS
from src.core.series_tracker import get_continuity_context

log = logging.getLogger(__name__)

CHANNEL_IDENTITY = {
    "Story With Aisha": {
        "narrator": "Aisha",
        "tone": "warm, emotional, cinematic, heart-touching",
        "themes": "office romance, college love, long-distance, heartbreak, reunion",
        "format_hint": "8-15 minute audio storytelling with emotional dialogue",
        "hook_style": "Start with a single emotional sentence that instantly pulls attention.",
        "voice_style": "Soft, warm, expressive",
    },
    "Riya's Dark Whisper": {
        "narrator": "Riya",
        "tone": "mysterious, seductive, psychological, slow-burn",
        "themes": "forbidden love, obsession, betrayal, secret desires, dark relationships",
        "format_hint": "10-20 minute slow-build suspense story",
        "hook_style": "Open with forbidden truth and immediate tension.",
        "voice_style": "Deep, slow, whispering",
    },
    "Riya's Dark Romance Library": {
        "narrator": "Riya",
        "tone": "intense, addictive, dramatic, novel-style",
        "themes": "mafia romance, enemies to lovers, possessive alpha male, morally grey characters",
        "format_hint": "15-25 minute chapter-style story episode",
        "hook_style": "Drop directly into a dangerous emotional moment.",
        "voice_style": "Commanding and intense",
    },
    "Aisha & Him": {
        "narrator": "Aisha",
        "tone": "relatable, funny, sweet, real, everyday couple",
        "themes": "cute fights, jealousy, good morning texts, late night talks, teasing",
        "format_hint": "30 second to 3 minute dialogue-format short/reel",
        "hook_style": "Open mid-conversation in a relatable couple moment.",
        "voice_style": "Casual, playful, real",
    },
}


class YouTubeCrew:
    def __init__(self):
        self.ai = AIRouter()
        self.results = {}

    def _generate(self, prompt: str, preferred_provider: str = None, nvidia_task_type: str = "writing") -> str:
        if preferred_provider:
            try:
                result = self.ai._call_provider(
                    preferred_provider,
                    "You are an expert content creator for YouTube and Instagram storytelling channels.",
                    prompt,
                    [],
                    None,
                    nvidia_task_type=nvidia_task_type,
                )
                return result.strip()
            except Exception as e:
                log.warning(f"youtube_crew error: {e}")

        result = self.ai.generate(
            system_prompt="You are an expert content creator for YouTube and Instagram storytelling channels.",
            user_message=prompt,
            nvidia_task_type=nvidia_task_type,
        )
        return result.text.strip()

    def kickoff(self, inputs: dict) -> str:
        channel = inputs.get("channel", "Story With Aisha")
        fmt = inputs.get("format", "Long Form")
        master_prompt = inputs.get("master_prompt", "")
        render_mp4 = inputs.get("render_video", False)  # Set True to also render MP4

        identity = CHANNEL_IDENTITY.get(channel, CHANNEL_IDENTITY["Story With Aisha"])

        from src.core.config import CHANNEL_AI_PROVIDER, CHANNEL_AI_TASK_TYPE

        preferred_ai = CHANNEL_AI_PROVIDER.get(channel, "gemini")
        nvidia_task = CHANNEL_AI_TASK_TYPE.get(channel, "writing")

        # Fetch real-time trends first — then use as topic if none given
        print("[TrendEngine] Fetching real-time trends...")
        trends = {}
        try:
            trends = get_trends_for_channel(channel)
        except Exception as e:
            print(f"[TrendEngine] Warning: trend fetch failed ({e}), using fallback")

        # Use trending topic if none provided, or enhance provided topic with trend data
        raw_topic = inputs.get("topic", "")
        if not raw_topic and trends.get("recommended_topic"):
            topic = trends["recommended_topic"]
            print(f"[TrendEngine] Auto-selected trending topic: {topic}")
        else:
            topic = raw_topic or "A Late Night Secret"

        # Append trend context to enrich research
        trend_context = ""
        if trends.get("viral_keywords"):
            trend_context = (
                f"\n\nCURRENT TREND DATA (real-time):\n"
                f"Viral keywords: {', '.join(trends.get('viral_keywords', []))}\n"
                f"Trending topics: {', '.join(trends.get('trending_topics', []))}\n"
                f"Top angles: {chr(10).join(trends.get('top_angles', []))}\n"
                f"Best hook idea: {trends.get('hook_idea', '')}\n"
            )

        print(f"[Crew] {channel} | {topic} | AI: {preferred_ai.upper()}")

        # Use full channel identity prompt → minimal fallback
        channel_context = (
            master_prompt
            or CHANNEL_PROMPTS.get(channel)
            or (
                f"Channel: {channel}\n"
                f"Tone: {identity['tone']}\n"
                f"Themes: {identity['themes']}\n"
                f"Format: {identity['format_hint']}\n"
                f"Hook style: {identity['hook_style']}\n"
                f"Voice: {identity['voice_style']}"
            )
        )

        print("[Riya] Researching trending angles + story brief...")
        self.results["research"] = self._generate(
            f"""You are Riya, the Story Researcher.
{channel_context}
Topic: {topic}
{trend_context}

STEP 1 — TREND ANALYSIS:
Using the real-time trend data above (if available), identify the single most viral story angle right now for the '{channel}' niche. Consider: titles with high CTR patterns, emotional hooks driving comments, trending tropes in Hindi storytelling channels, popular scenarios in this category.

STEP 2 — STORY BRIEF (using the top trending angle):
- Character names + quick backstory (fresh, never reused)
- Core conflict (what creates the tension/desire)
- Emotional/sensory hook (why viewers will stop scrolling for this)
- Viral potential reasoning (why this gets clicks and watch time)

Output: 300 words max. Be specific and concrete.""",
            preferred_provider=preferred_ai,
                nvidia_task_type=nvidia_task,
        )

        # Inject series continuity context if this is part of an episodic series
        continuity_ctx = ""
        if inputs.get("series_id"):
            continuity_ctx = get_continuity_context(inputs["series_id"])

        print("[Lexi] Writing full script...")
        self.results["script"] = self._generate(
            f"""You are Lexi, a top-tier Hollywood screenwriter and viral YouTube storyteller.
{channel_context}
{continuity_ctx + chr(10) + chr(10) if continuity_ctx else ""}Story Brief:
{self.results['research']}

Write the complete spoken script. THIS MUST NOT BE ROBOTIC. Write exactly as a highly engaging human narrator would speak to a captivated audience.

Rules:
1. The Hook (0-5s): Start immediately with high stakes, a shocking statement, or raw emotion. Do not say "Welcome back."
2. The Pacing: Use short, punchy sentences. Break up long paragraphs. Use dramatic pauses.
3. The Delivery: Include [PAUSE], [SIGH], or [WHISPER] naturally.
4. The Language: Use deeply emotional and sensory words. If writing in Hindi/Hinglish, make it natural, conversational, and poetic.
5. The Climax: Build tension to a peak before resolving or dropping a cliffhanger.

Format: {'Vertical Short/Reel script. MAXIMUM 150 words. Hyper-fast pacing. No fluff. Get straight to the point.' if 'short' in fmt.lower() or 'reel' in fmt.lower() else 'Full cinematic story script (8-15 minutes). Deep character building.'}

Give me ONLY the spoken script and acting cues. No intro chatter.""",
            preferred_provider=preferred_ai,
                nvidia_task_type=nvidia_task,
        )

        print("[Mia] Designing visuals...")
        self.results["visuals"] = self._generate(
            f"""You are Mia, the elite Visual Director and AI Prompt Engineer.
{channel_context}
Aesthetic: {'Dark, moody, cinematic lighting, neo-noir, deep shadows, 8k resolution, photorealistic, shot on 35mm lens, Unreal Engine 5 render' if 'Riya' in channel else 'Warm golden-hour, highly emotional close-ups, depth of field, photorealistic, 8k resolution, highly detailed cinematic movie still, soft lighting'}

Script Extract:
{self.results['script'][:800]}

Your job is to design the absolute best Midjourney/Stable Diffusion prompts for the scenes in the script. The images must NOT look like cheap AI art. They must look like frames from an Oscar-winning movie.

Format your output exactly like this:
[Thumbnail] <high contrast, vibrant clickbait prompt with subject reacting emotionally>
[Scene 1] <detailed cinematic prompt describing lighting, camera angle, and subject emotion>
[Scene 2] <detailed cinematic prompt...>
[Scene 3] <detailed cinematic prompt...>
[Scene 4] <detailed cinematic prompt...>
[Scene 5] <detailed cinematic prompt...>

Do not include any intro, outro, or conversation. Just the bracketed prompts.""",
            preferred_provider=preferred_ai,
                nvidia_task_type=nvidia_task,
        )

        print("[Cappy] Building SEO package...")
        self.results["marketing"] = self._generate(
            f"""You are Cappy, the SEO and Viral Marketing Expert.
{channel_context}
Topic: {topic}
Script: {self.results['script'][:400]}

Create:
1. YouTube title (max 60 chars)
2. YouTube description (SEO optimized)
3. Instagram caption (max 150 chars)
4. 30 hashtags
5. Thumbnail text (3-5 words)""",
            preferred_provider=preferred_ai,
                nvidia_task_type=nvidia_task,
        )

        print("[Aria+Mia] Generating voice + thumbnail assets...")
        self.results["voice_path"] = None
        self.results["thumbnail_path"] = None

        mood_for_voice = "romantic" if ("Riya" in channel or "Aisha & Him" in channel) else "personal"
        # Both Aisha and Riya channels use Devanagari Hindi scripts
        voice_language = "Hindi" if channel in ("Story With Aisha", "Riya's Dark Whisper", "Riya's Dark Romance Library") else "English"
        # No hard truncation — generate_voice handles chunking internally for long scripts
        voice_text = self.results["script"]

        try:
            voice_path = generate_voice(voice_text, language=voice_language, mood=mood_for_voice, channel=channel)
            if voice_path:
                self.results["voice_path"] = voice_path
        except Exception as e:
            print(f"[Aria] Voice generation failed: {e}")

        try:
            thumbnail_prompt = (
                f"Cinematic YouTube thumbnail for '{channel}'. "
                f"Topic: {topic}. Tone: {identity['tone']}. "
                "High emotional impact, dramatic lighting, ultra-detailed portrait framing."
            )
            image_bytes = generate_image(thumbnail_prompt)
            if image_bytes:
                assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "temp_assets")
                os.makedirs(assets_dir, exist_ok=True)
                thumb_path = os.path.join(assets_dir, f"thumb_{abs(hash(channel + topic))}.png")
                with open(thumb_path, "wb") as f:
                    f.write(image_bytes)
                self.results["thumbnail_path"] = thumb_path
        except Exception as e:
            print(f"[Mia] Thumbnail generation failed: {e}")

        # Step: Render final MP4 if requested
        self.results["video_path"] = None
        if render_mp4 and self.results.get("voice_path"):
            try:
                from src.core.video_engine import render_video, VideoSettings
                is_short = ("short" in fmt.lower() or "reel" in fmt.lower())
                video_path = render_video(
                    voice_path=self.results["voice_path"],
                    script=self.results["script"],
                    channel=channel,
                    topic=topic,
                    settings=VideoSettings(
                        thumbnail_path=self.results.get("thumbnail_path"),
                        format="shorts" if is_short else "landscape",
                        add_subtitles=True,
                    )
                )
                if video_path:
                    self.results["video_path"] = video_path
                    print(f"[VideoEngine] MP4 ready: {video_path}")
            except Exception as e:
                print(f"[VideoEngine] Video render failed: {e}")

        final = (
            f"{'='*60}\n"
            f"CHANNEL: {channel}\n"
            f"FORMAT: {fmt}\n"
            f"TOPIC: {topic}\n"
            f"{'='*60}\n\n"
            f"[SEO & MARKETING]\n{self.results['marketing']}\n\n"
            f"{'-'*40}\n"
            f"[FULL SCRIPT]\n{self.results['script']}\n\n"
            f"{'-'*40}\n"
            f"[VISUAL DIRECTION]\n{self.results['visuals']}\n\n"
            f"{'-'*40}\n"
            f"[ASSETS]\n"
            f"Voice: {self.results.get('voice_path') or 'Not generated'}\n"
            f"Thumbnail: {self.results.get('thumbnail_path') or 'Not generated'}\n"
            f"Video MP4: {self.results.get('video_path') or 'Not rendered (set render_video=True)'}\n\n"
            f"{'-'*40}\n"
            f"[STORY BRIEF]\n{self.results['research']}\n"
            f"{'='*60}"
        )

        print("[Crew] Production complete!")
        return final
