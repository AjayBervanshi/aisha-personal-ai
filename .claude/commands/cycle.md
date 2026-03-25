# /cycle — Full TDD Development Cycle

Run a complete TDD cycle: plan → test → implement → verify → commit.

## Usage
`/cycle <feature or bug description>`

## Steps
1. **Plan** (`/plan`) — document what we're building
2. **Test** (`/implement-tests`) — write failing tests first
3. **Implement** (`/implement`) — write code to pass tests
4. **Verify** — run tests, check syntax, manual spot-check
5. **Review** — security + code quality check
6. **Commit** (`/commit`) — conventional commit + push

## Rules
- Tests must fail BEFORE implementation (red-green-refactor)
- All 6 steps required — no skipping
- Each step verified before next begins
