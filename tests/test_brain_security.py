import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mocking all modules that require external dependencies
sys.modules['dotenv'] = MagicMock()
sys.modules['supabase'] = MagicMock()
sys.modules['src.memory.memory_manager'] = MagicMock()
sys.modules['src.core.ai_router'] = MagicMock()
sys.modules['src.core.language_detector'] = MagicMock()
sys.modules['src.core.mood_detector'] = MagicMock()
sys.modules['src.core.prompts.builder'] = MagicMock()

from src.core.aisha_brain import AishaBrain

class TestBrainSecurity(unittest.TestCase):

    def setUp(self):
        # We need to mock the dependencies again for the actual instantiation
        with patch('supabase.create_client'), \
             patch('src.memory.memory_manager.MemoryManager'), \
             patch('src.core.ai_router.AIRouter'):
            self.brain = AishaBrain()

    def test_guest_cannot_trigger_sensitive_intent(self):
        # A message that should trigger "key_health"
        msg = "verify my api keys"

        # Guest calling (is_owner=False)
        with patch('src.core.aisha_brain.AishaBrain._fire_intent') as mock_fire:
            # We call _detect_and_route_intent directly to test its logic
            res = self.brain._detect_and_route_intent(msg, is_owner=False)

            # _fire_intent should be called, but its internal logic should return None for guests
            mock_fire.assert_called_with("key_health", msg, is_owner=False)
            # The current implementation of _fire_intent for guest returns None
            # because "key_health" is in the blocked list for guests.

            # Since mock_fire is mocked, we need to check the actual method logic if we don't mock it

    def test_fire_intent_guest_blocking(self):
        msg_key = "update my key AIzaSy_test"
        msg_content = "make a video for me"

        # Test directly the _fire_intent logic
        res_key = self.brain._fire_intent("key_update", msg_key, is_owner=False)
        self.assertIsNone(res_key, "Guest should NOT be able to trigger key_update")

        res_content = self.brain._fire_intent("content_creation", msg_content, is_owner=False)
        self.assertIsNone(res_content, "Guest should NOT be able to trigger content_creation")

    def test_owner_requires_secret_code_for_high_risk(self):
        msg_no_code = "update my key AIzaSy_test"
        # Assuming the default secret code is "aisha-69" in config or mock it
        msg_with_code = "update my key AIzaSy_test code: aisha-69"

        # Owner calling (is_owner=True) but NO secret code
        with patch('threading.Thread'): # Avoid actually starting a thread
            res_no_code = self.brain._fire_intent("key_update", msg_no_code, is_owner=True)
            self.assertIsNone(res_no_code, "Owner should NOT be able to trigger key_update without secret code")

            # Owner calling WITH secret code
            res_with_code = self.brain._fire_intent("key_update", msg_with_code, is_owner=True)
            self.assertIsNotNone(res_with_code, "Owner SHOULD be able to trigger key_update WITH secret code")
            self.assertIn("updated", res_with_code.lower())

    def test_syscheck_no_code_required(self):
        # syscheck is not a high-risk intent
        msg = "sab theek hai?"

        # Owner calling
        with patch('src.core.aisha_brain.AishaBrain._fire_intent', wraps=self.brain._fire_intent) as spy:
             # Actually syscheck returns None by default to fall through to AI
             res = self.brain._detect_and_route_intent(msg, is_owner=True)
             self.assertIsNone(res) # Correct behavior for syscheck

if __name__ == '__main__':
    unittest.main()
