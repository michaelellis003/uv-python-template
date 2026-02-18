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

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed and on PATH

## License

Apache-2.0
