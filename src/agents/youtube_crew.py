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
        # Use AIRouter directly — NOT AishaBrain — to avoid memory pollution
        self.ai = AIRouter()
        self.results = {}

    def _generate(self, prompt: str, max_len: int = 4000) -> str:
        """
        Direct AI call with large token budget for full scripts.
        Falls back gracefully if provider fails.
        """
        result = self.ai.generate(
            system_prompt="You are an expert content creator for YouTube and Instagram storytelling channels.",
            user_message=prompt,
        )
        return result.text.strip()

    def kickoff(self, inputs: dict) -> str:
        topic   = inputs.get("topic",   "A Late Night Secret")
        channel = inputs.get("channel", "Story With Aisha")
        fmt     = inputs.get("format",  "Long Form")

        identity = CHANNEL_IDENTITY.get(channel, CHANNEL_IDENTITY["Story With Aisha"])

        print(f"[Crew] Production: '{channel}' | '{topic}' | {fmt}")

        # ── STEP 1: RIYA — Story Research & Trope Selection ───────────────────
        print("[Riya] Researching story trope...")
        self.results["research"] = self._generate(
            f"""You are Riya, the Story Researcher for '{channel}'.
Channel tone: {identity['tone']}
Themes: {identity['themes']}
Topic requested: {topic}

Find the most viral, emotionally gripping angle for this story.
Output: Character names, core conflict, emotional hook, and why this will go viral.
Keep it to 300 words."""
        )

        # ── STEP 2: LEXI — Full Script Writing ───────────────────────────────
        print("[Lexi] Writing full script...")
        self.results["script"] = self._generate(
            f"""You are Lexi, the Master Scriptwriter for '{channel}'.
Channel format: {identity['format_hint']}
Tone: {identity['tone']}
Hook style: {identity['hook_style']}
Voice style: {identity['voice_style']}

Story Brief from Riya:
{self.results['research']}

Write the COMPLETE, FULL script now. Include:
1. HOOK (first 5 seconds — no setup, pure emotion)
2. STORY NARRATION with natural dialogue
3. SCENE BREAKS (e.g., [PAUSE], [MUSIC SWELLS])
4. EMOTIONAL CLIFFHANGER at the end
5. CALL TO ACTION (subscribe/follow for Part 2)

Format: Numbered dialogue lines. Make it feel like a web series episode.
Length: {'30-60 second short script' if fmt == 'Short/Reel' else 'Full 8-15 minute story script'}"""
        )

        # ── STEP 3: MIA — Visual Direction ────────────────────────────────────
        print("[Mia] Designing visuals...")
        self.results["visuals"] = self._generate(
            f"""You are Mia, the Visual Director for '{channel}'.
Channel aesthetic: {'Dark, moody, cinematic noir' if 'Riya' in channel else 'Warm, golden hour, emotional close-ups'}

Based on this script excerpt:
{self.results['script'][:800]}

Create:
1. THUMBNAIL IDEA — One powerful image that makes people stop scrolling
2. 5 SCENE VISUAL PROMPTS for AI image generation
3. BACKGROUND MUSIC MOOD — describe what the music should feel like

Be specific and cinematic."""
        )

        # ── STEP 4: CAPPY — SEO & Marketing ──────────────────────────────────
        print("[Cappy] Building SEO package...")
        self.results["marketing"] = self._generate(
            f"""You are Cappy, the SEO and Viral Marketing Expert for '{channel}'.

Story topic: {topic}
Script excerpt: {self.results['script'][:400]}

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
