# -*- coding: utf-8 -*-
"""
test_pipeline.py
Run a full content pipeline for Story With Aisha.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

from src.agents.youtube_crew import YouTubeCrew

print("="*60)
print("AISHA — Full Content Pipeline Test")
print("Channel: Story With Aisha")
print("="*60)

crew = YouTubeCrew()
result = crew.kickoff({
    "channel": "Story With Aisha",
    "topic": "Ek Ladki Jo Sirf Ek Message Ka Intezaar Karti Thi",
    "format": "Long Form",
    "render_video": False,  # skip MP4 for now — just test script+voice+thumbnail
})

print("\n" + result)

# Save output to file
out = "temp_assets/pipeline_test_output.txt"
os.makedirs("temp_assets", exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    f.write(result)
print(f"\nFull output saved to: {out}")
