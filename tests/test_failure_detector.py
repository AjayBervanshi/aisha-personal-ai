import pytest
from src.core.failure_detector import detect_failure_patterns

def test_detect_failure_patterns_empty():
    assert detect_failure_patterns([]) == []

def test_detect_failure_patterns_wrong_name_used():
    conversations = [
        {
            "role": "assistant",
            "message": "Hello Ajay, how can I help you?",
            "user_id": "other_user_123"
        }
    ]
    patterns = detect_failure_patterns(conversations)
    assert len(patterns) == 1
    assert patterns[0]["pattern_type"] == "wrong_name_used"

def test_detect_failure_patterns_wrong_name_ignored_if_no_user_id():
    conversations = [
        {
            "role": "assistant",
            "message": "Hello Ajay, how can I help you?",
            "user_id": ""
        }
    ]
    patterns = detect_failure_patterns(conversations)
    assert len(patterns) == 0

def test_detect_failure_patterns_false_action_claim():
    conversations = [
        {
            "role": "assistant",
            "message": "Sure, I've updated your preferences.",
            "user_id": "user_123"
        }
    ]
    patterns = detect_failure_patterns(conversations)
    assert len(patterns) == 1
    assert patterns[0]["pattern_type"] == "false_action_claim"

def test_detect_failure_patterns_command_error_cross():
    conversations = [
        {
            "role": "user",
            "message": "❌ Command /start failed.",
            "user_id": "user_123"
        }
    ]
    patterns = detect_failure_patterns(conversations)
    assert len(patterns) == 1
    assert patterns[0]["pattern_type"] == "command_error"

def test_detect_failure_patterns_command_error_text():
    conversations = [
        {
            "role": "user",
            "message": "error: /start command not found.",
            "user_id": "user_123"
        }
    ]
    patterns = detect_failure_patterns(conversations)
    assert len(patterns) == 1
    assert patterns[0]["pattern_type"] == "command_error"

def test_detect_failure_patterns_unanswered_question():
    conversations = [
        {
            "role": "user",
            "message": "What is the meaning of life?",
            "user_id": "user_123"
        },
        {
            "role": "user",
            "message": "What is the meaning of life?",
            "user_id": "user_123"
        },
        {
            "role": "user",
            "message": "What is the meaning of life?",
            "user_id": "user_123"
        }
    ]
    patterns = detect_failure_patterns(conversations)
    assert len(patterns) == 1
    assert patterns[0]["pattern_type"] == "unanswered_question"

def test_detect_failure_patterns_api_failure():
    conversations = [
        {
            "role": "assistant",
            "message": "The gemini api returned 429 quota exhausted.",
            "user_id": "user_123"
        }
    ]
    patterns = detect_failure_patterns(conversations)
    assert len(patterns) == 1
    assert patterns[0]["pattern_type"] == "api_failure"

def test_detect_failure_patterns_no_failure():
    conversations = [
        {
            "role": "user",
            "message": "Hello!",
            "user_id": "user_123"
        },
        {
            "role": "assistant",
            "message": "Hi there! How can I help you today?",
            "user_id": "user_123"
        }
    ]
    patterns = detect_failure_patterns(conversations)
    assert len(patterns) == 0
