"""Shared test fixtures for pypkgkit tests."""

from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from pypkgkit.scaffold import REPO_NAME

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture
def mock_release_json() -> bytes:
    """Return a minimal GitHub API release response."""
    payload = {
        'tag_name': 'v1.5.0',
        'name': 'v1.5.0',
    }
    return json.dumps(payload).encode()


_MOCK_INIT_PY = '''\
"""Stub init.py for testing."""
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass(frozen=True)
class ProjectConfig:
    """Minimal ProjectConfig for tests."""
    name: str
    author: str
    email: str
    github_owner: str
    description: str
    license_key: str
    enable_pypi: bool
    snake_name: str = field(init=False)
    kebab_name: str = field(init=False)
    title_name: str = field(init=False)
    github_repo: str = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "snake_name", self.name.replace("-", "_"))
        object.__setattr__(self, "kebab_name", self.name.replace("_", "-"))
        title = self.name.replace("-", " ").title()
        object.__setattr__(self, "title_name", title)
        repo = f"{self.github_owner}/{self.kebab_name}"
        object.__setattr__(self, "github_repo", repo)

def validate_name(name):
    if not name:
        raise ValueError("empty name")

def validate_email(email):
    if "@" not in email:
        raise ValueError("bad email")

def validate_author_name(name):
    pass

def validate_github_owner(owner):
    pass

def validate_description(desc):
    if not desc.strip():
        raise ValueError("empty description")

OFFLINE_LICENSES = ()

def init_project(config, root):
    """Stub that writes a marker file."""
    (root / ".initialized").write_text(config.name)
    return True
'''


@pytest.fixture
def mock_tarball(tmp_path: Path) -> Callable[[str], Path]:
    """Build a minimal tarball that mimics a GitHub archive.

    Returns a factory callable: ``make(tag) -> Path``.
    The tarball contains a top-level directory named
    ``{REPO_NAME}-{tag}/`` with ``pyproject.toml`` and
    ``scripts/init.py`` inside.  The init.py stub includes
    ``ProjectConfig``, validators, and ``init_project`` so
    ``init_bridge`` tests can import it.
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

            # scripts/init.py (importable stub)
            data = _MOCK_INIT_PY.encode()
            info = tarfile.TarInfo(f'{prefix}/scripts/init.py')
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))

        return dest

    return _make
