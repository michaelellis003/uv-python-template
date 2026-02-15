# Python Package Template

[![](https://img.shields.io/badge/Python-3.10|3.11|3.12|3.13-blue)](https://www.python.org)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Pyright](https://img.shields.io/badge/Pyright-enabled-brightgreen)](https://github.com/microsoft/pyright)
[![codecov](https://codecov.io/gh/michaelellis003/python-package-template/graph/badge.svg?token=TUKP19SKJ3)](https://codecov.io/gh/michaelellis003/python-package-template)
[![License](https://img.shields.io/github/license/michaelellis003/python-package-template)](https://github.com/michaelellis003/python-package-template/blob/main/LICENSE)

A production-ready template for starting new Python packages. Clone it, rename a few things, and start building — dependency management, linting, type checking, testing, and CI/CD are already wired up.

## Table of Contents
1. [Features](#features)
2. [Getting Started](#getting-started)
3. [Customizing the Template](#customizing-the-template)
4. [Development Workflow](#development-workflow)
5. [Using uv](#using-uv)
6. [CI/CD Workflows](#cicd-workflows)
7. [Project Structure](#project-structure)

## Features
- [uv](https://docs.astral.sh/uv/) for fast Python package management, virtual environments, and lockfile resolution.
- [Pre-commit hooks](https://pre-commit.com) to enforce consistent code quality on every commit:
    - [Ruff](https://docs.astral.sh/ruff/) for linting and formatting,
    - [Pyright](https://github.com/microsoft/pyright) for static type checking.
- [Pytest](https://docs.pytest.org/en/stable/) with [pytest-cov](https://pytest-cov.readthedocs.io/) for testing and coverage.
- **GitHub Actions** CI/CD — lint, test across Python 3.10–3.13, and auto-release on merge to main.
- **TDD-first development lifecycle** with Claude Code configuration for AI-assisted development.

## Getting Started

### Prerequisites
- Python 3.10+ (uv will download it automatically if missing)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

Install uv:
```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Create a New Project from This Template

1. Click **"Use this template"** on GitHub (or clone the repo directly):
    ```bash
    git clone https://github.com/michaelellis003/python-package-template.git my-project
    cd my-project
    rm -rf .git && git init
    ```

2. Install dependencies:
    ```bash
    uv sync
    ```

3. Enable pre-commit hooks:
    ```bash
    uv run pre-commit install
    ```

4. Run the tests to verify everything works:
    ```bash
    uv run pytest -v --durations=0 --cov
    ```

## Customizing the Template

After cloning, update these files to match your project:

| What to change | Where |
|----------------|-------|
| Package name, version, author | `pyproject.toml` — `[project]` table |
| Package source directory | Rename `python_package_template/` to your package name |
| Public API exports | `<your_package>/__init__.py` — update `__all__` |
| Test imports | `tests/test_init.py` — update `from python_package_template import ...` |
| README badges & description | `README.md` — replace repo URLs and badge tokens |
| License | `LICENSE` — update copyright holder if needed |
| Python versions | `requires-python` in `pyproject.toml` and matrix in `.github/workflows/ci.yml` |
| Semantic release package name | `pyproject.toml` — `[tool.semantic_release]` update `--upgrade-package` in `build_command` |
| Codecov token | Add `CODECOV_TOKEN` secret in your GitHub repo settings |

The demo functions (`hello`, `add`, `subtract`, `multiply`) are provided as working examples of the TDD workflow. Replace them with your own code.

## Development Workflow

This project follows a strict TDD-first lifecycle:

1. **Define** — create an issue with Given/When/Then acceptance criteria
2. **Branch** — `<type>/<issue-id>-<short-description>` from `main`
3. **RED** — write one failing test
4. **GREEN** — write the minimum code to pass
5. **REFACTOR** — clean up while tests stay green
6. **COMMIT** — `<type>(<scope>): <description>` (Conventional Commits)
7. **Repeat** steps 3–6 until acceptance criteria are met
8. **DOCS** — update documentation to reflect any user-facing changes
9. **PUSH** — run `uv run pre-commit run --all-files` before pushing
10. **PR** — self-review, open PR (target < 400 lines), request review
11. **CI** — parallel: ruff lint, ruff format, pyright, test matrix
12. **MERGE** — squash and merge to main
13. **RELEASE** — `python-semantic-release` auto-bumps version, tags, and creates a GitHub Release based on conventional commit messages

## Using uv

For the full uv documentation, visit the [full docs](https://docs.astral.sh/uv/).

### Quick Reference

```bash
uv sync                                      # Install all dependencies
uv run pytest -v --durations=0 --cov         # Run tests with coverage
uv run pre-commit run --all-files            # Run all quality checks
uv run ruff check . --fix                    # Lint (with auto-fix)
uv run ruff format .                         # Format code
uv run pyright                               # Type check
```

### Managing Dependencies

- **Add a runtime dependency:**
    ```bash
    uv add requests
    ```
    Updates `[project.dependencies]` in `pyproject.toml` and syncs your environment.

- **Add a dev dependency:**
    ```bash
    uv add --dev pytest-mock
    ```
    Updates `[dependency-groups]` in `pyproject.toml`.

- **Add to a named group:**
    ```bash
    uv add --group docs sphinx
    ```

- **Remove a dependency:**
    ```bash
    uv remove requests
    ```

Read more about [dependency management in uv](https://docs.astral.sh/uv/concepts/projects/dependencies/).

### Versioning (Automated)

Version bumping is handled automatically by `python-semantic-release` on merge to main. It reads conventional commit messages to determine the bump type: `feat:` triggers a minor bump, `fix:`/`perf:` triggers a patch bump, and `feat!:`/`BREAKING CHANGE` triggers a major bump. Do not manually bump the version in `pyproject.toml`.

## CI/CD Workflows

### On Pull Request and Push to Main (`ci.yml`)

Runs four parallel jobs for fast feedback:
- **Ruff Lint** — checks for code quality issues
- **Ruff Format** — verifies consistent code formatting
- **Pyright** — static type checking
- **Pytest** — runs tests across Python 3.10, 3.11, 3.12, and 3.13 with Codecov upload

### On Merge to Main (`release.yml`)

- **Versioning** — `python-semantic-release` reads conventional commits and bumps the version automatically
- **Tagging** — creates a git tag for the new version
- **Building** — runs `uv build` to produce sdist and wheel
- **Releasing** — creates a GitHub Release with the built artifacts and release notes

## Project Structure

```
├── python_package_template/         # Package source (rename this)
│   ├── __init__.py                  # Public API exports + __version__
│   ├── main.py                     # Core module with demo functions
│   └── py.typed                    # PEP 561 type checking marker
├── tests/
│   ├── conftest.py                 # Shared test fixtures
│   └── test_init.py                # Unit tests
├── .github/
│   ├── actions/setup-uv/           # Reusable CI composite action
│   ├── dependabot.yml              # Automated dependency updates
│   ├── ISSUE_TEMPLATE/             # Bug report & feature request forms
│   ├── PULL_REQUEST_TEMPLATE.md    # PR checklist template
│   └── workflows/
│       ├── ci.yml                  # CI: parallel lint, format, typecheck, test matrix
│       ├── dependabot-auto-merge.yml  # Auto-merge minor/patch Dependabot PRs
│       └── release.yml             # Gated on CI, auto-version + GitHub Release
├── .claude/                         # Claude Code AI assistant config
│   ├── settings.json               # Permissions, hooks
│   ├── rules/                      # Development standards
│   ├── skills/                     # Slash commands (/tdd, /commit, /pr, etc.)
│   └── agents/                     # Specialized subagents
├── .editorconfig                   # Editor settings for non-Python files
├── pyproject.toml                  # Project config, deps, tool settings
├── uv.lock                        # Locked dependency versions
└── .pre-commit-config.yaml         # Pre-commit hook definitions
```
