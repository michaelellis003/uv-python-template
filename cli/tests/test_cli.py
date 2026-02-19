"""Tests for pypkgkit.cli module."""

from __future__ import annotations

import runpy
from unittest.mock import patch

import pytest

from pypkgkit.cli import (
    _collect_config_kwargs,
    _needs_interactive,
    main,
    parse_args,
)


class TestParseArgs:
    def test_new_command_returns_project_name(self):
        ns = parse_args(['new', 'my-project'])
        assert ns.command == 'new'
        assert ns.project_dir == 'my-project'

    def test_version_flag_exits(self):
        with pytest.raises(SystemExit, match='0'):
            parse_args(['--version'])

    def test_new_with_all_flags(self):
        ns = parse_args(
            [
                'new',
                'my-project',
                '--name',
                'my-pkg',
                '--author',
                'Jane Smith',
                '--email',
                'jane@example.com',
                '--github-owner',
                'janesmith',
                '--description',
                'My awesome package',
                '--license',
                'mit',
                '--pypi',
                '--template-version',
                'v1.5.0',
                '--github',
                '--private',
                '--require-reviews',
                '2',
            ]
        )
        assert ns.project_dir == 'my-project'
        assert ns.name == 'my-pkg'
        assert ns.author == 'Jane Smith'
        assert ns.email == 'jane@example.com'
        assert ns.github_owner == 'janesmith'
        assert ns.description == 'My awesome package'
        assert ns.license == 'mit'
        assert ns.pypi is True
        assert ns.template_version == 'v1.5.0'
        assert ns.github is True
        assert ns.private is True
        assert ns.require_reviews == 2

    def test_github_defaults_to_false(self):
        ns = parse_args(['new', 'my-project'])
        assert ns.github is False
        assert ns.private is False
        assert ns.require_reviews == 0


class TestCollectConfigKwargs:
    def test_with_all_flags(self):
        ns = parse_args(
            [
                'new',
                'my-project',
                '--name',
                'my-pkg',
                '--author',
                'Jane',
                '--email',
                'j@e.com',
                '--github-owner',
                'jane',
                '--description',
                'Desc',
                '--license',
                'mit',
                '--pypi',
            ]
        )
        kwargs = _collect_config_kwargs(ns)
        assert kwargs['name'] == 'my-pkg'
        assert kwargs['author'] == 'Jane'
        assert kwargs['email'] == 'j@e.com'
        assert kwargs['github_owner'] == 'jane'
        assert kwargs['description'] == 'Desc'
        assert kwargs['license_key'] == 'mit'
        assert kwargs['enable_pypi'] is True

    def test_with_no_flags(self):
        ns = parse_args(['new', 'my-project'])
        kwargs = _collect_config_kwargs(ns)
        assert kwargs['name'] is None
        assert kwargs['author'] is None
        assert kwargs['email'] is None
        assert kwargs['github_owner'] is None
        assert kwargs['description'] is None
        assert kwargs['license_key'] is None
        assert kwargs['enable_pypi'] is None


class TestNeedsInteractive:
    def test_returns_true_when_fields_missing(self):
        kwargs = {'name': 'pkg', 'author': None}
        assert _needs_interactive(kwargs) is True

    def test_returns_false_when_all_present(self):
        kwargs = {
            'name': 'pkg',
            'author': 'Jane',
            'email': 'j@e.com',
            'github_owner': 'jane',
            'description': 'Desc',
        }
        assert _needs_interactive(kwargs) is False


class TestMain:
    def test_new_calls_scaffold(self):
        with patch('pypkgkit.cli.scaffold') as mock_scaffold:
            mock_scaffold.return_value = 0
            rc = main(
                [
                    'new',
                    '/tmp/test-proj',
                    '--name',
                    'my-pkg',
                    '--author',
                    'Jane',
                    '--email',
                    'j@e.com',
                    '--github-owner',
                    'jane',
                    '--description',
                    'Desc',
                    '--license',
                    'mit',
                ]
            )

        assert rc == 0
        mock_scaffold.assert_called_once()
        call_args = mock_scaffold.call_args
        assert call_args[0][0] == '/tmp/test-proj'
        assert 'config_kwargs' in call_args[1]

    def test_new_passes_github_flags_to_scaffold(self):
        with patch('pypkgkit.cli.scaffold') as mock_scaffold:
            mock_scaffold.return_value = 0
            main(
                [
                    'new',
                    '/tmp/test-proj',
                    '--name',
                    'my-pkg',
                    '--github',
                    '--private',
                    '--require-reviews',
                    '2',
                    '--github-owner',
                    'jane',
                    '--description',
                    'Cool project',
                ]
            )

        kwargs = mock_scaffold.call_args[1]
        assert kwargs['github'] is True
        assert kwargs['github_owner'] == 'jane'
        assert kwargs['private'] is True
        assert kwargs['require_reviews'] == 2
        assert kwargs['description'] == 'Cool project'

    def test_new_defaults_github_false_in_scaffold(self):
        with patch('pypkgkit.cli.scaffold') as mock_scaffold:
            mock_scaffold.return_value = 0
            main(['new', '/tmp/test-proj'])

        kwargs = mock_scaffold.call_args[1]
        assert kwargs['github'] is False
        assert kwargs['private'] is False
        assert kwargs['require_reviews'] == 0

    def test_interactive_true_when_missing_fields_and_tty(self):
        with (
            patch('pypkgkit.cli.scaffold') as mock_scaffold,
            patch('pypkgkit.cli.is_interactive', return_value=True),
        ):
            mock_scaffold.return_value = 0
            main(['new', '/tmp/test-proj'])

        kwargs = mock_scaffold.call_args[1]
        assert kwargs['interactive'] is True

    def test_interactive_false_when_all_fields_provided(self):
        with patch('pypkgkit.cli.scaffold') as mock_scaffold:
            mock_scaffold.return_value = 0
            main(
                [
                    'new',
                    '/tmp/test-proj',
                    '--name',
                    'pkg',
                    '--author',
                    'Jane',
                    '--email',
                    'j@e.com',
                    '--github-owner',
                    'jane',
                    '--description',
                    'Desc',
                    '--license',
                    'mit',
                ]
            )

        kwargs = mock_scaffold.call_args[1]
        assert kwargs['interactive'] is False


class TestMainModule:
    """Tests for __main__.py entry point."""

    def test_main_module_exits_with_main_return_value(self):
        """Test that __main__ calls sys.exit with main() return value."""
        with (
            patch('pypkgkit.cli.main', return_value=1),
            pytest.raises(SystemExit, match='1'),
        ):
            runpy.run_module('pypkgkit', run_name='__main__', alter_sys=True)

    def test_main_module_exits_zero_on_success(self):
        """Test that __main__ exits 0 when main() returns 0."""
        with (
            patch('pypkgkit.cli.main', return_value=0),
            pytest.raises(SystemExit, match='0'),
        ):
            runpy.run_module('pypkgkit', run_name='__main__', alter_sys=True)
