# AGENT_STATE_FLOW_STANDARD — Review & Suggestions
Reviewer: Principal AI Systems Architect (Claude)
Date: 2026-03-18
Source doc: `docs/AGENT_STATE_FLOW_STANDARD.md`

---

## Current Standard Assessment

### What the Standard Gets Right

1. **Evidence-first rule** — "Every claim must include a concrete evidence pointer" — this is the most important rule and correctly placed first.
2. **Canonical State Line** — Single-line machine-readable status at top of every doc. Clean and effective.
3. **Severity labels** — CRITICAL / HIGH / MEDIUM / LOW are well-defined and consistently scoped to revenue impact.
4. **Flow Snapshot Template** — The 7-field template (Trigger → Entry → Orchestrator → Dependencies → Persistence → Success → Failure) covers all paths needed for inter-agent handoff.
5. **9-section structure** — Comprehensive. Covers code evidence, runtime evidence, assumptions, conflicts, snapshots, actions, blockers, and handoff.
6. **"Never mark migrations as applied without DB/runtime confirmation"** — Directly prevents the most common agent hallucination error.

---

## Issues Found (with Evidence)

### Issue 1 — No "Migration Status" Section (MEDIUM)
**Problem:** Migrations appear inside Section 3 (Unverified/Assumed) mixed with general assumptions. Since this project has 5+ active migrations, tracking them inline inside assumptions is error-prone.
**Evidence:** In `AISHA_STATE_HANDOFF_2026-03-18.md`, the `api_keys.secret` migration and `api_keys.active` migration were buried in Section 3 alongside unrelated assumptions. An incoming agent reading quickly could miss migration blockers.
**Fix:** Add a dedicated **Section 2b — Migration Status** between Sections 2 and 3.

### Issue 2 — No "Alert / Email Status" Field (MEDIUM)
**Problem:** The `ai_router.py` now sends email alerts on model failure. But no section of the standard tracks which alerts have fired recently, preventing duplicate work by agents.
**Evidence:** `src/core/ai_router.py` — `_alert_notified` dict tracks in-memory, but clears on restart. State doc has no field to record last-fired alerts.
**Fix:** Add `Alert Status` to Section 5 (State Snapshot).

### Issue 3 — Flow Snapshot Has No "Last Tested" Timestamp (HIGH)
**Problem:** The Flow Snapshot template records what the flow does but not when it was last verified end-to-end. An agent reading a 2-week-old handoff has no way to assess staleness.
**Evidence:** `AISHA_STATE_HANDOFF_2026-03-18.md` Section 6 shows flows without any "last run" timestamp. The 17/17 test result that validates these flows was 2026-03-18 — but this metadata is in Section 2, not in Section 6.
**Fix:** Add `Last verified: <timestamp>` as the 8th field in the Flow Snapshot Template.

### Issue 4 — No Revenue Impact Column in Blockers (HIGH)
**Problem:** The Blockers section uses Severity labels but no "Revenue Impact" column. Since the primary goal is Aisha making money, blockers that directly block income need to be visually distinct.
**Evidence:** In `AISHA_STATE_HANDOFF_2026-03-18.md`, the `api_keys.secret` blocker was CRITICAL but its revenue impact (blocks Instagram token load → blocks social posting → blocks income) wasn't explicit in the table.
**Fix:** Add `Revenue Impact` column to Blockers table: `Blocks Revenue / Delays Revenue / No Direct Impact`.

### Issue 5 — Section 9 Handoff Footer Needs "Test Commands" Field (MEDIUM)
**Problem:** The handoff footer records "what changed" and "next owner action" but doesn't include the exact command to verify system state. An incoming agent (or human) has to search to find how to run tests.
**Evidence:** There is no "Verification Command" field anywhere in the standard.
**Fix:** Add `Verification command:` to the Handoff Footer template. Example: `cd E:\VSCode\Aisha && python scripts/test_all_systems.py`

### Issue 6 — No "Platform/Environment" Anchor (LOW)
**Problem:** The standard doesn't require recording the deployment environment. A doc written for Railway prod means something different than one for Windows dev.
**Evidence:** Missing in all existing handoff docs — unclear if verified results are from local or Railway.
**Fix:** Add `Environment:` to Section 5 (State Snapshot). Values: `Local (Windows)`, `Railway (prod)`, `Both`.

---

## Suggested Improvements (Revised Standard)

### Updated Section Order

```
1. Verified in Code
2. Verified in Runtime
2b. Migration Status  ← NEW
3. Unverified / Assumed
4. Conflicts With Other Docs
5. Current State Snapshot  ← add Alert Status, Environment
6. Flow Snapshot  ← add Last verified timestamp
7. Next 3 Actions
8. Blockers  ← add Revenue Impact column
9. Owner + Timestamp  ← add Verification Command
```

### Updated Flow Snapshot Template (8 fields)
```
- Trigger:
- Entry point:
- Orchestrator:
- External dependencies:
- Persistence writes:
- Success output:
- Failure path:
- Last verified: <timestamp or unknown>   ← NEW
```

### Updated Blockers Table
```
| Blocker | Severity | Revenue Impact | Owner | ETA |
```

### Updated Handoff Footer Template
```
- Updated by:
- Date/time:
- What changed:
- What remains:
- Next owner action:
- Verification command:   ← NEW
```

### New Migration Status Section Template (2b)
```
## 2b. Migration Status
| Migration file | Status | Applied by | Verified in DB |
|---|---|---|---|
| 20260317000000_content_queue_idempotency.sql | ✅ Applied | Ajay (SQL Editor) | ✅ Confirmed |
| 20260317120000_fix_api_keys_secret_column.sql | ✅ Applied | Ajay (SQL Editor) | ⚠️ Unconfirmed |
| 20260318000000_fix_api_keys_active_column.sql | ⏳ Pending | — | ❌ Not applied |
```

---

## Overall Rating: STRONG ✅

The standard is significantly better than most inter-agent handoff protocols. The evidence requirement and the unverified/assumed separation are genuinely preventing hallucination errors (proved by the `api_keys.secret` blocker being correctly flagged instead of assumed applied).

**With the 6 fixes above, this standard would be production-grade for multi-agent orchestration.**

---

## Updated State Handoff (reflecting 2026-03-18 changes)

See: `docs/AISHA_STATE_HANDOFF_2026-03-18-v2.md`

---
*Saved at: docs/AGENT_STATE_FLOW_STANDARD_REVIEW_2026-03-18.md*
*For: Future agents, Ajay, Claude sessions*
