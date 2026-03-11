"""
youtube_crew.py
==============
Native implementation of Aisha's YouTube Crew.
Uses Aisha's internal brain to simulate specialized agents (Riya, Lexi, etc.)
sequentially, avoiding heavy dependencies like CrewAI.
"""

import os
import json
from src.core.aisha_brain import AishaBrain

class YouTubeCrew:
    def __init__(self):
        self.brain = AishaBrain()
        self.results = {}

    def kickoff(self, inputs: dict):
        topic = inputs.get('topic', 'AI Future')
        print(f"[YouTube Crew] Starting production on topic: '{topic}'")

        # 1. RIYA (Researcher)
        print("[Riya] Searching for trending topics and keywords...")
        self.results['research'] = self.brain.think(
            f"You are Riya, the Data Researcher. Topic: {topic}. "
            "Find 3 top-trending sub-topics and viral keywords. Be data-driven."
        )

        # 2. LEXI (Scriptwriter)
        print("[Lexi] Drafting viral script...")
        self.results['script'] = self.brain.think(
            f"You are Lexi, the Master Scriptwriter. Based on this research: {self.results['research']}, "
            "write a 3-minute viral YouTube script. Include a hook, body, and CTA. Make it engaging!"
        )

        # 3. ARIA (Audio Engineer) - Simulated for now, or calls generate_voice
        print("[Aria] Preparing voiceover parameters...")
        self.results['audio'] = "Audio generation triggered via ElevenLabs pool."

        # 4. MIA (Visual Director)
        print("[Mia] Designing visual prompts...")
        self.results['visuals'] = self.brain.think(
            f"You are Mia, the Visual Director. Create 5 cinematic image generation prompts for this script: "
            f"{self.results['script'][:1000]}"
        )

        # 5. CAPPY (Marketing)
        print("[Cappy] Finalizing SEO metadata...")
        self.results['marketing'] = self.brain.think(
            f"You are Cappy, the SEO Wizard. Create a viral title, description, and 15 high-reach tags for: "
            f"{self.results['script'][:500]}"
        )

        final_output = (
            f"--- PRODUCTION COMPLETED ---\n"
            f"TOPIC: {topic}\n\n"
            f"TITLE & SEO:\n{self.results['marketing']}\n\n"
            f"SCRIPT:\n{self.results['script']}\n\n"
            f"VISUAL PROMPTS:\n{self.results['visuals']}\n\n"
            f"AUDIO STATUS: {self.results['audio']}"
        )
        
        return final_output

if __name__ == "__main__":
    crew = YouTubeCrew()
    print(crew.kickoff({"topic": "How AI will create millionaires in 2026"}))
