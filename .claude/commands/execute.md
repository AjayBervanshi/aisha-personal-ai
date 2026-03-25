# /execute — Execute Next Plan Steps

Find and execute inline instructions or the next pending steps in a plan document.

## Usage
`/execute` (uses currently active plan) or `/execute <plan-file>`

## Steps
1. Find the plan document (most recent in `docs/plans/` or specified)
2. Locate the next uncompleted step (no ✅)
3. Execute it
4. Mark as ✅
5. Continue until all steps done or blocker found

## Blocker Handling
If a step requires manual action:
- Print exact instructions for Ajay
- Stop and wait
- Example: "Run this SQL in Supabase Dashboard → SQL Editor: ..."
