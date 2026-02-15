# CLAUDE.md

This file provides guidance for AI assistants working with this repository.
Modular rules live in `.claude/rules/` — each covers a specific concern.

## Project Overview

**python-package-template** (v0.3.0) — a production-ready template for
starting new Python packages. Uses uv, Ruff, Pyright, and pre-commit
hooks. Licensed Apache-2.0.

This is a **template repository**. Users clone it, rename the package
directory and metadata, then start building. The demo functions
(`hello`, `add`, `subtract`, `multiply`) are working examples of the
TDD workflow.

## Repository Structure

```
python_package_template/         # Main package source
  __init__.py                    # Public API exports (add, multiply, hello)
  main.py                       # Core module with demo functions
tests/
  test_init.py                  # Unit tests
.github/
  actions/setup-uv/            # Reusable CI composite action
  workflows/
    ci.yml                      # CI: lint + test matrix (3.10, 3.11, 3.12)
    release-and-tag.yml         # Release: auto-tag + GitHub Release on merge
.claude/
  settings.json                 # Claude Code project settings and hooks
  rules/                        # Modular instructions by topic
    tdd-workflow.md             # TDD Red-Green-Refactor lifecycle
    code-style.md               # Formatting, linting, docstrings
    git-conventions.md          # Branching, commits, PR workflow
    testing.md                  # Test structure and conventions
  skills/                       # Custom slash commands
    tdd/SKILL.md                # /tdd — TDD cycle for a feature
    commit/SKILL.md             # /commit — conventional commit
    pr/SKILL.md                 # /pr — open a pull request
    lint/SKILL.md               # /lint — run all quality checks
    issue/SKILL.md              # /issue — scaffold an issue
  agents/
    code-reviewer.md            # Code review subagent
    test-writer.md              # Test-first subagent
pyproject.toml                  # Project config, deps, tool settings
.pre-commit-config.yaml         # Pre-commit hook definitions
.python-versions                # Supported Python versions
```

## Quick Reference — Development Commands

```bash
uv sync                                      # Install deps
uv run pytest -v --durations=0 --cov         # Run tests
uv run pre-commit run --all-files            # Lint + format + type check
uv run ruff check . --fix                    # Ruff linter only
uv run ruff format .                         # Ruff formatter only
uv run pyright                               # Type checker only
```

## Development Lifecycle (TDD-First)

This project follows a strict TDD-first workflow. See
`.claude/rules/tdd-workflow.md` for the full Red-Green-Refactor protocol.

**The loop:**
1. Define work (issue with Given/When/Then acceptance criteria)
2. Branch (`<type>/<issue-id>-<short-description>`)
3. RED — write one failing test
4. GREEN — minimal code to pass
5. REFACTOR — clean up, tests still pass
6. COMMIT — `<type>(<scope>): <description>` after each cycle
7. Repeat 3-6 until acceptance criteria are met
8. DOCS — update documentation to reflect user-facing changes
9. PUSH — run lint + tests before pushing
10. PR — self-review, open PR, request review
11. CI — format, lint, type check, test matrix
12. MERGE — squash and merge to main

## Key Rules

- **Always write tests before implementation** (TDD)
- **Conventional Commits** — `feat`, `fix`, `test`, `refactor`, `docs`, `chore`
- **79-char lines, 4-space indent, single quotes, Google docstrings**
- **All functions need type hints and docstrings**
- **Update docs** (README, docstrings, CLAUDE.md) when behavior changes
- **Run `uv run pre-commit run --all-files` before every push**
- **PR target: < 400 lines changed**
