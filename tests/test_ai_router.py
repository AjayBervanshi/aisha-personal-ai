import unittest
from unittest.mock import patch, MagicMock
from src.core.ai_router import AIRouter, AIResult

class TestAIRouter(unittest.TestCase):

    @patch('src.core.ai_router.os.getenv')
    def test_fallback_chain(self, mock_getenv):
        # We want to simulate having Gemini and Anthropic keys, but Groq fails.
        # Actually, let's mock the clients being initialized
        router = AIRouter()

        # Mock that we have gemini, anthropic, and groq clients
        router._clients = {
            "gemini": MagicMock(),
            "anthropic": MagicMock(),
            "groq": MagicMock()
        }

        # Make Gemini and Groq fail — router order is gemini→groq→anthropic
        def mock_call_provider(provider, system, user, history, image, **kwargs):
            if provider in ("gemini", "groq"):
                raise Exception("Rate limit exceeded")
            if provider == "anthropic":
                return "Claude response"
            return "Other response"

        router._call_provider = mock_call_provider

        result = router.generate("system", "user")

        # Should fallback to anthropic (gemini + groq both fail first)
        self.assertEqual(result.provider, "anthropic")
        self.assertEqual(result.text, "Claude response")

        # Check that Gemini is now cooling down
        self.assertTrue(router._stats["gemini"].is_cooling_down())

    def test_all_fail(self):
        router = AIRouter()
        router._clients = {"gemini": MagicMock()}

        def mock_call_provider(*args, **kwargs):
            raise Exception("API Down")

        router._call_provider = mock_call_provider

        result = router.generate("system", "user")

        self.assertEqual(result.provider, "fallback")
        # Fallback message for non-owner — generic connection issue wording
        self.assertIn("temporary", result.text.lower())

if __name__ == '__main__':
    unittest.main()
