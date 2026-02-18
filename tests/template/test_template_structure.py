"""Tests that the template repository ships clean.

These verify no license artifacts are baked into the template
before init.py is run.
"""

from pathlib import Path


def test_template_has_no_license_header_file(template_dir: Path):
    """Test that LICENSE_HEADER does not exist at repo root."""
    assert not (template_dir / 'LICENSE_HEADER').exists()


def test_template_py_files_have_no_spdx_headers(template_dir: Path):
    """Test that no .py file has SPDX license headers."""
    pkg_dir = template_dir / 'python_package_template'
    tests_dir = template_dir / 'tests'
    # Exclude tests/template/ — those files reference the string
    # in assertions, not as actual license headers.
    exclude = template_dir / 'tests' / 'template'

    for directory in (pkg_dir, tests_dir):
        for py_file in directory.rglob('*.py'):
            if py_file.is_relative_to(exclude):
                continue
            content = py_file.read_text()
            assert '# SPDX-License-Identifier' not in content, (
                f'{py_file} contains an SPDX header'
            )


def test_pre_commit_config_has_no_insert_license_hook(
    template_dir: Path,
):
    """Test that .pre-commit-config.yaml has no insert-license hook."""
    config = (template_dir / '.pre-commit-config.yaml').read_text()
    assert 'insert-license' not in config


def test_pyproject_has_apache_license(template_dir: Path):
    """Test that pyproject.toml has Apache-2.0 license."""
    pyproject = (template_dir / 'pyproject.toml').read_text()
    assert 'license = {text = "Apache-2.0"}' in pyproject


def test_license_file_exists(template_dir: Path):
    """Test that LICENSE file exists at repo root."""
    assert (template_dir / 'LICENSE').exists()
