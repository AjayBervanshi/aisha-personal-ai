# /review — Comprehensive Code Review

Perform a code review on uncommitted or recently changed code.

## Usage
`/review` (reviews git diff) or `/review <file>`

## Steps
1. Get changes: `git diff HEAD` or read specified file
2. Run 3 parallel checks:
   - **Security**: OWASP Top 10, hardcoded secrets, injection, auth bypass
   - **Logic**: Bugs, edge cases, missing error handling, wrong types
   - **Quality**: Readability, duplication, naming, complexity
3. Output findings with severity: CRITICAL / HIGH / MEDIUM / LOW / INFO
4. For each CRITICAL/HIGH: provide exact fix
5. Summary verdict: APPROVE / NEEDS_CHANGES

## Auto-triggers
This command runs automatically after any production code change to:
- src/telegram/bot.py
- src/core/autonomous_loop.py
- src/core/ai_router.py
- src/core/self_editor.py
- src/core/self_improvement.py
