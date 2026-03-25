# /implement — Doc-Driven Code Implementation

Implement code from an existing plan document.

## Usage
`/implement <plan-file-path>`

## Steps
1. Read the plan document
2. Verify all preconditions are met (DB tables exist, API keys set)
3. Implement each step in order:
   - Write tests FIRST (TDD)
   - Implement code
   - Verify syntax: `python -m py_compile <file>`
4. After each file change, update plan with ✅ status
5. Run `/commit` when implementation is complete

## Guards
- Never skip tests
- Never hardcode secrets
- If a step is unclear, stop and ask — don't guess
