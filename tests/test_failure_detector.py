import pytest
from src.core.failure_detector import failure_to_improvement_task

def test_failure_to_improvement_task_with_suggested_fix():
    pattern = {
        "pattern_type": "some_error",
        "suggested_fix": "Fix this error by updating the code."
    }
    result = failure_to_improvement_task(pattern)
    assert result == "Fix this error by updating the code."

def test_failure_to_improvement_task_known_fallback():
    pattern = {"pattern_type": "wrong_name_used"}
    result = failure_to_improvement_task(pattern)
    assert result == "Fix the system prompt in src/core/prompts/builder.py to always use caller_name variable instead of hardcoded 'Ajay' for guest users."

    pattern = {"pattern_type": "api_failure"}
    result = failure_to_improvement_task(pattern)
    assert result == "Add NVIDIA NIM as immediate fallback in src/core/ai_router.py when primary providers return 401/403/429 errors."

def test_failure_to_improvement_task_unknown_pattern():
    pattern = {"pattern_type": "unknown_random_error"}
    result = failure_to_improvement_task(pattern)
    assert result == "Add better error handling and logging to src/telegram/bot.py for unknown command inputs."

def test_failure_to_improvement_task_empty_dict():
    pattern = {}
    result = failure_to_improvement_task(pattern)
    assert result == "Add better error handling and logging to src/telegram/bot.py for unknown command inputs."
