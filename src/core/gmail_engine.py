"""
gmail_engine.py
===============
Core engine for Aisha's email capabilities using SMTP and IMAP.
Aisha can now read, search, and send emails autonomously.
"""

import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.core.config import GMAIL_USER, GMAIL_APP_PASSWORD

class GmailEngine:
    def __init__(self):
        self.user = GMAIL_USER
        self.password = GMAIL_APP_PASSWORD

    def send_email(self, to_email: str, subject: str, body: str):
        """Send a plain text email from Aisha."""
        if not self.user or not self.password:
            print("[Gmail] Error: No credentials provided.")
            return False

        msg = MIMEMultipart()
        msg['From'] = f"Aisha AI <{self.user}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(self.user, self.password)
                server.send_message(msg)
            print(f"[Gmail] ✅ Email sent to {to_email}")
            return True
        except Exception as e:
            print(f"[Gmail] ❌ Error sending email: {e}")
            return False

    def check_inbox(self, limit: int = 5):
        """Read latest unread emails from the inbox."""
        if not self.user or not self.password:
            return []

        try:
            # Connect to IMAP
            mail = imaplib.IMAP4_SSL('imap.gmail.com')
            mail.login(self.user, self.password)
            mail.select('inbox')

            # Search for unread
            status, response = mail.search(None, '(UNSEEN)')
            if status != 'OK': return []

            email_ids = response[0].split()
            latest_ids = email_ids[-limit:]

            emails = []
            for e_id in latest_ids:
                status, data = mail.fetch(e_id, '(RFC822)')
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Basic parsing
                emails.append({
                    "from": msg['From'],
                    "subject": msg['Subject'],
                    "date": msg['Date'],
                    "body": self._get_body(msg)
                })
            
            mail.logout()
            return emails
        except Exception as e:
            print(f"[Gmail] ❌ Error checking inbox: {e}")
            return []

    def _get_body(self, msg):
        """Helper to extract body from multipart email."""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode()
        else:
            return msg.get_payload(decode=True).decode()
        return ""

if __name__ == "__main__":
    # Test
    gmail = GmailEngine()
    gmail.send_email(
        GMAIL_USER, 
        "Welcome to your inbox, Aisha! 💜", 
        "Ajay has linked your new email. You are officially in business, baby! Let's earn some money for Ajju. 💸"
    )
