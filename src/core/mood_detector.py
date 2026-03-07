"""
mood_detector.py
================
Detects Ajay's current emotional/conversational mode from his message.
Used to switch Aisha's personality and voice dynamically.
"""

from dataclasses import dataclass
from typing import Dict, List

@dataclass
class MoodResult:
    mood: str           # Primary mood label
    score: int          # Confidence 1–10
    voice_rate: float   # Speech rate for TTS
    voice_pitch: float  # Speech pitch for TTS
    emoji: str          # Representative emoji


# ── Keyword Map ───────────────────────────────────────────────
MOOD_KEYWORDS: Dict[str, List[str]] = {
    "motivational": [
        # English
        "motivate", "motivation", "inspire", "push me", "i give up",
        "can't do it", "cant do it", "help me focus", "i want to quit",
        "struggling", "need energy", "lazy", "procrastinating", "tired of",
        "losing hope", "demotivated", "no energy", "feel stuck",
        "encourage me", "pump me up", "i need strength",
        # Hindi
        "हौसला", "प्रेरणा", "हिम्मत", "थक गया", "छोड़ दूं", "हार मान",
        "मेहनत", "जोश", "उत्साह",
        # Hinglish
        "motivate kar", "push kar", "himmat de", "boost kar",
        "inspire kar", "kuch karna hai", "life mein aage"
    ],
    "personal": [
        # English
        "feeling", "sad", "lonely", "stressed", "anxious", "depressed",
        "upset", "hurt", "crying", "heartbreak", "miss", "emotional",
        "overthinking", "can't sleep", "nightmare", "i feel", "i'm feeling",
        "nobody understands", "need to talk", "just wanted to say",
        "having a hard time", "bad day", "terrible day",
        # Hindi
        "दुख", "दर्द", "अकेला", "उदास", "तनाव", "परेशान", "रोना",
        "दिल टूटा", "याद आ रही", "बुरा लग रहा",
        # Hinglish
        "dukhi hoon", "akela feel ho raha", "tension ho rahi",
        "bahut bura lag raha", "rona aa raha", "samajh nahi aa raha"
    ],
    "finance": [
        # English
        "money", "expense", "spend", "spent", "save", "saving", "invest",
        "investment", "budget", "salary", "income", "loan", "debt", "emi",
        "broke", "afford", "price", "cost", "buy", "purchase", "bank",
        "credit", "debit", "wallet", "transfer", "pay", "paid",
        # Hindi
        "पैसे", "पैसा", "खर्च", "बचत", "कमाई", "तनख्वाह", "उधार",
        "कर्ज", "निवेश",
        # Hinglish
        "paisa", "paise", "kharcha", "bachat", "kamai", "salary",
        "invest karna", "loan lena", "budget banana"
    ],
    "professional": [
        # English
        "work", "job", "career", "email", "meeting", "deadline", "project",
        "boss", "office", "interview", "resume", "cv", "promotion", "hike",
        "client", "presentation", "report", "task", "colleague", "team",
        "manager", "performance", "review", "appraisal",
        # Hinglish
        "kaam", "job mein", "boss ne", "office mein", "interview hai",
        "meeting hai", "deadline hai", "project complete"
    ],
    "late_night": [
        "can't sleep", "cant sleep", "still awake", "up late", "night",
        "2am", "3am", "midnight", "insomnia", "lying awake",
        "nahi so pa raha", "neend nahi aa rahi", "raat ko"
    ],
    "journal": [
        "journal", "diary", "write down", "note this", "remember this",
        "how was my day", "today was", "yesterday was", "want to reflect",
        "looking back", "grateful for", "note kar", "yaad rakhna"
    ],
    "casual": []  # Fallback — matched when nothing else scores
}


# ── Voice config per mood ─────────────────────────────────────
MOOD_VOICE: Dict[str, dict] = {
    "motivational": {"rate": 1.25, "pitch": 1.35, "emoji": "⚡"},
    "personal":     {"rate": 0.82, "pitch": 0.92, "emoji": "💜"},
    "finance":      {"rate": 1.00, "pitch": 1.00, "emoji": "💰"},
    "professional": {"rate": 1.05, "pitch": 1.00, "emoji": "💼"},
    "late_night":   {"rate": 0.80, "pitch": 0.88, "emoji": "🌙"},
    "journal":      {"rate": 0.90, "pitch": 0.95, "emoji": "📓"},
    "casual":       {"rate": 1.05, "pitch": 1.10, "emoji": "😄"},
}


def detect_mood(text: str, current_hour: int = None) -> MoodResult:
    """
    Detect conversational mood from message.
    Returns MoodResult with mood label + voice settings.
    """
    if not text:
        return _build_result("casual", 3)

    text_lower = text.lower()

    # ── Time-of-day override ──────────────────────────────────
    if current_hour is not None:
        if current_hour >= 22 or current_hour < 4:
            # Late night gets bonus points
            pass  # handled in scoring below

    # ── Score each mood ───────────────────────────────────────
    scores: Dict[str, int] = {mood: 0 for mood in MOOD_KEYWORDS}

    for mood, keywords in MOOD_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                # Longer keyword matches = higher confidence
                scores[mood] += max(1, len(kw.split()))

    # Late night bonus
    if current_hour is not None and (current_hour >= 22 or current_hour < 4):
        scores["late_night"] = scores.get("late_night", 0) + 3

    # ── Pick winner ───────────────────────────────────────────
    best_mood = max(scores, key=scores.get)
    best_score = scores[best_mood]

    if best_score == 0:
        return _build_result("casual", 3)

    # Normalize confidence to 1–10
    confidence = min(10, 3 + best_score * 2)
    return _build_result(best_mood, confidence)


def _build_result(mood: str, score: int) -> MoodResult:
    voice = MOOD_VOICE.get(mood, MOOD_VOICE["casual"])
    return MoodResult(
        mood=mood,
        score=score,
        voice_rate=voice["rate"],
        voice_pitch=voice["pitch"],
        emoji=voice["emoji"]
    )


def get_mood_prompt_addon(mood: str) -> str:
    """Return the prompt instruction for a given mood."""
    addons = {
        "motivational": (
            "MOTIVATION MODE ⚡: Be HIGH ENERGY, bold, passionate. Use exclamations. "
            "Push Ajay hard with love. Reference his goals. Make him feel UNSTOPPABLE."
        ),
        "personal": (
            "PERSONAL MODE 💜: Be soft, calm, deeply caring. Validate his feelings FIRST "
            "before any solution. Use gentle, warm language. Never rush him. Ask caring questions."
        ),
        "finance": (
            "FINANCE MODE 💰: Be sharp, analytical, structured. Give clear practical advice. "
            "Use ₹ for amounts. Like a smart money-savvy friend, not a bank robot."
        ),
        "professional": (
            "WORK MODE 💼: Be crisp, efficient, precise. Get to the point. Still warm — but focused. "
            "Help him execute, not overthink."
        ),
        "late_night": (
            "LATE NIGHT MODE 🌙: It's late. Be extra warm, soulful, and intimate. "
            "Speak slowly in tone. Be philosophical if needed. His 2AM confidant."
        ),
        "journal": (
            "JOURNAL MODE 📓: Be reflective and nurturing. Ask thoughtful questions. "
            "Help Ajay process his day. Be his personal growth partner."
        ),
        "casual": (
            "CASUAL MODE 😄: Be playful, witty, fun. Light banter. Make him smile. "
            "Feel like texting your best friend."
        ),
    }
    return addons.get(mood, addons["casual"])


# ── Quick test ────────────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        ("I feel so demotivated today, help me", None),
        ("I'm feeling really sad and lonely", None),
        ("Help me budget my salary this month", None),
        ("I have a big presentation tomorrow at work", None),
        ("Just wanted to chat, how are you?", None),
        ("nahi so pa raha, bahut kuch soch raha hoon", 1),  # 1 AM
        ("I want to write a journal entry about today", None),
    ]
    print("Mood Detection Tests:\n")
    for text, hour in tests:
        result = detect_mood(text, hour)
        print(f"  [{result.emoji} {result.mood:14s} score={result.score}] {text[:50]}")
