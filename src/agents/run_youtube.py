"""
run_youtube.py
==============
Runner script to kick off the YouTube Video Production Pipeline.
Usage: python src/agents/run_youtube.py --topic "AI Passive Income"
"""

import sys
import argparse
from src.agents.youtube_crew import YouTubeCrew

def run_production(topic: str):
    print(f"[YouTube Crew] Starting production on topic: '{topic}'")
    
    # 1. Assemble the Crew
    crew_instance = YouTubeCrew()
    
    # 2. Kickoff the Sequential Process
    inputs = {
        'topic': topic
    }
    
    try:
        result = crew_instance.kickoff(inputs=inputs)
        
        print("\n[YouTube Crew] Production Complete!")
        print("-" * 50)
        print(f"Final Deliverable Details:\n{result}")
        print("-" * 50)
        
        # 3. Notify Ajay via Gmail (since we just set it up!)
        from src.core.gmail_engine import GmailEngine
        gmail = GmailEngine()
        gmail.send_email(
            "aishaa1662001@gmail.com",
            f"YouTube Production Complete: {topic[:30]}",
            f"Hey Ajay! I've finished the production phase for our new video.\n\n"
            f"Deliverable Details:\n{result}\n\n"
            f"Next step: Final video rendering and upload. Ready for review! 💜💸"
        )
        
    except Exception as e:
        print(f"[YouTube Crew] Production Failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aisha's YouTube Production Runner")
    parser.add_argument("--topic", type=str, default="How AI will create millionaires in 2026", help="The topic for the video")
    
    args = parser.parse_args()
    run_production(args.topic)
