"""Fixtures for template-specific tests.

These tests verify the template infrastructure itself (file structure,
init.sh behavior). They are automatically removed when init.sh runs.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

# Directories/files to exclude when copying the repo to a tmpdir
_EXCLUDE_DIRS = {
    '.git',
    '.venv',
    '.ruff_cache',
    '.pytest_cache',
    '__pycache__',
    'node_modules',
    'site',
    'dist',
    'build',
    '.coverage',
}


def _ignore_dirs(directory: str, contents: list[str]) -> set[str]:
    """Return set of directory names to exclude from shutil.copytree."""
    return {c for c in contents if c in _EXCLUDE_DIRS}


@pytest.fixture
def template_dir() -> Path:
    """Return the repo root path for structure tests."""
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def init_project(tmp_path: Path, template_dir: Path):
    """Factory fixture: copy repo to tmpdir and run init.sh.

    Returns a callable that accepts optional extra CLI flags
    (e.g. ``['--license', 'mit']``) and returns the tmpdir Path.
    """

    def _run(
        extra_flags: list[str] | None = None,
        stdin_text: str = 'n\ny\n',
    ) -> Path:
        project = tmp_path / 'project'
        shutil.copytree(
            template_dir,
            project,
            ignore=_ignore_dirs,
        )

        # Ensure init.sh is executable
        init_script = project / 'scripts' / 'init.sh'
        init_script.chmod(0o755)

        cmd = [
            str(init_script),
            '--name',
            'test-pkg',
            '--author',
            'Test Author',
            '--email',
            'test@example.com',
            '--github-owner',
            'testowner',
            '--description',
            'A test package',
        ]
        if extra_flags:
            cmd.extend(extra_flags)

        result = subprocess.run(
            cmd,
            cwd=str(project),
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            msg = (
                f'init.sh failed (rc={result.returncode})\n'
                f'STDOUT:\n{result.stdout}\n'
                f'STDERR:\n{result.stderr}'
            )
            raise RuntimeError(msg)

        return project

    return _run
