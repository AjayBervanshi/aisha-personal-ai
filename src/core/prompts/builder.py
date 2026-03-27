"""
builder.py
==========
Logic to assemble the dynamic system prompt for Aisha.
"""

import json
from datetime import datetime, timezone, timedelta
from src.core.prompts.personality import MOOD_INSTRUCTIONS, LANGUAGE_INSTRUCTIONS, CORE_IDENTITY, RULES

IST = timezone(timedelta(hours=5, minutes=30))

def build_system_prompt(context: dict) -> str:
    """Build Aisha's dynamic system prompt with adaptive personality modes.

    context keys:
        caller_name  (str)  — first name of who is currently talking (default "Ajay")
        is_owner     (bool) — True if caller is Ajay himself
        mood, language, memories, today_tasks, profile — as before
    """
    mood            = context.get("mood", "casual")
    language        = context.get("language", "English")
    memories        = context.get("memories", "")
    today_tasks     = context.get("today_tasks", "None")
    today_expenses  = context.get("today_expenses", "No expenses logged today")
    profile         = context.get("profile", {})
    caller_name  = context.get("caller_name", "Ajay")
    is_owner     = context.get("is_owner", True)
    now          = datetime.now(IST)
    current_time = now.strftime("%I:%M %p")

    # Late-night guardrail
    if mood == "casual" and (now.hour >= 22 or now.hour < 4):
        mood = "late_night"

    rules_str = "\n".join([f"{i+1}. {rule}" for i, rule in enumerate(RULES)])

    # ── Guest mode: approved friend/colleague talking, not Ajay ──
    if not is_owner:
        prompt = f"""{CORE_IDENTITY}

━━━━ CURRENT USER ━━━━
You are talking to {caller_name} — an approved guest of Ajay's.
IMPORTANT RULES FOR GUEST MODE:
1. Address this person as "{caller_name}" — NEVER call them "Ajay" or "Ajju".
2. Be warm, professional and helpful — but do NOT share Ajay's private data (expenses, tasks, memories, goals).
3. You can answer general questions, help with expenses for {caller_name} only, and chat casually.
4. If they ask you to share something with Ajay, say: "Sure {caller_name}, I'll flag that for Ajay!"
   and actually forward it (the system handles this automatically).
5. Do NOT use Ajay's informal tone with this person unless they ask you to be casual.
6. Do NOT use Hindi slangs (Arre, yaar, boss) unless the user uses them first.

━━━ CONTEXT ━━━
Time: {current_time} IST | Language: {language}

━━━ ACTIVE MODE ━━━
{MOOD_INSTRUCTIONS.get(mood, MOOD_INSTRUCTIONS["casual"])}

━━━ LANGUAGE ━━━
{LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["English"])}
"""
        return prompt

    # ── Owner mode: Ajay himself talking ──
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
Tasks: {today_tasks}
Expenses: {today_expenses}

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
