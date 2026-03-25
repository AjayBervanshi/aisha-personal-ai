# /implement-tests — Write Tests for Plan

Write tests for an existing implementation (TDD catch-up or test-first).

## Usage
`/implement-tests <plan-file-path or feature>`

## Steps
1. Read the feature/implementation being tested
2. Create test file at `tests/test_<module>.py`
3. Cover:
   - **Happy path** — normal successful execution
   - **Edge cases** — empty inputs, max values, None
   - **Error cases** — API failures, DB errors, network timeout
   - **Security cases** — injection attempts, unauthorized access
4. Use `pytest` format with fixtures
5. Mock external services (Telegram, Supabase, ElevenLabs) with `unittest.mock`
6. Run: `cd e:/VSCode/Aisha && /e/VSCode/.venv/Scripts/python -m pytest tests/ -v`

## Standards
- All tests must pass before `/commit`
- Test files must be UTF-8 with `sys.stdout` wrapper for Windows
