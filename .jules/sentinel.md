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

## 2024-05-18 - Auth Bypass in API Token Validation
**Vulnerability:** The API `verify_token` in `src/api/server.py` had a "fail-open" dev mode fallback. If the `API_SECRET_TOKEN` environment variable was missing or empty, it allowed all requests without authentication instead of failing securely.
**Learning:** Security mechanisms must fail securely by default. A missing configuration variable (like an API token) should lead to denied access (fail-closed), rather than inadvertently granting open access (fail-open), especially in production environments where environment variables might fail to load properly. It's also important to return generic server error messages (like "Server configuration error.") rather than leaking the missing config details (like the missing token name).
**Prevention:** Avoid writing "dev mode" fallbacks directly in core security/authentication handlers that bypass standard checks based merely on the absence of configuration variables. All unauthenticated access should be explicitly handled. Validate and enforce that critical security configuration variables are present on service startup.

## 2026-04-11 - Fix Timing Attacks in Token Validation
**Vulnerability:** Token comparisons in `src/api/server.py` (`credentials.credentials != _API_TOKEN`) and `src/telegram/bot.py` (`tg_secret != TRIGGER_SECRET`, `secret != TRIGGER_SECRET`) used plain `!=` which is vulnerable to timing attacks. An attacker can measure response time differences to guess secrets character by character.
**Learning:** Simple string equality checks (`==` or `!=`) exit early on the first mismatched character. Timing side-channels can leak secret values over many requests.
**Prevention:** Always use `secrets.compare_digest()` for comparing sensitive tokens and secrets to ensure constant-time comparison.

## 2026-04-10 - Unauthenticated CallMe Webhook Memory Injection
**Vulnerability:** A new webhook endpoint (`/api/callme/transcript`) was added to log phone conversations into semantic memory without checking the `X-Trigger-Secret` header, meaning any attacker could craft arbitrary POST requests to inject false memories directly into Aisha's database.
**Learning:** All new REST endpoints added to the internal HTTP server MUST enforce the `TRIGGER_SECRET` fail-secure mechanism before processing the payload.
**Prevention:** Added `X-Trigger-Secret` validation to the new endpoint matching the exact fail-secure logic used by the existing `pg_cron` trigger.
## 2026-04-13 - [CRITICAL] Remote Code Execution via eval()
**Vulnerability:** The workflow engine used Python's built-in `eval()` to execute condition strings in logic nodes.
**Learning:** Even when passing a restricted global dict (`{"__builtins__": {}}`), `eval()` remains highly unsafe and vulnerable to code injection/RCE, as users can still access system functions through other means or crash the application.
**Prevention:** Never use `eval()` on untrusted input. Instead, use an Abstract Syntax Tree (AST) evaluator with an explicit whitelist of allowed node types (`ast.parse`) or use a secure alternative like `asteval` library.
