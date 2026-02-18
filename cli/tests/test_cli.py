"""Tests for pypkgkit.cli module."""

from __future__ import annotations

from unittest.mock import patch

from pypkgkit.cli import (
    _build_passthrough_args,
    main,
    parse_args,
)


class TestParseArgs:
    def test_new_command_returns_project_name(self):
        ns = parse_args(['new', 'my-project'])
        assert ns.command == 'new'
        assert ns.project_dir == 'my-project'

    def test_version_flag(self):
        ns = parse_args(['--version'])
        assert ns.version is True

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


class TestBuildPassthroughArgs:
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
        args = _build_passthrough_args(ns)
        assert '--name' in args
        assert 'my-pkg' in args
        assert '--author' in args
        assert 'Jane' in args
        assert '--email' in args
        assert '--license' in args
        assert 'mit' in args
        assert '--pypi' in args

    def test_with_no_flags(self):
        ns = parse_args(['new', 'my-project'])
        args = _build_passthrough_args(ns)
        assert args == []


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
                ]
            )

        assert rc == 0
        mock_scaffold.assert_called_once()
        call_kwargs = mock_scaffold.call_args
        assert call_kwargs[0][0] == '/tmp/test-proj'
