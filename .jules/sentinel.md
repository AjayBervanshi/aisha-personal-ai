## 2024-05-24 - Remove Hardcoded Defaults
**Vulnerability:** Found hardcoded fallback passwords and default email addresses in configuration dictionaries in `src/skills/auto_error_logger.py` and `src/skills/auto_error_notifier.py`.
**Learning:** Defaulting to placeholder strings like `'password'` or dummy webhook URLs can lead to accidental data leakage or false positives in security scanners, as applications might attempt real operations with these dummy credentials.
**Prevention:** Always retrieve secrets and configurations securely using `os.environ.get()` and handle `None` gracefully instead of providing hardcoded dummy values.
