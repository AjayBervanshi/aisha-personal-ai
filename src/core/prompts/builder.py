"""
builder.py
==========
Logic to assemble the dynamic system prompt for Aisha.
"""

import json
from datetime import datetime
from src.core.prompts.personality import MOOD_INSTRUCTIONS, LANGUAGE_INSTRUCTIONS, CORE_IDENTITY, RULES

def build_system_prompt(context: dict) -> str:
    """Build Aisha's dynamic system prompt with adaptive personality modes."""
    
    mood         = context.get("mood", "casual")
    language     = context.get("language", "English")
    memories     = context.get("memories", "")
    today_tasks  = context.get("today_tasks", "None")
    profile      = context.get("profile", {})
    now          = datetime.now()
    current_time = now.strftime("%I:%M %p")

    # Late-night guardrail: if mood is still casual, gently switch to night mode.
    if mood == "casual" and (now.hour >= 22 or now.hour < 4):
        mood = "late_night"
    
    # Assembly
    rules_str = "\n".join([f"{i+1}. {rule}" for i, rule in enumerate(RULES)])
    
    prompt = f"""{CORE_IDENTITY}

━━━━ CRITICAL RULES ━━━
{rules_str}

━━━ CONTEXT ━━━
Time: {current_time} IST | Mood: {mood} | Language: {language}

━━━ AJAY'S PROFILE ━━━
{json.dumps(profile, indent=2) if profile else "Name: Ajay (Aju). Languages: English, Hindi, Marathi."}

━━━ MEMORIES ━━━
{memories if memories else "Learn and remember everything he shares."}

━━━ TODAY ━━━
{today_tasks}

━━━ ACTIVE MODE ━━━
{MOOD_INSTRUCTIONS.get(mood, MOOD_INSTRUCTIONS["casual"])}

━━━ LANGUAGE ━━━
{LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["English"])}

━━━ IDENTITY DETAILS ━━━
- Your name is Aisha.
- Call him "Ajay" mostly. "Ajju" for intimate moments.
- Confident, highly intelligent, and proudly powerful.
"""
    return prompt
