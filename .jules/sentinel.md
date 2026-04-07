## 2024-05-24 - Remove Hardcoded Defaults
**Vulnerability:** Found hardcoded fallback passwords and default email addresses in configuration dictionaries in `src/skills/auto_error_logger.py` and `src/skills/auto_error_notifier.py`.
**Learning:** Defaulting to placeholder strings like `'password'` or dummy webhook URLs can lead to accidental data leakage or false positives in security scanners, as applications might attempt real operations with these dummy credentials.
**Prevention:** Always retrieve secrets and configurations securely using `os.environ.get()` and handle `None` gracefully instead of providing hardcoded dummy values.

## 2025-02-28 - Avoid Information Disclosure in API Error Responses
**Vulnerability:** API endpoints in `src/api/server.py` were catching generic `Exception`s and directly passing the raw exception string `str(e)` to the `HTTPException` detail field, potentially exposing sensitive database errors, internal paths, or API failures to unauthenticated users or malicious actors.
**Learning:** Using `str(e)` in an exception response acts as an information disclosure leak. Raw error messages can provide valuable context to attackers during reconnaissance.
**Prevention:** Catch specific exceptions whenever possible. For generic fallback `except Exception:` blocks, log the error internally using `traceback.print_exc()` or a logging framework, and return a sanitized, generic error message (e.g., "An internal server error occurred.") to the client.

## 2025-02-28 - Fail-Secure Authentication
**Vulnerability:** The API authentication handler `verify_token` in `src/api/server.py` had a dev-mode fallback that allowed all unauthenticated requests if the `API_SECRET_TOKEN` environment variable was missing or empty.
**Learning:** Defaulting to allow access in case of configuration errors is a "fail-open" vulnerability. If a production environment is deployed with a missing environment variable, it inadvertently exposes all protected endpoints to unauthenticated users.
**Prevention:** Always adhere to the "fail-secure" principle in authentication mechanisms. Mechanisms must default to denying access if configuration variables are missing or improperly set. Use generic error details (e.g., "Server configuration error.") instead of exposing internal details in HTTP error responses.
