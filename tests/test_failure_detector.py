import pytest
from src.core.failure_detector import failure_to_improvement_task

def test_failure_to_improvement_task_with_suggested_fix():
    pattern = {
        "pattern_type": "wrong_name_used",
        "suggested_fix": "Use the actual name from the variable."
    }
    result = failure_to_improvement_task(pattern)
    assert result == "Use the actual name from the variable."

def test_failure_to_improvement_task_fallback_wrong_name_used():
    pattern = {"pattern_type": "wrong_name_used"}
    result = failure_to_improvement_task(pattern)
    assert "use caller_name variable instead of hardcoded" in result

def test_failure_to_improvement_task_fallback_false_action_claim():
    pattern = {"pattern_type": "false_action_claim"}
    result = failure_to_improvement_task(pattern)
    assert "Add real action handlers in src/telegram/bot.py" in result

def test_failure_to_improvement_task_fallback_command_error():
    pattern = {"pattern_type": "command_error"}
    result = failure_to_improvement_task(pattern)
    assert "Add robust try/except error handling" in result

def test_failure_to_improvement_task_fallback_unanswered_question():
    pattern = {"pattern_type": "unanswered_question"}
    result = failure_to_improvement_task(pattern)
    assert "Improve fallback response logic" in result

def test_failure_to_improvement_task_fallback_api_failure():
    pattern = {"pattern_type": "api_failure"}
    result = failure_to_improvement_task(pattern)
    assert "Add NVIDIA NIM as immediate fallback" in result

def test_failure_to_improvement_task_unknown_pattern_type():
    pattern = {"pattern_type": "some_unknown_pattern"}
    result = failure_to_improvement_task(pattern)
    assert "Add better error handling and logging" in result

def test_failure_to_improvement_task_empty_dict():
    pattern = {}
    result = failure_to_improvement_task(pattern)
    assert "Add better error handling and logging" in result
