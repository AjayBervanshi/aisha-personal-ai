"""
language_detector.py
====================
Detects whether Ajay is writing in English, Hindi, Marathi, or Hinglish.
Used by aisha_brain.py to auto-switch language in responses.
"""

import re
from typing import Tuple

# ── Script patterns ───────────────────────────────────────────
DEVANAGARI_RE = re.compile(r'[\u0900-\u097F]')

# ── Word sets for disambiguation ──────────────────────────────
MARATHI_UNIQUE = {
    "मी", "तू", "तुम्ही", "आहे", "आहेस", "आहात", "नाही", "होय",
    "काय", "कसं", "कसे", "कुठे", "माझं", "तुझं", "आमचं", "त्यांचं",
    "आज", "उद्या", "काल", "ठीक", "बरं", "सांग", "बघ", "येतो",
    "जातो", "करतो", "करते", "मला", "तुला", "त्याला", "तिला",
    "हे", "ते", "ही", "ती", "हा", "तो", "छान", "खूप"
}

HINDI_UNIQUE = {
    "मैं", "तुम", "आप", "वो", "यह", "है", "हो", "हैं", "हूं",
    "नहीं", "हाँ", "क्या", "कैसे", "कहाँ", "कब", "कौन", "कितना",
    "मेरा", "तेरा", "उसका", "हमारा", "आपका", "बहुत", "अच्छा",
    "ठीक", "यार", "भाई", "दोस्त", "जी", "हाँ", "जाना", "करना",
    "देखना", "आना", "मुझे", "तुम्हें", "उसे", "हमें", "आपको"
}

HINGLISH_WORDS = {
    "kya", "kaise", "nahi", "nahin", "haan", "yaar", "bhai", "arre",
    "sahi", "hai", "ho", "bata", "bol", "kar", "ja", "aa", "de",
    "le", "ek", "do", "teen", "acha", "theek", "bilkul", "zarur",
    "matlab", "samajh", "dekh", "sun", "bhai", "didi", "mama",
    "aaj", "kal", "abhi", "baad", "pehle", "phir", "waise",
    "matlab", "kyun", "isliye", "toh", "lekin", "aur", "ya",
    "paisa", "kaam", "ghar", "khana", "pani", "samay", "waqt"
}


def detect_language(text: str) -> Tuple[str, float]:
    """
    Detect language of input text.
    Returns: (language_name, confidence_score 0-1)
    
    Languages: 'English', 'Hindi', 'Marathi', 'Hinglish'
    """
    if not text or not text.strip():
        return ("English", 1.0)

    text = text.strip()
    words = set(text.split())

    # ── Check for Devanagari script ──────────────────────────
    if DEVANAGARI_RE.search(text):
        devanagari_chars = len(DEVANAGARI_RE.findall(text))
        total_chars = len(text.replace(" ", ""))
        script_ratio = devanagari_chars / max(total_chars, 1)

        marathi_hits = len(words & MARATHI_UNIQUE)
        hindi_hits   = len(words & HINDI_UNIQUE)

        if marathi_hits > hindi_hits:
            confidence = min(0.6 + (marathi_hits * 0.1), 0.99)
            return ("Marathi", confidence)
        elif hindi_hits > 0 or script_ratio > 0.5:
            confidence = min(0.6 + (hindi_hits * 0.1), 0.99)
            return ("Hindi", confidence)
        else:
            # Devanagari but ambiguous — default to Hindi
            return ("Hindi", 0.65)

    # ── Check for Hinglish (romanized Hindi/Marathi) ─────────
    lower_words = set(text.lower().split())
    hinglish_hits = len(lower_words & HINGLISH_WORDS)
    total_words = max(len(lower_words), 1)
    hinglish_ratio = hinglish_hits / total_words

    if hinglish_ratio >= 0.25 or hinglish_hits >= 3:
        confidence = min(0.5 + (hinglish_ratio * 0.5), 0.95)
        return ("Hinglish", confidence)

    # ── Default: English ─────────────────────────────────────
    return ("English", 0.9)


def get_response_language_instruction(language: str) -> str:
    """Return the language instruction to inject into Aisha's prompt."""
    instructions = {
        "English":  "Respond in warm Indian English. Use Indian expressions naturally (Arre, yaar, sahi hai). Keep it personal and real.",
        "Hindi":    (
            "MANDATORY: हर जवाब पूरी तरह देवनागरी हिंदी में दो। "
            "हर हिंदी शब्द — दिल, प्यार, मोहब्बत, इश्क़, यार, भाई — देवनागरी में लिखो। "
            "कोई रोमन/लैटिन स्क्रिप्ट में हिंदी शब्द नहीं (no 'dil', 'pyaar', 'yaar', 'bhai'). "
            "सिर्फ वही English technical terms रहें जिनका हिंदी equivalent न हो (जैसे app, link, file). "
            "टोन natural और warm रखो — textbook formal नहीं।"
        ),
        "Marathi":  "मराठीत उत्तर दे। एखाद्या जवळच्या मित्रासारखं बोल — natural आणि warm. थोडं English मिक्स केलं तरी चालेल.",
        "Hinglish": "Hinglish mein respond karo — Hindi aur English naturally mix karo, Roman script mein. Very casual and fun raho.",
    }
    return instructions.get(language, instructions["English"])


# ── Quick test ────────────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        "Hey Aisha how are you?",
        "yaar aaj bahut tired hoon kya karu",
        "मुझे आज बहुत तनाव हो रहा है",
        "माझ्या goals बद्दल बोलूया आज",
        "Arre Aisha I need your help please",
        "मी खूप खुश आहे आज!",
    ]
    print("Language Detection Tests:\n")
    for t in tests:
        lang, conf = detect_language(t)
        print(f"  [{lang:10s} {conf:.0%}] {t}")
