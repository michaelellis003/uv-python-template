# Python Package Template

[![](https://img.shields.io/badge/Python-3.10|3.11|3.12|3.13-blue)](https://www.python.org)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Pyright](https://img.shields.io/badge/Pyright-enabled-brightgreen)](https://github.com/microsoft/pyright)
[![codecov](https://codecov.io/gh/michaelellis003/uv-python-template/graph/badge.svg?token=TUKP19SKJ3)](https://codecov.io/gh/michaelellis003/uv-python-template)
[![License](https://img.shields.io/github/license/michaelellis003/uv-python-template)](https://github.com/michaelellis003/uv-python-template/blob/main/LICENSE)

A production-ready template for starting new Python packages. Clone it, rename a few things, and start building — dependency management, linting, type checking, testing, and CI/CD are already wired up.

<!-- TEMPLATE-ONLY-START -->
## Demo

From zero to a working, tested, CI-enabled Python package:

```bash
uvx pypkgkit new my-project \
    --name my-pkg --author "Jane Smith" --email jane@example.com \
    --github-owner janesmith --description "My awesome package" --license mit
cd my-project
uv sync
uv run pytest -v --cov
```

That's it. You have a package with Ruff linting, Pyright type checking, pytest with coverage, pre-commit hooks, GitHub Actions CI across Python 3.10--3.13, semantic versioning, and MkDocs documentation -- all configured and ready to go.

## Create your project

### Prerequisites

- Python 3.10+ (uv will download it if missing)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

Install uv if you don't have it:

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Option A: pypkgkit (one command)

The fastest way. Downloads the latest template, runs init, and sets up git:

```bash
uvx pypkgkit new my-project
```

Pass `--github` to also create a GitHub repo, push, and configure branch protection (requires [gh CLI](https://cli.github.com)):

```bash
uvx pypkgkit new my-project \
    --name my-pkg --author "Jane Smith" --email jane@example.com \
    --github --description "My awesome package" --license mit
```

### Option B: Clone and init

```bash
git clone https://github.com/michaelellis003/uv-python-template.git my-project
cd my-project
rm -rf .git && git init
```

Then run the init script. It renames the package directory, updates all references, resets the version and changelog, and optionally configures your license:

```bash
# Interactive -- prompts for everything
uv run --script ./scripts/init.py

# Non-interactive -- pass all values as flags
uv run --script ./scripts/init.py \
    --name my-pkg --author "Jane Smith" --email jane@example.com \
    --github-owner janesmith --description "My awesome package" --license mit
```

### init.py flags

| Flag | Description |
|------|-------------|
| `--name`, `-n` | Package name (kebab-case) |
| `--author` | Author name |
| `--email` | Author email |
| `--github-owner` | GitHub username or organization |
| `--description` | Short project description |
| `--license` | License key (e.g. `mit`, `bsd-3-clause`, `gpl-3.0`, `apache-2.0`) |
| `--pypi` | Enable PyPI publishing in the release workflow |

### After init

Install dependencies, enable pre-commit hooks, and verify:

```bash
uv sync
uv run pre-commit install
uv run pytest -v --durations=0 --cov
```
<!-- TEMPLATE-ONLY-END -->

## Write your code

The demo functions (`hello`, `add`, `subtract`, `multiply`) in `python_package_template/main.py` show the TDD workflow in action. Replace them with your own code, update `__init__.py` exports, and rewrite the tests in `tests/test_main.py`.

### Adding dependencies

```bash
uv add requests                  # Runtime dependency
uv add --dev pytest-mock         # Dev dependency
uv add --group docs sphinx       # Named group (e.g. docs)
```

### Running tests

```bash
uv run pytest -v --durations=0 --cov
```

### Linting and formatting

Run everything at once (same checks as CI):

```bash
uv run pre-commit run --all-files
```

Or individually:

```bash
uv run ruff check . --fix        # Lint with auto-fix
uv run ruff format .             # Format
uv run pyright                   # Type check
```

### Docs

```bash
uv run --group docs mkdocs serve              # Preview at http://127.0.0.1:8000
uv run --group docs mkdocs build --strict     # Build static site
```

Docs deploy to [GitHub Pages](https://michaelellis003.github.io/uv-python-template/) automatically on push to `main`. Enable it under **Settings > Pages > Source: GitHub Actions**.

## Push and review

### What CI checks

On every PR and push to `main`, CI runs these checks in parallel: Ruff lint, Ruff format, Pyright, pytest across Python 3.10--3.13, coverage enforcement, lockfile sync, macOS and Windows smoke tests, and build validation (sdist + wheel + twine check + install test). All must pass before merging.

### Conventional commits

Commit messages drive automatic versioning. Use the format `<type>(<scope>): <description>`:

- `feat:` -- minor version bump (0.3.0 -> 0.4.0)
- `fix:` / `perf:` -- patch bump (0.3.0 -> 0.3.1)
- `feat!:` or `BREAKING CHANGE` footer -- major bump (0.3.0 -> 1.0.0)
- `test:`, `refactor:`, `docs:`, `chore:`, `ci:` -- no version bump

### Branch naming

```
<type>/<issue-id>-<short-description>
```

For example: `feat/AUTH-42-jwt-refresh-rotation`, `fix/API-118-null-pointer`.

## Ship it

### Automatic releases

When you merge to `main`, [python-semantic-release](https://python-semantic-release.readthedocs.io/) reads your commit messages, bumps the version in `pyproject.toml`, creates a git tag, and publishes a GitHub Release with built artifacts. No manual steps needed.

### PyPI publishing

To publish to PyPI automatically on each release:

1. Run `uv run --script ./scripts/init.py --pypi` to enable publishing (or uncomment the `PYPI-START`/`PYPI-END` block in `release.yml` manually).
2. Add a [trusted publisher](https://docs.pypi.org/trusted-publishers/) on pypi.org for your repo (workflow: `release.yml`).
3. Every merge to `main` with a `feat:` or `fix:` commit will auto-publish.

A manual **test-publish.yml** workflow is included for validating your pipeline against [TestPyPI](https://test.pypi.org) first. A conda-forge recipe skeleton lives in `recipe/meta.yaml`, ready to submit to [staged-recipes](https://github.com/conda-forge/staged-recipes) once your package is on PyPI. See the full [Publishing Guide](https://michaelellis003.github.io/uv-python-template/publishing/) for details.

### RELEASE_TOKEN

The release workflow works out of the box with the default `GITHUB_TOKEN`. However, commits made by `github-actions[bot]` don't trigger downstream workflows (like docs deploy). To fix that, create a fine-grained PAT with **Contents: read/write** and add it as a repo secret named `RELEASE_TOKEN`.

<!-- TEMPLATE-ONLY-START -->
## After initialization

These are the manual steps that remain after running init:

| Step | Details |
|------|---------|
| Replace demo code | Swap out `hello`/`add`/`subtract`/`multiply` in your package's `main.py` |
| Set up Codecov | Add `CODECOV_TOKEN` secret in repo settings, update the badge URL in README |
| Enable GitHub Pages | **Settings > Pages > Source: GitHub Actions** |
| Branch protection | Run `./scripts/setup-repo.sh` (requires `gh` CLI and admin access) |
| Update keywords | Fill in `keywords = []` in `pyproject.toml` |
| Add `RELEASE_TOKEN` (optional) | Fine-grained PAT with Contents: read/write, added as a repo secret |
<!-- TEMPLATE-ONLY-END -->

<details>
<summary>Project structure</summary>

```
python_package_template/         # Package source (rename this)
  __init__.py                    # Public API exports + __version__
  __main__.py                    # python -m entry point
  main.py                       # Core module with demo functions
  py.typed                       # PEP 561 type checking marker
tests/
  conftest.py                    # Shared test fixtures
  test_init.py                   # Package-level tests
  test_main.py                   # Unit tests for demo functions
  test_main_module.py            # Tests for __main__.py entry point
  template/                      # Template tests (removed by init)
    conftest.py                  # Fixtures: template_dir, init_project
    test_template_structure.py   # Verifies template ships clean
    test_init_license.py         # Integration tests for init license setup
    test_init_flags.py           # Tests for flag validation and special chars
  e2e/                           # Docker-based end-to-end tests
    Dockerfile                   # Parameterized base image
    verify-project.sh            # Container-side verification
    run-e2e.sh                   # Host-side matrix runner
docs/
  index.md                       # Documentation landing page
  api.md                         # Auto-generated API reference
  publishing.md                  # PyPI, TestPyPI, and conda-forge guide
.github/
  actions/setup-uv/              # Reusable CI composite action
  workflows/
    ci.yml                       # Lint, format, typecheck, test matrix
    release.yml                  # Auto-version + GitHub Release
    docs.yml                     # Build and deploy to GitHub Pages
    e2e.yml                      # Docker-based init verification
    test-publish.yml             # Manual TestPyPI publishing
    dependabot-auto-merge.yml    # Auto-merge minor/patch Dependabot PRs
    cli-release.yml              # CLI pypkgkit release
cli/                             # CLI pypkgkit package (removed by init)
  src/pypkgkit/                  # CLI source code
  tests/                         # CLI tests
scripts/
  init.py                        # Template initialization script
  setup-repo.sh                  # Branch protection setup
.pre-commit-config.yaml          # Pre-commit hook definitions
pyproject.toml                   # Project config, deps, tool settings
mkdocs.yml                       # MkDocs documentation config
```

</details>
