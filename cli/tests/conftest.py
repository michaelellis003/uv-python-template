"""Shared test fixtures for pypkgkit tests."""

from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable


REPO_OWNER = 'michaelellis003'
REPO_NAME = 'uv-python-template'


@pytest.fixture
def mock_release_json() -> bytes:
    """Return a minimal GitHub API release response."""
    payload = {
        'tag_name': 'v1.5.0',
        'name': 'v1.5.0',
    }
    return json.dumps(payload).encode()


@pytest.fixture
def mock_tarball(tmp_path: Path) -> Callable[[str], Path]:
    """Build a minimal tarball that mimics a GitHub archive.

    Returns a factory callable: ``make(tag) -> Path``.
    The tarball contains a top-level directory named
    ``{REPO_NAME}-{tag}/`` with ``pyproject.toml`` and
    ``scripts/init.py`` inside.
    """

    def _make(tag: str = 'v1.5.0') -> Path:
        prefix = f'{REPO_NAME}-{tag}'
        dest = tmp_path / f'{tag}.tar.gz'

        with tarfile.open(dest, 'w:gz') as tf:
            # pyproject.toml
            data = b'[project]\nname = "python-package-template"\n'
            info = tarfile.TarInfo(f'{prefix}/pyproject.toml')
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))

            # scripts/init.py
            data = b'# init script\n'
            info = tarfile.TarInfo(f'{prefix}/scripts/init.py')
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))

        return dest

    return _make
