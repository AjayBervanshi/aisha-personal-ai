#!/bin/bash
# pre-bash.sh — runs before every bash command Claude executes
# Safety guard: warn on destructive commands

CMD="$1"

# Block accidental rm -rf on project root
if echo "$CMD" | grep -qE 'rm\s+-rf\s+[./]*(src|\.env|supabase)'; then
  echo "BLOCKED: Destructive rm on critical path. Confirm manually." >&2
  exit 1
fi

# Warn on git push --force
if echo "$CMD" | grep -qE 'git push.*--force|git push.*-f'; then
  echo "WARNING: Force push detected. Proceeding with caution." >&2
fi

exit 0
