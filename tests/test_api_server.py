import unittest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
import os

# Set dummy env vars for AishaBrain initialization during import if needed
os.environ["SUPABASE_URL"] = "https://example.supabase.co"
os.environ["SUPABASE_SERVICE_KEY"] = "dummy-key"
os.environ["GEMINI_API_KEY"] = "dummy-key"

from src.api.server import app, verify_token

class TestVerifyToken(unittest.TestCase):
    def test_verify_token_no_token_configured(self):
        """Test verify_token when no API_SECRET_TOKEN is set (dev mode)."""
        with patch("src.api.server._API_TOKEN", ""):
            # Should return True regardless of credentials
            self.assertTrue(verify_token(None))

            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="any")
            self.assertTrue(verify_token(credentials))

    def test_verify_token_valid_token(self):
        """Test verify_token with a valid token."""
        token = "secret-token"
        with patch("src.api.server._API_TOKEN", token):
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
            self.assertTrue(verify_token(credentials))

    def test_verify_token_invalid_token(self):
        """Test verify_token with an invalid token."""
        token = "secret-token"
        with patch("src.api.server._API_TOKEN", token):
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong-token")
            with self.assertRaises(HTTPException) as cm:
                verify_token(credentials)
            self.assertEqual(cm.exception.status_code, 401)
            self.assertEqual(cm.exception.detail, "Invalid or missing API token")

    def test_verify_token_missing_credentials(self):
        """Test verify_token when credentials are missing."""
        token = "secret-token"
        with patch("src.api.server._API_TOKEN", token):
            with self.assertRaises(HTTPException) as cm:
                verify_token(None)
            self.assertEqual(cm.exception.status_code, 401)
            self.assertEqual(cm.exception.detail, "Invalid or missing API token")

class TestApiAuthIntegration(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.token = "test-secret-token"

    @patch("src.api.server._API_TOKEN", "test-secret-token")
    @patch("src.api.server.aisha")
    def test_protected_endpoints_missing_token(self, mock_aisha):
        """Test that protected endpoints return 401 when no token is provided."""
        endpoints = [
            ("POST", "/chat", {"message": "hi"}),
            ("GET", "/digest", None),
            ("GET", "/health-summary", None),
            ("POST", "/log-health", {"metric": "water", "value": "3"}),
        ]

        for method, path, json_data in endpoints:
            if method == "POST":
                response = self.client.post(path, json=json_data)
            else:
                response = self.client.get(path)

            self.assertEqual(response.status_code, 401, f"Endpoint {path} did not return 401")
            self.assertEqual(response.json()["detail"], "Invalid or missing API token")

    @patch("src.api.server._API_TOKEN", "test-secret-token")
    @patch("src.api.server.aisha")
    def test_protected_endpoints_invalid_token(self, mock_aisha):
        """Test that protected endpoints return 401 when an invalid token is provided."""
        headers = {"Authorization": "Bearer wrong-token"}
        endpoints = [
            ("POST", "/chat", {"message": "hi"}),
            ("GET", "/digest", None),
            ("GET", "/health-summary", None),
            ("POST", "/log-health", {"metric": "water", "value": "3"}),
        ]

        for method, path, json_data in endpoints:
            if method == "POST":
                response = self.client.post(path, json=json_data, headers=headers)
            else:
                response = self.client.get(path, headers=headers)

            self.assertEqual(response.status_code, 401, f"Endpoint {path} did not return 401")
            self.assertEqual(response.json()["detail"], "Invalid or missing API token")

    @patch("src.api.server._API_TOKEN", "test-secret-token")
    @patch("src.api.server.aisha")
    @patch("src.api.server.rate_limit")
    def test_protected_endpoints_valid_token(self, mock_rate_limit, mock_aisha):
        """Test that protected endpoints allow access with a valid token."""
        # Mocking AishaBrain.think for /chat
        mock_aisha.think.return_value = "Hello Ajay"

        # Mocking DigestEngine and HealthTracker for other endpoints
        with patch("src.core.digest_engine.DigestEngine") as mock_digest_engine, \
             patch("src.core.health_tracker.HealthTracker") as mock_health_tracker:

            mock_digest_engine.return_value.generate_daily_digest.return_value = "Daily digest content"
            mock_health_tracker.return_value.get_daily_summary.return_value = {"summary": "health summary"}

            headers = {"Authorization": f"Bearer {self.token}"}

            # Test /chat
            response = self.client.post("/chat", json={"message": "hi"}, headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"reply": "Hello Ajay"})

            # Test /digest
            response = self.client.get("/digest", headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"digest": "Daily digest content"})

            # Test /health-summary
            response = self.client.get("/health-summary", headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"summary": "health summary"})

            # Test /log-health
            response = self.client.post("/log-health", json={"metric": "water", "value": "3"}, headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"ok": True})

if __name__ == "__main__":
    unittest.main()
