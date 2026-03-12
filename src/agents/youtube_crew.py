"""
youtube_crew.py
==============
Aisha's YouTube Content Production Engine.
Handles all channels with unique identity and generates core assets.
"""

import os
from src.core.ai_router import AIRouter
from src.core.voice_engine import generate_voice
from src.core.image_engine import generate_image

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

    def _generate(self, prompt: str, preferred_provider: str = None) -> str:
        if preferred_provider:
            try:
                result = self.ai._call_provider(
                    preferred_provider,
                    "You are an expert content creator for YouTube and Instagram storytelling channels.",
                    prompt,
                    [],
                    None,
                )
                return result.strip()
            except Exception:
                pass

        result = self.ai.generate(
            system_prompt="You are an expert content creator for YouTube and Instagram storytelling channels.",
            user_message=prompt,
        )
        return result.text.strip()

    def kickoff(self, inputs: dict) -> str:
        topic = inputs.get("topic", "A Late Night Secret")
        channel = inputs.get("channel", "Story With Aisha")
        fmt = inputs.get("format", "Long Form")
        master_prompt = inputs.get("master_prompt", "")

        identity = CHANNEL_IDENTITY.get(channel, CHANNEL_IDENTITY["Story With Aisha"])

        from src.core.config import CHANNEL_AI_PROVIDER

        preferred_ai = CHANNEL_AI_PROVIDER.get(channel, "gemini")
        print(f"[Crew] {channel} | {topic} | AI: {preferred_ai.upper()}")

        channel_context = master_prompt if master_prompt else (
            f"Channel: {channel}\n"
            f"Tone: {identity['tone']}\n"
            f"Themes: {identity['themes']}\n"
            f"Format: {identity['format_hint']}\n"
            f"Hook style: {identity['hook_style']}\n"
            f"Voice: {identity['voice_style']}"
        )

        print("[Riya] Researching story trope...")
        self.results["research"] = self._generate(
            f"""You are Riya, the Story Researcher.
{channel_context}
Topic: {topic}

Find the most viral, emotionally gripping angle for this story.
Output: Character names, core conflict, emotional hook, why this will go viral.
Keep it to 300 words.""",
            preferred_provider=preferred_ai,
        )

        print("[Lexi] Writing full script...")
        self.results["script"] = self._generate(
            f"""You are Lexi, the Master Scriptwriter.
{channel_context}

Story Brief:
{self.results['research']}

Write the complete script. Include:
1. HOOK (first 5 seconds)
2. Story narration with natural dialogue
3. Scene notes ([PAUSE], [MUSIC], [SILENCE])
4. Emotional cliffhanger
5. CTA for next episode

Length: {'30-60 second reel script with punchy dialogue' if fmt == 'Short/Reel' else 'Full story script (8-15 minutes of narration)'}
Make every line count.""",
            preferred_provider=preferred_ai,
        )

        print("[Mia] Designing visuals...")
        self.results["visuals"] = self._generate(
            f"""You are Mia, the Visual Director.
{channel_context}
Aesthetic: {'Dark, moody, cinematic noir with deep shadows' if 'Riya' in channel else 'Warm golden-hour emotional close-ups'}

Script:
{self.results['script'][:800]}

Create:
1. Thumbnail concept
2. 5 scene prompts for AI image generation
3. Background music mood""",
            preferred_provider=preferred_ai,
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
        )

        print("[Aria+Mia] Generating voice + thumbnail assets...")
        self.results["voice_path"] = None
        self.results["thumbnail_path"] = None

        mood_for_voice = "romantic" if ("Riya" in channel or "Aisha & Him" in channel) else "personal"
        voice_text = self.results["script"][:3500]

        try:
            voice_path = generate_voice(voice_text, language="English", mood=mood_for_voice)
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
                assets_dir = "temp_assets"
                os.makedirs(assets_dir, exist_ok=True)
                thumb_path = os.path.join(assets_dir, f"thumb_{abs(hash(channel + topic))}.png")
                with open(thumb_path, "wb") as f:
                    f.write(image_bytes)
                self.results["thumbnail_path"] = thumb_path
        except Exception as e:
            print(f"[Mia] Thumbnail generation failed: {e}")

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
            f"Thumbnail: {self.results.get('thumbnail_path') or 'Not generated'}\n\n"
            f"{'-'*40}\n"
            f"[STORY BRIEF]\n{self.results['research']}\n"
            f"{'='*60}"
        )

        print("[Crew] Production complete!")
        return final
