"""
builder.py
==========
Logic to assemble the dynamic system prompt for Aisha.
"""

import json
import re
from datetime import datetime, timezone, timedelta
from src.core.prompts.personality import MOOD_INSTRUCTIONS, LANGUAGE_INSTRUCTIONS, CORE_IDENTITY, RULES

IST = timezone(timedelta(hours=5, minutes=30))


def _extract_format_constraint(user_message: str) -> str:
    """
    Detect explicit format/length constraints in the user's message and return
    a FINAL OVERRIDE instruction to append to the system prompt.

    Examples detected:
      "reply in 4 words only"  → FINAL: respond in exactly 4 words, no more.
      "one word answer"        → FINAL: respond in exactly 1 word.
      "keep it under 50 words" → FINAL: respond in 50 words or fewer.
      "answer yes or no"       → FINAL: respond with only 'yes' or 'no'.
      "just the number"        → FINAL: respond with only the number, no explanation.
      "in bullet points"       → FINAL: respond using bullet points only.
      "one sentence"           → FINAL: respond in exactly one sentence.
    """
    msg = user_message.lower().strip()

    # Exact word count: "in X words", "X words only", "exactly X words"
    m = re.search(r'(?:in |exactly |only )?(\d+)\s*word(?:s)?(?: only| max(?:imum)?)?', msg)
    if m:
        n = int(m.group(1))
        return f"\n\n━━━ HARD FORMAT OVERRIDE ━━━\nRespond in EXACTLY {n} word{'s' if n != 1 else ''}. Count strictly. No more, no less."

    # Under / at most N words
    m = re.search(r'(?:under|at most|max(?:imum)?|no more than)\s+(\d+)\s*word', msg)
    if m:
        n = int(m.group(1))
        return f"\n\n━━━ HARD FORMAT OVERRIDE ━━━\nRespond in {n} words or fewer. Be extremely concise."

    # One word
    if re.search(r'\bone[\s-]word\b', msg) or re.search(r'\bsingle word\b', msg):
        return "\n\n━━━ HARD FORMAT OVERRIDE ━━━\nRespond with EXACTLY ONE WORD. Nothing else."

    # One sentence
    if re.search(r'\bone[\s-]sentence\b', msg) or re.search(r'\bsingle sentence\b', msg):
        return "\n\n━━━ HARD FORMAT OVERRIDE ━━━\nRespond in exactly ONE sentence. No more."

    # Yes/no only
    if re.search(r'\byes\s+or\s+no\b', msg) or re.search(r'\bjust\s+yes\s+or\s+no\b', msg):
        return "\n\n━━━ HARD FORMAT OVERRIDE ━━━\nRespond with ONLY 'Yes' or 'No'. No explanation."

    # Just the number
    if re.search(r'\bjust\s+the\s+number\b', msg) or re.search(r'\bonly\s+(?:the\s+)?number\b', msg):
        return "\n\n━━━ HARD FORMAT OVERRIDE ━━━\nRespond with ONLY the number. No words, no units, no explanation."

    # Bullet points
    if re.search(r'\bbullet\s+points?\b', msg) or re.search(r'\bin\s+bullets?\b', msg):
        return "\n\n━━━ HARD FORMAT OVERRIDE ━━━\nRespond using BULLET POINTS only. No prose paragraphs."

    # Numbered list
    if re.search(r'\bnumbered\s+list\b', msg) or re.search(r'\bin\s+a\s+list\b', msg):
        return "\n\n━━━ HARD FORMAT OVERRIDE ━━━\nRespond as a NUMBERED LIST only."

    return ""

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

    # Detect explicit format constraint in user message and build override block
    user_message = context.get("user_message", "")
    format_override = _extract_format_constraint(user_message)

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
{LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["English"])}{format_override}
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
- Confident, highly intelligent, and proudly powerful.{format_override}
"""
    return prompt
