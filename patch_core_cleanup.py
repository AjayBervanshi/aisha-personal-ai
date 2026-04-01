with open("src/core/aisha_brain.py", "r") as f:
    code = f.read()

# Remove unused imports in aisha_brain.py
code = code.replace("from src.core.config import (\n    GEMINI_API_KEY, GROQ_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY,\n    GEMINI_MODEL, GROQ_MODEL, AI_TEMPERATURE, AI_MAX_TOKENS, AI_HISTORY_LIMIT, USER_NAME\n)", "from src.core.config import (\n    SUPABASE_URL, SUPABASE_SERVICE_KEY,\n    AI_HISTORY_LIMIT\n)")
code = code.replace("from src.core.mood_detector import detect_mood, get_mood_prompt_addon", "from src.core.mood_detector import detect_mood")

with open("src/core/aisha_brain.py", "w") as f:
    f.write(code)

with open("src/core/video_engine.py", "r") as f:
    code = f.read()

# Remove unused import in video_engine.py
code = code.replace("    import tempfile\n", "")

with open("src/core/video_engine.py", "w") as f:
    f.write(code)

print("Cleaned up unused imports in aisha_brain.py and video_engine.py!")
