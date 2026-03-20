# Agent State & Flow Standard
Date: 2026-03-18
Purpose: Keep all agent review/status docs consistent, evidence-based, and handoff-safe.

## Required Sections (in order)
1. Verified in Code
2. Verified in Runtime
3. Unverified / Assumed
4. Conflicts With Other Docs
5. Current State Snapshot
6. Flow Snapshot (request -> process -> persistence -> output)
7. Next 3 Actions
8. Blockers
9. Owner + Timestamp

## Evidence Rules
- Every claim must include at least one concrete evidence pointer (file path, function, migration, log artifact).
- If runtime proof is unavailable, mark as `Unverified / Assumed`.
- Never mark migrations as "applied" without DB/runtime confirmation.
- Never claim test pass rates without test output artifact.

## Severity Labels
- `CRITICAL`: blocks pipeline, data integrity, or security baseline.
- `HIGH`: high probability of production incident or revenue interruption.
- `MEDIUM`: quality/performance degradation with workaround.
- `LOW`: hygiene/refactor/documentation debt.

## Canonical State Line (top of every status doc)
`State: <phase> | Confidence: <high/medium/low> | Last runtime verification: <timestamp or unknown>`

## Flow Snapshot Template
- Trigger:
- Entry point:
- Orchestrator:
- External dependencies:
- Persistence writes:
- Success output:
- Failure path:

## Handoff Footer Template
- Updated by:
- Date/time:
- What changed:
- What remains:
- Next owner action:
