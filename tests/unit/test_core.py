import pytest
from unittest.mock import MagicMock, patch
from src.core.ai_router import AIRouter, AIResult
from src.core.aisha_brain import AishaBrain

class TestAIRouter:
    def test_router_initialization(self):
        """Test AIRouter init creates stats for all providers."""
        with patch("src.core.ai_router.AIRouter._init_clients"):
            router = AIRouter()
            assert "gemini" in router._stats
            assert "groq" in router._stats
            assert "nvidia" in router._stats

    @patch("src.core.ai_router.AIRouter._init_clients")
    def test_router_generate_success(self, mock_init):
        """Test generate loops providers correctly until success."""
        router = AIRouter()
        router._clients = {"gemini": MagicMock(), "groq": MagicMock()}

        with patch.object(router, '_call_gemini') as mock_gemini:
            mock_gemini.return_value = "Gemini response"

            result = router.generate("System", "User msg")

            assert result.provider == "gemini"
            assert result.text == "Gemini response"
            mock_gemini.assert_called_once()

    @patch("src.core.ai_router.AIRouter._init_clients")
    def test_router_generate_fallback(self, mock_init):
        """Test generate falls back if a provider fails."""
        router = AIRouter()
        router._clients = {"gemini": MagicMock(), "nvidia": MagicMock()}

        with patch.object(router, '_call_gemini') as mock_gemini, \
             patch.object(router, '_call_nvidia') as mock_nvidia:

            # Gemini fails
            mock_gemini.side_effect = Exception("Gemini down")
            # Nvidia succeeds
            mock_nvidia.return_value = "Nvidia response"

            result = router.generate("System", "User msg", preferred_provider="gemini")

            assert result.provider == "nvidia"
            assert result.text == "Nvidia response"

class TestAishaBrain:
    @patch("src.core.aisha_brain.MemoryManager")
    @patch("src.core.aisha_brain.AIRouter")
    @patch("src.core.aisha_brain.create_client")
    def test_brain_initialization(self, mock_create_client, mock_ai_router, mock_memory_manager, monkeypatch):
        """Test AishaBrain initializes core components."""
        monkeypatch.setenv("SUPABASE_URL", "http://test")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")

        brain = AishaBrain()
        assert brain.ai is not None
        assert brain.supabase is not None
        assert brain.memory is not None

    @patch("src.core.aisha_brain.MemoryManager")
    @patch("src.core.aisha_brain.AIRouter")
    @patch("src.core.aisha_brain.create_client")
    def test_brain_think(self, mock_create_client, mock_ai_router, mock_memory_manager, monkeypatch):
        """Test core think method orchestrates components."""
        monkeypatch.setenv("SUPABASE_URL", "http://test")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")

        brain = AishaBrain()

        # Mock Router response
        mock_result = AIResult(text="I am thinking", provider="gemini", model="gemini-2.5", latency_ms=100)
        brain.ai.generate.return_value = mock_result

        # Mock Memory Context
        brain.memory.load_context.return_value = {
            "profile": {"name": "TestUser"},
            "memories": "",
            "today_tasks": "",
            "today_expenses": ""
        }

        # Mock Intent detection to avoid spawning threads
        with patch.object(brain, "_detect_and_route_intent", return_value=None):
            # Act
            response = brain.think("Hello Aisha", caller_id=123)

            # Assert
            assert response == "I am thinking"
            brain.ai.generate.assert_called_once()
            brain.memory.load_context.assert_called()

    @patch("src.core.aisha_brain.MemoryManager")
    @patch("src.core.aisha_brain.AIRouter")
    @patch("src.core.aisha_brain.create_client")
    def test_brain_history_management(self, mock_create_client, mock_ai_router, mock_memory_manager, monkeypatch):
        """Test history correctly manages multiple users."""
        monkeypatch.setenv("SUPABASE_URL", "http://test")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")

        # Provide a mock owner ID
        with patch("src.core.aisha_brain.AishaBrain._get_owner_id", return_value=999), \
             patch.object(AishaBrain, "_load_history_from_db", return_value=[]):
            brain = AishaBrain()

        # History should be empty initially
        history_123 = brain._get_user_history(123, is_owner=False)
        assert history_123 == []

        # Reset session
        brain.reset_session(caller_id=123)
        assert brain._histories[123] == []
