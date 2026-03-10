import unittest
from unittest.mock import MagicMock, patch
from src.memory.memory_manager import MemoryManager

class TestMemoryManager(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.mm = MemoryManager(supabase=self.mock_db)

    def test_get_profile(self):
        mock_profile = MagicMock()
        mock_profile.data = [{"name": "Ajay", "current_mood": "casual"}]

        self.mock_db.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_profile

        profile = self.mm.get_profile()
        self.assertEqual(profile["name"], "Ajay")
        self.assertEqual(profile["current_mood"], "casual")

    @patch('src.memory.memory_manager.MemoryManager._generate_embedding')
    def test_save_memory(self, mock_embed):
        mock_embed.return_value = [0.1] * 768
        self.mm.save_memory("preference", "Coffee", "Loves black coffee", 4)

        self.mock_db.table.assert_called_with("aisha_memory")
        self.mock_db.table.return_value.insert.assert_called()

    @patch('src.memory.memory_manager.MemoryManager._generate_embedding')
    def test_semantic_search(self, mock_embed):
        mock_embed.return_value = [0.1] * 768
        mock_result = MagicMock()
        mock_result.data = [{"title": "Coffee", "content": "Loves black coffee", "similarity": 0.9}]
        self.mock_db.rpc.return_value.execute.return_value = mock_result

        results = self.mm.get_semantic_memories("Does he like coffee?")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Coffee")
        self.mock_db.rpc.assert_called_with('match_memories', {'query_embedding': [0.1] * 768, 'match_threshold': 0.7, 'match_count': 5})

if __name__ == '__main__':
    unittest.main()
