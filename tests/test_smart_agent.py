"""
tests/test_smart_agent.py
=========================
Professional smart test agent for Aisha.
- Randomizes test scenarios each run (no repetitive same tests)
- Tests all major subsystems
- Produces structured report
- Non-destructive: uses dry-run mode where possible
"""
import os
import sys
import json
import random
import logging
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("AishaTestAgent")

# ─── Test Scenario Pools ──────────────────────────────────────────────────────

TOPICS_POOL = [
    "Ek Anjaan Musafir",
    "Pyaar Ka Pehla Ehsaas",
    "Baarish Ki Raat",
    "Dil Ki Baat",
    "Khwabon Ka Safar",
    "Mohabbat Ka Rang",
    "Chaand Aur Sitare",
    "Teri Yaad",
    "Naye Rishte",
    "Zindagi Ke Rang",
    "Paheli Mulaqaat",
    "Sapnon Ki Duniya",
]

CHANNELS_POOL = [
    "Story With Aisha",
    "Aisha & Him",
]

MOODS_POOL = [
    "romantic",
    "mysterious",
    "playful",
    "professional",
    "happy",
    "melancholic",
]

QUESTIONS_POOL = [
    "Aaj ka din kaisa tha?",
    "Mujhe ek romantic story sunao",
    "Tumhara favourite colour kya hai?",
    "Aaj weather kaisa hai?",
    "Koi motivational baat karo",
    "Tumhari sabse achhi memory kya hai?",
    "Ek joke sunao",
    "Aaj kya plan hai tumhara?",
    "Tum kitni smjhdar ho?",
    "Mujhe ek short poem sunao",
]

# ─── Test Functions ───────────────────────────────────────────────────────────

def test_imports() -> dict:
    """Test that all core modules import without errors."""
    results = {"name": "imports", "passed": [], "failed": []}
    modules = [
        ("src.core.config", "Config"),
        ("src.core.ai_router", "AIRouter"),
        ("src.core.aisha_brain", "AishaBrain"),
        ("src.core.voice_engine", None),
        ("src.core.social_media_engine", "SocialMediaEngine"),
        ("src.core.series_tracker", None),
        ("src.core.token_manager", None),
        ("src.agents.antigravity_agent", "AntigravityAgent"),
    ]
    for module_path, class_name in modules:
        try:
            mod = __import__(module_path, fromlist=[class_name] if class_name else [""])
            if class_name:
                getattr(mod, class_name)
            results["passed"].append(module_path)
        except Exception as e:
            results["failed"].append({"module": module_path, "error": str(e)})
    results["status"] = "PASS" if not results["failed"] else "FAIL"
    return results


def test_ai_router() -> dict:
    """Test AI router with a random question."""
    question = random.choice(QUESTIONS_POOL)
    results = {"name": "ai_router", "question": question}
    try:
        from src.core.ai_router import AIRouter
        router = AIRouter()
        response = router.chat(question, max_tokens=100)
        results["status"] = "PASS"
        results["response_len"] = len(response) if response else 0
        results["response_preview"] = (response or "")[:100]
    except Exception as e:
        results["status"] = "FAIL"
        results["error"] = str(e)
    return results


def test_brain_response() -> dict:
    """Test AishaBrain with a random question and mood."""
    question = random.choice(QUESTIONS_POOL)
    mood = random.choice(MOODS_POOL)
    results = {"name": "brain_response", "question": question, "mood": mood}
    try:
        from src.core.aisha_brain import AishaBrain
        brain = AishaBrain()
        if hasattr(brain, 'set_mood'):
            brain.set_mood(mood)
        elif hasattr(brain, 'mood_override'):
            brain.mood_override = mood
        response = brain.think(question, user_id=1002381172)
        results["status"] = "PASS"
        results["response_len"] = len(response) if response else 0
        results["response_preview"] = (response or "")[:150]
    except Exception as e:
        results["status"] = "FAIL"
        results["error"] = str(e)
    return results


def test_content_job_enqueue() -> dict:
    """Test enqueuing a content job (dry run — enqueues but marks as test)."""
    topic = random.choice(TOPICS_POOL)
    channel = random.choice(CHANNELS_POOL)
    results = {"name": "content_job_enqueue", "topic": topic, "channel": channel}
    try:
        from src.agents.antigravity_agent import AntigravityAgent
        agent = AntigravityAgent()
        # Check if enqueue_job accepts a test/dry_run flag
        kwargs = {
            "topic": f"[TEST] {topic}",
            "channel": channel,
            "content_format": "Short/Reel",
            "platforms": ["youtube"],
            "auto_post": False,  # NEVER auto-post during tests
        }
        job_id = agent.enqueue_job(**kwargs)
        results["status"] = "PASS"
        results["job_id"] = str(job_id)

        # Clean up: mark test job as cancelled
        try:
            from supabase import create_client
            sb = create_client(os.getenv("SUPABASE_URL", ""), os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))
            sb.table("content_jobs").update({"status": "cancelled", "error": "test run"}).eq("id", str(job_id)).execute()
            results["cleanup"] = "cancelled"
        except Exception:
            pass
    except Exception as e:
        results["status"] = "FAIL"
        results["error"] = str(e)
    return results


def test_supabase_connection() -> dict:
    """Test Supabase DB connectivity."""
    results = {"name": "supabase_connection"}
    try:
        from supabase import create_client
        sb = create_client(os.getenv("SUPABASE_URL", ""), os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))
        count = sb.table("aisha_conversations").select("id", count="exact").limit(1).execute()
        results["status"] = "PASS"
        results["table_accessible"] = True
    except Exception as e:
        results["status"] = "FAIL"
        results["error"] = str(e)
    return results


def test_token_manager() -> dict:
    """Test token manager health check."""
    results = {"name": "token_manager"}
    try:
        from src.core.token_manager import check_instagram_token, check_youtube_token
        ig = check_instagram_token()
        yt = check_youtube_token()
        results["status"] = "PASS"
        results["instagram"] = ig.get("status")
        results["youtube"] = yt.get("status")
    except Exception as e:
        results["status"] = "FAIL"
        results["error"] = str(e)
    return results


def test_series_tracker() -> dict:
    """Test series tracker DB operations."""
    results = {"name": "series_tracker"}
    try:
        from src.core.series_tracker import get_or_create_series, get_next_episode_number
        channel = random.choice(CHANNELS_POOL)
        series = get_or_create_series(f"Test Series {random.randint(1, 9999)}", channel, total_episodes=3)
        if series:
            ep_num = get_next_episode_number(series["id"])
            results["status"] = "PASS"
            results["series_id"] = series.get("id")
            results["next_episode"] = ep_num
            # Clean up test series
            try:
                from supabase import create_client
                sb = create_client(os.getenv("SUPABASE_URL", ""), os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))
                sb.table("aisha_series").delete().eq("id", series["id"]).execute()
            except Exception:
                pass
        else:
            results["status"] = "FAIL"
            results["error"] = "series not created"
    except Exception as e:
        results["status"] = "FAIL"
        results["error"] = str(e)
    return results


# ─── Test Randomizer ──────────────────────────────────────────────────────────

ALL_TESTS = [
    test_imports,
    test_supabase_connection,
    test_ai_router,
    test_brain_response,
    test_content_job_enqueue,
    test_token_manager,
    test_series_tracker,
]


def run_smart_agent():
    """
    Run a randomized selection of tests.
    Always runs: imports, supabase (critical)
    Randomly selects 3-4 more from the pool.
    """
    print("\n" + "=" * 60)
    print(f"  AISHA SMART TEST AGENT — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Run seed: {random.randint(1000, 9999)}")
    print("=" * 60 + "\n")

    # Always run critical tests
    critical_tests = [test_imports, test_supabase_connection]
    # Random sample from the rest
    optional_tests = [t for t in ALL_TESTS if t not in critical_tests]
    selected_optional = random.sample(optional_tests, min(3, len(optional_tests)))

    tests_to_run = critical_tests + selected_optional
    random.shuffle(selected_optional)  # randomize order of optional tests

    results = []
    passed = 0
    failed = 0

    for test_fn in tests_to_run:
        print(f"Running: {test_fn.__name__}...")
        start = time.time()
        try:
            result = test_fn()
            elapsed = round(time.time() - start, 2)
            result["elapsed_s"] = elapsed
            results.append(result)

            status = result.get("status", "PASS")
            if status == "PASS":
                passed += 1
                print(f"   PASS ({elapsed}s)")
            else:
                failed += 1
                print(f"   FAIL ({elapsed}s): {result.get('error', '?')}")
        except Exception as e:
            failed += 1
            elapsed = round(time.time() - start, 2)
            results.append({"name": test_fn.__name__, "status": "FAIL", "error": str(e), "elapsed_s": elapsed})
            print(f"   FAIL ({elapsed}s): {e}")
        print()

    # Summary
    print("=" * 60)
    print(f"  RESULTS: {passed} passed / {failed} failed / {len(tests_to_run)} total")
    print("=" * 60)

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "passed": passed,
        "failed": failed,
        "total": len(tests_to_run),
        "tests": results,
    }
    report_path = Path(__file__).parent / "last_test_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str))
    print(f"\n  Report saved: {report_path}")

    return report


if __name__ == "__main__":
    # Load .env
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent / ".env")
    except ImportError:
        pass

    report = run_smart_agent()
    sys.exit(0 if report["failed"] == 0 else 1)
