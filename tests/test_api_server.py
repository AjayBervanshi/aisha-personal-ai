import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock module-level dependencies before importing the server
sys.modules['src.core.aisha_brain'] = MagicMock()

from fastapi import HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials
from src.api.server import verify_token
import src.api.server

class TestApiServerAuth(unittest.TestCase):
    def test_verify_token_dev_mode(self):
        # Set _API_TOKEN to empty
        with patch.object(src.api.server, '_API_TOKEN', ''):
            self.assertTrue(verify_token(None))
            self.assertTrue(verify_token(HTTPAuthorizationCredentials(scheme="Bearer", credentials="foo")))

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


from fastapi.testclient import TestClient
from src.api.server import app

@app.get("/test-verify-token")
def dummy_route(_auth=Depends(verify_token)):
    return {"status": "ok"}

client = TestClient(app)

class TestApiClient(unittest.TestCase):
    def test_verify_token_dev_mode(self):
        with patch.object(src.api.server, '_API_TOKEN', ''):
            response = client.get("/test-verify-token")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"status": "ok"})

    def test_verify_token_prod_missing_credentials(self):
        with patch.object(src.api.server, '_API_TOKEN', 'secret123'):
            response = client.get("/test-verify-token")
            # HTTPBearer with auto_error=False returns None for credentials.
            # verify_token then raises 401.
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()["detail"], "Invalid or missing API token")

    def test_verify_token_prod_invalid_credentials(self):
        with patch.object(src.api.server, '_API_TOKEN', 'secret123'):
            response = client.get("/test-verify-token", headers={"Authorization": "Bearer wrong_token"})
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()["detail"], "Invalid or missing API token")

    def test_verify_token_prod_valid_credentials(self):
        with patch.object(src.api.server, '_API_TOKEN', 'secret123'):
            response = client.get("/test-verify-token", headers={"Authorization": "Bearer secret123"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"status": "ok"})

if __name__ == '__main__':
    unittest.main()
