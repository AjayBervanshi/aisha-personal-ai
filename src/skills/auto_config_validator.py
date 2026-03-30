import os
import logging
import re
from typing import Dict, Any, Callable, List

# Configure logging for this module
logger = logging.getLogger(__name__)
# Ensure basic config is set up if this module is run independently
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class ConfigValidator:
    """
    A module designed to validate critical configuration settings required for Aisha AI's operation.

    This validator checks for the presence and basic validity of essential environment variables
    such as TELEGRAM_BOT_TOKEN, AJAY_TELEGRAM_ID, SUPABASE_URL, and SUPABASE_KEY.
    It provides a detailed report indicating which settings are correctly configured,
    which are missing, or which are improperly formatted.

    The module can run independently to pre-flight check configurations before the main
    autonomous loop starts, preventing potential crashes or functional errors due to
    misconfigured environments.

    Critical settings are those whose absence or invalidity would likely lead to
    immediate functional failure (e.g., inability to connect to core services).
    Non-critical settings might cause degraded functionality but not a complete halt.

    Usage:
        validator = ConfigValidator()
        report = validator.validate_all_settings()

        if report["overall_status"] == "ERROR":
            logger.error("Critical configuration errors found. Please review the report.")
            # Optionally, exit the application here if critical errors are unacceptable
            # import sys; sys.exit(1)
        elif report["overall_status"] == "WARNING":
            logger.warning("Some configuration warnings found. Functionality might be degraded.")
        else:
            logger.info("All critical configurations are valid.")

        # Print detailed report
        for setting, result in report.items():
            if setting != "overall_status":
                logger.info(f"  {setting}: {result['status']} - {result['message']}")
    """

    # Define critical settings and their validation functions
    # Each dictionary: {"name", "validator", "is_critical", "description"}
    _SETTINGS_TO_CHECK: List[Dict[str, Any]] = [
        {
            "name": "TELEGRAM_BOT_TOKEN",
            "validator": lambda v: ConfigValidator._validate_telegram_bot_token(v),
            "is_critical": True,
            "description": "Telegram Bot API token. Required for Telegram integration."
        },
        {
            "name": "AJAY_TELEGRAM_ID",
            "validator": lambda v: ConfigValidator._validate_telegram_id(v),
            "is_critical": True, # Critical for direct communication/admin
            "description": "Telegram User ID of the primary administrator (Ajay). Required for direct commands and notifications."
        },
        {
            "name": "SUPABASE_URL",
            "validator": lambda v: ConfigValidator._validate_url(v),
            "is_critical": True,
            "description": "Supabase project URL. Required for database access."
        },
        {
            "name": "SUPABASE_KEY", # Assuming this is the "service key" mentioned in the prompt
            "validator": lambda v: ConfigValidator._validate_non_empty_string(v),
            "is_critical": True,
            "description": "Supabase service key (anon or service_role). Required for database access."
        },
        # Add other settings as needed, e.g., for other services or optional features
        # {
        #     "name": "OPENAI_API_KEY",
        #     "validator": lambda v: ConfigValidator._validate_non_empty_string(v),
        #     "is_critical": True,
        #     "description": "OpenAI API key. Required for AI model interactions."
        # },
        # {
        #     "name": "SOME_OPTIONAL_SETTING",
        #     "validator": lambda v: ConfigValidator._validate_non_empty_string(v),
        #     "is_critical": False, # Example of a non-critical setting
        #     "description": "An optional setting for a specific feature."
        # }
    ]

    def __init__(self):
        """
        Initializes the ConfigValidator.
        """
        self.report: Dict[str, Any] = {}
        logger.info("ConfigValidator initialized. Preparing to check critical environment variables.")

    @staticmethod
    def _validate_telegram_bot_token(token: str) -> bool:
        """
        Validates a Telegram Bot Token format.
        A typical token looks like '123456:ABC-DEF1234ghIkl-789_jkl-LMNOPQRSTUVW'
        """
        if not token:
            return False
        # Basic regex: digits, colon, then alphanumeric/hyphen/underscore
        return bool(re.fullmatch(r'\d+:[a-zA-Z0-9_-]+', token))

    @staticmethod
    def _validate_telegram_id(telegram_id: str) -> bool:
        """
        Validates if a string represents a valid Telegram User ID (an integer).
        """
        if not telegram_id:
            return False
        try:
            # Telegram IDs can be negative for channels/groups, but user IDs are positive.
            # For simplicity, we just check if it's an integer.
            int(telegram_id)
            return True
        except ValueError:
            return False

    @staticmethod
    def _validate_url(url: str) -> bool:
        """
        Validates if a string is a basic URL (starts with http:// or https://).
        """
        if not url:
            return False
        return url.startswith("http://") or url.startswith("https://")

    @staticmethod
    def _validate_non_empty_string(value: str) -> bool:
        """
        Validates if a string is not empty or consists only of whitespace.
        """
        return bool(value and value.strip())

    def _validate_setting(self, setting_info: Dict[str, Any]) -> None:
        """
        Helper method to validate a single configuration setting.

        Args:
            setting_info (Dict[str, Any]): A dictionary containing 'name', 'validator', 'is_critical', and 'description'.
        """
        setting_name = setting_info["name"]
        validator_func = setting_info["validator"]
        is_critical = setting_info["is_critical"]
        description = setting_info["description"]

        value = os.getenv(setting_name)

        if value is None:
            status = "ERROR" if is_critical else "WARNING"
            message = f"'{setting_name}' is missing from environment variables. {description}"
            log_func = logger.error if is_critical else logger.warning
            log_func(message)
            self.report[setting_name] = {"status": status, "message": message}
            return

        if not validator_func(value):
            status = "ERROR" if is_critical else "WARNING"
            message = f"'{setting_name}' is present but invalid. Value: '{value}'. {description}"
            log_func = logger.error if is_critical else logger.warning
            log_func(message)
            self.report[setting_name] = {"status": status, "message": message}
            return

        message = f"'{setting_name}' is present and valid."
        logger.info(message)
        self.report[setting_name] = {"status": "OK", "message": message}

    def validate_all_settings(self) -> Dict[str, Any]:
        """
        Performs validation for all defined critical and non-critical settings.

        Returns:
            Dict[str, Any]: A report dictionary containing the status and message for each
                            setting, and an overall_status indicating the highest severity
                            found ("OK", "WARNING", or "ERROR").
        """
        logger.info("Starting configuration validation...")
        self.report = {} # Reset report for fresh validation

        for setting_info in self._SETTINGS_TO_CHECK:
            self._validate_setting(setting_info)

        # Determine overall status
        overall_status = "OK"
        for setting_name, result in self.report.items():
            if result["status"] == "ERROR":
                overall_status = "ERROR"
                break # Critical error found, no need to check further for overall status
            elif result["status"] == "WARNING" and overall_status == "OK":
                overall_status = "WARNING" # Promote to warning if only warnings found so far

        self.report["overall_status"] = overall_status
        logger.info(f"Configuration validation complete. Overall status: {overall_status}")
        return self.report

if __name__ == "__main__":
    # This block demonstrates how to use the ConfigValidator.
    # For testing, you might want to set/unset environment variables.

    # --- Test Case 1: All critical settings missing/invalid ---
    print("\n--- Test Case 1: All critical settings missing/invalid ---")
    # Temporarily unset variables for a clean test
    original_env = {k: os.getenv(k) for k in ["TELEGRAM_BOT_TOKEN", "AJAY_TELEGRAM_ID", "SUPABASE_URL", "SUPABASE_KEY"]}
    for k in original_env:
        if k in os.environ:
            del os.environ[k]

    validator = ConfigValidator()
    report1 = validator.validate_all_settings()
    print("\nValidation Report 1:")
    for key, value in report1.items():
        if key == "overall_status":
            print(f"Overall Status: {value}")
        else:
            print(f"  {key}: {value['status']} - {value['message']}")
    assert report1["overall_status"] == "ERROR", "Test Case 1 failed: Expected ERROR status."

    # --- Test Case 2: Mixed settings (some valid, some invalid/missing) ---
    print("\n--- Test Case 2: Mixed settings (some valid, some invalid/missing) ---")
    os.environ["TELEGRAM_BOT_TOKEN"] = "1234567890:AAH_some_valid_token_here"
    os.environ["AJAY_TELEGRAM_ID"] = "12345" # Valid ID
    # SUPABASE_URL and SUPABASE_KEY are still missing from previous cleanup

    validator = ConfigValidator()
    report2 = validator.validate_all_settings()
    print("\nValidation Report 2:")
    for key, value in report2.items():
        if key == "overall_status":
            print(f"Overall Status: {value}")
        else:
            print(f"  {key}: {value['status']} - {value['message']}")
    assert report2["overall_status"] == "ERROR", "Test Case 2 failed: Expected ERROR status due to missing Supabase."

    # --- Test Case 3: All critical settings valid ---
    print("\n--- Test Case 3: All critical settings valid ---")
    os.environ["TELEGRAM_BOT_TOKEN"] = "1234567890:AAH_some_valid_token_here"
    os.environ["AJAY_TELEGRAM_ID"] = "12345"
    os.environ["SUPABASE_URL"] = "https://your-project.supabase.co"
    os.environ["SUPABASE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlvdXItcHJvamVjdC1pZCJ9.your-supabase-key"

    validator = ConfigValidator()
    report3 = validator.validate_all_settings()
    print("\nValidation Report 3:")
    for key, value in report3.items():
        if key == "overall_status":
            print(f"Overall Status: {value}")
        else:
            print(f"  {key}: {value['status']} - {value['message']}")
    assert report3["overall_status"] == "OK", "Test Case 3 failed: Expected OK status."

    # Clean up environment variables and restore original state
    for k, v in original_env.items():
        if v is not None:
            os.environ[k] = v
        elif k in os.environ:
            del os.environ[k]

    print("\n--- End of ConfigValidator tests ---")