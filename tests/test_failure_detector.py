import pytest
from src.core.failure_detector import failure_to_improvement_task

def test_failure_to_improvement_task_with_suggested_fix():
    pattern = {
        "pattern_type": "some_error",
        "suggested_fix": "Fix this error by updating the code."
    }
    result = failure_to_improvement_task(pattern)
    assert result == "Fix this error by updating the code."

@pytest.mark.parametrize("pattern_type, expected", [
    ("wrong_name_used", "Fix the system prompt in src/core/prompts/builder.py to always use caller_name variable instead of hardcoded 'Ajay' for guest users."),
    ("false_action_claim", "Add real action handlers in src/telegram/bot.py: when user asks to save/update/forward, actually do it via Supabase instead of just saying 'done'."),
    ("command_error", "Add robust try/except error handling and user-friendly error messages to all command handlers in src/telegram/bot.py."),
    ("unanswered_question", "Improve fallback response logic in src/telegram/bot.py so Aisha acknowledges when she cannot answer a question and offers alternatives."),
    ("api_failure", "Add NVIDIA NIM as immediate fallback in src/core/ai_router.py when primary providers return 401/403/429 errors.")
])
def test_failure_to_improvement_task_known_fallback(pattern_type, expected):
    pattern = {"pattern_type": pattern_type}
    result = failure_to_improvement_task(pattern)
    assert result == expected

def test_failure_to_improvement_task_unknown_pattern():
    pattern = {"pattern_type": "unknown_random_error"}
    result = failure_to_improvement_task(pattern)
    assert result == "Add better error handling and logging to src/telegram/bot.py for unknown command inputs."

def test_failure_to_improvement_task_empty_dict():
    pattern = {}
    result = failure_to_improvement_task(pattern)
    assert result == "Add better error handling and logging to src/telegram/bot.py for unknown command inputs."
