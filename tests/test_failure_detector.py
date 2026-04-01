import pytest
from unittest.mock import patch, MagicMock

from src.core.failure_detector import (
    failure_to_improvement_task,
    get_recent_failures,
    detect_failure_patterns,
    get_top_improvement_task,
)

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

@patch('src.core.failure_detector.requests.get')
def test_get_recent_failures_success(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"role": "user", "message": "hello", "created_at": "2023-01-01T00:00:00Z", "user_id": "123"},
        {"role": "assistant", "content": "hi there", "created_at": "2023-01-01T00:00:01Z", "user_id": "123"}
    ]
    mock_get.return_value = mock_response

    result = get_recent_failures()

    assert len(result) == 2
    assert result[0] == {"role": "user", "message": "hello", "created_at": "2023-01-01T00:00:00Z", "user_id": "123"}
    assert result[1] == {"role": "assistant", "message": "hi there", "created_at": "2023-01-01T00:00:01Z", "user_id": "123"}
    # Should only call requests.get once because aisha_conversations succeeded
    assert mock_get.call_count == 1

@patch('src.core.failure_detector.requests.get')
def test_get_recent_failures_fallback_to_memory(mock_get):
    # First call (aisha_conversations) fails with 404
    # Second call (aisha_memory) succeeds
    mock_resp_404 = MagicMock()
    mock_resp_404.status_code = 404
    mock_resp_404.content = b'{"code": "PGRST116"}'
    mock_resp_404.json.return_value = {"code": "PGRST116"}

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = [
        {"role": "user", "content": "hello memory", "created_at": "2023-01-01T00:00:00Z", "user_id": "123"}
    ]

    mock_get.side_effect = [mock_resp_404, mock_resp_200]

    result = get_recent_failures()

    assert len(result) == 1
    assert result[0] == {"role": "user", "message": "hello memory", "created_at": "2023-01-01T00:00:00Z", "user_id": "123"}
    assert mock_get.call_count == 2

@patch('src.core.failure_detector.requests.get')
def test_get_recent_failures_connection_error(mock_get):
    import requests
    mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

    result = get_recent_failures()

    assert result == []
    # Stops immediately on connection error
    assert mock_get.call_count == 1

def test_detect_failure_patterns_empty():
    assert detect_failure_patterns([]) == []

def test_detect_failure_patterns_wrong_name_used():
    conversations = [
        {"role": "assistant", "message": "Hello Ajay!", "user_id": "other_user_123"}
    ]
    patterns = detect_failure_patterns(conversations)
    assert len(patterns) == 1
    assert patterns[0]["pattern_type"] == "wrong_name_used"

def test_detect_failure_patterns_false_action_claim():
    conversations = [
        {"role": "assistant", "message": "I've updated the task for you.", "user_id": "123"}
    ]
    patterns = detect_failure_patterns(conversations)
    assert len(patterns) == 1
    assert patterns[0]["pattern_type"] == "false_action_claim"

def test_detect_failure_patterns_command_error():
    conversations = [
        {"role": "user", "message": "Error: /remind command failed with KeyError", "user_id": "123"}
    ]
    patterns = detect_failure_patterns(conversations)
    assert len(patterns) == 1
    assert patterns[0]["pattern_type"] == "command_error"

    conversations2 = [
        {"role": "user", "message": "❌ Failed to connect", "user_id": "123"}
    ]
    patterns2 = detect_failure_patterns(conversations2)
    assert len(patterns2) == 1
    assert patterns2[0]["pattern_type"] == "command_error"

def test_detect_failure_patterns_unanswered_question():
    conversations = [
        {"role": "user", "message": "What is the capital of France?", "user_id": "123"},
        {"role": "user", "message": "What is the capital of France?", "user_id": "123"},
        {"role": "user", "message": "What is the capital of france?", "user_id": "123"}
    ]
    patterns = detect_failure_patterns(conversations)
    assert len(patterns) == 1
    assert patterns[0]["pattern_type"] == "unanswered_question"

def test_detect_failure_patterns_api_failure():
    conversations = [
        {"role": "assistant", "message": "Gemini returned 429 quota exhausted", "user_id": "123"}
    ]
    patterns = detect_failure_patterns(conversations)
    assert len(patterns) == 1
    assert patterns[0]["pattern_type"] == "api_failure"

def test_detect_failure_patterns_multiple():
    conversations = [
        {"role": "assistant", "message": "Hello Ajay!", "user_id": "other"},
        {"role": "assistant", "message": "I've saved it.", "user_id": "other"},
        {"role": "user", "message": "❌ Failed to connect", "user_id": "other"},
        {"role": "assistant", "message": "Gemini returned 429 quota exhausted", "user_id": "other"},
        {"role": "user", "message": "What is the capital of France?", "user_id": "other"},
        {"role": "user", "message": "What is the capital of France?", "user_id": "other"},
        {"role": "user", "message": "What is the capital of France?", "user_id": "other"}
    ]
    patterns = detect_failure_patterns(conversations)
    types = [p["pattern_type"] for p in patterns]
    assert set(types) == {
        "wrong_name_used",
        "false_action_claim",
        "command_error",
        "unanswered_question",
        "api_failure"
    }

@patch('src.core.failure_detector.get_recent_failures')
def test_get_top_improvement_task_no_conversations(mock_get_failures):
    mock_get_failures.return_value = []
    task = get_top_improvement_task()
    assert task is None

@patch('src.core.failure_detector.get_recent_failures')
def test_get_top_improvement_task_no_patterns(mock_get_failures):
    mock_get_failures.return_value = [
        {"role": "user", "message": "hello", "user_id": "123"}
    ]
    task = get_top_improvement_task()
    assert task is None

@patch('src.core.failure_detector.get_recent_failures')
def test_get_top_improvement_task_selects_highest_severity(mock_get_failures):
    # false_action_claim is severity 3, wrong_name_used is severity 2
    mock_get_failures.return_value = [
        {"role": "assistant", "message": "I've saved it.", "user_id": "other"},
        {"role": "assistant", "message": "Hello Ajay!", "user_id": "other"}
    ]
    task = get_top_improvement_task()

    assert task is not None
    assert "save/update/forward" in task.lower()
