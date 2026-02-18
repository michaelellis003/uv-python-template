# pypkgkit

Scaffold new Python packages from the
[uv-python-template](https://github.com/michaelellis003/uv-python-template).

## Installation

```bash
# With uv (recommended)
uvx pypkgkit new my-project

# Or install globally
uv tool install pypkgkit
```

## Usage

```bash
# Interactive — prompts for all values
pypkgkit new my-project

# Non-interactive — pass all values as flags
pypkgkit new my-project \
    --name my-pkg \
    --author "Jane Smith" \
    --email jane@example.com \
    --github-owner janesmith \
    --description "My awesome package" \
    --license mit

# Full GitHub setup — creates repo, pushes, and configures rulesets
pypkgkit new my-project \
    --name my-pkg \
    --author "Jane Smith" \
    --email jane@example.com \
    --github \
    --description "My awesome package"

# Private repo with required PR reviews
pypkgkit new my-project --github --private --require-reviews 2

# Pin a specific template version
pypkgkit new my-project --template-version v1.5.0

# Show version
pypkgkit --version
```

## How It Works

1. Fetches the latest release tag from the GitHub API
2. Downloads the release tarball (no API rate limit)
3. Extracts to the target directory
4. Runs `scripts/init.py` via `uv run --script` to initialize the project
5. Initializes a git repository with an initial commit
6. *(with `--github`)* Creates a GitHub repository via `gh` CLI
7. *(with `--github`)* Pushes to GitHub
8. *(with `--github`)* Configures branch protection rulesets (required CI status checks, admin bypass)

When `--github` is used without `--github-owner`, the owner is auto-detected from `gh auth status`.

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed and on PATH
- [git](https://git-scm.com) installed and on PATH
- *(for `--github`)* [gh CLI](https://cli.github.com) installed and authenticated

## License

Apache-2.0
