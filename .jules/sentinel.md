## 2026-04-10 - Unauthenticated CallMe Webhook Memory Injection
**Vulnerability:** A new webhook endpoint (`/api/callme/transcript`) was added to log phone conversations into semantic memory without checking the `X-Trigger-Secret` header, meaning any attacker could craft arbitrary POST requests to inject false memories directly into Aisha's database.
**Learning:** All new REST endpoints added to the internal HTTP server MUST enforce the `TRIGGER_SECRET` fail-secure mechanism before processing the payload.
**Prevention:** Added `X-Trigger-Secret` validation to the new endpoint matching the exact fail-secure logic used by the existing `pg_cron` trigger.
