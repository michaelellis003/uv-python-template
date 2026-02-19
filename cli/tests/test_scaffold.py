"""Tests for pypkgkit.scaffold module."""

from __future__ import annotations

import io
import tarfile
from email.message import Message
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from pypkgkit.scaffold import (
    REPO_NAME,
    REPO_OWNER,
    _download_and_extract,
    _prompt_missing_config,
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

    def test_http_403_rate_limit_error(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ):
        """Test 403 rate-limit error shows helpful message."""
        target = tmp_path / 'my-project'

        exc = HTTPError(
            'https://api.github.com/repos/x/y/releases/latest',
            403,
            'rate limit exceeded',
            Message(),
            None,
        )
        with patch(
            'pypkgkit.scaffold.get_latest_release_tag',
            side_effect=exc,
        ):
            result = scaffold(str(target))

        assert result != 0
        captured = capsys.readouterr()
        assert 'rate limit' in captured.err.lower()

    def test_non_403_http_error(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ):
        """Test non-403 HTTPError shows generic API error."""
        target = tmp_path / 'my-project'

        exc = HTTPError(
            'https://api.github.com/repos/x/y/releases/latest',
            500,
            'Internal Server Error',
            Message(),
            None,
        )
        with patch(
            'pypkgkit.scaffold.get_latest_release_tag',
            side_effect=exc,
        ):
            result = scaffold(str(target))

        assert result != 0
        captured = capsys.readouterr()
        assert 'api error' in captured.err.lower()

    def test_gh_not_authenticated_returns_error(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ):
        """Test early failure when gh is not authenticated."""
        target = tmp_path / 'my-project'

        with (
            patch(
                'pypkgkit.scaffold.check_gh_installed',
                return_value=True,
            ),
            patch(
                'pypkgkit.scaffold.check_gh_authenticated',
                return_value=False,
            ),
        ):
            result = scaffold(str(target), github=True)

        assert result != 0
        captured = capsys.readouterr()
        assert 'not authenticated' in captured.err.lower()

    def test_detect_gh_owner_returns_none(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ):
        """Test error when auto-detection of GitHub owner fails."""
        target = tmp_path / 'my-project'

        with (
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
                return_value=None,
            ),
        ):
            result = scaffold(str(target), github=True)

        assert result != 0
        captured = capsys.readouterr()
        assert 'github username' in captured.err.lower()

    def test_git_not_installed_returns_error(
        self,
        tmp_path: Path,
        mock_release_json: bytes,
        mock_tarball: Callable[[str], Path],
        capsys: pytest.CaptureFixture[str],
    ):
        """Test error when git is not installed."""
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
                return_value=False,
            ),
        ):
            result = scaffold(str(target), config_kwargs=_FULL_CONFIG)

        assert result != 0
        captured = capsys.readouterr()
        assert 'git' in captured.err.lower()

    def test_setup_github_failure_propagates(
        self,
        tmp_path: Path,
        mock_release_json: bytes,
        mock_tarball: Callable[[str], Path],
    ):
        """Test that setup_github failure propagates."""
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
                return_value=1,
            ),
        ):
            result = scaffold(
                str(target),
                config_kwargs=_FULL_CONFIG,
                github=True,
            )

        assert result != 0

    def test_load_init_module_file_not_found(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ):
        """Test error when scripts/init.py is missing."""
        target = tmp_path / 'my-project'
        # Create a directory with no scripts/init.py
        target.mkdir()
        (target / 'pyproject.toml').write_text('[project]\n')

        with patch(
            'pypkgkit.scaffold._download_and_extract',
            return_value=0,
        ):
            result = scaffold(str(target), config_kwargs=_FULL_CONFIG)

        # target already exists, so it returns error
        assert result != 0


class TestExtractTarballEdgeCases:
    """Test edge cases in extract_tarball."""

    def test_zero_top_level_dirs_raises(self, tmp_path: Path):
        """Test ValueError when archive has no directories."""
        tarball_path = tmp_path / 'flat.tar.gz'
        with tarfile.open(tarball_path, 'w:gz') as tf:
            data = b'hello'
            info = tarfile.TarInfo('file.txt')
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))

        dest = tmp_path / 'extracted'
        dest.mkdir()

        with pytest.raises(ValueError, match='Expected 1 top-level'):
            extract_tarball(tarball_path, dest)

    def test_multiple_top_level_dirs_raises(self, tmp_path: Path):
        """Test ValueError when archive has multiple top-level dirs."""
        tarball_path = tmp_path / 'multi.tar.gz'
        with tarfile.open(tarball_path, 'w:gz') as tf:
            for name in ['dir_a/file.txt', 'dir_b/file.txt']:
                data = b'content'
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))

        dest = tmp_path / 'extracted'
        dest.mkdir()

        with pytest.raises(ValueError, match='Expected 1 top-level'):
            extract_tarball(tarball_path, dest)


class TestDownloadAndExtract:
    """Test _download_and_extract error paths."""

    def test_os_error_during_download(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ):
        """Test OSError during download returns error."""
        target = tmp_path / 'my-project'

        with patch(
            'pypkgkit.scaffold.download_tarball',
            side_effect=OSError('disk full'),
        ):
            result = _download_and_extract('v1.0.0', target)

        assert result != 0
        captured = capsys.readouterr()
        assert 'download' in captured.err.lower()

    def test_tar_error_during_extraction(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ):
        """Test TarError during extraction returns error."""
        target = tmp_path / 'my-project'

        with (
            patch('pypkgkit.scaffold.download_tarball'),
            patch(
                'pypkgkit.scaffold.extract_tarball',
                side_effect=tarfile.TarError('corrupt'),
            ),
        ):
            result = _download_and_extract('v1.0.0', target)

        assert result != 0
        captured = capsys.readouterr()
        assert 'corrupt' in captured.err.lower()

    def test_file_exists_error_during_move(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ):
        """Test FileExistsError during move returns error."""
        target = tmp_path / 'my-project'

        with (
            patch('pypkgkit.scaffold.download_tarball'),
            patch(
                'pypkgkit.scaffold.extract_tarball',
                return_value=tmp_path / 'inner',
            ),
            patch(
                'pypkgkit.scaffold.move_template_to_target',
                side_effect=FileExistsError('exists'),
            ),
        ):
            result = _download_and_extract('v1.0.0', target)

        assert result != 0
        captured = capsys.readouterr()
        assert 'already exists' in captured.err.lower()

    def test_url_error_during_download(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ):
        """Test URLError during download returns error."""
        target = tmp_path / 'my-project'

        with patch(
            'pypkgkit.scaffold.download_tarball',
            side_effect=URLError('connection refused'),
        ):
            result = _download_and_extract('v1.0.0', target)

        assert result != 0
        captured = capsys.readouterr()
        assert 'download' in captured.err.lower()


class TestPromptMissingConfig:
    """Test _prompt_missing_config interactive paths."""

    def _make_mock_init_mod(self):
        """Create a mock init module with validators."""
        mod = MagicMock()
        mod.validate_name = MagicMock()
        mod.validate_email = MagicMock()
        mod.validate_author_name = MagicMock()
        mod.validate_github_owner = MagicMock()
        mod.validate_description = MagicMock()
        mod.OFFLINE_LICENSES = []
        return mod

    def test_happy_path_all_prompts(self):
        """Test that all prompts are called for empty config."""
        mod = self._make_mock_init_mod()

        with (
            patch('pypkgkit.scaffold.print_welcome'),
            patch('pypkgkit.scaffold.print_header'),
            patch('pypkgkit.scaffold.print_divider'),
            patch('pypkgkit.scaffold.print_field'),
            patch('pypkgkit.scaffold.print_bar'),
            patch(
                'pypkgkit.scaffold.prompt_text',
                side_effect=[
                    'my-pkg',
                    'Jane',
                    'j@e.com',
                    'jane',
                    'A project',
                ],
            ),
            patch(
                'pypkgkit.scaffold.prompt_confirm',
                side_effect=[False, True],
            ),
            patch(
                'pypkgkit.scaffold.prompt_choice',
                return_value=0,
            ),
        ):
            result = _prompt_missing_config(mod, {}, 'my-pkg')

        assert result['name'] == 'my-pkg'
        assert result['author'] == 'Jane'
        assert result['email'] == 'j@e.com'
        assert result['github_owner'] == 'jane'
        assert result['description'] == 'A project'
        assert result['license_key'] == 'none'

    def test_abort_on_decline(self):
        """Test SystemExit when user declines confirmation."""
        mod = self._make_mock_init_mod()

        with (
            patch('pypkgkit.scaffold.print_welcome'),
            patch('pypkgkit.scaffold.print_header'),
            patch('pypkgkit.scaffold.print_divider'),
            patch('pypkgkit.scaffold.print_field'),
            patch('pypkgkit.scaffold.print_bar'),
            patch(
                'pypkgkit.scaffold.prompt_text',
                return_value='test',
            ),
            patch(
                'pypkgkit.scaffold.prompt_confirm',
                side_effect=[False, False],
            ),
            patch(
                'pypkgkit.scaffold.prompt_choice',
                return_value=0,
            ),
            pytest.raises(SystemExit),
        ):
            _prompt_missing_config(mod, {}, 'my-pkg')

    def test_prefilled_fields_not_prompted(self):
        """Test that prefilled fields skip prompts."""
        mod = self._make_mock_init_mod()

        prefilled = {
            'name': 'my-pkg',
            'author': 'Jane',
            'email': 'j@e.com',
            'github_owner': 'jane',
            'description': 'A project',
            'enable_pypi': False,
            'license_key': 'mit',
        }

        with (
            patch('pypkgkit.scaffold.print_welcome'),
            patch('pypkgkit.scaffold.print_header'),
            patch('pypkgkit.scaffold.print_divider'),
            patch('pypkgkit.scaffold.print_field'),
            patch('pypkgkit.scaffold.print_bar'),
            patch(
                'pypkgkit.scaffold.prompt_text',
            ) as mock_text,
            patch(
                'pypkgkit.scaffold.prompt_confirm',
                return_value=True,
            ),
            patch(
                'pypkgkit.scaffold.prompt_choice',
            ) as mock_choice,
        ):
            result = _prompt_missing_config(mod, prefilled, 'my-pkg')

        # No prompts should have been called
        mock_text.assert_not_called()
        mock_choice.assert_not_called()
        assert result['name'] == 'my-pkg'
