## 2024-05-24 - Remove Hardcoded Defaults
**Vulnerability:** Found hardcoded fallback passwords and default email addresses in configuration dictionaries in `src/skills/auto_error_logger.py` and `src/skills/auto_error_notifier.py`.
**Learning:** Defaulting to placeholder strings like `'password'` or dummy webhook URLs can lead to accidental data leakage or false positives in security scanners, as applications might attempt real operations with these dummy credentials.
**Prevention:** Always retrieve secrets and configurations securely using `os.environ.get()` and handle `None` gracefully instead of providing hardcoded dummy values.

## 2025-02-28 - Avoid Information Disclosure in API Error Responses
**Vulnerability:** API endpoints in `src/api/server.py` were catching generic `Exception`s and directly passing the raw exception string `str(e)` to the `HTTPException` detail field, potentially exposing sensitive database errors, internal paths, or API failures to unauthenticated users or malicious actors.
**Learning:** Using `str(e)` in an exception response acts as an information disclosure leak. Raw error messages can provide valuable context to attackers during reconnaissance.
**Prevention:** Catch specific exceptions whenever possible. For generic fallback `except Exception:` blocks, log the error internally using `traceback.print_exc()` or a logging framework, and return a sanitized, generic error message (e.g., "An internal server error occurred.") to the client.

## 2024-05-15 - [Critical Auth Bypass] Missing Secret Token Allowed Dev Mode Fallback in Production
**Vulnerability:** The `verify_token` method in `src/api/server.py` had a logic flaw where if the `API_SECRET_TOKEN` was unconfigured, it would silently fall back to "dev mode" and return `True` for all requests, completely bypassing authentication.
**Learning:** This is a critical violation of the fail-secure principle. A missing environment variable in a production deployment would inadvertently expose all API endpoints without warning, as it defaulted to open access rather than throwing an error.
**Prevention:** Never use 'dev mode' fallbacks in production authentication or authorization logic. All authentication mechanisms must fail securely by defaulting to denying access or raising an exception if security configuration variables are missing or empty.
