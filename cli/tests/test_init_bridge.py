"""Tests for pypkgkit.init_bridge module."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from pypkgkit.init_bridge import load_init_module, run_init

if TYPE_CHECKING:
    from collections.abc import Callable


class TestLoadInitModule:
    def test_loads_module_with_project_config(
        self,
        tmp_path: Path,
        mock_tarball: Callable[[str], Path],
    ):
        tarball_path = mock_tarball('v1.5.0')
        from pypkgkit.scaffold import extract_tarball

        dest = tmp_path / 'extracted'
        dest.mkdir()
        inner = extract_tarball(tarball_path, dest)

        mod = load_init_module(inner)

        assert hasattr(mod, 'ProjectConfig')
        assert hasattr(mod, 'init_project')
        assert hasattr(mod, 'validate_name')

    def test_raises_when_init_py_missing(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError, match=r'init\.py'):
            load_init_module(tmp_path)


class TestRunInit:
    def test_calls_init_project_and_returns_true(
        self,
        tmp_path: Path,
        mock_tarball: Callable[[str], Path],
    ):
        tarball_path = mock_tarball('v1.5.0')
        from pypkgkit.scaffold import extract_tarball

        dest = tmp_path / 'extracted'
        dest.mkdir()
        template_dir = extract_tarball(tarball_path, dest)

        config_kwargs = {
            'name': 'my-pkg',
            'author': 'Jane',
            'email': 'j@e.com',
            'github_owner': 'jane',
            'description': 'A test project',
            'license_key': 'mit',
            'enable_pypi': False,
        }

        result = run_init(template_dir, config_kwargs)

        assert result is True
        assert (template_dir / '.initialized').exists()
        assert (template_dir / '.initialized').read_text() == 'my-pkg'

    def test_returns_false_on_init_failure(
        self,
        tmp_path: Path,
        mock_tarball: Callable[[str], Path],
        capsys: pytest.CaptureFixture[str],
    ):
        tarball_path = mock_tarball('v1.5.0')
        from pypkgkit.scaffold import extract_tarball

        dest = tmp_path / 'extracted'
        dest.mkdir()
        template_dir = extract_tarball(tarball_path, dest)

        # Overwrite init.py with one that raises
        init_py = template_dir / 'scripts' / 'init.py'
        init_py.write_text(
            'from dataclasses import dataclass, field\n'
            '@dataclass(frozen=True)\n'
            'class ProjectConfig:\n'
            '    name: str\n'
            '    author: str\n'
            '    email: str\n'
            '    github_owner: str\n'
            '    description: str\n'
            '    license_key: str\n'
            '    enable_pypi: bool\n'
            '    snake_name: str = field(init=False)\n'
            '    kebab_name: str = field(init=False)\n'
            '    title_name: str = field(init=False)\n'
            '    github_repo: str = field(init=False)\n'
            '    def __post_init__(self):\n'
            '        object.__setattr__(self, "snake_name", '
            '            self.name.replace("-", "_"))\n'
            '        object.__setattr__(self, "kebab_name", '
            '            self.name.replace("_", "-"))\n'
            '        object.__setattr__(self, "title_name", '
            '            self.name.replace("-", " ").title())\n'
            '        object.__setattr__(self, "github_repo", '
            '            f"{self.github_owner}/{self.kebab_name}")\n'
            'def init_project(config, root):\n'
            '    raise RuntimeError("boom")\n'
        )

        config_kwargs = {
            'name': 'my-pkg',
            'author': 'Jane',
            'email': 'j@e.com',
            'github_owner': 'jane',
            'description': 'A test project',
            'license_key': 'mit',
            'enable_pypi': False,
        }

        result = run_init(template_dir, config_kwargs)
        assert result is False

        captured = capsys.readouterr()
        assert 'boom' in captured.err

    def test_uses_preloaded_init_mod(
        self,
        tmp_path: Path,
        mock_tarball: Callable[[str], Path],
    ):
        """Test that passing init_mod skips load_init_module."""
        tarball_path = mock_tarball('v1.5.0')
        from pypkgkit.init_bridge import load_init_module
        from pypkgkit.scaffold import extract_tarball

        dest = tmp_path / 'extracted'
        dest.mkdir()
        template_dir = extract_tarball(tarball_path, dest)

        mod = load_init_module(template_dir)

        config_kwargs = {
            'name': 'my-pkg',
            'author': 'Jane',
            'email': 'j@e.com',
            'github_owner': 'jane',
            'description': 'A test project',
            'license_key': 'mit',
            'enable_pypi': False,
        }

        result = run_init(template_dir, config_kwargs, init_mod=mod)
        assert result is True
        assert (template_dir / '.initialized').read_text() == 'my-pkg'

    def test_debug_env_prints_traceback(
        self,
        tmp_path: Path,
        mock_tarball: Callable[[str], Path],
        capsys: pytest.CaptureFixture[str],
    ):
        """Test PYPKGKIT_DEBUG prints full traceback on failure."""
        tarball_path = mock_tarball('v1.5.0')
        from pypkgkit.scaffold import extract_tarball

        dest = tmp_path / 'extracted'
        dest.mkdir()
        template_dir = extract_tarball(tarball_path, dest)

        # Overwrite init.py with one that raises
        init_py = template_dir / 'scripts' / 'init.py'
        init_py.write_text(
            'from dataclasses import dataclass, field\n'
            '@dataclass(frozen=True)\n'
            'class ProjectConfig:\n'
            '    name: str\n'
            '    author: str\n'
            '    email: str\n'
            '    github_owner: str\n'
            '    description: str\n'
            '    license_key: str\n'
            '    enable_pypi: bool\n'
            '    snake_name: str = field(init=False)\n'
            '    kebab_name: str = field(init=False)\n'
            '    title_name: str = field(init=False)\n'
            '    github_repo: str = field(init=False)\n'
            '    def __post_init__(self):\n'
            '        object.__setattr__(self, "snake_name", '
            '            self.name.replace("-", "_"))\n'
            '        object.__setattr__(self, "kebab_name", '
            '            self.name.replace("_", "-"))\n'
            '        object.__setattr__(self, "title_name", '
            '            self.name.replace("-", " ").title())\n'
            '        object.__setattr__(self, "github_repo", '
            '            f"{self.github_owner}/{self.kebab_name}")\n'
            'def init_project(config, root):\n'
            '    raise RuntimeError("debug-boom")\n'
        )

        config_kwargs = {
            'name': 'my-pkg',
            'author': 'Jane',
            'email': 'j@e.com',
            'github_owner': 'jane',
            'description': 'A test project',
            'license_key': 'mit',
            'enable_pypi': False,
        }

        with patch.dict('os.environ', {'PYPKGKIT_DEBUG': '1'}):
            result = run_init(template_dir, config_kwargs)

        assert result is False
        captured = capsys.readouterr()
        assert 'debug-boom' in captured.err
        assert 'Traceback' in captured.err
        assert 'RuntimeError' in captured.err

    def test_no_debug_env_no_traceback(
        self,
        tmp_path: Path,
        mock_tarball: Callable[[str], Path],
        capsys: pytest.CaptureFixture[str],
    ):
        """Test no traceback when PYPKGKIT_DEBUG is not set."""
        tarball_path = mock_tarball('v1.5.0')
        from pypkgkit.scaffold import extract_tarball

        dest = tmp_path / 'extracted'
        dest.mkdir()
        template_dir = extract_tarball(tarball_path, dest)

        # Overwrite init.py with one that raises
        init_py = template_dir / 'scripts' / 'init.py'
        init_py.write_text(
            'from dataclasses import dataclass, field\n'
            '@dataclass(frozen=True)\n'
            'class ProjectConfig:\n'
            '    name: str\n'
            '    author: str\n'
            '    email: str\n'
            '    github_owner: str\n'
            '    description: str\n'
            '    license_key: str\n'
            '    enable_pypi: bool\n'
            '    snake_name: str = field(init=False)\n'
            '    kebab_name: str = field(init=False)\n'
            '    title_name: str = field(init=False)\n'
            '    github_repo: str = field(init=False)\n'
            '    def __post_init__(self):\n'
            '        object.__setattr__(self, "snake_name", '
            '            self.name.replace("-", "_"))\n'
            '        object.__setattr__(self, "kebab_name", '
            '            self.name.replace("_", "-"))\n'
            '        object.__setattr__(self, "title_name", '
            '            self.name.replace("-", " ").title())\n'
            '        object.__setattr__(self, "github_repo", '
            '            f"{self.github_owner}/{self.kebab_name}")\n'
            'def init_project(config, root):\n'
            '    raise RuntimeError("no-debug-boom")\n'
        )

        config_kwargs = {
            'name': 'my-pkg',
            'author': 'Jane',
            'email': 'j@e.com',
            'github_owner': 'jane',
            'description': 'A test project',
            'license_key': 'mit',
            'enable_pypi': False,
        }

        with patch.dict('os.environ', {}, clear=False):
            # Ensure PYPKGKIT_DEBUG is not set
            import os

            os.environ.pop('PYPKGKIT_DEBUG', None)
            result = run_init(template_dir, config_kwargs)

        assert result is False
        captured = capsys.readouterr()
        assert 'no-debug-boom' in captured.err
        assert 'Traceback' not in captured.err
