# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Initialize a new project from the python-package-template.

This script renames the package directory, updates all references,
resets the version and changelog, and regenerates the lockfile.

Usage:
    uv run --script scripts/init.py
    uv run --script scripts/init.py -- --name my-cool-package
    uv run --script scripts/init.py -- --name my-pkg --author "Jane Smith" \
        --email jane@example.com --github-owner janesmith \
        --description "My awesome package"
    uv run --script scripts/init.py -- --name my-pkg --pypi
    uv run --script scripts/init.py -- --name my-pkg --license mit

Prerequisites:
    - uv installed (https://docs.astral.sh/uv/getting-started/installation/)
    - Run from the project root directory
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STDLIB_NAMES: frozenset[str] = frozenset(
    {
        'abc',
        'ast',
        'asyncio',
        'base64',
        'collections',
        'contextlib',
        'copy',
        'csv',
        'dataclasses',
        'datetime',
        'decimal',
        'enum',
        'functools',
        'hashlib',
        'http',
        'importlib',
        'inspect',
        'io',
        'itertools',
        'json',
        'logging',
        'math',
        'multiprocessing',
        'operator',
        'os',
        'pathlib',
        'pickle',
        'platform',
        'pprint',
        'queue',
        'random',
        're',
        'secrets',
        'shutil',
        'signal',
        'socket',
        'sqlite3',
        'string',
        'struct',
        'subprocess',
        'sys',
        'test',
        'textwrap',
        'threading',
        'time',
        'tomllib',
        'typing',
        'unittest',
        'uuid',
        'warnings',
        'xml',
        'zipfile',
    }
)

SPDX_MAP: dict[str, str] = {
    'agpl-3.0': 'AGPL-3.0-only',
    'apache-2.0': 'Apache-2.0',
    'bsd-2-clause': 'BSD-2-Clause',
    'bsd-3-clause': 'BSD-3-Clause',
    'bsl-1.0': 'BSL-1.0',
    'cc0-1.0': 'CC0-1.0',
    'epl-2.0': 'EPL-2.0',
    'gpl-2.0': 'GPL-2.0-only',
    'gpl-3.0': 'GPL-3.0-only',
    'lgpl-2.1': 'LGPL-2.1-only',
    'mit': 'MIT',
    'mpl-2.0': 'MPL-2.0',
    'unlicense': 'Unlicense',
}

CLASSIFIER_MAP: dict[str, str] = {
    'MIT': 'License :: OSI Approved :: MIT License',
    'Apache-2.0': 'License :: OSI Approved :: Apache Software License',
    'BSD-2-Clause': 'License :: OSI Approved :: BSD License',
    'BSD-3-Clause': 'License :: OSI Approved :: BSD License',
    'GPL-2.0-only': (
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)'
    ),
    'GPL-3.0-only': (
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)'
    ),
    'LGPL-2.1-only': (
        'License :: OSI Approved '
        ':: GNU Lesser General Public License v2 or later (LGPLv2+)'
    ),
    'AGPL-3.0-only': (
        'License :: OSI Approved :: GNU Affero General Public License v3'
    ),
    'MPL-2.0': (
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)'
    ),
    'Unlicense': ('License :: OSI Approved :: The Unlicense (Unlicense)'),
    'BSL-1.0': (
        'License :: OSI Approved :: Boost Software License 1.0 (BSL-1.0)'
    ),
    'CC0-1.0': (
        'License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication'
    ),
    'EPL-2.0': (
        'License :: OSI Approved :: Eclipse Public License 2.0 (EPL-2.0)'
    ),
}


@dataclass(frozen=True)
class LicenseInfo:
    """Metadata for a single license option."""

    key: str
    name: str
    spdx_id: str


OFFLINE_LICENSES: tuple[LicenseInfo, ...] = (
    LicenseInfo('apache-2.0', 'Apache License 2.0', 'Apache-2.0'),
    LicenseInfo('mit', 'MIT License', 'MIT'),
    LicenseInfo(
        'bsd-3-clause',
        'BSD 3-Clause "New" or "Revised" License',
        'BSD-3-Clause',
    ),
    LicenseInfo(
        'gpl-3.0',
        'GNU General Public License v3.0',
        'GPL-3.0-only',
    ),
    LicenseInfo('mpl-2.0', 'Mozilla Public License 2.0', 'MPL-2.0'),
    LicenseInfo('unlicense', 'The Unlicense', 'Unlicense'),
)


# ---------------------------------------------------------------------------
# Name transforms
# ---------------------------------------------------------------------------


def to_snake(name: str) -> str:
    """Convert a package name to snake_case.

    Args:
        name: Package name (may contain hyphens or underscores).

    Returns:
        Name with hyphens replaced by underscores.
    """
    return name.replace('-', '_')


def to_kebab(name: str) -> str:
    """Convert a package name to kebab-case.

    Args:
        name: Package name (may contain hyphens or underscores).

    Returns:
        Name with underscores replaced by hyphens.
    """
    return name.replace('_', '-')


def to_title(name: str) -> str:
    """Convert a package name to Title Case.

    Args:
        name: Package name (may contain hyphens or underscores).

    Returns:
        Title-cased name with separators replaced by spaces.
    """
    return name.replace('-', ' ').replace('_', ' ').title()


# ---------------------------------------------------------------------------
# String escaping
# ---------------------------------------------------------------------------


def escape_toml_string(value: str) -> str:
    """Escape a string for use inside a TOML double-quoted value.

    Backslashes are doubled first, then double quotes are escaped.

    Args:
        value: Raw string to escape.

    Returns:
        TOML-safe escaped string.
    """
    value = value.replace('\\', '\\\\')
    return value.replace('"', '\\"')


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_NAME_RE = re.compile(r'^[a-z]([a-z0-9_-]*[a-z0-9])?$')
_GITHUB_OWNER_RE = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$')


def validate_name(name: str) -> None:
    """Validate a Python package name.

    Args:
        name: Package name to validate.

    Raises:
        ValueError: If the name is invalid.
    """
    if not _NAME_RE.match(name):
        msg = (
            f"Invalid package name: '{name}'. "
            'Must start with a lowercase letter '
            'and contain only [a-z0-9_-].'
        )
        raise ValueError(msg)

    if name in ('python-package-template', 'python_package_template'):
        msg = 'Please choose a name other than the template default.'
        raise ValueError(msg)

    snake = to_snake(name)
    if snake in STDLIB_NAMES:
        msg = (
            f"Package name '{name}' would shadow "
            f"the Python stdlib module '{snake}'."
        )
        raise ValueError(msg)


def validate_email(email: str) -> None:
    """Validate an email address (basic check).

    Args:
        email: Email address to validate.

    Raises:
        ValueError: If the email is invalid.
    """
    if '@' not in email:
        msg = f"Invalid email: '{email}' (must contain @)"
        raise ValueError(msg)
    if '\n' in email or '\r' in email:
        msg = 'Email must be a single line.'
        raise ValueError(msg)


def validate_github_owner(owner: str) -> None:
    """Validate a GitHub username or organization name.

    Args:
        owner: GitHub username or org name.

    Raises:
        ValueError: If the owner name is invalid.
    """
    if not _GITHUB_OWNER_RE.match(owner):
        msg = (
            f"Invalid GitHub owner: '{owner}'. "
            'Must contain only alphanumeric characters or hyphens, '
            'and cannot begin or end with a hyphen.'
        )
        raise ValueError(msg)


def validate_author_name(name: str) -> None:
    """Validate an author name.

    Args:
        name: Author name to validate.

    Raises:
        ValueError: If the author name is invalid.
    """
    if '\n' in name or '\r' in name:
        msg = 'Author name must be a single line.'
        raise ValueError(msg)


def validate_description(description: str) -> None:
    """Validate a project description.

    Args:
        description: Project description to validate.

    Raises:
        ValueError: If the description is empty or multiline.
    """
    if not description.strip():
        msg = 'Description cannot be empty.'
        raise ValueError(msg)
    if '\n' in description or '\r' in description:
        msg = 'Description must be a single line.'
        raise ValueError(msg)


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------


def spdx_id_for_key(license_key: str) -> str:
    """Map a GitHub license API key to an SPDX identifier.

    Args:
        license_key: Lowercase license key (e.g. 'mit', 'gpl-3.0').

    Returns:
        SPDX identifier string (e.g. 'MIT', 'GPL-3.0-only').
    """
    return SPDX_MAP.get(license_key, license_key.upper())


def classifier_for_spdx(spdx_id: str) -> str | None:
    """Map an SPDX identifier to a PyPI trove classifier.

    Args:
        spdx_id: SPDX license identifier (e.g. 'MIT').

    Returns:
        Trove classifier string, or None if no mapping exists.
    """
    return CLASSIFIER_MAP.get(spdx_id)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProjectConfig:
    """Immutable container for all project configuration values."""

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

    def __post_init__(self) -> None:
        """Compute derived fields from the package name."""
        object.__setattr__(self, 'snake_name', to_snake(self.name))
        object.__setattr__(self, 'kebab_name', to_kebab(self.name))
        object.__setattr__(self, 'title_name', to_title(self.name))
        object.__setattr__(
            self,
            'github_repo',
            f'{self.github_owner}/{to_kebab(self.name)}',
        )


# ---------------------------------------------------------------------------
# File operations
# ---------------------------------------------------------------------------

_EXCLUDE_DIRS: frozenset[str] = frozenset(
    {
        '.git',
        '.venv',
        '.ruff_cache',
        '.pytest_cache',
        '__pycache__',
        'site',
        'dist',
        'build',
        'cli',
    }
)

_EXCLUDE_NAMES: frozenset[str] = frozenset(
    {
        'uv.lock',
        'CHANGELOG.md',
        'init.sh',
        'init.py',
        '.coverage',
    }
)

_BINARY_EXTS: frozenset[str] = frozenset(
    {
        '.png',
        '.jpg',
        '.gif',
        '.ico',
        '.gz',
        '.zip',
        '.whl',
        '.tar',
        '.inv',
        '.so',
        '.dylib',
    }
)

_TEMPLATE_TEST_PARTS = ('tests', 'template')

_TEMPLATE_DESC = (
    'A production-ready template for starting new Python packages.'
)


def _is_template_test_path(parts: tuple[str, ...]) -> bool:
    """Check if path parts indicate a tests/template/ path."""
    return (
        len(parts) >= len(_TEMPLATE_TEST_PARTS)
        and parts[: len(_TEMPLATE_TEST_PARTS)] == _TEMPLATE_TEST_PARTS
    )


def find_project_files(root: Path) -> list[Path]:
    """Find all text files eligible for template replacement.

    Args:
        root: Project root directory.

    Returns:
        List of Path objects to process.
    """
    results: list[Path] = []
    for path in root.rglob('*'):
        if not path.is_file():
            continue

        # Exclude directories by checking all parents
        parts = path.relative_to(root).parts
        if any(part in _EXCLUDE_DIRS for part in parts):
            continue

        # Exclude tests/template/
        if _is_template_test_path(parts):
            continue

        if path.name in _EXCLUDE_NAMES:
            continue

        if path.suffix in _BINARY_EXTS:
            continue

        results.append(path)

    return results


def replace_in_file(path: Path, old: str, new: str) -> None:
    """Replace all occurrences of a string in a file.

    Args:
        path: File to modify.
        old: String to find.
        new: Replacement string.
    """
    content = path.read_text()
    updated = content.replace(old, new)
    if updated != content:
        path.write_text(updated)


def replace_in_files(files: list[Path], old: str, new: str) -> None:
    """Replace a string across multiple files.

    Args:
        files: List of file paths to process.
        old: String to find.
        new: Replacement string.
    """
    for f in files:
        replace_in_file(f, old, new)


def update_project_references(
    root: Path,
    config: ProjectConfig,
    files: list[Path],
) -> None:
    """Replace all template name/URL references in project files.

    Order matters: more specific patterns (GitHub URLs) are replaced
    before generic name patterns.

    Args:
        root: Project root directory.
        config: Project configuration.
        files: Files to update.
    """
    # GitHub URLs (most specific first)
    replace_in_files(
        files,
        'michaelellis003/python-package-template',
        config.github_repo,
    )
    replace_in_files(
        files,
        'michaelellis003/uv-python-template',
        config.github_repo,
    )

    # Author info in pyproject.toml
    pyproject = root / 'pyproject.toml'
    if pyproject.exists():
        replace_in_file(
            pyproject,
            'name = "Michael Ellis"',
            f'name = "{escape_toml_string(config.author)}"',
        )
        replace_in_file(
            pyproject,
            'email = "michaelellis003@gmail.com"',
            f'email = "{escape_toml_string(config.email)}"',
        )

    # CODEOWNERS
    codeowners = root / '.github' / 'CODEOWNERS'
    if codeowners.exists():
        replace_in_file(
            codeowners,
            '@michaelellis003',
            f'@{config.github_owner}',
        )

    # GitHub Pages URL
    replace_in_files(
        files,
        'michaelellis003.github.io/uv-python-template',
        f'{config.github_owner}.github.io/{config.kebab_name}',
    )

    # Package names (generic — last)
    replace_in_files(files, 'python_package_template', config.snake_name)
    replace_in_files(files, 'python-package-template', config.kebab_name)
    replace_in_files(files, 'Python Package Template', config.title_name)

    # conda-forge owner
    meta_yaml = root / 'recipe' / 'meta.yaml'
    if meta_yaml.exists():
        replace_in_file(
            meta_yaml,
            'michaelellis003',
            config.github_owner,
        )


def update_description(root: Path, config: ProjectConfig) -> None:
    """Update project description in pyproject.toml and meta.yaml.

    Args:
        root: Project root directory.
        config: Project configuration.
    """
    pyproject = root / 'pyproject.toml'
    if pyproject.exists():
        replace_in_file(
            pyproject,
            _TEMPLATE_DESC,
            escape_toml_string(config.description),
        )

    meta_yaml = root / 'recipe' / 'meta.yaml'
    if meta_yaml.exists():
        replace_in_file(meta_yaml, _TEMPLATE_DESC, config.description)


def setup_license_metadata(
    root: Path,
    spdx_id: str,
    author: str,
    year: int,
) -> None:
    """Update license references in pyproject.toml and meta.yaml.

    Args:
        root: Project root directory.
        spdx_id: SPDX license identifier.
        author: Author name for LICENSE_HEADER.
        year: Copyright year.
    """
    pyproject = root / 'pyproject.toml'
    if pyproject.exists():
        replace_in_file(
            pyproject,
            'license = {text = "Apache-2.0"}',
            f'license = {{text = "{spdx_id}"}}',
        )

        classifier = classifier_for_spdx(spdx_id)
        if classifier:
            replace_in_file(
                pyproject,
                'License :: OSI Approved :: Apache Software License',
                classifier,
            )
        else:
            # Remove stale Apache classifier
            content = pyproject.read_text()
            lines = content.split('\n')
            lines = [
                ln
                for ln in lines
                if 'License :: OSI Approved :: Apache Software License'
                not in ln
            ]
            pyproject.write_text('\n'.join(lines))

    meta_yaml = root / 'recipe' / 'meta.yaml'
    if meta_yaml.exists():
        replace_in_file(
            meta_yaml, 'license: Apache-2.0', f'license: {spdx_id}'
        )

    # Generate LICENSE_HEADER
    header = root / 'LICENSE_HEADER'
    header.write_text(
        f'Copyright {year} {author}\nSPDX-License-Identifier: {spdx_id}\n'
    )


def apply_license_headers(
    root: Path,
    snake_name: str,
    author: str,
    spdx_id: str,
    year: int,
) -> None:
    """Add SPDX license headers to all .py files.

    Args:
        root: Project root directory.
        snake_name: Snake-case package name (directory to scan).
        author: Author name for the copyright line.
        spdx_id: SPDX license identifier.
        year: Copyright year.
    """
    header_line1 = f'# Copyright {year} {author}'
    header_line2 = f'# SPDX-License-Identifier: {spdx_id}'

    dirs_to_scan = [root / snake_name, root / 'tests']
    for directory in dirs_to_scan:
        if not directory.exists():
            continue
        for py_file in directory.rglob('*.py'):
            content = py_file.read_text()
            lines = content.split('\n')

            if lines and lines[0].startswith('#!'):
                # Preserve shebang
                new_lines = [
                    lines[0],
                    header_line1,
                    header_line2,
                    *lines[1:],
                ]
            else:
                new_lines = [header_line1, header_line2, *lines]

            py_file.write_text('\n'.join(new_lines))


def add_insert_license_hook(root: Path) -> None:
    """Add the insert-license pre-commit hook.

    Args:
        root: Project root directory.
    """
    config_path = root / '.pre-commit-config.yaml'
    if not config_path.exists():
        return

    content = config_path.read_text()
    hook_block = (
        '  - repo: https://github.com/Lucas-C/pre-commit-hooks\n'
        '    rev: v1.5.5\n'
        '    hooks:\n'
        '      - id: insert-license\n'
        '        files: \\.py$\n'
        '        args:\n'
        '          - --license-filepath=LICENSE_HEADER\n'
        '          - --comment-style=#\n'
        '          - --detect-license-in-X-top-lines=5\n'
    )
    marker = '  # Keep rev in sync with ruff version'
    content = content.replace(marker, hook_block + marker)
    config_path.write_text(content)


def enable_pypi(root: Path) -> None:
    """Uncomment PyPI publishing steps in release.yml.

    Args:
        root: Project root directory.
    """
    release = root / '.github' / 'workflows' / 'release.yml'
    if not release.exists():
        return

    content = release.read_text()
    lines = content.split('\n')
    result: list[str] = []
    in_block = False

    for line in lines:
        if '# PYPI-START' in line:
            in_block = True
            continue
        if '# PYPI-END' in line:
            in_block = False
            continue
        if in_block:
            # Skip bare comment lines (just "      #")
            if re.match(r'^(\s*)#$', line):
                continue
            # Uncomment: "      # content" -> "      content"
            uncommented = re.sub(r'^(\s*)# ', r'\1', line)
            result.append(uncommented)
        else:
            result.append(line)

    release.write_text('\n'.join(result))


def strip_template_sections(root: Path, config: ProjectConfig) -> None:
    """Remove TEMPLATE-ONLY marker sections from files.

    For README.md, replaces the template section with a standard
    Getting Started section. For CLAUDE.md, replaces with a project
    description.

    Args:
        root: Project root directory.
        config: Project configuration.
    """
    readme = root / 'README.md'
    if readme.exists():
        content = readme.read_text()
        # Replace template section with standard Getting Started
        replacement = (
            '## Getting Started\n'
            '\n'
            '### Prerequisites\n'
            '- Python 3.10+\n'
            '- [uv](https://docs.astral.sh/uv/getting-started/'
            'installation/)\n'
            '\n'
            '### Installation\n'
            '\n'
            '```bash\n'
            f'git clone https://github.com/{config.github_repo}.git\n'
            f'cd {config.kebab_name}\n'
            'uv sync\n'
            '```\n'
            '\n'
            '### Running Tests\n'
            '\n'
            '```bash\n'
            'uv run pytest -v --cov\n'
            '```\n'
            '\n'
            '### Pre-commit Hooks\n'
            '\n'
            '```bash\n'
            'uv run pre-commit install\n'
            '```\n'
        )
        content = _replace_marker_section(content, replacement)
        readme.write_text(content)

    claude_md = root / 'CLAUDE.md'
    if claude_md.exists():
        content = claude_md.read_text()
        replacement = (
            f'**{config.kebab_name}** — {config.description}. '
            'Uses uv, Ruff, Pyright, and pre-commit\n'
            f'hooks. Licensed {spdx_id_for_key(config.license_key)}.\n'
        )
        content = _replace_marker_section(content, replacement)
        claude_md.write_text(content)


def _replace_marker_section(content: str, replacement: str) -> str:
    """Replace content between TEMPLATE-ONLY markers.

    Args:
        content: File content.
        replacement: Text to insert in place of the marker section.

    Returns:
        Updated content with markers and enclosed text replaced.
    """
    lines = content.split('\n')
    result: list[str] = []
    skip = False

    for line in lines:
        if '<!-- TEMPLATE-ONLY-START -->' in line:
            skip = True
            result.append(replacement.rstrip('\n'))
            continue
        if '<!-- TEMPLATE-ONLY-END -->' in line:
            skip = False
            continue
        if not skip:
            result.append(line)

    return '\n'.join(result)


def _strip_cli_tests_from_ci(root: Path) -> None:
    """Remove the cli-tests job and its needs reference from ci.yml.

    Removes the block from the ``# CLI package`` comment through the
    end of the cli-tests job definition, and strips ``, cli-tests``
    from the ``ci-pass`` needs list.

    Args:
        root: Project root directory.
    """
    ci_yml = root / '.github' / 'workflows' / 'ci.yml'
    if not ci_yml.exists():
        return

    content = ci_yml.read_text()
    lines = content.split('\n')

    # --- Remove the cli-tests job block ---
    result: list[str] = []
    skip = False
    for line in lines:
        if line.strip().startswith('# CLI package'):
            skip = True
            continue
        if skip and line.strip() == 'cli-tests:':
            continue
        # Detect the start of the next top-level job (2-space indent)
        if skip and re.match(r'^  \S', line):
            skip = False
        if skip:
            continue
        result.append(line)

    # --- Remove cli-tests from ci-pass needs list ---
    cleaned: list[str] = []
    for line in result:
        if 'needs:' in line and 'cli-tests' in line:
            line = line.replace(', cli-tests', '')
            line = line.replace('cli-tests, ', '')
            line = line.replace('cli-tests', '')
        cleaned.append(line)

    ci_yml.write_text('\n'.join(cleaned))


def cleanup_template_infrastructure(root: Path) -> None:
    """Remove template-specific files and directories.

    Removes: scripts/init.sh, scripts/init.py, tests/template/,
    tests/e2e/, .dockerignore, e2e.yml workflow.

    Args:
        root: Project root directory.
    """
    import shutil

    # Files to remove
    files_to_remove = [
        root / 'scripts' / 'init.sh',
        root / 'scripts' / 'init.py',
        root / '.dockerignore',
        root / '.github' / 'workflows' / 'e2e.yml',
        root / '.github' / 'workflows' / 'cli-release.yml',
    ]
    for f in files_to_remove:
        if f.exists():
            f.unlink()

    # Directories to remove
    dirs_to_remove = [
        root / 'tests' / 'template',
        root / 'tests' / 'e2e',
        root / 'cli',
    ]
    for d in dirs_to_remove:
        if d.exists():
            shutil.rmtree(d)

    # Strip cli-tests job from ci.yml
    _strip_cli_tests_from_ci(root)


def reset_version_and_changelog(root: Path) -> None:
    """Reset version to 0.1.0 and clear CHANGELOG.md.

    Args:
        root: Project root directory.
    """
    pyproject = root / 'pyproject.toml'
    if pyproject.exists():
        content = pyproject.read_text()
        content = re.sub(
            r'^version = ".*"',
            'version = "0.1.0"',
            content,
            flags=re.MULTILINE,
        )
        pyproject.write_text(content)

    changelog = root / 'CHANGELOG.md'
    changelog.write_text('# CHANGELOG\n\n<!-- version list -->\n')


def update_keywords(root: Path) -> None:
    """Clear template keywords in pyproject.toml.

    Args:
        root: Project root directory.
    """
    pyproject = root / 'pyproject.toml'
    if pyproject.exists():
        replace_in_file(
            pyproject,
            'keywords = ["template", "python", "uv", "ruff", "pyright"]',
            'keywords = []',
        )


def remove_todo_comments(root: Path) -> None:
    """Remove TODO comments from pyproject.toml.

    Args:
        root: Project root directory.
    """
    pyproject = root / 'pyproject.toml'
    if pyproject.exists():
        content = pyproject.read_text()
        lines = content.split('\n')
        lines = [
            ln
            for ln in lines
            if '# TODO: Update the --upgrade-package' not in ln
        ]
        pyproject.write_text('\n'.join(lines))


def find_stale_references(root: Path) -> list[Path]:
    """Find files containing stale template references.

    Args:
        root: Project root directory.

    Returns:
        List of files with stale references.
    """
    stale_patterns = [
        'python_package_template',
        'python-package-template',
        'uv-python-template',
        'michaelellis003',
        'Michael Ellis',
    ]

    text_exts = {
        '.py',
        '.toml',
        '.yml',
        '.yaml',
        '.md',
        '.cfg',
        '.json',
        '.sh',
    }

    stale: list[Path] = []
    for path in root.rglob('*'):
        if not path.is_file():
            continue

        parts = path.relative_to(root).parts
        if any(part in _EXCLUDE_DIRS for part in parts):
            continue

        # Skip lockfile, init scripts, template tests
        if path.name in ('uv.lock', 'init.sh', 'init.py'):
            continue
        if _is_template_test_path(parts):
            continue

        if path.suffix not in text_exts:
            continue

        try:
            content = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue

        if any(pattern in content for pattern in stale_patterns):
            stale.append(path)

    return stale


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description=(
            'Interactive setup script for the python-package-template.'
        ),
    )
    parser.add_argument(
        '--name',
        '-n',
        help='Package name (kebab-case)',
    )
    parser.add_argument(
        '--author',
        help='Author name (e.g. "Jane Smith")',
    )
    parser.add_argument(
        '--email',
        help='Author email',
    )
    parser.add_argument(
        '--github-owner',
        help='GitHub username or organization',
    )
    parser.add_argument(
        '--description',
        help='Short project description',
    )
    parser.add_argument(
        '--license',
        help='License SPDX key (e.g. mit, bsd-3-clause, gpl-3.0)',
    )
    parser.add_argument(
        '--pypi',
        action='store_true',
        default=False,
        help='Enable PyPI publishing',
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# License fetching (network)
# ---------------------------------------------------------------------------

_LICENSE_API = 'https://api.github.com/licenses'
_API_TIMEOUT = 5


def fetch_licenses() -> list[LicenseInfo]:
    """Fetch available licenses from the GitHub Licenses API.

    Falls back to OFFLINE_LICENSES if the API is unavailable.

    Returns:
        List of LicenseInfo objects.
    """
    try:
        with urlopen(_LICENSE_API, timeout=_API_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
        return [
            LicenseInfo(
                key=lic['key'],
                name=lic['name'],
                spdx_id=spdx_id_for_key(lic['key']),
            )
            for lic in data
        ]
    except Exception:
        return list(OFFLINE_LICENSES)


def fetch_license_body(key: str, author: str, year: int) -> str | None:
    """Fetch full license text from the GitHub API.

    Args:
        key: License key (e.g. 'mit').
        author: Author name for placeholder replacement.
        year: Copyright year for placeholder replacement.

    Returns:
        License body text, or None if unavailable.
    """
    try:
        url = f'{_LICENSE_API}/{key}'
        with urlopen(url, timeout=_API_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
        body = data.get('body', '')
        for placeholder in ['[year]', '[yyyy]', '<year>']:
            body = body.replace(placeholder, str(year))
        for placeholder in [
            '[fullname]',
            '[name of copyright owner]',
            '[name of copyright holder]',
            '<name of copyright owner>',
            '<name of copyright holder>',
            '<copyright holders>',
        ]:
            body = body.replace(placeholder, author)
        return body
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Interactive prompts
# ---------------------------------------------------------------------------


def _prompt_required(value: str | None, prompt: str, flag: str) -> str:
    """Prompt for a required value if not already provided.

    Args:
        value: Pre-existing value (from flags) or None.
        prompt: Human-readable prompt text.
        flag: CLI flag name for error messages.

    Returns:
        Non-empty trimmed string.

    Raises:
        SystemExit: If stdin is not interactive and value is missing.
    """
    if value is not None:
        stripped = value.strip()
        if stripped:
            return stripped

    if not sys.stdin.isatty():
        print(
            f'error: {prompt} is required '
            f'(use {flag} in non-interactive mode)',
            file=sys.stderr,
        )
        sys.exit(1)

    while True:
        raw = input(f'{prompt}: ').strip()
        if raw:
            return raw
        print(f'  {prompt} cannot be empty.')


def _prompt_pypi(enable_pypi: bool) -> bool:
    """Prompt for PyPI publishing preference.

    Args:
        enable_pypi: Pre-set value from --pypi flag.

    Returns:
        True if PyPI publishing should be enabled.
    """
    if enable_pypi:
        return True
    if not sys.stdin.isatty():
        return False
    answer = input('Enable PyPI publishing? [y/N] ').strip().lower()
    return answer in ('y', 'yes')


def _prompt_license(
    license_key: str | None,
) -> tuple[str, str]:
    """Prompt for license selection or validate provided key.

    Args:
        license_key: Pre-set license key from --license flag.

    Returns:
        Tuple of (license_key, license_name).
    """
    if license_key is not None:
        key_lower = license_key.lower()
        if key_lower == 'none':
            return 'none', 'Apache License 2.0 (unchanged)'

        licenses = fetch_licenses()
        for lic in licenses:
            if lic.key.lower() == key_lower:
                return lic.key, lic.name

        available = ', '.join(lic.key for lic in licenses)
        print(
            f"error: Unknown license key: '{license_key}'. "
            f'Available: {available}',
            file=sys.stderr,
        )
        sys.exit(1)

    if not sys.stdin.isatty():
        return 'none', 'Apache License 2.0 (unchanged)'

    licenses = fetch_licenses()
    print('\nSelect a license:')
    print('  0) Skip (keep existing Apache-2.0)')
    for i, lic in enumerate(licenses, 1):
        print(f'  {i}) {lic.name} ({lic.key})')

    raw = input('\nChoice [0]: ').strip()
    if not raw or raw == '0':
        return 'none', 'Apache License 2.0 (unchanged)'

    try:
        idx = int(raw)
        if 1 <= idx <= len(licenses):
            chosen = licenses[idx - 1]
            return chosen.key, chosen.name
    except ValueError:
        pass

    print(f'error: Invalid choice: {raw}', file=sys.stderr)
    sys.exit(1)


def prompt_project_config(
    args: argparse.Namespace,
) -> ProjectConfig:
    """Build a ProjectConfig from flags and interactive prompts.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Fully populated ProjectConfig.
    """
    print()
    print('Python Package Template \u2014 Project Setup')
    print('=' * 41)
    print()
    print('This script will rename the package, update all references,')
    print('reset the version and changelog, and prepare your project.')
    print()

    name = _prompt_required(args.name, 'Package name', '--name')
    kebab = to_kebab(name)
    validate_name(kebab)

    author = _prompt_required(args.author, 'Author name', '--author')
    validate_author_name(author)

    email = _prompt_required(args.email, 'Author email', '--email')
    validate_email(email)

    github_owner = _prompt_required(
        args.github_owner, 'GitHub owner', '--github-owner'
    )
    validate_github_owner(github_owner)

    description = _prompt_required(
        args.description, 'Short description', '--description'
    )
    validate_description(description)

    enable_pypi = _prompt_pypi(args.pypi)
    license_key, license_name = _prompt_license(args.license)

    config = ProjectConfig(
        name=kebab,
        author=author,
        email=email,
        github_owner=github_owner,
        description=description,
        license_key=license_key,
        enable_pypi=enable_pypi,
    )

    spdx = spdx_id_for_key(license_key)
    print('-' * 41)
    print(f'  Package name (kebab):  {config.kebab_name}')
    print(f'  Package name (snake):  {config.snake_name}')
    print(f'  Package name (title):  {config.title_name}')
    print(f'  Author:                {author} <{email}>')
    print(f'  GitHub repo:           {config.github_repo}')
    print(f'  Description:           {description}')
    pypi_str = 'yes' if enable_pypi else 'no'
    print(f'  PyPI publishing:       {pypi_str}')
    print(f'  License:               {license_name} ({spdx})')
    print('-' * 41)
    print()

    if sys.stdin.isatty():
        confirm = input('Proceed? [Y/n] ').strip().lower()
        if confirm == 'n':
            print('Aborted.')
            sys.exit(0)
    else:
        # Non-interactive: read confirmation from stdin
        confirm = sys.stdin.readline().strip().lower()
        if confirm == 'n':
            print('Aborted.')
            sys.exit(0)

    return config


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def init_project(config: ProjectConfig, root: Path) -> bool:
    """Run the full project initialization pipeline.

    Args:
        config: Project configuration.
        root: Project root directory.

    Returns:
        True if validation passed, False if there were warnings.
    """
    year = datetime.now(tz=timezone.utc).year
    ok = True

    _rename_package_dir(root, config)
    _update_all_references(root, config)
    _update_readme_badges(root, config)

    print('==> Updating keywords...')
    update_keywords(root)

    print('==> Resetting version to 0.1.0...')
    reset_version_and_changelog(root)

    print('==> Cleaning up TODO comments...')
    remove_todo_comments(root)

    print('==> Updating README...')
    _update_readme_structure(root)

    ok = _setup_license_if_needed(root, config, year) and ok

    print('==> Stripping template-only sections...')
    strip_template_sections(root, config)
    _strip_init_references(root, config)

    if config.enable_pypi:
        print('==> Enabling PyPI publishing...')
        enable_pypi(root)
        print('==> PyPI publishing enabled in release.yml.')

    print('==> Regenerating uv.lock...')
    ok = _regenerate_lockfile(root) and ok

    print('==> Validating initialized project...')
    ok = _validate_project(root, config) and ok

    print('==> Removing template infrastructure...')
    cleanup_template_infrastructure(root)
    _cleanup_documentation_refs(root)

    return ok


def _rename_package_dir(root: Path, config: ProjectConfig) -> None:
    """Rename python_package_template/ to the new package name.

    Args:
        root: Project root directory.
        config: Project configuration.
    """
    old_dir = root / 'python_package_template'
    if old_dir.exists():
        print(f'==> Renaming python_package_template/ -> {config.snake_name}/')
        old_dir.rename(root / config.snake_name)


def _update_all_references(root: Path, config: ProjectConfig) -> None:
    """Update all package name/author/URL references.

    Args:
        root: Project root directory.
        config: Project configuration.
    """
    print('==> Updating package name references...')
    files = find_project_files(root)
    update_project_references(root, config, files)

    print('==> Updating project description...')
    update_description(root, config)


def _update_readme_badges(root: Path, config: ProjectConfig) -> None:
    """Update README badges and description line.

    Args:
        root: Project root directory.
        config: Project configuration.
    """
    print('==> Updating README badges...')
    readme = root / 'README.md'
    if not readme.exists():
        return
    content = readme.read_text()
    lines = content.split('\n')
    lines = [ln for ln in lines if 'codecov.io' not in ln]
    readme.write_text('\n'.join(lines))
    replace_in_file(
        readme,
        (
            'A production-ready template for starting new Python '
            'packages. Clone it, rename a few things, and start '
            'building \u2014 dependency management, linting, type '
            'checking, testing, and CI/CD are already wired up.'
        ),
        config.description,
    )


def _setup_license_if_needed(
    root: Path, config: ProjectConfig, year: int
) -> bool:
    """Set up license files and headers if a license was chosen.

    Args:
        root: Project root directory.
        config: Project configuration.
        year: Current year for copyright lines.

    Returns:
        True if no warnings occurred.
    """
    if config.license_key.lower() == 'none':
        print('==> Skipping license setup (keeping Apache-2.0 defaults).')
        return True

    spdx = spdx_id_for_key(config.license_key)
    print(f'==> Setting up license ({spdx})...')

    body = fetch_license_body(config.license_key, config.author, year)
    if body:
        (root / 'LICENSE').write_text(body + '\n')
        print('==> LICENSE file updated.')
    else:
        print(
            'warning: Could not fetch license text from GitHub API. '
            'LICENSE file left unchanged.'
        )

    setup_license_metadata(root, spdx, config.author, year)
    print('==> LICENSE_HEADER generated.')

    add_insert_license_hook(root)
    print('==> insert-license pre-commit hook added.')

    print('==> Applying license headers to .py files...')
    apply_license_headers(root, config.snake_name, config.author, spdx, year)
    print('==> License headers applied.')
    return True


def _update_readme_structure(root: Path) -> None:
    """Update README.md structure hints after rename.

    Args:
        root: Project root directory.
    """
    readme = root / 'README.md'
    if readme.exists():
        replace_in_file(
            readme,
            '# Package source (rename this)',
            '# Package source',
        )


def _strip_init_references(root: Path, config: ProjectConfig) -> None:
    """Remove init script references from various files.

    Args:
        root: Project root directory.
        config: Project configuration.
    """
    spdx = spdx_id_for_key(config.license_key)
    _strip_init_refs_from_docs(root)
    _strip_init_refs_from_md(root, spdx)
    _rewrite_docs_index(root, config)
    _strip_testing_md_template_section(root)
    _update_code_style_rules(root, config)


def _strip_init_refs_from_docs(root: Path) -> None:
    """Remove init script references from docs and workflow files.

    Args:
        root: Project root directory.
    """
    pub = root / 'docs' / 'publishing.md'
    if pub.exists():
        replace_in_file(
            pub,
            (
                'run `uv run --script ./scripts/init.py --pypi`,\n'
                '   or manually uncomment'
            ),
            'manually uncomment',
        )

    release = root / '.github' / 'workflows' / 'release.yml'
    if release.exists():
        replace_in_file(
            release,
            'Run init.py with --pypi, or uncomment',
            'Uncomment',
        )


def _strip_init_refs_from_md(root: Path, spdx: str) -> None:
    """Remove init script references from README and CLAUDE.md.

    Args:
        root: Project root directory.
        spdx: SPDX license identifier.
    """
    readme = root / 'README.md'
    if readme.exists():
        replace_in_file(
            readme,
            (
                'Run `uv run --script ./scripts/init.py --pypi` '
                'to enable publishing (or uncomment'
            ),
            'Uncomment',
        )
        replace_in_file(
            readme,
            'the `PYPI-START`/`PYPI-END` block in `release.yml` manually).',
            'the `PYPI-START`/`PYPI-END` block in `release.yml`.',
        )
        replace_in_file(
            readme,
            'Apache-2.0 license (configurable via init.py)',
            f'{spdx} license',
        )

    claude_md = root / 'CLAUDE.md'
    if claude_md.exists():
        replace_in_file(
            claude_md,
            'Apache-2.0 license (configurable via init.py)',
            f'{spdx} license',
        )

    # Remove init.sh/init.py from project structure diagrams
    for md_file in (readme, claude_md):
        if md_file.exists():
            content = md_file.read_text()
            lines = [
                ln
                for ln in content.split('\n')
                if not (
                    ('init.sh' in ln or 'init.py' in ln)
                    and ('Interactive' in ln or 'initialization' in ln)
                )
            ]
            md_file.write_text('\n'.join(lines))


def _rewrite_docs_index(root: Path, config: ProjectConfig) -> None:
    """Rewrite docs/index.md with project-specific content.

    Args:
        root: Project root directory.
        config: Project configuration.
    """
    docs_index = root / 'docs' / 'index.md'
    if not docs_index.exists():
        return
    docs_index.write_text(
        f'# {config.title_name}\n'
        f'\n'
        f'{config.description}\n'
        f'\n'
        f'## Features\n'
        f'\n'
        f'- **[uv](https://docs.astral.sh/uv/)** for fast Python '
        f'package management\n'
        f'- **[Ruff](https://docs.astral.sh/ruff/)** for linting '
        f'and formatting\n'
        f'- **[Pyright](https://github.com/microsoft/pyright)** '
        f'for static type checking\n'
        f'- **[Pytest](https://docs.pytest.org/)** with coverage '
        f'for testing\n'
        f'- **GitHub Actions** CI/CD with auto-release on merge '
        f'to main\n'
        f'\n'
        f'## Quick Start\n'
        f'\n'
        f'```bash\n'
        f'git clone https://github.com/{config.github_repo}.git\n'
        f'cd {config.kebab_name}\n'
        f'uv sync\n'
        f'uv run pytest -v --cov\n'
        f'```\n'
        f'\n'
        f'## Next Steps\n'
        f'\n'
        f'- [API Reference](api.md) \u2014 auto-generated '
        f'documentation for all public functions\n'
    )


def _strip_testing_md_template_section(root: Path) -> None:
    """Remove Template Tests section from testing.md.

    Args:
        root: Project root directory.
    """
    testing_md = root / '.claude' / 'rules' / 'testing.md'
    if not testing_md.exists():
        return
    content = testing_md.read_text()
    lines = content.split('\n')
    result: list[str] = []
    skip = False
    for line in lines:
        if line.strip() == '## Template Tests':
            skip = True
            continue
        if skip and line.startswith('## '):
            skip = False
        if skip and 'are automatically removed when' in line:
            continue
        if not skip:
            result.append(line)
    testing_md.write_text('\n'.join(result))


def _update_code_style_rules(root: Path, config: ProjectConfig) -> None:
    """Rewrite the License Headers section in code-style.md.

    Args:
        root: Project root directory.
        config: Project configuration.
    """
    code_style = root / '.claude' / 'rules' / 'code-style.md'
    if not code_style.exists():
        return

    content = code_style.read_text()
    old_section = (
        '## License Headers\n'
        '\n'
        '- After running `init.py` with a license selection, '
        'all `.py` files\n'
        '  will have SPDX license headers and an `insert-license` '
        'pre-commit\n'
        '  hook enforces them on new files.\n'
        '- Place after shebang (if present), before module docstring.\n'
        '- Format:\n'
        '  ```python\n'
        '  # Copyright YYYY Author Name\n'
        '  # SPDX-License-Identifier: LICENSE-ID\n'
        '  ```\n'
        '- The template repo itself does not ship with headers \u2014 '
        'they are\n'
        '  generated by `init.py` based on the selected license.'
    )

    if config.license_key.lower() != 'none':
        new_section = (
            '## License Headers\n'
            '\n'
            '- All `.py` files have SPDX license headers. '
            'The `insert-license`\n'
            '  pre-commit hook enforces them on new files.\n'
            '- Place after shebang (if present), before module '
            'docstring.\n'
            '- Format:\n'
            '  ```python\n'
            '  # Copyright YYYY Author Name\n'
            '  # SPDX-License-Identifier: LICENSE-ID\n'
            '  ```'
        )
    else:
        new_section = (
            '## License Headers\n'
            '\n'
            '- Add SPDX license headers to all `.py` files '
            'when applicable.\n'
            '- Place after shebang (if present), before module '
            'docstring.\n'
            '- Format:\n'
            '  ```python\n'
            '  # Copyright YYYY Author Name\n'
            '  # SPDX-License-Identifier: LICENSE-ID\n'
            '  ```'
        )

    content = content.replace(old_section, new_section)
    code_style.write_text(content)


def _regenerate_lockfile(root: Path) -> bool:
    """Regenerate uv.lock file.

    Args:
        root: Project root directory.

    Returns:
        True if successful.
    """
    try:
        subprocess.run(
            ['uv', 'lock'],
            cwd=root,
            check=True,
            capture_output=True,
        )
        print('==> uv.lock regenerated.')
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print('warning: uv lock failed. Run "uv lock" manually.')
        return False


def _validate_project(root: Path, config: ProjectConfig) -> bool:
    """Run post-init validation checks.

    Args:
        root: Project root directory.
        config: Project configuration.

    Returns:
        True if all checks passed.
    """
    ok = True

    # Check import
    try:
        subprocess.run(
            ['uv', 'run', 'python', '-c', f'import {config.snake_name}'],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"warning: Could not import '{config.snake_name}'.")
        ok = False

    # Check for stale references
    stale = find_stale_references(root)
    if stale:
        print('warning: Stale template references found in:')
        for f in stale:
            print(f'    {f}')
        ok = False

    return ok


def _cleanup_documentation_refs(root: Path) -> None:
    """Remove template test/e2e references from documentation.

    Args:
        root: Project root directory.
    """
    claude_md = root / 'CLAUDE.md'
    readme = root / 'README.md'

    for md_file in (claude_md, readme):
        if md_file is None or not md_file.exists():
            continue
        content = md_file.read_text()
        lines = content.split('\n')
        result = [ln for ln in lines if not _is_template_doc_line(ln)]
        md_file.write_text('\n'.join(result))

    # Remove E2E section from README
    if readme.exists():
        content = readme.read_text()
        lines = content.split('\n')
        result: list[str] = []
        skip = False
        for line in lines:
            if (
                '### On Push to Main and Pull Request' in line
                and 'e2e' in line
            ):
                skip = True
                continue
            if skip and line.startswith('###'):
                skip = False
            if not skip:
                result.append(line)
        readme.write_text('\n'.join(result))


def _is_template_doc_line(line: str) -> bool:
    """Check if a line references template infrastructure docs.

    Args:
        line: Line of text to check.

    Returns:
        True if the line should be removed.
    """
    patterns = [
        'template/',
        'conftest.py',
        'test_template_structure',
        'test_init_license',
        'test_init_flags',
        'e2e/',
        'Dockerfile',
        'verify-project.sh',
        'run-e2e.sh',
        'e2e.yml',
        '.dockerignore',
        'cli/',
        'cli-release.yml',
    ]
    match_hints = [
        '# Template',
        '# Fixtures',
        '# Docker',
        '# Parameterized',
        '# Container-side',
        '# Host-side',
        '# E2E',
        '# CLI',
        'Verifies template',
        'Integration tests',
        'Docker build',
        'Template-specific',
        'pypkgkit',
    ]
    # Only match lines that look like documentation structure entries
    stripped = line.strip()
    if not stripped:
        return False
    for pattern in patterns:
        if pattern in line and any(hint in line for hint in match_hints):
            return True
    return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _print_summary(config: ProjectConfig, ok: bool) -> None:
    """Print the post-init summary.

    Args:
        config: Project configuration.
        ok: Whether validation passed.
    """
    print()
    if ok:
        print('==> Project initialized successfully!')
    else:
        print('warning: Project initialized with warnings (see above).')

    spdx = spdx_id_for_key(config.license_key)
    pypi_str = 'yes' if config.enable_pypi else 'no'
    print()
    print(f'  Package directory:  {config.snake_name}/')
    print(f'  Package name:       {config.kebab_name}')
    print(f'  Author:             {config.author} <{config.email}>')
    print(f'  GitHub:             https://github.com/{config.github_repo}')
    print(f'  PyPI publishing:    {pypi_str}')
    print(f'  License:            {spdx}')
    print()
    print('Next steps:')
    print('  1. Review the changes:     git diff')
    print('  2. Install deps:           uv sync')
    print('  3. Run tests:              uv run pytest -v --cov')
    print('  4. Enable pre-commit:      uv run pre-commit install')
    print(f'  5. Replace the demo code in {config.snake_name}/main.py')
    print('  6. Commit initialized state:')
    print(
        "       git add -A && git commit -m 'chore: initialize from template'"
    )
    print('  7. Push to your repo:')
    print('       git remote set-url origin <your-repo-url>')
    print('       git push -u origin main')
    print('  8. Set up Codecov and add the badge to README.md')
    print(
        '  9. Enable GitHub Pages:    '
        'Settings > Pages > Source: GitHub Actions'
    )
    print('  10. Set up branch protection: ./scripts/setup-repo.sh')

    if config.enable_pypi:
        print()
        print('PyPI setup:')
        print('  1. Go to https://pypi.org/manage/account/publishing/')
        print('  2. Add a trusted publisher:')
        print(f'       Owner:    {config.github_owner}')
        print(f'       Repo:     {config.kebab_name}')
        print('       Workflow: release.yml')
        print('  3. (Optional) Set up TestPyPI the same way at')
        print('     https://test.pypi.org/manage/account/publishing/')
        print('     with workflow: test-publish.yml')
    print()


def main() -> None:
    """Entry point for the init script."""
    root = Path.cwd()

    # Ensure we're in the project root
    if not (root / 'pyproject.toml').exists():
        print(
            'error: pyproject.toml not found. '
            'Run this script from the project root.',
            file=sys.stderr,
        )
        sys.exit(1)

    if not (root / 'python_package_template').exists():
        print(
            'error: python_package_template/ directory not found.\n'
            'Has this template already been initialized?',
            file=sys.stderr,
        )
        sys.exit(1)

    args = parse_args()
    try:
        config = prompt_project_config(args)
    except ValueError as exc:
        print(f'error: {exc}', file=sys.stderr)
        sys.exit(1)
    ok = init_project(config, root)
    _print_summary(config, ok)

    if not ok:
        sys.exit(1)


if __name__ == '__main__':
    main()
