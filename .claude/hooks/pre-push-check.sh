#!/bin/bash
# Hook: Run lint and test checks before allowing git push.
# Used by Claude Code PreToolUse hook on Bash(git push *).
set -euo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Only intercept git push commands
if echo "$COMMAND" | grep -qE '^git push'; then
    cd "$(echo "$INPUT" | jq -r '.cwd')"

    echo "Running pre-push quality checks..." >&2

    # Run ruff format check
    if ! uv run ruff format --check . >/dev/null 2>&1; then
        echo "BLOCKED: Ruff formatting check failed. Run 'uv run ruff format .' first." >&2
        exit 2
    fi

    # Run ruff lint check
    if ! uv run ruff check . >/dev/null 2>&1; then
        echo "BLOCKED: Ruff lint check failed. Run 'uv run ruff check . --fix' first." >&2
        exit 2
    fi

    # Run tests
    if ! uv run pytest -x --tb=short -q 2>/dev/null; then
        echo "BLOCKED: Tests are failing. Fix failing tests before pushing." >&2
        exit 2
    fi

    echo "All pre-push checks passed." >&2
fi

exit 0
