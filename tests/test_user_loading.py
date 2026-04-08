import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.getcwd())

# Mock necessary modules before importing bot
sys.modules['telebot'] = MagicMock()
sys.modules['telebot.types'] = MagicMock()
sys.modules['supabase'] = MagicMock()
sys.modules['pytz'] = MagicMock()
sys.modules['src.core.aisha_brain'] = MagicMock()
sys.modules['src.core.voice_engine'] = MagicMock()
sys.modules['dotenv'] = MagicMock()

import src.telegram.bot as bot

class TestUserLoading(unittest.TestCase):
    @patch('src.telegram.bot.db')
    def test_load_users_from_db_logic(self, mock_db):
        # 1. Setup mock data
        rbac_data = [
            {"telegram_user_id": 1, "role": "admin"},
            {"telegram_user_id": 2, "role": "guest"}
        ]
        legacy_data = [
            {"telegram_user_id": 2}, # Already in RBAC
            {"telegram_user_id": 3}  # New legacy user
        ]

        # Mock Supabase responses
        mock_f1 = MagicMock()
        mock_f1.data = rbac_data
        mock_f2 = MagicMock()
        mock_f2.data = legacy_data

        # We need to mock the chained calls: db.table().select().execute()
        # and db.table().select().eq().execute()

        def mock_table(name):
            mock_select = MagicMock()
            mock_select.select.return_value = mock_select
            mock_select.eq.return_value = mock_select
            if name == "aisha_users":
                mock_select.execute.return_value = mock_f1
            else:
                mock_select.execute.return_value = mock_f2
            return mock_select

        mock_db.table.side_effect = mock_table

        # Reset global state
        bot._user_roles = {}
        bot._approved_users = set()

        # 2. Run the function
        bot.load_users_from_db()

        # 3. Verify logic
        # Expected:
        # 1: admin (from RBAC)
        # 2: guest (from RBAC, not overridden by legacy)
        # 3: guest (from legacy)

        self.assertEqual(bot._user_roles[1], "admin")
        self.assertEqual(bot._user_roles[2], "guest")
        self.assertEqual(bot._user_roles[3], "guest")
        self.assertIn(1, bot._approved_users)
        self.assertIn(2, bot._approved_users)
        self.assertIn(3, bot._approved_users)
        self.assertEqual(len(bot._approved_users), 3)

if __name__ == "__main__":
    unittest.main()
