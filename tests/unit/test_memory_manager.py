import pytest
from unittest.mock import MagicMock, patch
from src.memory.memory_manager import MemoryManager

@pytest.fixture
def memory_manager(mock_env_vars, mock_supabase_client):
    """Fixture providing a MemoryManager instance with mocked Supabase."""
    # MemoryManager expects SUPABASE_SERVICE_KEY, not SUPABASE_KEY
    with patch.dict("os.environ", {"SUPABASE_SERVICE_KEY": "test-service-key"}):
        manager = MemoryManager(supabase=mock_supabase_client)
        return manager

class TestMemoryManager:
    def test_init_with_client(self, mock_supabase_client):
        """Test initialization with an explicit client."""
        manager = MemoryManager(supabase=mock_supabase_client)
        assert manager.db == mock_supabase_client

    def test_init_with_env_vars(self):
        """Test initialization via environment variables."""
        with patch.dict("os.environ", {"SUPABASE_URL": "test-url", "SUPABASE_SERVICE_KEY": "test-key"}), \
             patch("src.memory.memory_manager.create_client") as mock_create:
            mock_create.return_value = MagicMock()
            manager = MemoryManager()
            mock_create.assert_called_once_with("test-url", "test-key")
            assert manager.db == mock_create.return_value

    def test_init_missing_env_vars(self):
        """Test initialization fails when env vars are missing."""
        with patch.dict("os.environ", clear=True):
            with pytest.raises(ValueError, match="SUPABASE_URL and SUPABASE_SERVICE_KEY must be set"):
                MemoryManager()

    def test_get_profile_success(self, memory_manager):
        """Test retrieving a user profile successfully."""
        mock_response = MagicMock()
        mock_response.data = [{"name": "Ajay", "preferences": {}}]

        # Chain mock: table().select().limit().execute()
        memory_manager.db.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_response

        profile = memory_manager.get_profile()
        assert profile == {"name": "Ajay", "preferences": {}}
        memory_manager.db.table.assert_called_with("ajay_profile")

    def test_get_profile_empty(self, memory_manager):
        """Test retrieving profile when no data is returned."""
        mock_response = MagicMock()
        mock_response.data = []
        memory_manager.db.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_response

        profile = memory_manager.get_profile()
        assert profile == {}

    def test_get_profile_exception(self, memory_manager):
        """Test retrieving profile handles exceptions safely."""
        memory_manager.db.table.side_effect = Exception("DB Error")

        profile = memory_manager.get_profile()
        assert profile == {}

    @patch("src.memory.memory_manager.MemoryManager._generate_embedding")
    def test_save_memory(self, mock_generate_embedding, memory_manager):
        """Test saving a standard memory, verifying database calls."""
        mock_generate_embedding.return_value = [0.1, 0.2, 0.3]

        memory_manager.save_memory(
            category="finance",
            title="Salary Update",
            content="Received new salary",
            importance=4,
            tags=["income", "update"]
        )

        expected_row = {
            "category": "finance",
            "title": "Salary Update",
            "content": "Received new salary",
            "importance": 4,
            "tags": ["income", "update"],
            "source": "conversation",
            "embedding": [0.1, 0.2, 0.3]
        }

        memory_manager.db.table.assert_called_with("aisha_memory")
        memory_manager.db.table.return_value.insert.assert_called_with(expected_row)
        memory_manager.db.table.return_value.insert.return_value.execute.assert_called_once()

    @patch("src.memory.memory_manager.MemoryManager._generate_embedding")
    def test_save_memory_no_embedding(self, mock_generate_embedding, memory_manager):
        """Test saving a memory gracefully handles embedding failures."""
        mock_generate_embedding.return_value = None

        memory_manager.save_memory(
            category="general",
            title="Random thought",
            content="I like turtles"
        )

        # Expected row shouldn't have 'embedding'
        expected_row = {
            "category": "general",
            "title": "Random thought",
            "content": "I like turtles",
            "importance": 3,
            "tags": [],
            "source": "conversation",
        }

        memory_manager.db.table.return_value.insert.assert_called_with(expected_row)

    def test_save_conversation(self, memory_manager):
        """Test logging conversation turns."""
        memory_manager.save_conversation("user", "Hello there!")

        expected_row = {
            "platform": "telegram",
            "role": "user",
            "message": "Hello there!",
            "language": "English",
            "mood_detected": "casual",
        }

        memory_manager.db.table.assert_called_with("aisha_conversations")
        memory_manager.db.table.return_value.insert.assert_called_with(expected_row)

    def test_save_conversation_guest(self, memory_manager):
         """Test logging conversation turn with a guest_user_id."""
         memory_manager.save_conversation("user", "I am a guest", user_id=12345)

         expected_row = {
            "platform": "telegram",
            "role": "user",
            "message": "I am a guest",
            "language": "English",
            "mood_detected": "casual",
            "guest_user_id": 12345
         }
         memory_manager.db.table.return_value.insert.assert_called_with(expected_row)

    def test_get_recent_conversation_owner(self, memory_manager):
        """Test fetching conversation for owner (null guest id)."""
        mock_response = MagicMock()
        mock_response.data = [{"role": "user", "message": "hello"}, {"role": "ai", "message": "hi"}]

        mock_query = memory_manager.db.table.return_value.select.return_value
        mock_query.is_.return_value.order.return_value.limit.return_value.execute.return_value = mock_response

        conv = memory_manager.get_recent_conversation(limit=2)

        # Should reverse the results
        assert conv == [{"role": "ai", "message": "hi"}, {"role": "user", "message": "hello"}]
        mock_query.is_.assert_called_with("guest_user_id", "null")

    def test_get_recent_conversation_guest(self, memory_manager):
        """Test fetching conversation for guest."""
        mock_response = MagicMock()
        mock_response.data = [{"role": "user", "message": "guest message"}]

        mock_query = memory_manager.db.table.return_value.select.return_value
        mock_query.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_response

        conv = memory_manager.get_recent_conversation(limit=1, user_id=999)

        assert conv == [{"role": "user", "message": "guest message"}]
        mock_query.eq.assert_called_with("guest_user_id", 999)

    @patch("src.memory.memory_manager.MemoryManager.get_profile")
    @patch("src.memory.memory_manager.MemoryManager.get_top_memories")
    def test_load_context(self, mock_top_mems, mock_get_profile, memory_manager):
        """Test the context loader aggregates data correctly."""
        mock_get_profile.return_value = {"name": "Ajay"}
        mock_top_mems.return_value = [
            {"category": "preference", "title": "Food", "content": "Likes pizza"}
        ]

        # Mocking db calls for schedule and finance
        mock_tasks_res = MagicMock()
        mock_tasks_res.data = [{"title": "Work", "priority": "high"}]

        mock_fin_res = MagicMock()
        mock_fin_res.data = [{"amount": 100, "category": "food", "description": "pizza"}]

        # This is a bit tricky, the table() call happens twice, so we mock side_effect based on args
        def mock_table(table_name):
            mock_table_obj = MagicMock()
            if table_name == "aisha_schedule":
                mock_table_obj.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_tasks_res
            elif table_name == "aisha_finance":
                 mock_table_obj.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_fin_res
            return mock_table_obj

        memory_manager.db.table.side_effect = mock_table

        context = memory_manager.load_context()

        assert context["profile"] == {"name": "Ajay"}
        assert "Likes pizza" in context["memories"]
        assert "Work" in context["today_tasks"]
        assert "100" in context["today_expenses"]
