## 2024-05-24 - Remove Hardcoded Defaults
**Vulnerability:** Found hardcoded fallback passwords and default email addresses in configuration dictionaries in `src/skills/auto_error_logger.py` and `src/skills/auto_error_notifier.py`.
**Learning:** Defaulting to placeholder strings like `'password'` or dummy webhook URLs can lead to accidental data leakage or false positives in security scanners, as applications might attempt real operations with these dummy credentials.
**Prevention:** Always retrieve secrets and configurations securely using `os.environ.get()` and handle `None` gracefully instead of providing hardcoded dummy values.

## 2025-02-28 - Avoid Information Disclosure in API Error Responses
**Vulnerability:** API endpoints in `src/api/server.py` were catching generic `Exception`s and directly passing the raw exception string `str(e)` to the `HTTPException` detail field, potentially exposing sensitive database errors, internal paths, or API failures to unauthenticated users or malicious actors.
**Learning:** Using `str(e)` in an exception response acts as an information disclosure leak. Raw error messages can provide valuable context to attackers during reconnaissance.
**Prevention:** Catch specific exceptions whenever possible. For generic fallback `except Exception:` blocks, log the error internally using `traceback.print_exc()` or a logging framework, and return a sanitized, generic error message (e.g., "An internal server error occurred.") to the client.
## 2025-04-08 - [Fail-Secure API Authentication]
**Vulnerability:** The API server (`src/api/server.py`) had a 'dev mode' fallback that bypassed authentication entirely (returning `True`) if the `API_SECRET_TOKEN` environment variable was missing or empty. This could lead to severe unauthorized access if the environment variable was inadvertently dropped during deployment or configuration updates.
**Learning:** Security mechanisms must be fail-secure. When configuration necessary for a security check is missing, the system should default to denying access (e.g. throwing a 500 Server Configuration Error) rather than failing open.
**Prevention:** Avoid 'dev mode' bypasses in production-bound authentication logic. Ensure missing secrets raise explicit errors that halt access without leaking internal details.
