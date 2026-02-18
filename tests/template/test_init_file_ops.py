"""Unit tests for init.py file operation functions.

These tests use tmp_path with minimal file trees to verify each
file manipulation function in isolation, without running full init.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load scripts/init.py as a module via importlib (PEP 723 script)
# ---------------------------------------------------------------------------

_INIT_SCRIPT = (
    Path(__file__).resolve().parent.parent.parent / 'scripts' / 'init.py'
)


@pytest.fixture(scope='module')
def init_mod():
    """Import scripts/init.py as a Python module."""
    spec = importlib.util.spec_from_file_location('init', _INIT_SCRIPT)
    assert spec is not None, f'Cannot load {_INIT_SCRIPT}'
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules['init'] = mod
    spec.loader.exec_module(mod)
    yield mod
    sys.modules.pop('init', None)


# ===================================================================
# find_project_files
# ===================================================================


class TestFindProjectFiles:
    """Tests for find_project_files."""

    def test_find_project_files_returns_text_files(self, init_mod, tmp_path):
        """Test that text files are found."""
        (tmp_path / 'file.py').write_text('hello')
        (tmp_path / 'file.toml').write_text('[project]')
        result = init_mod.find_project_files(tmp_path)
        names = {p.name for p in result}
        assert 'file.py' in names
        assert 'file.toml' in names

    def test_find_project_files_excludes_git_dir(self, init_mod, tmp_path):
        """Test that .git directory contents are excluded."""
        git_dir = tmp_path / '.git'
        git_dir.mkdir()
        (git_dir / 'config').write_text('gitconfig')
        (tmp_path / 'file.py').write_text('hello')
        result = init_mod.find_project_files(tmp_path)
        names = {p.name for p in result}
        assert 'config' not in names

    def test_find_project_files_excludes_venv(self, init_mod, tmp_path):
        """Test that .venv directory is excluded."""
        venv = tmp_path / '.venv'
        venv.mkdir()
        (venv / 'pyvenv.cfg').write_text('home = /usr')
        (tmp_path / 'file.py').write_text('hello')
        result = init_mod.find_project_files(tmp_path)
        names = {p.name for p in result}
        assert 'pyvenv.cfg' not in names

    def test_find_project_files_excludes_binary_extensions(
        self, init_mod, tmp_path
    ):
        """Test that binary file extensions are excluded."""
        (tmp_path / 'image.png').write_bytes(b'\x89PNG')
        (tmp_path / 'file.py').write_text('hello')
        result = init_mod.find_project_files(tmp_path)
        names = {p.name for p in result}
        assert 'image.png' not in names

    def test_find_project_files_excludes_lockfile(self, init_mod, tmp_path):
        """Test that uv.lock is excluded."""
        (tmp_path / 'uv.lock').write_text('lock')
        (tmp_path / 'file.py').write_text('hello')
        result = init_mod.find_project_files(tmp_path)
        names = {p.name for p in result}
        assert 'uv.lock' not in names

    def test_find_project_files_excludes_changelog(self, init_mod, tmp_path):
        """Test that CHANGELOG.md is excluded."""
        (tmp_path / 'CHANGELOG.md').write_text('# Changes')
        (tmp_path / 'file.py').write_text('hello')
        result = init_mod.find_project_files(tmp_path)
        names = {p.name for p in result}
        assert 'CHANGELOG.md' not in names

    def test_find_project_files_excludes_init_scripts(
        self, init_mod, tmp_path
    ):
        """Test that init.sh and init.py are excluded."""
        (tmp_path / 'init.sh').write_text('#!/bin/bash')
        (tmp_path / 'init.py').write_text('# init')
        (tmp_path / 'file.py').write_text('hello')
        result = init_mod.find_project_files(tmp_path)
        names = {p.name for p in result}
        assert 'init.sh' not in names
        assert 'init.py' not in names

    def test_find_project_files_excludes_template_tests(
        self, init_mod, tmp_path
    ):
        """Test that tests/template/ directory is excluded."""
        template_dir = tmp_path / 'tests' / 'template'
        template_dir.mkdir(parents=True)
        (template_dir / 'test_init.py').write_text('# test')
        (tmp_path / 'file.py').write_text('hello')
        result = init_mod.find_project_files(tmp_path)
        names = {p.name for p in result}
        assert 'test_init.py' not in names


# ===================================================================
# replace_in_file
# ===================================================================


class TestReplaceInFile:
    """Tests for replace_in_file."""

    def test_replace_in_file_replaces_text(self, init_mod, tmp_path):
        """Test that text is replaced in a file."""
        f = tmp_path / 'test.txt'
        f.write_text('hello world')
        init_mod.replace_in_file(f, 'world', 'python')
        assert f.read_text() == 'hello python'

    def test_replace_in_file_replaces_all_occurrences(
        self, init_mod, tmp_path
    ):
        """Test that all occurrences are replaced."""
        f = tmp_path / 'test.txt'
        f.write_text('foo bar foo baz foo')
        init_mod.replace_in_file(f, 'foo', 'qux')
        assert f.read_text() == 'qux bar qux baz qux'

    def test_replace_in_file_no_match_leaves_unchanged(
        self, init_mod, tmp_path
    ):
        """Test that file is unchanged when pattern not found."""
        f = tmp_path / 'test.txt'
        f.write_text('hello world')
        init_mod.replace_in_file(f, 'missing', 'replaced')
        assert f.read_text() == 'hello world'


# ===================================================================
# replace_in_files
# ===================================================================


class TestReplaceInFiles:
    """Tests for replace_in_files."""

    def test_replace_in_files_replaces_across_files(self, init_mod, tmp_path):
        """Test that text is replaced across multiple files."""
        f1 = tmp_path / 'a.txt'
        f2 = tmp_path / 'b.txt'
        f1.write_text('old_name')
        f2.write_text('old_name rocks')
        init_mod.replace_in_files([f1, f2], 'old_name', 'new_name')
        assert f1.read_text() == 'new_name'
        assert f2.read_text() == 'new_name rocks'


# ===================================================================
# update_project_references
# ===================================================================


class TestUpdateProjectReferences:
    """Tests for update_project_references."""

    def test_update_project_references_replaces_github_urls(
        self, init_mod, tmp_path
    ):
        """Test that GitHub URLs are replaced."""
        f = tmp_path / 'README.md'
        f.write_text('https://github.com/michaelellis003/uv-python-template')
        config = init_mod.ProjectConfig(
            name='my-pkg',
            author='Jane Smith',
            email='jane@example.com',
            github_owner='janesmith',
            description='A package',
            license_key='mit',
            enable_pypi=False,
        )
        init_mod.update_project_references(tmp_path, config, [f])
        content = f.read_text()
        assert 'janesmith/my-pkg' in content
        assert 'michaelellis003' not in content

    def test_update_project_references_replaces_snake_name(
        self, init_mod, tmp_path
    ):
        """Test that python_package_template is replaced."""
        f = tmp_path / 'code.py'
        f.write_text('import python_package_template')
        config = init_mod.ProjectConfig(
            name='my-pkg',
            author='Jane',
            email='j@e.com',
            github_owner='jane',
            description='Pkg',
            license_key='mit',
            enable_pypi=False,
        )
        init_mod.update_project_references(tmp_path, config, [f])
        assert 'import my_pkg' in f.read_text()

    def test_update_project_references_replaces_kebab_name(
        self, init_mod, tmp_path
    ):
        """Test that python-package-template is replaced."""
        f = tmp_path / 'pyproject.toml'
        f.write_text('name = "python-package-template"')
        config = init_mod.ProjectConfig(
            name='my-pkg',
            author='Jane',
            email='j@e.com',
            github_owner='jane',
            description='Pkg',
            license_key='mit',
            enable_pypi=False,
        )
        init_mod.update_project_references(tmp_path, config, [f])
        assert 'name = "my-pkg"' in f.read_text()

    def test_update_project_references_replaces_title_name(
        self, init_mod, tmp_path
    ):
        """Test that Python Package Template title is replaced."""
        f = tmp_path / 'README.md'
        f.write_text('# Python Package Template')
        config = init_mod.ProjectConfig(
            name='my-pkg',
            author='Jane',
            email='j@e.com',
            github_owner='jane',
            description='Pkg',
            license_key='mit',
            enable_pypi=False,
        )
        init_mod.update_project_references(tmp_path, config, [f])
        assert '# My Pkg' in f.read_text()

    def test_update_project_references_replaces_author_in_pyproject(
        self, init_mod, tmp_path
    ):
        """Test that author info is replaced in pyproject.toml."""
        f = tmp_path / 'pyproject.toml'
        f.write_text(
            'name = "Michael Ellis"\nemail = "michaelellis003@gmail.com"'
        )
        config = init_mod.ProjectConfig(
            name='my-pkg',
            author='Jane Smith',
            email='jane@example.com',
            github_owner='jane',
            description='Pkg',
            license_key='mit',
            enable_pypi=False,
        )
        init_mod.update_project_references(tmp_path, config, [f])
        content = f.read_text()
        assert 'Jane Smith' in content
        assert 'jane@example.com' in content

    def test_update_project_references_replaces_codeowners(
        self, init_mod, tmp_path
    ):
        """Test that CODEOWNERS @mention is replaced."""
        github_dir = tmp_path / '.github'
        github_dir.mkdir()
        f = github_dir / 'CODEOWNERS'
        f.write_text('* @michaelellis003')
        config = init_mod.ProjectConfig(
            name='my-pkg',
            author='Jane',
            email='j@e.com',
            github_owner='janesmith',
            description='Pkg',
            license_key='mit',
            enable_pypi=False,
        )
        init_mod.update_project_references(tmp_path, config, [f])
        assert '@janesmith' in f.read_text()

    def test_update_project_references_replaces_pages_url(
        self, init_mod, tmp_path
    ):
        """Test that GitHub Pages URL is replaced."""
        f = tmp_path / 'mkdocs.yml'
        f.write_text(
            'site_url: https://michaelellis003.github.io/uv-python-template'
        )
        config = init_mod.ProjectConfig(
            name='my-pkg',
            author='Jane',
            email='j@e.com',
            github_owner='janesmith',
            description='Pkg',
            license_key='mit',
            enable_pypi=False,
        )
        init_mod.update_project_references(tmp_path, config, [f])
        content = f.read_text()
        assert 'janesmith.github.io/my-pkg' in content


# ===================================================================
# update_description
# ===================================================================


class TestUpdateDescription:
    """Tests for update_description."""

    def test_update_description_in_pyproject(self, init_mod, tmp_path):
        """Test that description is updated in pyproject.toml."""
        f = tmp_path / 'pyproject.toml'
        f.write_text(
            'description = "A production-ready template for '
            'starting new Python packages."'
        )
        config = init_mod.ProjectConfig(
            name='my-pkg',
            author='Jane',
            email='j@e.com',
            github_owner='jane',
            description='My awesome package',
            license_key='mit',
            enable_pypi=False,
        )
        init_mod.update_description(tmp_path, config)
        content = f.read_text()
        assert 'My awesome package' in content

    def test_update_description_escapes_toml(self, init_mod, tmp_path):
        """Test that description with quotes is TOML-escaped."""
        f = tmp_path / 'pyproject.toml'
        f.write_text(
            'description = "A production-ready template for '
            'starting new Python packages."'
        )
        config = init_mod.ProjectConfig(
            name='my-pkg',
            author='Jane',
            email='j@e.com',
            github_owner='jane',
            description='A "great" package',
            license_key='mit',
            enable_pypi=False,
        )
        init_mod.update_description(tmp_path, config)
        content = f.read_text()
        assert r'\"great\"' in content

    def test_update_description_in_meta_yaml(self, init_mod, tmp_path):
        """Test that description is updated in recipe/meta.yaml."""
        recipe_dir = tmp_path / 'recipe'
        recipe_dir.mkdir()
        f = recipe_dir / 'meta.yaml'
        f.write_text(
            'summary: A production-ready template for '
            'starting new Python packages.'
        )
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text(
            'description = "A production-ready template for '
            'starting new Python packages."'
        )
        config = init_mod.ProjectConfig(
            name='my-pkg',
            author='Jane',
            email='j@e.com',
            github_owner='jane',
            description='My awesome package',
            license_key='mit',
            enable_pypi=False,
        )
        init_mod.update_description(tmp_path, config)
        content = f.read_text()
        assert 'My awesome package' in content


# ===================================================================
# setup_license
# ===================================================================


class TestSetupLicense:
    """Tests for setup_license."""

    def test_setup_license_updates_pyproject(self, init_mod, tmp_path):
        """Test that pyproject.toml license field is updated."""
        f = tmp_path / 'pyproject.toml'
        f.write_text('license = {text = "Apache-2.0"}')
        init_mod.setup_license_metadata(tmp_path, 'MIT', 'Test Author', 2025)
        assert 'license = {text = "MIT"}' in f.read_text()

    def test_setup_license_updates_classifier(self, init_mod, tmp_path):
        """Test that license classifier is updated in pyproject."""
        f = tmp_path / 'pyproject.toml'
        f.write_text(
            'license = {text = "Apache-2.0"}\n'
            '"License :: OSI Approved :: Apache Software License"'
        )
        init_mod.setup_license_metadata(tmp_path, 'MIT', 'Test Author', 2025)
        content = f.read_text()
        assert 'MIT License' in content

    def test_setup_license_updates_meta_yaml(self, init_mod, tmp_path):
        """Test that recipe/meta.yaml license is updated."""
        f = tmp_path / 'pyproject.toml'
        f.write_text('license = {text = "Apache-2.0"}')
        recipe = tmp_path / 'recipe'
        recipe.mkdir()
        meta = recipe / 'meta.yaml'
        meta.write_text('license: Apache-2.0')
        init_mod.setup_license_metadata(tmp_path, 'MIT', 'Test Author', 2025)
        assert 'license: MIT' in meta.read_text()

    def test_setup_license_creates_license_header(self, init_mod, tmp_path):
        """Test that LICENSE_HEADER file is created."""
        f = tmp_path / 'pyproject.toml'
        f.write_text('license = {text = "Apache-2.0"}')
        init_mod.setup_license_metadata(tmp_path, 'MIT', 'Test Author', 2025)
        header = tmp_path / 'LICENSE_HEADER'
        assert header.exists()
        content = header.read_text()
        assert 'Copyright 2025 Test Author' in content
        assert 'SPDX-License-Identifier: MIT' in content


# ===================================================================
# apply_license_headers
# ===================================================================


class TestApplyLicenseHeaders:
    """Tests for apply_license_headers."""

    def test_apply_license_headers_adds_to_py_files(self, init_mod, tmp_path):
        """Test that SPDX headers are added to .py files."""
        pkg = tmp_path / 'my_pkg'
        pkg.mkdir()
        f = pkg / 'main.py'
        f.write_text('def hello():\n    return "hello"\n')
        init_mod.apply_license_headers(
            tmp_path, 'my_pkg', 'Test Author', 'MIT', 2025
        )
        content = f.read_text()
        assert content.startswith('# Copyright 2025 Test Author\n')
        assert '# SPDX-License-Identifier: MIT\n' in content

    def test_apply_license_headers_preserves_shebang(self, init_mod, tmp_path):
        """Test that shebang lines are preserved at top."""
        pkg = tmp_path / 'my_pkg'
        pkg.mkdir()
        f = pkg / '__main__.py'
        f.write_text('#!/usr/bin/env python3\nprint("hi")\n')
        init_mod.apply_license_headers(
            tmp_path, 'my_pkg', 'Test Author', 'MIT', 2025
        )
        content = f.read_text()
        lines = content.split('\n')
        assert lines[0] == '#!/usr/bin/env python3'
        assert lines[1] == '# Copyright 2025 Test Author'
        assert lines[2] == '# SPDX-License-Identifier: MIT'

    def test_apply_license_headers_includes_test_files(
        self, init_mod, tmp_path
    ):
        """Test that test .py files also get headers."""
        tests = tmp_path / 'tests'
        tests.mkdir()
        f = tests / 'test_main.py'
        f.write_text('def test_foo():\n    pass\n')
        # Need a pkg dir too (function searches both)
        pkg = tmp_path / 'my_pkg'
        pkg.mkdir()
        (pkg / '__init__.py').write_text('')
        init_mod.apply_license_headers(
            tmp_path, 'my_pkg', 'Test Author', 'MIT', 2025
        )
        content = f.read_text()
        assert '# SPDX-License-Identifier: MIT' in content


# ===================================================================
# add_insert_license_hook
# ===================================================================


class TestAddInsertLicenseHook:
    """Tests for add_insert_license_hook."""

    def test_add_insert_license_hook_adds_block(self, init_mod, tmp_path):
        """Test that the insert-license hook block is added."""
        f = tmp_path / '.pre-commit-config.yaml'
        f.write_text(
            'repos:\n  # Keep rev in sync with ruff version\n  - repo: ruff\n'
        )
        init_mod.add_insert_license_hook(tmp_path)
        content = f.read_text()
        assert 'insert-license' in content
        assert 'Lucas-C/pre-commit-hooks' in content

    def test_add_insert_license_hook_before_ruff(self, init_mod, tmp_path):
        """Test that hook is inserted before the ruff block."""
        f = tmp_path / '.pre-commit-config.yaml'
        f.write_text(
            'repos:\n  # Keep rev in sync with ruff version\n  - repo: ruff\n'
        )
        init_mod.add_insert_license_hook(tmp_path)
        content = f.read_text()
        hook_pos = content.index('insert-license')
        ruff_pos = content.index('Keep rev in sync')
        assert hook_pos < ruff_pos


# ===================================================================
# enable_pypi
# ===================================================================


class TestEnablePypi:
    """Tests for enable_pypi."""

    def test_enable_pypi_uncomments_publish_block(self, init_mod, tmp_path):
        """Test that PYPI-START/END block is uncommented."""
        workflows = tmp_path / '.github' / 'workflows'
        workflows.mkdir(parents=True)
        f = workflows / 'release.yml'
        f.write_text(
            'jobs:\n'
            '  release:\n'
            '      # PYPI-START\n'
            '      # - name: Publish\n'
            '      #   run: twine upload\n'
            '      # PYPI-END\n'
            '  other:\n'
        )
        init_mod.enable_pypi(tmp_path)
        content = f.read_text()
        assert '# PYPI-START' not in content
        assert '# PYPI-END' not in content
        assert '- name: Publish' in content


# ===================================================================
# strip_template_sections
# ===================================================================


class TestStripTemplateSections:
    """Tests for strip_template_sections."""

    def test_strip_template_sections_removes_markers(self, init_mod, tmp_path):
        """Test that TEMPLATE-ONLY markers are removed."""
        f = tmp_path / 'README.md'
        f.write_text(
            '# Title\n'
            '<!-- TEMPLATE-ONLY-START -->\n'
            'Template stuff here\n'
            '<!-- TEMPLATE-ONLY-END -->\n'
            'Keep this\n'
        )
        config = init_mod.ProjectConfig(
            name='my-pkg',
            author='Jane',
            email='j@e.com',
            github_owner='jane',
            description='Pkg',
            license_key='mit',
            enable_pypi=False,
        )
        init_mod.strip_template_sections(tmp_path, config)
        content = f.read_text()
        assert 'TEMPLATE-ONLY' not in content
        assert 'Template stuff here' not in content
        assert 'Keep this' in content


# ===================================================================
# cleanup_template_infrastructure
# ===================================================================


class TestCleanupTemplateInfrastructure:
    """Tests for cleanup_template_infrastructure."""

    def test_cleanup_removes_init_script(self, init_mod, tmp_path):
        """Test that scripts/init.sh and init.py are removed."""
        scripts = tmp_path / 'scripts'
        scripts.mkdir()
        (scripts / 'init.sh').write_text('#!/bin/bash')
        (scripts / 'init.py').write_text('# init')
        init_mod.cleanup_template_infrastructure(tmp_path)
        assert not (scripts / 'init.sh').exists()
        assert not (scripts / 'init.py').exists()

    def test_cleanup_removes_template_tests(self, init_mod, tmp_path):
        """Test that tests/template/ is removed."""
        template = tmp_path / 'tests' / 'template'
        template.mkdir(parents=True)
        (template / 'test_init.py').write_text('# test')
        init_mod.cleanup_template_infrastructure(tmp_path)
        assert not template.exists()

    def test_cleanup_removes_e2e_tests(self, init_mod, tmp_path):
        """Test that tests/e2e/ is removed."""
        e2e = tmp_path / 'tests' / 'e2e'
        e2e.mkdir(parents=True)
        (e2e / 'run-e2e.sh').write_text('#!/bin/bash')
        init_mod.cleanup_template_infrastructure(tmp_path)
        assert not e2e.exists()

    def test_cleanup_removes_dockerignore(self, init_mod, tmp_path):
        """Test that .dockerignore is removed."""
        (tmp_path / '.dockerignore').write_text('*.pyc')
        init_mod.cleanup_template_infrastructure(tmp_path)
        assert not (tmp_path / '.dockerignore').exists()

    def test_cleanup_removes_e2e_workflow(self, init_mod, tmp_path):
        """Test that e2e.yml workflow is removed."""
        workflows = tmp_path / '.github' / 'workflows'
        workflows.mkdir(parents=True)
        (workflows / 'e2e.yml').write_text('name: E2E')
        init_mod.cleanup_template_infrastructure(tmp_path)
        assert not (workflows / 'e2e.yml').exists()

    def test_cleanup_preserves_other_files(self, init_mod, tmp_path):
        """Test that non-template files are preserved."""
        (tmp_path / 'pyproject.toml').write_text('[project]')
        (tmp_path / 'README.md').write_text('# Project')
        init_mod.cleanup_template_infrastructure(tmp_path)
        assert (tmp_path / 'pyproject.toml').exists()
        assert (tmp_path / 'README.md').exists()


# ===================================================================
# reset_version_and_changelog
# ===================================================================


class TestResetVersionAndChangelog:
    """Tests for reset_version_and_changelog."""

    def test_reset_version_sets_0_1_0(self, init_mod, tmp_path):
        """Test that version is reset to 0.1.0."""
        f = tmp_path / 'pyproject.toml'
        f.write_text('version = "1.5.3"')
        init_mod.reset_version_and_changelog(tmp_path)
        assert 'version = "0.1.0"' in f.read_text()

    def test_reset_changelog_content(self, init_mod, tmp_path):
        """Test that CHANGELOG.md is reset."""
        f = tmp_path / 'CHANGELOG.md'
        f.write_text('# v1.5.3\n- Some change\n')
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('version = "1.5.3"')
        init_mod.reset_version_and_changelog(tmp_path)
        content = f.read_text()
        assert '# CHANGELOG' in content
        assert 'Some change' not in content


# ===================================================================
# update_keywords
# ===================================================================


class TestUpdateKeywords:
    """Tests for update_keywords."""

    def test_update_keywords_clears_template_keywords(
        self, init_mod, tmp_path
    ):
        """Test that template keywords are cleared."""
        f = tmp_path / 'pyproject.toml'
        f.write_text(
            'keywords = ["template", "python", "uv", "ruff", "pyright"]'
        )
        init_mod.update_keywords(tmp_path)
        assert 'keywords = []' in f.read_text()


# ===================================================================
# remove_todo_comments
# ===================================================================


class TestRemoveTodoComments:
    """Tests for remove_todo_comments."""

    def test_remove_todo_comments_removes_upgrade_package(
        self, init_mod, tmp_path
    ):
        """Test that TODO comment is removed from pyproject."""
        f = tmp_path / 'pyproject.toml'
        f.write_text(
            'build_command = """\n'
            '    # TODO: Update the --upgrade-package name\n'
            '    uv lock\n'
            '"""'
        )
        init_mod.remove_todo_comments(tmp_path)
        content = f.read_text()
        assert 'TODO' not in content
        assert 'uv lock' in content


# ===================================================================
# validate_project
# ===================================================================


class TestValidateProject:
    """Tests for validate_project."""

    def test_validate_project_detects_stale_refs(self, init_mod, tmp_path):
        """Test that stale template references are detected."""
        (tmp_path / 'README.md').write_text(
            'Visit michaelellis003 for more info'
        )
        stale = init_mod.find_stale_references(tmp_path)
        assert len(stale) > 0

    def test_validate_project_no_stale_refs_clean(self, init_mod, tmp_path):
        """Test that clean project has no stale references."""
        (tmp_path / 'README.md').write_text('# My Pkg\nA great package')
        stale = init_mod.find_stale_references(tmp_path)
        assert len(stale) == 0
