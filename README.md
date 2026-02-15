# Python Package Template

[![](https://img.shields.io/badge/Python-3.10|3.11|3.12-blue)](https://www.python.org)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Pyright](https://img.shields.io/badge/Pyright-enabled-brightgreen)](https://github.com/microsoft/pyright)
[![codecov](https://codecov.io/gh/michaelellis003/python-package-template/graph/badge.svg?token=TUKP19SKJ3)](https://codecov.io/gh/michaelellis003/python-package-template)
[![License](https://img.shields.io/github/license/michaelellis003/python-package-template)](https://github.com/michaelellis003/python-package-template/blob/main/LICENSE)

The `python-package-template` repository offers a robust template for creating Python packages. It incorporates best practices for project structure, dependency management, testing, and CI/CD, enabling developers to quickly set up and maintain high-quality Python projects.

## Table of Contents
1. [Features](#features)
2. [How to use](#how-to-use)
3. [Using uv](#using-uv)
   - [Managing Dependencies](#managing-dependencies)
   - [Updating Package Version](#updating-package-version)
5. [CI/CD Workflows](#ci-cd-workflows)

## Features
- [uv](https://docs.astral.sh/uv/) for Python package management and environment handling.
- [Pre-commit hooks](https://pre-commit.com) to enforce consistent code style, including:
    - [Ruff](https://docs.astral.sh/ruff/) for linting and formatting,
    - [Pyright](https://github.com/microsoft/pyright) for static type checking.
- [Pytest](https://docs.pytest.org/en/stable/) for running code tests.
- **GitHub Actions** for CI/CD, including automated tests, lint checks, and release tagging.

## How to use
1. Install uv
- [See the uv documentation](https://docs.astral.sh/uv/getting-started/installation/) for more details and alternate methods. Examples include:
    ```
    # using the standalone installer
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

2. Install package dependencies needed for development:
    ```
    uv sync
    ```

3. Enable pre-commit hooks in your local environment so they run automatically before every commit:
    ```
    uv run pre-commit install
    ```

4. Update project metadata in:
    - `pyproject.toml`:
        - Change the project name, version, and author information to match your package.
    - `README.md`, `LICENSE`, `CHANGELOG.md` (optional):
        - Replace placeholder names, badges, and repository links with those for your project.

## Using uv
For the full uv documentation, visit the [full docs](https://docs.astral.sh/uv/)

### Managing Dependencies
- Adding Dependencies
    - To add a new runtime dependency to your project, use:
        ```
        uv add <package_name>
        ```
    - Example:
        ```
        uv add requests
        ```
        This updates your `pyproject.toml` under `[project.dependencies]` and synchronizes your virtual environment automatically.

    - For dev-only dependencies, use the `--dev` flag:
        ```
        uv add --dev pytest
        ```
        This updates `[dependency-groups]` in your `pyproject.toml`.

    - uv supports organizing dependencies into named groups:
        ```
        uv add --group <group-name> <package_name>
        ```
        Read more about this [here](https://docs.astral.sh/uv/concepts/projects/dependencies/)

- Removing Dependencies
    - Similarly, to remove a dependency:
        ```
        uv remove requests
        ```
        uv removes the package from your `pyproject.toml` and uninstalls it from your virtual environment.

### Updating Package Version
- Before merging a branch into main to release a new version of your package you will need to update the version number in the `pyproject.toml`. If you do not update the version number before merging to the main branch the `release-and-tag.yml` workflow will fail.
- Update the `version` field directly in `pyproject.toml` under the `[project]` table.

## CI-CD Workflows

This project uses GitHub Actions for continuous integration and deployment.

### On Push to Non-Main Branches

- **Linting & Formatting:** Runs `pre-commit` checks using `ruff`.
- **Testing:** Runs `pytest` across Python 3.10, 3.11, and 3.12.
- **Coverage Upload:** Sends test coverage reports to Codecov.

### On Merging into Main

- **Tagging & Releasing:** Automatically tags a new version based on `pyproject.toml`.
- **Builds the Package:** Uses uv to create distribution files.
- **Creates a GitHub Release:** Uploads the built package to GitHub releases.
