import unittest
from unittest.mock import MagicMock
from src.memory.memory_manager import MemoryManager

class TestMemoryIsolation(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.mm = MemoryManager(supabase=self.mock_db)

    def test_save_conversation_isolation(self):
        # When we save a conversation with telegram_id=123, it should be in the insert payload
        self.mm.save_conversation(
            role="user",
            message="Hello",
            platform="telegram",
            telegram_id=12345
        )

        self.mock_db.table.assert_called_with("aisha_conversations")
        insert_data = self.mock_db.table.return_value.insert.call_args[0][0]
        self.assertEqual(insert_data["telegram_id"], 12345)
        self.assertEqual(insert_data["message"], "Hello")

    def test_get_recent_conversation_isolation(self):
        # When we fetch recent conversations, it should filter by telegram_id=123
        self.mm.get_recent_conversation(limit=5, telegram_id=12345)

        self.mock_db.table.assert_called_with("aisha_conversations")
        # Check that .eq("telegram_id", 12345) was called on the query builder
        self.mock_db.table.return_value.select.return_value.eq.assert_called_with("telegram_id", 12345)

if __name__ == '__main__':
    unittest.main()
