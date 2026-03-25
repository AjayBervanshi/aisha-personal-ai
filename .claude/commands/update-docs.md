# /update-docs — Sync Documentation

Update documentation to reflect the current code state.

## Steps
1. Diff current code against last known doc state
2. Update `docs/ARCHITECTURE.md` if structure changed
3. Update `README.md` if setup instructions changed
4. Update `docs/API.md` if new handlers/endpoints added
5. Update `.claude/memory/context.md` with current issues/status
6. Commit documentation changes separately: `docs: update architecture docs`
