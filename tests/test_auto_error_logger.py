import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add src to path if necessary
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from skills.auto_error_logger import AutoErrorLogger, main

class TestAutoErrorLogger(unittest.TestCase):

    def setUp(self):
        self.notification_config = {
            'from': 'test_from@example.com',
            'to': 'test_to@example.com',
            'smtp_server': 'smtp.test.com',
            'smtp_port': 465,
            'password': 'test_password'
        }

    def test_init(self):
        logger = AutoErrorLogger(self.notification_config)
        self.assertEqual(logger.notification_config, self.notification_config)

    @patch('smtplib.SMTP_SSL')
    def test_send_notification(self, mock_smtp):
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance

        logger = AutoErrorLogger(self.notification_config)
        logger.send_notification("Test Error")

        mock_smtp.assert_called_with('smtp.test.com', 465)
        mock_smtp_instance.login.assert_called_with('test_from@example.com', 'test_password')
        mock_smtp_instance.send_message.assert_called()

    @patch.dict(os.environ, {
        'SMTP_FROM': 'env_from@example.com',
        'SMTP_TO': 'env_to@example.com',
        'SMTP_SERVER': 'env_smtp.example.com',
        'SMTP_PORT': '587',
        'SMTP_PASSWORD': 'env_password'
    })
    @patch('skills.auto_error_logger.AutoErrorLogger')
    def test_main_uses_env_vars(self, MockLogger):
        # We need to re-import or reload because of how main is structured,
        # but here we can just test if the config passed to MockLogger is correct
        from skills.auto_error_logger import main

        # We also need to mock handle_exception to avoid actual execution if it gets called
        with patch('skills.auto_error_logger.AutoErrorLogger.handle_exception') as mock_handle:
            main()

            # Check if MockLogger was instantiated with values from environment
            MockLogger.assert_called()
            args, kwargs = MockLogger.call_args
            config = args[0]

            self.assertEqual(config['from'], 'env_from@example.com')
            self.assertEqual(config['to'], 'env_to@example.com')
            self.assertEqual(config['smtp_server'], 'env_smtp.example.com')
            self.assertEqual(config['smtp_port'], 587)
            self.assertEqual(config['password'], 'env_password')

    @patch.dict(os.environ, {}, clear=True)
    @patch('skills.auto_error_logger.AutoErrorLogger')
    def test_main_uses_defaults_when_env_vars_missing(self, MockLogger):
        from skills.auto_error_logger import main

        main()

        MockLogger.assert_called()
        args, kwargs = MockLogger.call_args
        config = args[0]

        self.assertIsNone(config['from'])
        self.assertIsNone(config['to'])
        self.assertIsNone(config['smtp_server'])
        self.assertEqual(config['smtp_port'], 465)
        self.assertIsNone(config['password'])

if __name__ == '__main__':
    unittest.main()
