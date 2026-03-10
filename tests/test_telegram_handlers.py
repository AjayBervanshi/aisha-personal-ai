import unittest
from unittest.mock import patch, MagicMock

# We must mock environment variables before importing bot
with patch('os.getenv') as mock_getenv:
    def side_effect(key, default=None):
        if key == "TELEGRAM_BOT_TOKEN": return "123:ABC"
        if key == "SUPABASE_URL": return "http://test.com"
        if key == "SUPABASE_SERVICE_KEY": return "testkey"
        if key == "AJAY_TELEGRAM_ID": return "12345"
        return default
    mock_getenv.side_effect = side_effect

    with patch('src.core.aisha_brain.create_client'):
        with patch('src.telegram.bot.telebot'):
            with patch('src.telegram.bot.AishaBrain'):
                with patch('src.telegram.bot.create_client'):
                    from src.telegram.bot import cmd_start, cmd_help, handle_text, is_ajay, AUTHORIZED_ID

class TestTelegramHandlers(unittest.TestCase):

    @patch('src.telegram.bot.bot')
    def test_unauthorized_user(self, mock_bot):
        msg = MagicMock()
        msg.from_user.id = 9999999

        import src.telegram.bot as bot_module
        original_id = bot_module.AUTHORIZED_ID
        bot_module.AUTHORIZED_ID = 12345

        try:
            cmd_start(msg)
            mock_bot.reply_to.assert_called_once()
            self.assertIn("Aisha is a private assistant", mock_bot.reply_to.call_args[0][1])
        finally:
            bot_module.AUTHORIZED_ID = original_id

    @patch('src.telegram.bot.bot')
    def test_authorized_user_start(self, mock_bot):
        msg = MagicMock()
        msg.from_user.id = 12345
        msg.chat.id = 1

        import src.telegram.bot as bot_module
        original_id = bot_module.AUTHORIZED_ID
        bot_module.AUTHORIZED_ID = 12345

        try:
            cmd_start(msg)
            mock_bot.send_message.assert_called_once()
            self.assertIn("I'm Aisha — your personal companion", mock_bot.send_message.call_args[0][1])
        finally:
            bot_module.AUTHORIZED_ID = original_id

if __name__ == '__main__':
    unittest.main()
