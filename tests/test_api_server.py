import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from unittest.mock import patch, MagicMock
import sys

# Mock AishaBrain and create_client BEFORE importing src.api.server
# This is required because server.py initializes AishaBrain at module level
sys.modules['src.core.aisha_brain'] = MagicMock()
sys.modules['supabase'] = MagicMock()

from src.api.server import verify_token

def test_verify_token_no_token_configured():
    with patch("src.api.server._API_TOKEN", ""):
        assert verify_token(None) is True
        assert verify_token(HTTPAuthorizationCredentials(scheme="Bearer", credentials="any")) is True

def test_verify_token_invalid_token():
    with patch("src.api.server._API_TOKEN", "secret"):
        with pytest.raises(HTTPException) as exc_info:
            verify_token(None)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid or missing API token"

        with pytest.raises(HTTPException) as exc_info:
            verify_token(HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong"))
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid or missing API token"

def test_verify_token_valid_token():
    with patch("src.api.server._API_TOKEN", "secret"):
        assert verify_token(HTTPAuthorizationCredentials(scheme="Bearer", credentials="secret")) is True
