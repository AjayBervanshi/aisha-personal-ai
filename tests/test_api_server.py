import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock dependencies before importing the server
sys.modules['src.core.aisha_brain'] = MagicMock()
sys.modules['supabase'] = MagicMock()

from src.api.server import verify_token
import src.api.server as server_module

def test_verify_token_dev_mode():
    """Test that verify_token allows all requests when no API token is configured."""
    # Temporarily remove API token
    old_token = server_module._API_TOKEN
    server_module._API_TOKEN = ""

    try:
        # Should return True regardless of credentials
        assert verify_token(None) is True
        assert verify_token(HTTPAuthorizationCredentials(scheme="Bearer", credentials="any")) is True
    finally:
        server_module._API_TOKEN = old_token


def test_verify_token_valid_credentials():
    """Test that verify_token allows requests with correct Bearer token."""
    old_token = server_module._API_TOKEN
    server_module._API_TOKEN = "test_secret_123"

    try:
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test_secret_123")
        assert verify_token(creds) is True
    finally:
        server_module._API_TOKEN = old_token


def test_verify_token_invalid_credentials():
    """Test that verify_token rejects requests with incorrect Bearer token."""
    old_token = server_module._API_TOKEN
    server_module._API_TOKEN = "test_secret_123"

    try:
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong_token")
        with pytest.raises(HTTPException) as exc_info:
            verify_token(creds)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid or missing API token"
    finally:
        server_module._API_TOKEN = old_token


def test_verify_token_missing_credentials():
    """Test that verify_token rejects requests with no credentials when token is required."""
    old_token = server_module._API_TOKEN
    server_module._API_TOKEN = "test_secret_123"

    try:
        with pytest.raises(HTTPException) as exc_info:
            verify_token(None)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid or missing API token"
    finally:
        server_module._API_TOKEN = old_token
