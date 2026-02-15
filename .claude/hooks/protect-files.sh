#!/bin/bash
# Hook: Prevent edits to protected files (lock files, CI configs, etc.)
# Used by Claude Code PreToolUse hook on Edit|Write.
set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
    exit 0
fi

PROTECTED_PATTERNS=(
    ".env"
    "uv.lock"
    ".git/"
)

for pattern in "${PROTECTED_PATTERNS[@]}"; do
    if [[ "$FILE_PATH" == *"$pattern"* ]]; then
        echo "BLOCKED: $FILE_PATH is a protected file ('$pattern'). Do not edit directly." >&2
        exit 2
    fi
done

exit 0
