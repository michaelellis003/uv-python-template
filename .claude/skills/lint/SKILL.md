---
name: lint
description: Run all quality checks (format, lint, type check, tests). Use before pushing or to verify code quality.
user-invocable: true
allowed-tools: Bash, Read
---

# Run All Quality Checks

Execute the full quality pipeline matching what CI runs.

## Protocol

### Step 1: Format Check
```bash
poetry run ruff format --check .
```
If formatting issues found, fix them:
```bash
poetry run ruff format .
```

### Step 2: Lint Check
```bash
poetry run ruff check .
```
If lint issues found, attempt auto-fix:
```bash
poetry run ruff check . --fix
```
Report any remaining issues that need manual fixes.

### Step 3: Type Check
```bash
poetry run pyright
```
Report any type errors found.

### Step 4: Run Tests
```bash
poetry run pytest -v --durations=0 --cov
```

### Step 5: Summary
Report a table:

| Check      | Status |
|------------|--------|
| Format     | pass/fail |
| Lint       | pass/fail |
| Type Check | pass/fail |
| Tests      | X/Y passed |
| Coverage   | XX% |

If everything passes, tell the user the code is ready to push.
If anything fails, list the specific issues to fix.
