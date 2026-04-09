import os
import logging
from supabase import create_client
from dotenv import load_dotenv

log = logging.getLogger("Aisha.SecretManager")

class SecretManager:
    """
    Fetches API keys securely from Supabase instead of relying on hardcoded .env files.
    This ensures no keys are ever committed to the repository.
    """
    def __init__(self):
        load_dotenv()
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_KEY")

        if not self.url or not self.key:
            log.warning("Supabase credentials not found in env. Cannot fetch dynamic secrets.")
            self.supabase = None
        else:
            try:
                self.supabase = create_client(self.url, self.key)
            except Exception as e:
                log.error(f"Failed to initialize Supabase client for secrets: {e}")
                self.supabase = None

    def get_secret(self, secret_name: str, fallback_env_var: str = None) -> str:
        """
        Attempts to fetch a secret from Supabase.
        If it fails, falls back to the local environment variable.
        Assumes a Supabase table named 'aisha_secrets' with columns 'name' and 'value'.
        """
        if self.supabase:
            try:
                # Assuming table 'aisha_secrets' exists.
                # If the user has a different table name (e.g., 'config' or 'secrets'), adjust here.
                response = self.supabase.table('aisha_secrets').select('value').eq('name', secret_name).execute()
                if response.data and len(response.data) > 0:
                    return response.data[0]['value']
            except Exception as e:
                log.warning(f"Failed to fetch secret '{secret_name}' from Supabase: {e}")

        # Fallback to local environment variables if Supabase fails or isn't set up yet
        env_val = os.getenv(fallback_env_var or secret_name)
        if env_val:
            return env_val

        return None

# Global instance
secrets = SecretManager()

def get_api_key(key_name: str) -> str:
    """Helper function to get an API key securely."""
    return secrets.get_secret(key_name)
