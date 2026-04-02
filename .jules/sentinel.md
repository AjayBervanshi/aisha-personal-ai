## 2026-04-02 - Secure Failure for Missing API Token
**Vulnerability:** Authentication bypass in API
**Learning:** Returning `True` in an auth dependency when the secret token is missing allows unauthenticated access if the env is misconfigured.
**Prevention:** Always fail securely (e.g. raise a 500 Internal Server Error) when critical security configurations like API tokens are missing.
