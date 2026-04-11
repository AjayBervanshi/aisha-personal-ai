import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.core.aisha_brain import AishaBrain

def main():
    brain = AishaBrain()
    print("\n" + "="*50)
    print("Chat with Aisha (Phase 3: Advanced Social & Finance)")
    print("="*50 + "\n")

    # We clear the memory to ensure it's doing fresh lookups
    brain.reset_session()

    messages = [
        "Aisha, create a highly engaging Instagram Reel script about the top 5 AI tools for productivity in 2026. Give me scene-by-scene descriptions and voiceover.",
        "Now, add an expense to my finance tracker: I just bought a new microphone for 4500 rupees.",
        "What are my latest expenses?",
        "Write a 100-word romantic poem in Hindi using Devanagari script.",
        "Generate a YouTube video description for a video about 'How to build an AI soulmate'. Include 3 tags."
    ]

    for user_input in messages:
        print(f"Ajay: {user_input}")
        resp = brain.think(user_input)
        print(f"\nAisha: {resp}\n")
        print("-" * 50)

if __name__ == "__main__":
    main()
