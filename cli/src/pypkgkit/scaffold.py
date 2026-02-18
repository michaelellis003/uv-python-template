"""Download, extract, and invoke template initialization."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

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


def invoke_init(project_dir: Path, args: list[str]) -> int:
    """Run ``scripts/init.py`` in the project directory.

    Args:
        project_dir: Root of the extracted template.
        args: Extra CLI arguments for init.py.

    Returns:
        Process return code.

    Raises:
        FileNotFoundError: If ``scripts/init.py`` does not exist
            or ``uv`` is not installed.
    """
    init_py = project_dir / 'scripts' / 'init.py'
    if not init_py.exists():
        msg = f'scripts/init.py not found in {project_dir}'
        raise FileNotFoundError(msg)

    cmd = ['uv', 'run', '--script', str(init_py), *args]
    result = subprocess.run(cmd, cwd=project_dir)  # noqa: S603
    return result.returncode


def _resolve_tag(template_version: str | None) -> str:
    """Resolve the release tag to download.

    Args:
        template_version: Explicit tag, or None to fetch latest.

    Returns:
        Git tag string.
    """
    return template_version or get_latest_release_tag()


def _err(msg: str) -> int:
    """Print an error message and return 1.

    Args:
        msg: Error message.

    Returns:
        Always returns 1.
    """
    print(f'error: {msg}', file=sys.stderr)
    return 1


def _download_and_extract(tag: str, target_path: Path) -> int:
    """Download the template tarball and extract to *target_path*.

    Args:
        tag: Git tag to download.
        target_path: Final destination directory.

    Returns:
        0 on success, 1 on failure.
    """
    import tempfile

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


def scaffold(
    target: str,
    *,
    template_version: str | None = None,
    init_args: list[str] | None = None,
) -> int:
    """Full scaffold pipeline: download, extract, init.

    Args:
        target: Directory name for the new project.
        template_version: Pin a specific release tag.
        init_args: Extra arguments for ``scripts/init.py``.

    Returns:
        0 on success, non-zero on failure.
    """
    target_path = Path(target).resolve()

    if target_path.exists():
        return _err(f'{target_path} already exists')

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

    rc = _download_and_extract(tag, target_path)
    if rc != 0:
        return rc

    try:
        return invoke_init(target_path, init_args or [])
    except FileNotFoundError as exc:
        if 'uv' in str(exc).lower() or 'No such file' in str(exc):
            return _err(
                'uv is not installed. '
                'Install it from https://docs.astral.sh/uv/'
            )
        return _err(str(exc))
