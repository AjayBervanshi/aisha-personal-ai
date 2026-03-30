import os
import logging
import smtplib
from email.message import EmailMessage
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AutoErrorNotifier:
    """
    A standalone Python module that integrates with the existing autonomous loop code to send notifications when errors occur.
    
    This module provides a flexible way to configure notification channels, such as email or messaging platforms, and allows for customizable error messages.
    
    It also includes logging to track when notifications are sent and to what channels, to ensure that errors are properly documented and can be investigated later.
    """

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def send_email_notification(self, subject, message):
        try:
            msg = EmailMessage()
            msg.set_content(message)
            msg['subject'] = subject
            msg['to'] = self.config['email']['to']
            msg['from'] = self.config['email']['from']
            server = smtplib.SMTP(self.config['email']['smtp_server'])
            server.starttls()
            server.login(self.config['email']['from'], self.config['email']['password'])
            server.send_message(msg)
            server.quit()
            self.logger.info('Email notification sent to %s', self.config['email']['to'])
        except Exception as e:
            self.logger.error('Failed to send email notification: %s', str(e))

    def send_slack_notification(self, message):
        try:
            response = requests.post(self.config['slack']['webhook_url'], json={'text': message})
            if response.status_code == 200:
                self.logger.info('Slack notification sent to %s', self.config['slack']['channel'])
            else:
                self.logger.error('Failed to send Slack notification: %s', response.text)
        except Exception as e:
            self.logger.error('Failed to send Slack notification: %s', str(e))

    def send_notification(self, error_message):
        if 'email' in self.config:
            self.send_email_notification('Error Notification', error_message)
        if 'slack' in self.config:
            self.send_slack_notification(error_message)

def main():
    config = {
        'email': {
            'to': os.environ.get('SMTP_TO'),
            'from': os.environ.get('SMTP_FROM'),
            'smtp_server': os.environ.get('SMTP_SERVER'),
            'password': os.environ.get('SMTP_PASSWORD')
        },
        'slack': {
            'webhook_url': os.environ.get('SLACK_WEBHOOK_URL'),
            'channel': os.environ.get('SLACK_CHANNEL', 'error-notifications')
        }
    }
    notifier = AutoErrorNotifier(config)
    notifier.send_notification('Test error message')

if __name__ == '__main__':
    main()