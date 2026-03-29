import unittest
from unittest.mock import patch, MagicMock
from src.core.ai_router import AIRouter, AIResult

class TestAIRouter(unittest.TestCase):

    @patch('src.core.ai_router.os.getenv')
    def test_fallback_chain(self, mock_getenv):
        router = AIRouter()

        router._clients = {
            "gemini": MagicMock(),
            "anthropic": MagicMock(),
            "groq": MagicMock()
        }

        def mock_call_provider(provider, system, user, history, image=None, tools=None):
            if provider == "gemini":
                raise Exception("Rate limit exceeded")
            if provider == "openai":
                raise Exception("Rate limit exceeded")
            if provider == "groq":
                raise Exception("Rate limit exceeded")
            if provider == "xai":
                raise Exception("Rate limit exceeded")
            if provider == "anthropic":
                return "Claude response", None
            return "Other response", None

        router._call_provider = mock_call_provider

        result = router.generate("system", "user")

        self.assertEqual(result.provider, "anthropic")
        self.assertEqual(result.text, "Claude response")

        self.assertTrue(router._stats["gemini"].is_cooling_down())

    def test_all_fail(self):
        router = AIRouter()
        router._clients = {"gemini": MagicMock()}

        def mock_call_provider(*args, **kwargs):
            raise Exception("API Down")

        router._call_provider = mock_call_provider

        result = router.generate("system", "user")

        self.assertEqual(result.provider, "fallback")
        self.assertIn("all my AI brains are taking a nap", result.text)

if __name__ == '__main__':
    unittest.main()
