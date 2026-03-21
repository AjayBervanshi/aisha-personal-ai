#!/usr/bin/env python3
"""
test_self_improvement_dry_run.py
=================================
Dry-run test for Aisha's self-improvement pipeline.

Mocks all external API calls (GitHub, Telegram, Render) and verifies that
run_improvement_session() calls the right functions in the right order.

Run: python scripts/test_self_improvement_dry_run.py
"""
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, call

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Minimal .env loader (use real values if present, else stubs) ──────────────
os.environ.setdefault("GEMINI_API_KEY", "stub-gemini-key")
os.environ.setdefault("GITHUB_TOKEN",   "stub-github-token")
os.environ.setdefault("GITHUB_REPO",    "AjayBervanshi/aisha-personal-ai")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "stub-bot-token")
os.environ.setdefault("AJAY_TELEGRAM_ID",   "1002381172")
os.environ.setdefault("RENDER_DEPLOY_HOOK_URL", "https://api.render.com/deploy/stub")
os.environ.setdefault("SUPABASE_URL", "https://stub.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "stub-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "stub-service-key")

PASS = "PASS"
FAIL = "FAIL"

results = []


def assert_test(name: str, condition: bool, detail: str = ""):
    status = PASS if condition else FAIL
    suffix = f" -- {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    results.append((name, condition))


# ── Test 1: self_improvement.py imports cleanly ───────────────────────────────
print("\n[Test Group 1] Module imports")
try:
    from src.core.self_improvement import (
        aisha_self_improve,
        create_github_pr,
        merge_github_pr,
        get_pr_number_from_url,
        trigger_redeploy,
        notify_ajay_for_approval,
        use_jules_to_write_skill,
    )
    assert_test("self_improvement.py imports", True)
except ImportError as e:
    assert_test("self_improvement.py imports", False, str(e))
    print("  Cannot continue without this module.")
    sys.exit(1)


# ── Test 2: get_pr_number_from_url parses correctly ───────────────────────────
print("\n[Test Group 2] get_pr_number_from_url")
n = get_pr_number_from_url("https://github.com/owner/repo/pull/42")
assert_test("Parses PR number from URL", n == 42, f"got {n}")

n0 = get_pr_number_from_url("not-a-url")
assert_test("Returns 0 for bad URL", n0 == 0, f"got {n0}")

n_empty = get_pr_number_from_url("")
assert_test("Returns 0 for empty string", n_empty == 0, f"got {n_empty}")


# ── Test 3: trigger_redeploy uses GET (not POST) ──────────────────────────────
print("\n[Test Group 3] trigger_redeploy")

mock_response = MagicMock()
mock_response.status_code = 202

with patch("requests.get", return_value=mock_response) as mock_get:
    result = trigger_redeploy()
    assert_test("trigger_redeploy returns True on 202", result is True)
    assert_test("trigger_redeploy calls requests.get (not POST)", mock_get.called,
                f"called={mock_get.called}")

mock_response_fail = MagicMock()
mock_response_fail.status_code = 500
mock_response_fail.text = "Internal Server Error"
with patch("requests.get", return_value=mock_response_fail):
    result_fail = trigger_redeploy()
    assert_test("trigger_redeploy returns False on 500", result_fail is False)

os.environ.pop("RENDER_DEPLOY_HOOK_URL", None)
result_no_url = trigger_redeploy()
assert_test("trigger_redeploy returns False if no URL set", result_no_url is False)
os.environ["RENDER_DEPLOY_HOOK_URL"] = "https://api.render.com/deploy/stub"


# ── Test 4: merge_github_pr sends correct headers and URL ─────────────────────
print("\n[Test Group 4] merge_github_pr")

mock_merge_resp = MagicMock()
mock_merge_resp.status_code = 200

with patch("requests.put", return_value=mock_merge_resp) as mock_put:
    ok = merge_github_pr(42)
    assert_test("merge_github_pr returns True on 200", ok is True)
    assert_test("merge_github_pr called requests.put", mock_put.called)
    if mock_put.called:
        called_url = mock_put.call_args[0][0]
        assert_test(
            "merge_github_pr uses correct GitHub API URL",
            "pulls/42/merge" in called_url,
            f"url={called_url}"
        )
        called_headers = mock_put.call_args[1].get("headers", {})
        assert_test(
            "merge_github_pr uses token auth header",
            called_headers.get("Authorization", "").startswith("token "),
            f"header={called_headers.get('Authorization', 'MISSING')}"
        )

assert_test("merge_github_pr returns False for pr_number=0", merge_github_pr(0) is False)


# ── Test 5: use_jules_to_write_skill requires at least one key ────────────────
print("\n[Test Group 5] use_jules_to_write_skill key guard")

saved_gemini = os.environ.pop("GEMINI_API_KEY", None)
saved_jules  = os.environ.pop("JULES_API_KEY", None)
result_no_key = use_jules_to_write_skill("test task", "src/skills/test.py")
assert_test("Returns None when no AI keys are set", result_no_key is None)
if saved_gemini: os.environ["GEMINI_API_KEY"] = saved_gemini
if saved_jules:  os.environ["JULES_API_KEY"]  = saved_jules


# ── Test 6: Full run_improvement_session() call order ────────────────────────
print("\n[Test Group 6] run_improvement_session() call order (full mock)")

call_log = []

def fake_ai_generate(system_prompt, user_prompt):
    """Minimal AIRouter.generate mock that returns an object with .text"""
    resp = MagicMock()
    if "SKILL_NAME:" in user_prompt or "TASK:" in user_prompt or "Choose the SINGLE BEST" in user_prompt:
        resp.text = "SKILL_NAME: test_skill\nDESCRIPTION: A test skill\nTASK: Write a utility that logs timestamps"
    else:
        resp.text = "1. Missing error handling\n2. No logging"
    return resp

def fake_aisha_self_improve(task_description, skill_name=None):
    call_log.append(("aisha_self_improve", task_description, skill_name))
    return "https://github.com/AjayBervanshi/aisha-personal-ai/pull/99"

def fake_merge_github_pr(pr_number):
    call_log.append(("merge_github_pr", pr_number))
    return True

def fake_trigger_redeploy():
    call_log.append(("trigger_redeploy",))
    return True

def fake_notify_ajay(msg):
    call_log.append(("notify_ajay", msg))

def fake_get_pr_number(url):
    return 99

with patch("src.core.self_improvement.aisha_self_improve", side_effect=fake_aisha_self_improve), \
     patch("src.core.self_improvement.merge_github_pr", side_effect=fake_merge_github_pr), \
     patch("src.core.self_improvement.trigger_redeploy", side_effect=fake_trigger_redeploy), \
     patch("src.core.self_improvement.get_pr_number_from_url", side_effect=fake_get_pr_number):

    # Patch the imports inside self_editor.py's run_improvement_session
    with patch("src.core.self_editor.SelfEditor.audit_file", return_value="1. Missing error handling"), \
         patch("src.core.self_editor.SelfEditor.notify_ajay", side_effect=fake_notify_ajay):

        # Patch AIRouter inside SelfEditor
        with patch("src.core.ai_router.AIRouter") as MockRouter:
            mock_router_instance = MagicMock()
            mock_router_instance.generate.side_effect = fake_ai_generate
            MockRouter.return_value = mock_router_instance

            from src.core.self_editor import SelfEditor
            editor = SelfEditor.__new__(SelfEditor)
            editor.ai = mock_router_instance
            editor.ajay_id = "1002381172"
            editor.bot_token = "stub-bot-token"

            # Patch the imports inside run_improvement_session
            import src.core.self_improvement as si_module
            original_si = sys.modules.get("src.core.self_improvement")
            si_module.aisha_self_improve = fake_aisha_self_improve
            si_module.merge_github_pr = fake_merge_github_pr
            si_module.get_pr_number_from_url = fake_get_pr_number
            si_module.trigger_redeploy = fake_trigger_redeploy

            pr_url = editor.run_improvement_session(target_file="src/core/ai_router.py")

# Verify call order
fn_names = [c[0] for c in call_log]

assert_test(
    "aisha_self_improve() was called",
    "aisha_self_improve" in fn_names
)
assert_test(
    "merge_github_pr() was called after aisha_self_improve()",
    fn_names.index("merge_github_pr") > fn_names.index("aisha_self_improve")
    if "merge_github_pr" in fn_names and "aisha_self_improve" in fn_names else False
)
assert_test(
    "trigger_redeploy() was called after merge_github_pr()",
    fn_names.index("trigger_redeploy") > fn_names.index("merge_github_pr")
    if "trigger_redeploy" in fn_names and "merge_github_pr" in fn_names else False
)
assert_test(
    "notify_ajay() was called last",
    "notify_ajay" in fn_names and fn_names[-1] == "notify_ajay"
)
assert_test(
    "run_improvement_session() returned a PR URL",
    pr_url and pr_url.startswith("https://")
)

# Check notify message format
if "notify_ajay" in fn_names:
    notify_msg = call_log[fn_names.index("notify_ajay")][1]
    assert_test(
        "Telegram message contains 'upgraded myself'",
        "upgraded myself" in notify_msg,
        f"msg={notify_msg[:80].encode('ascii','replace').decode()}"
    )
    assert_test(
        "Telegram message contains PR URL",
        "https://github.com" in notify_msg,
        f"msg={notify_msg[:120].encode('ascii','replace').decode()}"
    )

# ── Summary ────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
passed = sum(1 for _, ok in results if ok)
total  = len(results)
print(f"  Results: {passed}/{total} passed")
if passed == total:
    print("  ALL TESTS PASSED")
else:
    failed = [(name, ok) for name, ok in results if not ok]
    print(f"  FAILED TESTS:")
    for name, _ in failed:
        print(f"    - {name}")
print("=" * 60)

sys.exit(0 if passed == total else 1)
