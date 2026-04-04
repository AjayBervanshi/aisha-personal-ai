import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock module-level dependencies before importing the server
sys.modules['src.core.aisha_brain'] = MagicMock()

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from src.api.server import verify_token
import src.api.server

class TestApiServerAuth(unittest.TestCase):
    def test_verify_token_dev_mode(self):
        # Set _API_TOKEN to empty
        with patch.object(src.api.server, '_API_TOKEN', ''), patch.object(src.api.server, 'IS_DEV', True):
            self.assertTrue(verify_token(None))
            self.assertTrue(verify_token(HTTPAuthorizationCredentials(scheme="Bearer", credentials="foo")))

    def test_verify_token_prod_missing_token_env_var(self):
        with patch.object(src.api.server, '_API_TOKEN', ''), patch.object(src.api.server, 'IS_DEV', False):
            with self.assertRaises(HTTPException) as cm:
                verify_token(None)
            self.assertEqual(cm.exception.status_code, 401)
            self.assertEqual(cm.exception.detail, "Server configuration error: API authentication is required but not configured")

    def test_verify_token_prod_missing_credentials(self):
        with patch.object(src.api.server, '_API_TOKEN', 'secret123'):
            with self.assertRaises(HTTPException) as cm:
                verify_token(None)
            self.assertEqual(cm.exception.status_code, 401)
            self.assertEqual(cm.exception.detail, "Invalid or missing API token")

    def test_verify_token_prod_invalid_credentials(self):
        with patch.object(src.api.server, '_API_TOKEN', 'secret123'):
            creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong_password")
            with self.assertRaises(HTTPException) as cm:
                verify_token(creds)
            self.assertEqual(cm.exception.status_code, 401)
            self.assertEqual(cm.exception.detail, "Invalid or missing API token")

    def test_verify_token_prod_valid_credentials(self):
        with patch.object(src.api.server, '_API_TOKEN', 'secret123'):
            creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="secret123")
            self.assertTrue(verify_token(creds))

if __name__ == '__main__':
    unittest.main()
