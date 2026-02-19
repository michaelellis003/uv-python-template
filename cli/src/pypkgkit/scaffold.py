"""Download, extract, and invoke template initialization."""

from __future__ import annotations

import json
import shutil
import tarfile
import tempfile
from pathlib import Path
from types import ModuleType
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from pypkgkit import __version__
from pypkgkit import defaults as _defaults
from pypkgkit._util import err as _err
from pypkgkit.github import (
    check_gh_authenticated,
    check_gh_installed,
    check_git_installed,
    detect_gh_owner,
    git_init,
    setup_github,
)
from pypkgkit.init_bridge import load_init_module, run_init
from pypkgkit.prompt import (
    print_bar,
    print_divider,
    print_field,
    print_header,
    print_next_steps,
    print_outro,
    print_step,
    print_welcome,
    prompt_choice,
    prompt_confirm,
    prompt_text,
)

REPO_OWNER = 'michaelellis003'
REPO_NAME = 'uv-python-template'
_API_BASE = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}'
_ARCHIVE_BASE = f'https://github.com/{REPO_OWNER}/{REPO_NAME}'
_TIMEOUT = 60
_HTTP_FORBIDDEN = 403


def get_latest_release_tag() -> str:
    """Fetch the latest release tag from the GitHub API.

    Returns:
        Tag name string (e.g. ``'v1.5.0'``).

    Raises:
        URLError: On network failure.
        HTTPError: On API error (e.g. 403 rate limit).
    """
    url = f'{_API_BASE}/releases/latest'
    with urlopen(url, timeout=_TIMEOUT) as resp:
        data = json.loads(resp.read().decode())
    return data['tag_name']


def get_tarball_url(tag: str) -> str:
    """Build the archive download URL for a given tag.

    Args:
        tag: Git tag (e.g. ``'v1.5.0'``).

    Returns:
        Full URL to the ``.tar.gz`` archive.
    """
    return f'{_ARCHIVE_BASE}/archive/refs/tags/{tag}.tar.gz'


def download_tarball(url: str, dest: Path) -> Path:
    """Download a tarball to *dest*.

    Args:
        url: URL to download.
        dest: Local path to write the file.

    Returns:
        The *dest* path.
    """
    with urlopen(url, timeout=_TIMEOUT) as resp:
        dest.write_bytes(resp.read())
    return dest


def extract_tarball(path: Path, dest: Path) -> Path:
    """Extract a tarball and return the inner directory.

    Validates every member path to reject path-traversal attacks.

    Args:
        path: Path to the ``.tar.gz`` file.
        dest: Directory to extract into.

    Returns:
        Path to the single top-level directory inside the archive.

    Raises:
        ValueError: If any member has ``..`` or an absolute path.
    """
    with tarfile.open(path, 'r:gz') as tf:
        for member in tf.getmembers():
            member_path = Path(member.name)
            if member_path.is_absolute() or '..' in member_path.parts:
                msg = (
                    f'Refusing to extract: path traversal '
                    f'detected in {member.name!r}'
                )
                raise ValueError(msg)
        # filter='data' requires Python 3.12+
        try:
            tf.extractall(dest, filter='data')
        except TypeError:
            tf.extractall(dest)  # noqa: S202

    # The archive contains a single top-level directory
    children = [p for p in dest.iterdir() if p.is_dir()]
    if len(children) != 1:
        msg = (
            f'Expected 1 top-level directory in archive, found {len(children)}'
        )
        raise ValueError(msg)
    return children[0]


def move_template_to_target(src: Path, target: Path) -> None:
    """Move *src* directory to *target*.

    Args:
        src: Source directory (extracted template).
        target: Desired destination path.

    Raises:
        FileExistsError: If *target* already exists.
    """
    if target.exists():
        msg = f'{target} already exists'
        raise FileExistsError(msg)
    shutil.move(str(src), str(target))


def _resolve_tag(template_version: str | None) -> str:
    """Resolve the release tag to download.

    Args:
        template_version: Explicit tag, or None to fetch latest.

    Returns:
        Git tag string.
    """
    return template_version or get_latest_release_tag()


def _download_and_extract(tag: str, target_path: Path) -> int:
    """Download the template tarball and extract to *target_path*.

    Args:
        tag: Git tag to download.
        target_path: Final destination directory.

    Returns:
        0 on success, 1 on failure.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tarball_dest = Path(tmpdir) / 'template.tar.gz'

        try:
            url = get_tarball_url(tag)
            download_tarball(url, tarball_dest)
        except (URLError, OSError) as exc:
            return _err(f'Failed to download template: {exc}')

        try:
            inner = extract_tarball(tarball_dest, Path(tmpdir))
        except (ValueError, tarfile.TarError) as exc:
            return _err(str(exc))

        try:
            move_template_to_target(inner, target_path)
        except FileExistsError:
            return _err(f'{target_path} already exists')

    return 0


def _prompt_missing_config(
    init_mod: ModuleType,
    config_kwargs: dict,
    target_name: str,
) -> dict:
    """Fill in missing config fields via interactive prompts.

    Uses validators from the loaded init module where available.

    Args:
        init_mod: The loaded ``scripts/init.py`` module.
        config_kwargs: Partially-filled config dict (None = missing).
        target_name: Project directory name for deriving defaults.

    Returns:
        Complete config dict with all required fields.
    """
    result = dict(config_kwargs)

    # Detect defaults
    default_name = result.get('name') or _defaults.derive_package_name(
        target_name
    )
    default_author = result.get('author') or _defaults.detect_git_user_name()
    default_email = result.get('email') or _defaults.detect_git_user_email()
    default_owner = result.get('github_owner') or _defaults.detect_gh_owner()

    # Get validators from init module
    v_name = getattr(init_mod, 'validate_name', None)
    v_email = getattr(init_mod, 'validate_email', None)
    v_author = getattr(init_mod, 'validate_author_name', None)
    v_owner = getattr(init_mod, 'validate_github_owner', None)
    v_desc = getattr(init_mod, 'validate_description', None)

    print_welcome(__version__)
    print_header('New Project Setup')

    if not result.get('name'):
        result['name'] = prompt_text(
            'Package name',
            default=default_name,
            validator=v_name,
        )

    if not result.get('author'):
        result['author'] = prompt_text(
            'Author name',
            default=default_author,
            validator=v_author,
        )

    if not result.get('email'):
        result['email'] = prompt_text(
            'Author email',
            default=default_email,
            validator=v_email,
        )

    if not result.get('github_owner'):
        result['github_owner'] = prompt_text(
            'GitHub owner',
            default=default_owner,
            validator=v_owner,
        )

    if not result.get('description'):
        result['description'] = prompt_text(
            'Description',
            validator=v_desc,
        )

    if not result.get('enable_pypi'):
        result['enable_pypi'] = prompt_confirm(
            'Enable PyPI publishing?', default=False
        )

    # License selection
    if not result.get('license_key'):
        offline = getattr(init_mod, 'OFFLINE_LICENSES', ())
        options = ['Skip (keep Apache-2.0)']
        license_keys = ['none']
        for lic in offline:
            options.append(f'{lic.name} ({lic.key})')
            license_keys.append(lic.key)
        idx = prompt_choice('Select a license', options)
        result['license_key'] = license_keys[idx]

    # Summary
    print_divider()
    print_field('Package name', result.get('name', ''))
    print_field(
        'Author',
        f'{result.get("author", "")} <{result.get("email", "")}>',
    )
    print_field(
        'GitHub repo',
        f'{result.get("github_owner", "")}/{result.get("name", "")}',
    )
    print_field('Description', result.get('description', ''))
    pypi_str = 'yes' if result.get('enable_pypi') else 'no'
    print_field('PyPI', pypi_str)
    print_field('License', result.get('license_key', 'none'))
    print_divider()
    print_bar()

    if not prompt_confirm('Proceed?', default=True):
        print('  Aborted.')
        raise SystemExit(0)

    return result


def scaffold(
    target: str,
    *,
    template_version: str | None = None,
    config_kwargs: dict | None = None,
    interactive: bool = False,
    github: bool = False,
    github_owner: str | None = None,
    private: bool = False,
    require_reviews: int = 0,
    description: str = '',
) -> int:
    """Full scaffold pipeline: download, extract, init, git, github.

    Args:
        target: Directory name for the new project.
        template_version: Pin a specific release tag.
        config_kwargs: Init config fields (None values = prompt).
        interactive: Run interactive prompts for missing fields.
        github: Create a GitHub repository and configure rulesets.
        github_owner: GitHub username or org (auto-detected if omitted).
        private: Create a private GitHub repository.
        require_reviews: Number of required PR approvals.
        description: Short project description.

    Returns:
        0 on success, non-zero on failure.
    """
    target_path = Path(target).resolve()

    if target_path.exists():
        return _err(f'{target_path} already exists')

    # Early gh checks + owner auto-detection (before init.py)
    if github:
        if not check_gh_installed():
            return _err(
                'gh CLI is not installed. Install from https://cli.github.com'
            )
        if not check_gh_authenticated():
            return _err('gh is not authenticated. Run: gh auth login')
        if not github_owner:
            github_owner = detect_gh_owner()
            if not github_owner:
                return _err(
                    'Could not detect GitHub username. '
                    'Use --github-owner to specify.'
                )

    # Inject github_owner into config_kwargs if auto-detected
    effective_kwargs = dict(config_kwargs or {})
    if github and github_owner:
        effective_kwargs.setdefault('github_owner', github_owner)

    try:
        tag = _resolve_tag(template_version)
    except HTTPError as exc:
        if exc.code == _HTTP_FORBIDDEN:
            return _err(
                'GitHub API rate limit exceeded. '
                'Use --template-version to skip the API call.'
            )
        return _err(f'GitHub API error: {exc}')
    except URLError as exc:
        return _err(f'Network error: {exc.reason}')

    if not interactive:
        print_bar()

    print_step(f'Downloading template ({tag})')
    rc = _download_and_extract(tag, target_path)
    if rc != 0:
        return rc

    # Load init module from the downloaded template
    try:
        init_mod = load_init_module(target_path)
    except FileNotFoundError as exc:
        return _err(str(exc))

    # Interactive prompts for missing fields
    if interactive:
        try:
            effective_kwargs = _prompt_missing_config(
                init_mod, effective_kwargs, target_path.name
            )
        except SystemExit as exc:
            return exc.code if isinstance(exc.code, int) else 1

    # Run init_project via bridge
    if not run_init(target_path, effective_kwargs, init_mod=init_mod):
        return _err('Project initialization failed')

    print_step('Updated references')

    # Always: git init
    if not check_git_installed():
        return _err('git is not installed. Install from https://git-scm.com')
    rc = git_init(target_path)
    if rc != 0:
        return _err('git init failed')

    print_step('Initialized git repository')

    # Conditional: GitHub setup
    if github and github_owner is not None:
        rc = setup_github(
            target_path,
            owner=github_owner,
            repo_name=target_path.name,
            description=description,
            private=private,
            require_reviews=require_reviews,
        )
        if rc != 0:
            return rc
        print_step('Created GitHub repository')

    print_bar()
    print_outro('Done! Your package is ready.')

    print_next_steps(
        [
            f'cd {target_path.name}',
            'uv sync',
            'uv run pytest -v --cov',
        ]
    )

    return 0
