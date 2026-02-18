"""Tests for pypkgkit.scaffold module."""

from __future__ import annotations

import tarfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from pypkgkit.scaffold import (
    download_tarball,
    extract_tarball,
    get_latest_release_tag,
    get_tarball_url,
    invoke_init,
    move_template_to_target,
    scaffold,
)

if TYPE_CHECKING:
    from collections.abc import Callable


REPO_OWNER = 'michaelellis003'
REPO_NAME = 'uv-python-template'


class TestGetTarballUrl:
    def test_returns_correct_format(self):
        url = get_tarball_url('v1.5.0')
        expected = (
            f'https://github.com/{REPO_OWNER}/{REPO_NAME}'
            '/archive/refs/tags/v1.5.0.tar.gz'
        )
        assert url == expected


class TestGetLatestReleaseTag:
    def test_returns_tag_name(self, mock_release_json: bytes):
        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_release_json
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch('pypkgkit.scaffold.urlopen', return_value=mock_resp):
            tag = get_latest_release_tag()

        assert tag == 'v1.5.0'


class TestDownloadTarball:
    def test_writes_file_to_dest(self, tmp_path: Path):
        content = b'fake tarball data'
        mock_resp = MagicMock()
        mock_resp.read.return_value = content
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        dest = tmp_path / 'archive.tar.gz'
        with patch('pypkgkit.scaffold.urlopen', return_value=mock_resp):
            result = download_tarball(
                'https://example.com/archive.tar.gz', dest
            )

        assert result == dest
        assert dest.read_bytes() == content


class TestExtractTarball:
    def test_returns_inner_directory(
        self,
        tmp_path: Path,
        mock_tarball: Callable[[str], Path],
    ):
        tarball_path = mock_tarball('v1.5.0')
        dest = tmp_path / 'extracted'
        dest.mkdir()

        inner = extract_tarball(tarball_path, dest)

        assert inner.name == f'{REPO_NAME}-v1.5.0'
        assert (inner / 'pyproject.toml').exists()
        assert (inner / 'scripts' / 'init.py').exists()

    def test_rejects_path_traversal(self, tmp_path: Path):
        import io

        tarball_path = tmp_path / 'evil.tar.gz'
        with tarfile.open(tarball_path, 'w:gz') as tf:
            data = b'evil'
            info = tarfile.TarInfo('../../etc/passwd')
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))

        dest = tmp_path / 'extracted'
        dest.mkdir()

        with pytest.raises(ValueError, match='path traversal'):
            extract_tarball(tarball_path, dest)


class TestMoveTemplateToTarget:
    def test_creates_directory(self, tmp_path: Path):
        src = tmp_path / 'source'
        src.mkdir()
        (src / 'file.txt').write_text('hello')

        target = tmp_path / 'target'
        move_template_to_target(src, target)

        assert target.exists()
        assert (target / 'file.txt').read_text() == 'hello'
        assert not src.exists()

    def test_raises_on_existing_dir(self, tmp_path: Path):
        src = tmp_path / 'source'
        src.mkdir()
        target = tmp_path / 'target'
        target.mkdir()

        with pytest.raises(FileExistsError, match='already exists'):
            move_template_to_target(src, target)


class TestInvokeInit:
    def test_calls_uv_run_script(self, tmp_path: Path):
        init_py = tmp_path / 'scripts' / 'init.py'
        init_py.parent.mkdir(parents=True)
        init_py.write_text('# init script')

        with patch('pypkgkit.scaffold.subprocess') as mock_sub:
            mock_sub.run.return_value = MagicMock(returncode=0)
            invoke_init(tmp_path, ['--name', 'my-pkg'])

        mock_sub.run.assert_called_once()
        cmd = mock_sub.run.call_args[0][0]
        assert cmd[0] == 'uv'
        assert 'run' in cmd
        assert '--script' in cmd
        assert '--name' in cmd
        assert 'my-pkg' in cmd

    def test_raises_when_init_py_missing(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError, match=r'init\.py'):
            invoke_init(tmp_path, [])


class TestScaffold:
    def test_full_pipeline_succeeds(
        self,
        tmp_path: Path,
        mock_release_json: bytes,
        mock_tarball: Callable[[str], Path],
    ):
        tarball_path = mock_tarball('v1.5.0')
        target = tmp_path / 'my-project'

        mock_resp_release = MagicMock()
        mock_resp_release.read.return_value = mock_release_json
        mock_resp_release.__enter__ = lambda s: s
        mock_resp_release.__exit__ = MagicMock(return_value=False)

        mock_resp_tarball = MagicMock()
        mock_resp_tarball.read.return_value = tarball_path.read_bytes()
        mock_resp_tarball.__enter__ = lambda s: s
        mock_resp_tarball.__exit__ = MagicMock(return_value=False)

        call_count = 0

        def mock_urlopen(url, *, timeout=None):
            nonlocal call_count
            call_count += 1
            if 'api.github.com' in url:
                return mock_resp_release
            return mock_resp_tarball

        with (
            patch('pypkgkit.scaffold.urlopen', side_effect=mock_urlopen),
            patch('pypkgkit.scaffold.subprocess') as mock_sub,
        ):
            mock_sub.run.return_value = MagicMock(returncode=0)
            result = scaffold(str(target), init_args=['--name', 'my-pkg'])

        assert result == 0
        assert target.exists()

    def test_existing_directory_returns_error(self, tmp_path: Path):
        target = tmp_path / 'existing'
        target.mkdir()

        result = scaffold(str(target))
        assert result != 0

    def test_network_error_shows_message(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ):
        from urllib.error import URLError

        target = tmp_path / 'my-project'

        with patch(
            'pypkgkit.scaffold.urlopen',
            side_effect=URLError('connection refused'),
        ):
            result = scaffold(str(target))

        assert result != 0
        captured = capsys.readouterr()
        assert 'error' in captured.err.lower()
