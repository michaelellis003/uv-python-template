# Python Package Template

A production-ready template for starting new Python packages. Clone it,
rename a few things, and start building — dependency management, linting,
type checking, testing, and CI/CD are already wired up.

## Features

- **[uv](https://docs.astral.sh/uv/)** for fast Python package management
- **[Ruff](https://docs.astral.sh/ruff/)** for linting and formatting
- **[Pyright](https://github.com/microsoft/pyright)** for static type checking
- **[Pytest](https://docs.pytest.org/)** with coverage for testing
- **GitHub Actions** CI/CD with auto-release on merge to main
- **TDD-first** development lifecycle

## Quick Start

```bash
git clone https://github.com/michaelellis003/uv-python-template.git my-project
cd my-project
./scripts/init.sh
uv sync
uv run pytest -v --cov
```

## Next Steps

- [API Reference](api.md) — auto-generated documentation for all public functions
