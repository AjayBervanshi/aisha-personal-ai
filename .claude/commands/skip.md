# /skip — Skip Current Step

Skip the current step in an active plan and advance to the next.

## Usage
`/skip` or `/skip <reason>`

## Steps
1. Find the current plan document
2. Find the first uncompleted step
3. Mark it as ⏭️ SKIPPED with reason
4. Move to next step
5. Log skip reason in `.claude/memory/write_log.txt`

## When to Use
- External dependency not available (API key missing, service down)
- Step is blocked on manual action that Ajay will do later
- Step is no longer relevant due to scope change
