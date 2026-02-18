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

import re
from dataclasses import dataclass, field
from pathlib import Path

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

_NAME_RE = re.compile(r'^[a-z][a-z0-9_-]*$')
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
    ]
    for f in files_to_remove:
        if f.exists():
            f.unlink()

    # Directories to remove
    dirs_to_remove = [
        root / 'tests' / 'template',
        root / 'tests' / 'e2e',
    ]
    for d in dirs_to_remove:
        if d.exists():
            shutil.rmtree(d)


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
