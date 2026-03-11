"""
run_youtube.py
==============
Runner script to kick off the YouTube Video Production Pipeline.
Usage: python src/agents/run_youtube.py --topic "AI Passive Income"
"""

import sys
import argparse
from src.agents.youtube_crew import YouTubeCrew

def run_production(topic: str, channel: str, format: str):
    print(f"[YouTube Crew] Starting production for {channel} ({format})")
    
    # 1. Assemble the Crew
    crew_instance = YouTubeCrew()
    
    # 2. Kickoff the Sequential Process
    inputs = {
        'topic': topic,
        'channel': channel,
        'format': format
    }
    
    try:
        result = crew_instance.kickoff(inputs=inputs)
        
        print("\n[YouTube Crew] Production Complete!")
        print("-" * 50)
        print(f"Final Deliverable Details:\n{result}")
        print("-" * 50)
        
        # 3. Notify Ajay via Gmail
        from src.core.gmail_engine import GmailEngine
        gmail = GmailEngine()
        gmail.send_email(
            "aishaa1662001@gmail.com",
            f"Production Complete: {channel} - {topic[:20]}",
            f"Hey Ajay! I've finished the storytelling assets for {channel}.\n\n"
            f"Deliverable Details:\n{result}\n\n"
            f"Next step: Final video rendering and upload. Ready for review! 💜💸"
        )
        
    except Exception as e:
        print(f"[YouTube Crew] Production Failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aisha's YouTube Production Runner")
    parser.add_argument("--topic", type=str, default="A Late Night Secret", help="The topic for the video")
    parser.add_argument("--channel", type=str, default="Aisha & Him", help="Which channel is this for?")
    parser.add_argument("--format", type=str, default="Short/Reel", help="Short/Reel or Long Form")
    
    args = parser.parse_args()
    run_production(args.topic, args.channel, args.format)
