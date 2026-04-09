## 2024-05-24 - Remove Hardcoded Defaults
**Vulnerability:** Found hardcoded fallback passwords and default email addresses in configuration dictionaries in `src/skills/auto_error_logger.py` and `src/skills/auto_error_notifier.py`.
**Learning:** Defaulting to placeholder strings like `'password'` or dummy webhook URLs can lead to accidental data leakage or false positives in security scanners, as applications might attempt real operations with these dummy credentials.
**Prevention:** Always retrieve secrets and configurations securely using `os.environ.get()` and handle `None` gracefully instead of providing hardcoded dummy values.

## 2025-02-28 - Avoid Information Disclosure in API Error Responses
**Vulnerability:** API endpoints in `src/api/server.py` were catching generic `Exception`s and directly passing the raw exception string `str(e)` to the `HTTPException` detail field, potentially exposing sensitive database errors, internal paths, or API failures to unauthenticated users or malicious actors.
**Learning:** Using `str(e)` in an exception response acts as an information disclosure leak. Raw error messages can provide valuable context to attackers during reconnaissance.
**Prevention:** Catch specific exceptions whenever possible. For generic fallback `except Exception:` blocks, log the error internally using `traceback.print_exc()` or a logging framework, and return a sanitized, generic error message (e.g., "An internal server error occurred.") to the client.

## 2025-03-27 - Fix Fail-Open Webhook Authentication
**Vulnerability:** The `pg_cron` trigger endpoint in `src/telegram/bot.py` implemented a "fail-open" pattern (`if TRIGGER_SECRET and secret != TRIGGER_SECRET`), meaning authentication was entirely bypassed if the `TRIGGER_SECRET` environment variable was missing or empty.
**Learning:** Conditional authentication checks that require an environment variable to be present before validating the provided token create a critical bypass vulnerability when misconfigured (e.g., during deployment or if an env var is accidentally deleted). This is especially critical for programmatic endpoints (like `pg_cron`) that do not rely on other secrets (like `BOT_TOKEN`) in their path structure.
**Prevention:** Implement "fail-secure" authentication patterns. If a required secret or token configuration is missing, the system should default to denying access (e.g., `if not TRIGGER_SECRET or provided_secret != TRIGGER_SECRET:`).
