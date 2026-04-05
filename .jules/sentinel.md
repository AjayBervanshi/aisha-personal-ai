## 2024-05-24 - Remove Hardcoded Defaults
**Vulnerability:** Found hardcoded fallback passwords and default email addresses in configuration dictionaries in `src/skills/auto_error_logger.py` and `src/skills/auto_error_notifier.py`.
**Learning:** Defaulting to placeholder strings like `'password'` or dummy webhook URLs can lead to accidental data leakage or false positives in security scanners, as applications might attempt real operations with these dummy credentials.
**Prevention:** Always retrieve secrets and configurations securely using `os.environ.get()` and handle `None` gracefully instead of providing hardcoded dummy values.

## 2025-02-28 - Avoid Information Disclosure in API Error Responses
**Vulnerability:** API endpoints in `src/api/server.py` were catching generic `Exception`s and directly passing the raw exception string `str(e)` to the `HTTPException` detail field, potentially exposing sensitive database errors, internal paths, or API failures to unauthenticated users or malicious actors.
**Learning:** Using `str(e)` in an exception response acts as an information disclosure leak. Raw error messages can provide valuable context to attackers during reconnaissance.
**Prevention:** Catch specific exceptions whenever possible. For generic fallback `except Exception:` blocks, log the error internally using `traceback.print_exc()` or a logging framework, and return a sanitized, generic error message (e.g., "An internal server error occurred.") to the client.

## 2025-05-24 - Fix Auth Bypass Fallback in Production API
**Vulnerability:** The API token verification in `src/api/server.py` failed open (returned True) when `API_SECRET_TOKEN` was completely unset, causing a critical auth bypass in production if the token was not correctly configured.
**Learning:** Never assume a missing configuration means the application is in development. Failing open in production setups causes critical access control vulnerabilities.
**Prevention:** Always default to a secure, closed state (e.g., `HTTP 401`) when credentials or critical security variables are missing, unless an explicit environment variable (like `APP_ENV=development`) confirms an insecure dev environment.
