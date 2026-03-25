# /pr-review — Pull Request Review

Review an open PR on the Aisha GitHub repo before merging.

## Steps
1. List open PRs: `gh pr list --repo AjayBervanshi/aisha-personal-ai`
2. If PR number provided as argument: `gh pr view $ARGUMENTS`
3. Read the diff: `gh pr diff $ARGUMENTS`
4. Check:
   - **Security**: No hardcoded secrets, tokens, or credentials
   - **Logic**: Does the change match the PR description?
   - **Tests**: Are there tests for the changes?
   - **Breaking changes**: Anything that could break Render deploy?
   - **DB schema**: Any new tables/columns needed in Supabase?
5. Output verdict: APPROVE / REQUEST_CHANGES / COMMENT
6. If APPROVE: `gh pr merge $ARGUMENTS --squash`

## Context
- All PRs may be Aisha's autonomous self-improvement PRs
- Check that PR doesn't modify .env or hardcode credentials
- Verify syntax with `python -m py_compile <file>` before approving
