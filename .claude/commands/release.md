# /release — Release Process

Automate the release process: changelog, tag, deploy.

## Usage
`/release <version>` e.g. `/release v1.2.0`

## Steps
1. Verify all tests pass
2. Update `CHANGELOG.md` with changes since last tag
3. Bump version in `src/core/config.py` (AISHA_VERSION)
4. Create git tag: `git tag -a $VERSION -m "Release $VERSION"`
5. Push tag: `git push origin $VERSION`
6. Trigger Render deploy (via Render MCP or webhook)
7. Verify deploy health: `curl https://aisha-bot-yudp.onrender.com/health`
8. Notify Ajay via Telegram with release summary

## Pre-flight Checks
- No hardcoded secrets in diff
- All protected files pass syntax check
- Supabase migrations applied
