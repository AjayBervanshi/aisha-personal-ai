# Architecture Fixes Review (Revised)
**Date:** 2026-03-17
**Reviewed file:** `E:/VSCode/Aisha/docs/ARCHITECTURE_FIXES_2026-03-17.md`
**Reviewer goal:** validate claims, revise for technical accuracy, and suggest next actions.

---

## 1) Executive Summary
The fixes document is directionally strong and identifies the right high-risk areas. However, several "fixed" items are only partially implemented or not yet reflected in runtime code. The revised status is:

- **Verified implemented in code:** temp file cleanup scheduler, key-expiry scheduler, long-polling bot path exists.
- **Partially implemented:** token strategy (DB table exists, but runtime still reads token files/env), Telegram single-path claim (operationally possible, not provable from repo).
- **Not yet implemented:** content publish idempotency, per-platform status model, startup recovery for stuck processing jobs, SelfEditor safety guardrails.
- **Incorrect claim in original fixes doc:** "zero automated tests" (a `tests/` suite exists in repo, though execution status is unknown in this environment).

---

## 2) Claim Validation Matrix

| Claim in fixes doc | Evidence from repo | Revised status |
|---|---|---|
| Added `run_temp_cleanup()` and schedule | `src/core/autonomous_loop.py` has method + `schedule.every().day.at("04:00")` | ✅ Verified |
| Added `run_key_expiry_check()` and daily schedule | `src/core/autonomous_loop.py` has method + `schedule.every().day.at("09:00")` | ✅ Verified |
| Tokens moved to Supabase and used by app | `src/core/social_media_engine.py` still loads token files/env; no runtime read from `api_keys` | ⚠️ Partial |
| Telegram dual-path conflict resolved | `bot.py` long polling exists; edge function still present; webhook de-registration not codified in repo | ⚠️ Operational/unverified |
| No automated tests | `tests/` directory contains multiple pytest files | ❌ Incorrect |
| RLS still open TRUE policies | present in `supabase/aisha_full_migration.sql` and older migrations | ✅ Verified |
| SelfEditor has no hard guardrails | `src/core/self_editor.py` directly writes file content in `apply_patch()` | ✅ Verified |

---

## 3) Key Corrections

### A. Token-storage fix is incomplete
- The document says token fix is done.
- Runtime still depends on token files (`youtube_token*.json`) and environment-based Instagram tokens.
- `autonomous_loop.py` key-expiry check still reads `tokens/youtube_token.json`.

**Correction:** mark as "partially complete" until all runtime paths load from DB.

### B. `api_keys` integration has a schema mismatch risk
- Migration defines `api_keys.secret`.
- `store-api-keys` edge function writes field `key`.

**Correction:** standardize on one column (`secret` or `key`) and migrate code + SQL accordingly.

### C. Test-suite claim should be updated
- A test suite exists in `tests/`.
- Current issue is likely reliability/coverage/execution in CI, not total absence.

**Correction:** replace "no automated tests" with "test suite exists but not reliably enforced in CI with quality gates".

### D. Telegram single-source-of-truth is not yet architecture-enforced
- Manual `deleteWebhook` can fix live behavior.
- Repo still contains edge webhook path and no explicit guard preventing reactivation.

**Correction:** codify a boot-time assertion and deployment runbook check.

---

## 4) Revised Recommended Actions

### High Priority (this week)
1. **Close token migration fully**
- Update `social_media_engine.py` and related callers to read from `api_keys` only.
- Remove token-file dependency paths after migration.
- Update expiry-check logic to use DB token source.

2. **Fix `api_keys` schema contract**
- Choose canonical column name.
- Add migration to align table and edge function payloads.
- Add one integration test for read/write token roundtrip.

3. **Enforce Telegram ingestion mode in code**
- Add startup check that warns/fails if webhook is set while polling mode is active.
- Document one production ingress mode and disable the other by config.

4. **Introduce publish idempotency**
- Persist external IDs (`youtube_video_id`, `instagram_post_id`) and guard re-uploads.
- Use explicit state transitions for publish lifecycle.

### Medium Priority (this month)
1. Add startup recovery for stale `processing` jobs with deterministic retry criteria.
2. Add per-platform status fields and migrate from overloaded single `status` semantics.
3. Harden SelfEditor: branch/PR-only workflow + mandatory human approval + rollback path.
4. Replace TRUE RLS policies with least-privilege service-role-only or scoped policies.

### Low Priority (this quarter)
1. CI/CD unification: include edge-function deployment + smoke checks.
2. Add observability baselines: uptime, error budget, queue-depth/throughput metrics.
3. Refactor `AishaBrain` into bounded services once reliability baseline is stable.

---

## 5) Suggested Document Rewrite (How to present status)
Use three status buckets in future fix logs:

- **Applied (code merged + runtime active)**
- **Applied (partial / migration in progress)**
- **Planned (not yet merged)**

This avoids over-reporting completion and improves architecture decision traceability.

---

## 6) Final Architect Note
The original fixes doc is a good operational triage artifact, but it mixed confirmed changes with intent-level actions. After correction, the architecture direction remains strong: reliability and security are improving, but token architecture consistency, idempotency, and policy hardening are the immediate blockers before adding new features.
