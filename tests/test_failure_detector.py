import pytest
from src.core.failure_detector import failure_to_improvement_task

def test_failure_to_improvement_task_with_suggested_fix():
    pattern = {
        "pattern_type": "some_error",
        "suggested_fix": "Fix this error by updating the code."
    }
    result = failure_to_improvement_task(pattern)
    assert result == "Fix this error by updating the code."

@pytest.mark.parametrize("pattern_type, expected_task", [
    (
        "wrong_name_used",
        "Fix the system prompt in src/core/prompts/builder.py to always use caller_name variable instead of hardcoded 'Ajay' for guest users."
    ),
    (
        "false_action_claim",
        "Add real action handlers in src/telegram/bot.py: when user asks to save/update/forward, actually do it via Supabase instead of just saying 'done'."
    ),
    (
        "command_error",
        "Add robust try/except error handling and user-friendly error messages to all command handlers in src/telegram/bot.py."
    ),
    (
        "unanswered_question",
        "Improve fallback response logic in src/telegram/bot.py so Aisha acknowledges when she cannot answer a question and offers alternatives."
    ),
    (
        "api_failure",
        "Add NVIDIA NIM as immediate fallback in src/core/ai_router.py when primary providers return 401/403/429 errors."
    ),
    (
        "unknown_random_error",
        "Add better error handling and logging to src/telegram/bot.py for unknown command inputs."
    )
])
def test_failure_to_improvement_task_known_fallback(pattern_type, expected_task):
    pattern = {"pattern_type": pattern_type}
    result = failure_to_improvement_task(pattern)
    assert result == expected_task

def test_failure_to_improvement_task_empty_dict():
    pattern = {}
    result = failure_to_improvement_task(pattern)
    assert result == "Add better error handling and logging to src/telegram/bot.py for unknown command inputs."

def test_detect_failure_patterns_empty():
    from src.core.failure_detector import detect_failure_patterns
    assert detect_failure_patterns([]) == []

def test_detect_failure_patterns_wrong_name_used():
    from src.core.failure_detector import detect_failure_patterns
    conversations = [
        {"role": "assistant", "message": "Hello Ajay!", "user_id": "not_ajay_123"}
    ]
    patterns = detect_failure_patterns(conversations)
    assert len(patterns) == 1
    assert patterns[0]["pattern_type"] == "wrong_name_used"

def test_detect_failure_patterns_false_action_claim():
    from src.core.failure_detector import detect_failure_patterns
    conversations = [
        {"role": "assistant", "message": "I've saved your preferences.", "user_id": "user1"}
    ]
    patterns = detect_failure_patterns(conversations)
    assert len(patterns) == 1
    assert patterns[0]["pattern_type"] == "false_action_claim"

def test_detect_failure_patterns_command_error():
    from src.core.failure_detector import detect_failure_patterns
    conversations = [
        {"role": "user", "message": "❌ Error: Something went wrong with /help command", "user_id": "user1"}
    ]
    patterns = detect_failure_patterns(conversations)
    assert len(patterns) == 1
    assert patterns[0]["pattern_type"] == "command_error"
    assert "help" in patterns[0]["suggested_fix"]

def test_detect_failure_patterns_unanswered_question():
    from src.core.failure_detector import detect_failure_patterns
    conversations = [
        {"role": "user", "message": "What is the time?", "user_id": "user1"},
        {"role": "user", "message": "What is the time?", "user_id": "user1"},
        {"role": "user", "message": "What is the time?", "user_id": "user1"}
    ]
    patterns = detect_failure_patterns(conversations)
    assert len(patterns) == 1
    assert patterns[0]["pattern_type"] == "unanswered_question"

def test_detect_failure_patterns_api_failure():
    from src.core.failure_detector import detect_failure_patterns
    conversations = [
        {"role": "assistant", "message": "Gemini error 429 quota exhausted.", "user_id": "user1"}
    ]
    patterns = detect_failure_patterns(conversations)
    assert len(patterns) == 1
    assert patterns[0]["pattern_type"] == "api_failure"
    assert "429" in patterns[0]["description"]
    assert "gemini" in patterns[0]["description"].lower()

def test_detect_failure_patterns_multiple():
    from src.core.failure_detector import detect_failure_patterns
    conversations = [
        {"role": "assistant", "message": "Hello Ajay!", "user_id": "user1"},
        {"role": "assistant", "message": "I've updated your calendar.", "user_id": "user1"},
        {"role": "user", "message": "❌ Error: /start failed", "user_id": "user1"}
    ]
    patterns = detect_failure_patterns(conversations)
    # The detector finds all that match their respective separate loops
    types = [p["pattern_type"] for p in patterns]
    assert "wrong_name_used" in types
    assert "false_action_claim" in types
    assert "command_error" in types
    assert len(patterns) == 3
