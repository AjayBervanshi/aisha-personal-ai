import logging
from typing import Callable, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CredentialHealthMonitor:
    """
    A class used to monitor the health of various credentials.

    It allows registration of validation functions for different credentials.
    The registered checks can be run and a consolidated status report is returned,
    allowing the main application to react to failing dependencies.

    Attributes:
    ----------
    checks : Dict[str, Callable]
        A dictionary of registered validation functions.

    Methods:
    -------
    register_check(name: str, check: Callable)
        Registers a validation function for a credential.
    run_checks()
        Runs all registered checks and returns a consolidated status report.
    """

    def __init__(self):
        self.checks = {}

    def register_check(self, name: str, check: Callable):
        """
        Registers a validation function for a credential.

        Args:
        ----
        name (str): The name of the credential.
        check (Callable): The validation function.

        Raises:
        ------
        ValueError: If the name is already registered.
        """
        if name in self.checks:
            raise ValueError(f"Check for {name} is already registered")
        self.checks[name] = check

    def run_checks(self) -> Dict[str, bool]:
        """
        Runs all registered checks and returns a consolidated status report.

        Returns:
        -------
        Dict[str, bool]: A dictionary with the credential names as keys and the check results as values.
        """
        results = {}
        for name, check in self.checks.items():
            try:
                results[name] = check()
            except Exception as e:
                logger.error(f"Error running check for {name}: {e}")
                results[name] = False
        return results


def check_telegram_token() -> bool:
    # Replace with actual implementation
    return True


def check_facebook_token() -> bool:
    # Replace with actual implementation
    return True


if __name__ == "__main__":
    monitor = CredentialHealthMonitor()
    monitor.register_check("telegram_token", check_telegram_token)
    monitor.register_check("facebook_token", check_facebook_token)
    results = monitor.run_checks()
    logger.info(results)