# CLAUDE.md

This file provides guidance for AI assistants working with this repository.

## Project Overview

This is a **Python package template** (`python-package-template`, v0.2.0) designed for bootstrapping production-ready Python packages. It uses Poetry for dependency management and packaging, with Ruff, Pyright, and pre-commit hooks enforcing code quality. Licensed under Apache-2.0.

## Repository Structure

```
python_package_template/     # Main package source
  __init__.py                # Package exports (add, multiply, hello)
  main.py                   # Core module with demo functions
tests/
  test_init.py              # Unit tests
.github/
  actions/setup-python-poetry/action.yml  # Reusable CI action
  workflows/
    ci.yml                  # CI pipeline (lint + test matrix)
    release-and-tag.yml     # Auto-tag and release on merge to main
pyproject.toml              # Project config, dependencies, tool settings
.pre-commit-config.yaml     # Pre-commit hook definitions
.python-versions            # Supported Python versions (3.10, 3.11, 3.12)
```

## Development Commands

All commands are run through Poetry:

```bash
# Install dependencies
poetry install --no-interaction

# Run tests
poetry run pytest -v --durations=0 --cov --cov-report=xml

# Run linting and formatting (via pre-commit)
poetry run pre-commit run --all-files

# Run ruff linter only
poetry run ruff check . --fix

# Run ruff formatter only
poetry run ruff format .

# Run type checking
poetry run pyright
```

## Code Style and Conventions

### Formatting Rules (enforced by Ruff)
- **Line length:** 79 characters
- **Indent:** 4 spaces
- **Quotes:** Single quotes
- **Target Python version:** 3.10

### Linting Rules (Ruff)
Enabled rule sets: pyflakes (F), pycodestyle (E4/E7/E9/E501), pep8-naming (N), pydocstyle (D), pyupgrade (UP), flake8-bugbear (B), flake8-simplify (SIM), isort (I).

Tests (`tests/*`) are exempt from the line-length rule E501.

### Docstrings
- **Required** on all public modules, classes, and functions.
- Use **Google-style** docstring convention.
- Include `Args` and `Returns` sections with types.

Example:
```python
def add(a: int, b: int) -> int:
    """Add two integers.

    Args:
        a (int): The first integer.
        b (int): The second integer.

    Returns:
        int: The sum of the two integers.
    """
    return a + b
```

### Type Annotations
- All functions must have type hints for parameters and return values.
- Pyright is used for static type checking (excludes `tests/` directory).

### Imports
- Public API is re-exported from `python_package_template/__init__.py` using `__all__`.
- Import ordering is managed by isort (via Ruff).

## Testing

- Framework: **pytest**
- Coverage: **pytest-cov** (reports uploaded to Codecov in CI)
- Tests live in `tests/` and import from the package directly.
- Run with: `poetry run pytest -v --durations=0 --cov --cov-report=xml`

## CI/CD

### CI Pipeline (`.github/workflows/ci.yml`)
Triggers on pushes to non-main branches:
1. **Lint & Format:** Runs `poetry run pre-commit run --all-files`
2. **Test Matrix:** Runs pytest against Python 3.10, 3.11, and 3.12

### Release Pipeline (`.github/workflows/release-and-tag.yml`)
Triggers on PR merge to main:
1. Reads version from `pyproject.toml`
2. Creates a git tag (`v{VERSION}`)
3. Builds the package (`poetry build`)
4. Creates a GitHub Release with distribution artifacts

## Pre-commit Hooks

The following hooks run on every commit:
- **pre-commit-hooks:** Large file check, case conflict check, private key detection, merge conflict check, trailing whitespace
- **Ruff:** Linting with `--fix` and formatting
- **Pyright:** Type checking
- **Poetry:** Config validation, lock file sync, dependency install

## Key Files to Update When Modifying the Template

- `pyproject.toml` — Version, dependencies, tool configuration
- `.python-versions` — Supported Python versions (also update `requires-python` and `target-version` in `pyproject.toml`)
- `python_package_template/__init__.py` — Public API exports
