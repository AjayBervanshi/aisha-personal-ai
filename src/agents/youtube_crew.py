"""
youtube_crew.py
==============
Aisha's YouTube Content Production Engine.
Handles all 4 channels with unique identities and formats.
Uses AIRouter directly (NOT brain.think) to avoid polluting Ajay's memory.
"""

import os
import sys
from src.core.ai_router import AIRouter

# ── Channel Identity Bible ─────────────────────────────────────────────────────
CHANNEL_IDENTITY = {
    "Story With Aisha": {
        "narrator": "Aisha",
        "tone": "warm, emotional, cinematic, heart-touching",
        "themes": "office romance, college love, long-distance, heartbreak, reunion",
        "format_hint": "8-15 minute audio storytelling with emotional dialogue",
        "hook_style": "Start with a single emotional sentence that makes you feel something immediately.",
        "voice_style": "Soft, warm, expressive — like a close friend telling you a story",
    },
    "Riya's Dark Whisper": {
        "narrator": "Riya",
        "tone": "mysterious, seductive, psychological, slow-burn",
        "themes": "forbidden love, obsession, betrayal, secret desires, dark relationships",
        "format_hint": "10-20 minute slow-build suspense story",
        "hook_style": "Open with a whisper of forbidden truth — something dangerous.",
        "voice_style": "Deep, slow, whispering — like a secret being told in the dark",
    },
    "Riya's Dark Romance Library": {
        "narrator": "Riya",
        "tone": "intense, addictive, dramatic, novel-style",
        "themes": "mafia romance, enemies to lovers, possessive alpha male, morally grey characters",
        "format_hint": "15-25 minute chapter-style story episode",
        "hook_style": "Drop into the middle of a tense, dangerous moment. No setup — pure action/emotion.",
        "voice_style": "Commanding, intense, slightly breathless — like reading a bestselling dark romance",
    },
    "Aisha & Him": {
        "narrator": "Aisha",
        "tone": "relatable, funny, sweet, real, everyday couple",
        "themes": "cute fights, jealousy, good morning texts, late night talks, relationship teasing",
        "format_hint": "30 second to 3 minute dialogue-format short/reel",
        "hook_style": "Open mid-conversation. Drop into a relatable couple moment instantly.",
        "voice_style": "Casual, playful, real — like texting your partner",
    },
}

class YouTubeCrew:
    def __init__(self):
        self.ai = AIRouter()
        self.results = {}

    def _generate(self, prompt: str, preferred_provider: str = None) -> str:
        """
        Direct AI call. Uses preferred_provider if specified (e.g. 'xai' for Riya's channels).
        Falls back to normal routing if preferred is unavailable.
        """
        if preferred_provider:
            # Try preferred provider first
            try:
                result = self.ai._call_provider(preferred_provider, 
                    "You are an expert content creator for YouTube and Instagram storytelling channels.",
                    prompt, [], None)
                return result.strip()
            except Exception:
                pass  # Fall through to normal routing

        result = self.ai.generate(
            system_prompt="You are an expert content creator for YouTube and Instagram storytelling channels.",
            user_message=prompt,
        )
        return result.text.strip()

    def kickoff(self, inputs: dict) -> str:
        topic    = inputs.get("topic",   "A Late Night Secret")
        channel  = inputs.get("channel", "Story With Aisha")
        fmt      = inputs.get("format",  "Long Form")
        # Use master prompt if provided, else fall back to built-in identity
        master_prompt = inputs.get("master_prompt", "")

        identity = CHANNEL_IDENTITY.get(channel, CHANNEL_IDENTITY["Story With Aisha"])
        
        # Riya's channels use Grok; Aisha's use Gemini
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

        # ── STEP 1: RIYA — Story Research & Trope Selection ───────────────────
        print("[Riya] Researching story trope...")
        self.results["research"] = self._generate(
            f"""You are Riya, the Story Researcher.
{channel_context}
Topic: {topic}

Find the most viral, emotionally gripping angle for this story.
Output: Character names, core conflict, emotional hook, why this will go viral.
Keep it to 300 words.""",
            preferred_provider=preferred_ai
        )

        # ── STEP 2: LEXI — Full Script Writing ───────────────────────────────
        print("[Lexi] Writing full script...")
        self.results["script"] = self._generate(
            f"""You are Lexi, the Master Scriptwriter.
{channel_context}

Story Brief:
{self.results['research']}

Write the COMPLETE, FULL script. Include:
1. HOOK (first 5 seconds — no setup, pure emotion)
2. STORY NARRATION with natural dialogue
3. SCENE BREAKS ([PAUSE], [MUSIC SWELLS], [SILENCE])
4. EMOTIONAL CLIFFHANGER at the end
5. CALL TO ACTION (Part 2 hook)

Length: {'30-60 second reel script with punchy dialogue' if fmt == 'Short/Reel' else 'Full story script (8-15 minutes of narration)'}
Make every line count. This must be addictive.""",
            preferred_provider=preferred_ai
        )

        # ── STEP 3: MIA — Visual Direction ────────────────────────────────────
        print("[Mia] Designing visuals...")
        self.results["visuals"] = self._generate(
            f"""You are Mia, the Visual Director.
{channel_context}
Aesthetic: {'Dark, moody, cinematic noir — deep shadows, candlelight, rain' if 'Riya' in channel else 'Warm, golden hour, soft bokeh, emotional close-ups'}

Script:
{self.results['script'][:800]}

Create:
1. THUMBNAIL — One frame that stops the scroll (describe it precisely)
2. 5 SCENE PROMPTS for AI image generation (be specific about lighting, mood, composition)
3. MUSIC MOOD — what should the background music feel like?""",
            preferred_provider=preferred_ai
        )

        # ── STEP 4: CAPPY — SEO & Marketing ──────────────────────────────────
        print("[Cappy] Building SEO package...")
        self.results["marketing"] = self._generate(
            f"""You are Cappy, the SEO and Viral Marketing Expert.
{channel_context}
Topic: {topic}
Script: {self.results['script'][:400]}

Create the COMPLETE marketing package:
1. YOUTUBE TITLE — Emotional, curiosity-driven, max 60 chars
2. YOUTUBE DESCRIPTION — 300 words, SEO-optimized, ends with subscribe CTA
3. INSTAGRAM CAPTION — Punchy, emotional, max 150 chars
4. HASHTAGS — 30 targeted hashtags for romance/storytelling niche
5. THUMBNAIL TEXT — 3-5 bold words to overlay on the thumbnail image

Make them feel addictive. People must click."""
        )

        # ── FINAL PACKAGE ──────────────────────────────────────────────────────
        final = (
            f"{'='*60}\n"
            f"CHANNEL: {channel}\n"
            f"FORMAT: {fmt}\n"
            f"TOPIC: {topic}\n"
            f"{'='*60}\n\n"
            f"[SEO & MARKETING]\n{self.results['marketing']}\n\n"
            f"{'─'*40}\n"
            f"[FULL SCRIPT]\n{self.results['script']}\n\n"
            f"{'─'*40}\n"
            f"[VISUAL DIRECTION]\n{self.results['visuals']}\n\n"
            f"{'─'*40}\n"
            f"[STORY BRIEF]\n{self.results['research']}\n"
            f"{'='*60}"
        )

        print("[Crew] Production complete!")
        return final
