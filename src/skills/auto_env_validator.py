import os
import logging
from dotenv import load_dotenv
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_environment_variables(env_file_path: str = '.env') -> Dict[str, str]:
    """
    Load environment variables from a .env file and system environment variables.

    Args:
    env_file_path (str): Path to the .env file. Defaults to '.env'.

    Returns:
    Dict[str, str]: A dictionary containing the loaded environment variables.
    """
    try:
        load_dotenv(env_file_path)
        return dict(os.environ)
    except Exception as e:
        logger.error(f"Failed to load environment variables: {e}")
        return {}

def validate_environment_variables(env_vars: Dict[str, str], required_vars: List[str]) -> bool:
    """
    Validate the presence and validity of required environment variables.

    Args:
    env_vars (Dict[str, str]): A dictionary containing the environment variables to validate.
    required_vars (List[str]): A list of required environment variable names.

    Returns:
    bool: True if all required variables are present and valid, False otherwise.
    """
    for var in required_vars:
        if var not in env_vars or not env_vars[var]:
            logger.error(f"Missing or invalid environment variable: {var}")
            return False
    return True

def handle_missing_variables(missing_vars: List[str]) -> None:
    """
    Handle missing environment variables by logging an error and exiting the program.

    Args:
    missing_vars (List[str]): A list of missing environment variable names.
    """
    logger.error(f"Missing environment variables: {missing_vars}")
    exit(1)

def main() -> None:
    """
    Main entry point for the environment variable validator.
    """
    required_vars = ['TELEGRAM_BOT_TOKEN', 'SUPABASE_URL', 'SUPABASE_SERVICE_KEY']
    env_vars = load_environment_variables()
    if not validate_environment_variables(env_vars, required_vars):
        missing_vars = [var for var in required_vars if var not in env_vars or not env_vars[var]]
        handle_missing_variables(missing_vars)

if __name__ == "__main__":
    main()