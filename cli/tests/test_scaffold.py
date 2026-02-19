"""Tests for pypkgkit.scaffold module."""

from __future__ import annotations

import tarfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from pypkgkit.scaffold import (
    REPO_NAME,
    REPO_OWNER,
    download_tarball,
    extract_tarball,
    get_latest_release_tag,
    get_tarball_url,
    move_template_to_target,
    scaffold,
)

if TYPE_CHECKING:
    from collections.abc import Callable

_FULL_CONFIG = {
    'name': 'my-pkg',
    'author': 'Jane',
    'email': 'j@e.com',
    'github_owner': 'jane',
    'description': 'A test project',
    'license_key': 'none',
    'enable_pypi': False,
}


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


def _mock_urlopen_factory(mock_release_json: bytes, tarball_bytes: bytes):
    """Create a mock_urlopen side_effect function."""
    mock_resp_release = MagicMock()
    mock_resp_release.read.return_value = mock_release_json
    mock_resp_release.__enter__ = lambda s: s
    mock_resp_release.__exit__ = MagicMock(return_value=False)

    mock_resp_tarball = MagicMock()
    mock_resp_tarball.read.return_value = tarball_bytes
    mock_resp_tarball.__enter__ = lambda s: s
    mock_resp_tarball.__exit__ = MagicMock(return_value=False)

    def mock_urlopen(url, *, timeout=None):
        if 'api.github.com' in url:
            return mock_resp_release
        return mock_resp_tarball

    return mock_urlopen


class TestScaffold:
    def test_full_pipeline_succeeds(
        self,
        tmp_path: Path,
        mock_release_json: bytes,
        mock_tarball: Callable[[str], Path],
    ):
        tarball_path = mock_tarball('v1.5.0')
        target = tmp_path / 'my-project'

        mock_urlopen = _mock_urlopen_factory(
            mock_release_json, tarball_path.read_bytes()
        )

        with (
            patch(
                'pypkgkit.scaffold.urlopen',
                side_effect=mock_urlopen,
            ),
            patch(
                'pypkgkit.scaffold.check_git_installed',
                return_value=True,
            ),
            patch('pypkgkit.scaffold.git_init', return_value=0),
        ):
            result = scaffold(str(target), config_kwargs=_FULL_CONFIG)

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

    def test_git_init_always_called_after_init(
        self,
        tmp_path: Path,
        mock_release_json: bytes,
        mock_tarball: Callable[[str], Path],
    ):
        """Test that git_init runs even without --github."""
        tarball_path = mock_tarball('v1.5.0')
        target = tmp_path / 'my-project'

        mock_urlopen = _mock_urlopen_factory(
            mock_release_json, tarball_path.read_bytes()
        )

        with (
            patch(
                'pypkgkit.scaffold.urlopen',
                side_effect=mock_urlopen,
            ),
            patch(
                'pypkgkit.scaffold.check_git_installed',
                return_value=True,
            ),
            patch(
                'pypkgkit.scaffold.git_init', return_value=0
            ) as mock_git_init,
        ):
            result = scaffold(str(target), config_kwargs=_FULL_CONFIG)

        assert result == 0
        mock_git_init.assert_called_once_with(target)

    def test_github_setup_called_when_flag_set(
        self,
        tmp_path: Path,
        mock_release_json: bytes,
        mock_tarball: Callable[[str], Path],
    ):
        """Test that setup_github runs when github=True."""
        tarball_path = mock_tarball('v1.5.0')
        target = tmp_path / 'my-project'

        mock_urlopen = _mock_urlopen_factory(
            mock_release_json, tarball_path.read_bytes()
        )

        with (
            patch(
                'pypkgkit.scaffold.urlopen',
                side_effect=mock_urlopen,
            ),
            patch(
                'pypkgkit.scaffold.check_git_installed',
                return_value=True,
            ),
            patch(
                'pypkgkit.scaffold.check_gh_installed',
                return_value=True,
            ),
            patch(
                'pypkgkit.scaffold.check_gh_authenticated',
                return_value=True,
            ),
            patch(
                'pypkgkit.scaffold.detect_gh_owner',
                return_value='jane',
            ),
            patch('pypkgkit.scaffold.git_init', return_value=0),
            patch(
                'pypkgkit.scaffold.setup_github',
                return_value=0,
            ) as mock_setup,
        ):
            result = scaffold(
                str(target),
                config_kwargs=_FULL_CONFIG,
                github=True,
                private=True,
                require_reviews=2,
                description='Cool',
            )

        assert result == 0
        mock_setup.assert_called_once_with(
            target,
            owner='jane',
            repo_name='my-project',
            description='Cool',
            private=True,
            require_reviews=2,
        )

    def test_github_not_called_when_flag_false(
        self,
        tmp_path: Path,
        mock_release_json: bytes,
        mock_tarball: Callable[[str], Path],
    ):
        """Test that setup_github is NOT called without flag."""
        tarball_path = mock_tarball('v1.5.0')
        target = tmp_path / 'my-project'

        mock_urlopen = _mock_urlopen_factory(
            mock_release_json, tarball_path.read_bytes()
        )

        with (
            patch(
                'pypkgkit.scaffold.urlopen',
                side_effect=mock_urlopen,
            ),
            patch(
                'pypkgkit.scaffold.check_git_installed',
                return_value=True,
            ),
            patch('pypkgkit.scaffold.git_init', return_value=0),
            patch(
                'pypkgkit.scaffold.setup_github',
                return_value=0,
            ) as mock_setup,
        ):
            result = scaffold(str(target), config_kwargs=_FULL_CONFIG)

        assert result == 0
        mock_setup.assert_not_called()

    def test_github_owner_auto_detected(
        self,
        tmp_path: Path,
        mock_release_json: bytes,
        mock_tarball: Callable[[str], Path],
    ):
        """Test that owner is auto-detected when not provided."""
        tarball_path = mock_tarball('v1.5.0')
        target = tmp_path / 'my-project'

        mock_urlopen = _mock_urlopen_factory(
            mock_release_json, tarball_path.read_bytes()
        )

        with (
            patch(
                'pypkgkit.scaffold.urlopen',
                side_effect=mock_urlopen,
            ),
            patch(
                'pypkgkit.scaffold.check_git_installed',
                return_value=True,
            ),
            patch(
                'pypkgkit.scaffold.check_gh_installed',
                return_value=True,
            ),
            patch(
                'pypkgkit.scaffold.check_gh_authenticated',
                return_value=True,
            ),
            patch(
                'pypkgkit.scaffold.detect_gh_owner',
                return_value='autodetected',
            ) as mock_detect,
            patch('pypkgkit.scaffold.git_init', return_value=0),
            patch(
                'pypkgkit.scaffold.setup_github',
                return_value=0,
            ) as mock_setup,
        ):
            result = scaffold(
                str(target),
                config_kwargs=_FULL_CONFIG,
                github=True,
            )

        assert result == 0
        mock_detect.assert_called_once()
        mock_setup.assert_called_once()
        assert mock_setup.call_args[1]['owner'] == 'autodetected'

    def test_github_owner_injected_into_config_kwargs(
        self,
        tmp_path: Path,
        mock_release_json: bytes,
        mock_tarball: Callable[[str], Path],
    ):
        """Test --github-owner is injected into config_kwargs."""
        tarball_path = mock_tarball('v1.5.0')
        target = tmp_path / 'my-project'

        mock_urlopen = _mock_urlopen_factory(
            mock_release_json, tarball_path.read_bytes()
        )

        # Config without github_owner
        kwargs = dict(_FULL_CONFIG)
        del kwargs['github_owner']

        with (
            patch(
                'pypkgkit.scaffold.urlopen',
                side_effect=mock_urlopen,
            ),
            patch(
                'pypkgkit.scaffold.check_git_installed',
                return_value=True,
            ),
            patch(
                'pypkgkit.scaffold.check_gh_installed',
                return_value=True,
            ),
            patch(
                'pypkgkit.scaffold.check_gh_authenticated',
                return_value=True,
            ),
            patch(
                'pypkgkit.scaffold.detect_gh_owner',
                return_value='autodetected',
            ),
            patch('pypkgkit.scaffold.git_init', return_value=0),
            patch(
                'pypkgkit.scaffold.setup_github',
                return_value=0,
            ),
            patch(
                'pypkgkit.scaffold.run_init',
                return_value=True,
            ) as mock_run_init,
        ):
            scaffold(
                str(target),
                config_kwargs=kwargs,
                github=True,
            )

        # run_init should have received github_owner
        call_kwargs = mock_run_init.call_args[0][1]
        assert call_kwargs['github_owner'] == 'autodetected'

    def test_github_fails_early_when_gh_not_installed(
        self,
        tmp_path: Path,
        mock_release_json: bytes,
        mock_tarball: Callable[[str], Path],
        capsys: pytest.CaptureFixture[str],
    ):
        """Test early failure when gh CLI is missing."""
        target = tmp_path / 'my-project'

        with patch(
            'pypkgkit.scaffold.check_gh_installed',
            return_value=False,
        ):
            result = scaffold(str(target), github=True)

        assert result != 0
        captured = capsys.readouterr()
        assert 'gh' in captured.err.lower()

    def test_git_init_failure_returns_error(
        self,
        tmp_path: Path,
        mock_release_json: bytes,
        mock_tarball: Callable[[str], Path],
        capsys: pytest.CaptureFixture[str],
    ):
        """Test error when git init fails."""
        tarball_path = mock_tarball('v1.5.0')
        target = tmp_path / 'my-project'

        mock_urlopen = _mock_urlopen_factory(
            mock_release_json, tarball_path.read_bytes()
        )

        with (
            patch(
                'pypkgkit.scaffold.urlopen',
                side_effect=mock_urlopen,
            ),
            patch(
                'pypkgkit.scaffold.check_git_installed',
                return_value=True,
            ),
            patch('pypkgkit.scaffold.git_init', return_value=1),
        ):
            result = scaffold(str(target), config_kwargs=_FULL_CONFIG)

        assert result != 0
        captured = capsys.readouterr()
        assert 'git init' in captured.err.lower()

    def test_interactive_prompts_fill_missing_fields(
        self,
        tmp_path: Path,
        mock_release_json: bytes,
        mock_tarball: Callable[[str], Path],
    ):
        """Test interactive mode fills in missing config fields."""
        tarball_path = mock_tarball('v1.5.0')
        target = tmp_path / 'my-project'

        mock_urlopen = _mock_urlopen_factory(
            mock_release_json, tarball_path.read_bytes()
        )

        with (
            patch(
                'pypkgkit.scaffold.urlopen',
                side_effect=mock_urlopen,
            ),
            patch(
                'pypkgkit.scaffold.check_git_installed',
                return_value=True,
            ),
            patch('pypkgkit.scaffold.git_init', return_value=0),
            patch(
                'pypkgkit.scaffold._prompt_missing_config',
                return_value=_FULL_CONFIG,
            ) as mock_prompt,
        ):
            result = scaffold(
                str(target),
                config_kwargs={'name': 'my-pkg'},
                interactive=True,
            )

        assert result == 0
        mock_prompt.assert_called_once()

    def test_init_failure_returns_error(
        self,
        tmp_path: Path,
        mock_release_json: bytes,
        mock_tarball: Callable[[str], Path],
        capsys: pytest.CaptureFixture[str],
    ):
        """Test error when run_init returns False."""
        tarball_path = mock_tarball('v1.5.0')
        target = tmp_path / 'my-project'

        mock_urlopen = _mock_urlopen_factory(
            mock_release_json, tarball_path.read_bytes()
        )

        with (
            patch(
                'pypkgkit.scaffold.urlopen',
                side_effect=mock_urlopen,
            ),
            patch(
                'pypkgkit.scaffold.run_init',
                return_value=False,
            ),
        ):
            result = scaffold(str(target), config_kwargs=_FULL_CONFIG)

        assert result != 0
        captured = capsys.readouterr()
        assert 'initialization failed' in captured.err.lower()
