# /commit — Smart Conventional Commit

Stage all modified tracked files and create a conventional commit message.

## Steps
1. Run `git status` to see what changed
2. Run `git diff --stat` to understand scope
3. Stage relevant files (avoid .env, secrets)
4. Write commit message following conventional format:
   - `feat:` new feature
   - `fix:` bug fix
   - `refactor:` code restructuring
   - `docs:` documentation only
   - `test:` test changes
   - `chore:` maintenance
5. Include Claude footer: `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`
6. Push to origin/main

## Auto-push
Always push after committing unless user says "commit only".
