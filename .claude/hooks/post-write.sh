#!/bin/bash
# post-write.sh — runs after every file write Claude does
# Auto-logs modified Python files for audit trail

FILE="$1"

# Log .py file changes to audit trail
if [[ "$FILE" == *.py ]]; then
  LOGFILE="e:/VSCode/Aisha/.claude/memory/write_log.txt"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Modified: $FILE" >> "$LOGFILE"
fi

exit 0
