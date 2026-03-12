import os
import sys
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(".env")

from src.core.ai_router import AIRouter

router = AIRouter()

providers = ["gemini", "anthropic", "groq", "xai", "openai"]

for p in providers:
    try:
        print(f"\nTesting {p}...")
        res = router._call_provider(p, "You are a test.", "Say 'Test OK'.", [])
        print(f"SUCCESS: {res}")
    except Exception as e:
        print(f"FAILED {p}: {e}")
