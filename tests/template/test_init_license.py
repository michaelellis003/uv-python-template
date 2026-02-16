"""Integration tests for init.sh license setup.

These tests copy the repo to a temp directory, run init.sh with
various --license flags, and verify the resulting project state.
"""

from datetime import datetime, timezone

import pytest

CURRENT_YEAR = str(datetime.now(tz=timezone.utc).year)


# ------------------------------------------------------------------
# --license mit
# ------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.slow
class TestLicenseMit:
    """Tests for init.sh --license mit."""

    @pytest.fixture(autouse=True)
    def _setup(self, init_project):
        """Run init.sh with --license mit once for all tests."""
        self.project = init_project(
            extra_flags=['--license', 'mit'],
        )

    def test_init_license_mit_creates_license_header(self):
        """Test that LICENSE_HEADER exists with MIT SPDX id."""
        header = self.project / 'LICENSE_HEADER'
        assert header.exists(), 'LICENSE_HEADER not created'
        content = header.read_text()
        assert 'SPDX-License-Identifier: MIT' in content
        assert f'Copyright {CURRENT_YEAR} Test Author' in content

    def test_init_license_mit_adds_insert_license_hook(self):
        """Test that .pre-commit-config.yaml has insert-license."""
        config = (self.project / '.pre-commit-config.yaml').read_text()
        assert 'insert-license' in config

    def test_init_license_mit_applies_headers_to_py_files(self):
        """Test that all .py files have MIT SPDX headers."""
        snake_name = 'test_pkg'
        for directory in (
            self.project / snake_name,
            self.project / 'tests',
        ):
            if not directory.exists():
                continue
            for py_file in directory.rglob('*.py'):
                content = py_file.read_text()
                assert '# Copyright' in content, (
                    f'{py_file.name} missing Copyright header'
                )
                assert '# SPDX-License-Identifier: MIT' in content, (
                    f'{py_file.name} missing SPDX header'
                )

    def test_init_license_mit_updates_pyproject_license(self):
        """Test that pyproject.toml has MIT license."""
        pyproject = (self.project / 'pyproject.toml').read_text()
        assert 'license = {text = "MIT"}' in pyproject

    def test_init_license_mit_updates_meta_yaml_license(self):
        """Test that recipe/meta.yaml has MIT license."""
        meta_yaml = self.project / 'recipe' / 'meta.yaml'
        assert meta_yaml.exists(), 'recipe/meta.yaml not found'
        content = meta_yaml.read_text()
        assert 'license: MIT' in content
        assert 'license: Apache-2.0' not in content


# ------------------------------------------------------------------
# --license none
# ------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.slow
class TestLicenseNone:
    """Tests for init.sh --license none."""

    @pytest.fixture(autouse=True)
    def _setup(self, init_project):
        """Run init.sh with --license none once for all tests."""
        self.project = init_project(
            extra_flags=['--license', 'none'],
        )

    def test_init_license_none_keeps_license_file(self):
        """Test that LICENSE file still exists."""
        assert (self.project / 'LICENSE').exists()

    def test_init_license_none_no_license_header_file(self):
        """Test that LICENSE_HEADER is not created."""
        assert not (self.project / 'LICENSE_HEADER').exists()

    def test_init_license_none_no_insert_license_hook(self):
        """Test that .pre-commit-config.yaml has no insert-license."""
        config = (self.project / '.pre-commit-config.yaml').read_text()
        assert 'insert-license' not in config

    def test_init_license_none_keeps_meta_yaml_license(self):
        """Test that recipe/meta.yaml keeps Apache-2.0 license."""
        meta_yaml = self.project / 'recipe' / 'meta.yaml'
        assert meta_yaml.exists(), 'recipe/meta.yaml not found'
        content = meta_yaml.read_text()
        assert 'license: Apache-2.0' in content

    def test_init_license_none_no_spdx_headers(self):
        """Test that no .py files have SPDX headers."""
        snake_name = 'test_pkg'
        for directory in (
            self.project / snake_name,
            self.project / 'tests',
        ):
            if not directory.exists():
                continue
            for py_file in directory.rglob('*.py'):
                content = py_file.read_text()
                assert '# SPDX-License-Identifier' not in content, (
                    f'{py_file.name} has unexpected SPDX header'
                )


# ------------------------------------------------------------------
# Default (no --license flag)
# ------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.slow
def test_init_without_license_flag_defaults_to_none(init_project):
    """Test that omitting --license and choosing 0 skips setup."""
    # When no --license flag, init.sh prompts for:
    # 1. PyPI publishing (n), 2. license choice (0=skip), 3. confirm (y)
    project = init_project(
        extra_flags=None,
        stdin_text='n\n0\ny\n',
    )

    assert not (project / 'LICENSE_HEADER').exists()

    config = (project / '.pre-commit-config.yaml').read_text()
    assert 'insert-license' not in config

    snake_name = 'test_pkg'
    for directory in (project / snake_name, project / 'tests'):
        if not directory.exists():
            continue
        for py_file in directory.rglob('*.py'):
            content = py_file.read_text()
            assert '# SPDX-License-Identifier' not in content
