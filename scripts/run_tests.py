"""
run_tests.py
============
Full integration test suite for Aisha.
Tests every component before deployment.

Usage:
  python scripts/run_tests.py              # Run all tests
  python scripts/run_tests.py --quick      # Skip slow tests
  python scripts/run_tests.py --component brain  # Test one component
"""

import sys
import os
import time
import argparse
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

# ── Test result tracker ───────────────────────────────────────
results = {"passed": 0, "failed": 0, "skipped": 0, "errors": []}

def test(name: str, fn, skip_if=None):
    """Run a single test with proper error handling."""
    if skip_if:
        print(f"  ⏭️  SKIP  {name} ({skip_if})")
        results["skipped"] += 1
        return False
    try:
        fn()
        print(f"  ✅ PASS  {name}")
        results["passed"] += 1
        return True
    except AssertionError as e:
        print(f"  ❌ FAIL  {name}: {e}")
        results["failed"] += 1
        results["errors"].append(f"{name}: {e}")
        return False
    except Exception as e:
        print(f"  💥 ERROR {name}: {type(e).__name__}: {e}")
        results["failed"] += 1
        results["errors"].append(f"{name}: {type(e).__name__}: {e}")
        return False


# ══════════════════════════════════════════════════════════════
# TEST SUITES
# ══════════════════════════════════════════════════════════════

def test_config():
    print("\n🔑 [1/6] Config Tests")
    from src.core.config import USER_NAME, TIMEZONE, AI_TEMPERATURE

    def check_defaults():
        assert USER_NAME in ("Ajay", None, ""), "USER_NAME should be Ajay"
        assert TIMEZONE == "Asia/Kolkata", "Timezone should be Asia/Kolkata"
        assert 0.5 <= AI_TEMPERATURE <= 1.0, "Temperature out of range"

    test("Default config values", check_defaults)
    test("Config module importable", lambda: __import__("src.core.config"))


def test_language_detector():
    print("\n🌐 [2/6] Language Detector Tests")
    from src.core.language_detector import detect_language

    cases = [
        ("Hello how are you?",             "English"),
        ("yaar kya ho raha hai bata",       "Hinglish"),
        ("मैं बहुत खुश हूं आज",             "Hindi"),
        ("मी आज खूप खुश आहे",             "Marathi"),
        ("Arre yaar this is so sahi",        "Hinglish"),
        ("I need help with my work today",   "English"),
    ]
    for text, expected in cases:
        lang, conf = detect_language(text)
        test(
            f'detect_language("{text[:30]}")',
            lambda l=lang, e=expected: assert_equal(l, e, f"got {l}, expected {e}")
        )


def test_mood_detector():
    print("\n😊 [3/6] Mood Detector Tests")
    from src.core.mood_detector import detect_mood

    cases = [
        ("I feel so demotivated please push me", "motivational"),
        ("I'm feeling really sad today",          "personal"),
        ("Help me budget ₹5000 salary",           "finance"),
        ("I have a meeting with my boss tomorrow", "professional"),
        ("just chatting what's up",               "casual"),
    ]
    for text, expected in cases:
        result = detect_mood(text)
        test(
            f'detect_mood("{text[:35]}")',
            lambda r=result, e=expected: assert_equal(r.mood, e, f"got {r.mood}, expected {e}")
        )


def test_memory_manager():
    print("\n🗄️  [4/6] Memory Manager Tests")
    supa_ok = bool(os.getenv("SUPABASE_URL") and "your_" not in os.getenv("SUPABASE_URL", ""))

    if not supa_ok:
        test("Supabase connection", None, skip_if="SUPABASE_URL not configured")
        test("Profile load", None, skip_if="SUPABASE_URL not configured")
        test("Memory save", None, skip_if="SUPABASE_URL not configured")
        return

    from src.memory.memory_manager import MemoryManager
    mm = MemoryManager()

    def check_profile():
        profile = mm.get_profile()
        assert isinstance(profile, dict), "Profile should be a dict"

    def check_memories():
        mems = mm.get_top_memories(limit=5)
        assert isinstance(mems, list), "Memories should be a list"

    def check_tasks():
        tasks = mm.get_today_tasks()
        assert isinstance(tasks, list), "Tasks should be a list"

    test("Supabase connection + profile load", check_profile)
    test("Memory retrieval", check_memories)
    test("Today tasks load", check_tasks)


def test_ai_brain():
    print("\n🧠 [5/6] AI Brain Tests")
    gemini_ok = bool(os.getenv("GEMINI_API_KEY") and "your_" not in os.getenv("GEMINI_API_KEY", ""))

    if not gemini_ok:
        test("Gemini API call", None, skip_if="GEMINI_API_KEY not configured")
        test("Hindi response", None, skip_if="GEMINI_API_KEY not configured")
        return

    from src.core.aisha_brain import AishaBrain
    brain = AishaBrain()

    def check_english():
        reply = brain.think("Say exactly: 'Aisha test passed'", platform="test")
        assert reply and len(reply) > 5, "Empty response"

    def check_hindi():
        reply = brain.think("बोलो 'Aisha test passed'", platform="test")
        assert reply and len(reply) > 5, "Empty Hindi response"

    def check_motivation_mode():
        reply = brain.think("Motivate me Aisha!", platform="test")
        assert reply and len(reply) > 20, "Motivation response too short"

    test("English AI response", check_english)
    test("Hindi AI response", check_hindi)
    test("Motivation mode response", check_motivation_mode)


def test_telegram_bot():
    print("\n📱 [6/6] Telegram Bot Tests")
    tg_ok = bool(os.getenv("TELEGRAM_BOT_TOKEN") and "your_" not in os.getenv("TELEGRAM_BOT_TOKEN", ""))

    if not tg_ok:
        test("Telegram bot token", None, skip_if="TELEGRAM_BOT_TOKEN not configured")
        return

    import telebot
    def check_bot_init():
        bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
        info = bot.get_me()
        assert info.first_name, "Bot has no name"
        print(f"       Bot: @{info.username} ({info.first_name})")

    test("Telegram bot initialization", check_bot_init)


# ── Helpers ────────────────────────────────────────────────────
def assert_equal(a, b, msg=""):
    assert a == b, msg or f"{a!r} != {b!r}"


# ── Main ───────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Aisha Test Suite")
    parser.add_argument("--quick", action="store_true", help="Skip AI calls")
    parser.add_argument("--component", choices=["config","language","mood","memory","brain","telegram"])
    args = parser.parse_args()

    print("=" * 55)
    print("🌟 AISHA — Integration Test Suite")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    start = time.time()

    component = args.component
    if not component or component == "config":     test_config()
    if not component or component == "language":   test_language_detector()
    if not component or component == "mood":       test_mood_detector()
    if not component or component == "memory":     test_memory_manager()
    if not component or component == "brain":
        if not args.quick: test_ai_brain()
        else: print("\n🧠 [5/6] AI Brain Tests — SKIPPED (--quick mode)")
    if not component or component == "telegram":
        if not args.quick: test_telegram_bot()
        else: print("\n📱 [6/6] Telegram Tests — SKIPPED (--quick mode)")

    elapsed = time.time() - start

    print("\n" + "=" * 55)
    print(f"  Passed:  {results['passed']}")
    print(f"  Failed:  {results['failed']}")
    print(f"  Skipped: {results['skipped']}")
    print(f"  Time:    {elapsed:.1f}s")
    print("=" * 55)

    if results["errors"]:
        print("\n❌ Failures:")
        for e in results["errors"]:
            print(f"   • {e}")

    if results["failed"] == 0:
        print("\n✅ All tests passed! Aisha is ready 💜\n")
        if results["skipped"] > 0:
            print("⚠️  Some tests were skipped. Add missing API keys in .env to run them.\n")
    else:
        print("\n❌ Some tests failed. Fix them before deploying!\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
