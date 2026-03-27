import unittest
from unittest.mock import patch, MagicMock
from src.core.aisha_brain import AishaBrain, MemoryManager

class TestAishaBrain(unittest.TestCase):
    @patch('src.core.aisha_brain.create_client')
    @patch('src.core.aisha_brain.AIRouter')
    def test_think_pipeline(self, mock_router_cls, mock_create_client):
        mock_router = mock_router_cls.return_value

        mock_result = MagicMock()
        mock_result.text = '{"extract": false}' # Valid JSON for the second call

        def mock_generate(*args, **kwargs):
            # First call is the AI response, second is the memory extractor
            if "expert JSON parser" in kwargs.get("system_prompt", ""):
                m = MagicMock()
                m.text = '{"extract": false}'
                return m
            else:
                m = MagicMock()
                m.text = "This is a mocked response from AI"
                return m

        mock_router.generate.side_effect = mock_generate

        with patch.object(MemoryManager, 'load_context') as mock_load_context, \
             patch.object(MemoryManager, 'save_conversation') as mock_save_conv, \
             patch.object(MemoryManager, 'update_mood') as mock_update_mood:

            mock_load_context.return_value = {
                "profile": {"name": "Ajay"},
                "memories": "No memories",
                "today_tasks": "No tasks"
            }

            brain = AishaBrain()
            response = brain.think("Hello Aisha")

            self.assertEqual(response, "This is a mocked response from AI")
            # Memory extraction runs in a background thread — at least 1 call guaranteed
            self.assertGreaterEqual(mock_router.generate.call_count, 1)
            mock_load_context.assert_called_once()
            # save_conversation called for user + assistant turns (2 min)
            self.assertGreaterEqual(mock_save_conv.call_count, 2)
            mock_update_mood.assert_called_once()

if __name__ == '__main__':
    unittest.main()
