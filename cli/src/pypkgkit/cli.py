"""CLI entry point for pypkgkit."""

from __future__ import annotations

import argparse
import sys

from pypkgkit import __version__
from pypkgkit.scaffold import scaffold


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Parsed namespace.
    """
    parser = argparse.ArgumentParser(
        prog='pypkgkit',
        description=('Scaffold new Python packages from uv-python-template.'),
    )
    parser.add_argument(
        '--version',
        action='store_true',
        default=False,
        help='Show version and exit',
    )

    sub = parser.add_subparsers(dest='command')
    new_cmd = sub.add_parser('new', help='Create a new project')
    new_cmd.add_argument(
        'project_dir',
        help='Directory name for the new project',
    )
    new_cmd.add_argument('--name', help='Package name (kebab-case)')
    new_cmd.add_argument('--author', help='Author name')
    new_cmd.add_argument('--email', help='Author email')
    new_cmd.add_argument('--github-owner', help='GitHub username or org')
    new_cmd.add_argument('--description', help='Short project description')
    new_cmd.add_argument('--license', help='License SPDX key')
    new_cmd.add_argument(
        '--pypi',
        action='store_true',
        default=False,
        help='Enable PyPI publishing',
    )
    new_cmd.add_argument(
        '--template-version',
        help='Pin a specific template release tag',
    )
    new_cmd.add_argument(
        '--github',
        action='store_true',
        default=False,
        help='Create a GitHub repository and configure rulesets',
    )
    new_cmd.add_argument(
        '--private',
        action='store_true',
        default=False,
        help='Create a private GitHub repository (default: public)',
    )
    new_cmd.add_argument(
        '--require-reviews',
        type=int,
        default=0,
        metavar='N',
        help='Require N PR approvals in branch ruleset (default: 0)',
    )

    return parser.parse_args(argv)


def _build_passthrough_args(ns: argparse.Namespace) -> list[str]:
    """Build init.py argument list from parsed namespace.

    Args:
        ns: Parsed CLI namespace from ``parse_args``.

    Returns:
        List of arguments to pass to ``scripts/init.py``.
    """
    args: list[str] = []
    if getattr(ns, 'name', None):
        args.extend(['--name', ns.name])
    if getattr(ns, 'author', None):
        args.extend(['--author', ns.author])
    if getattr(ns, 'email', None):
        args.extend(['--email', ns.email])
    if getattr(ns, 'github_owner', None):
        args.extend(['--github-owner', ns.github_owner])
    if getattr(ns, 'description', None):
        args.extend(['--description', ns.description])
    if getattr(ns, 'license', None):
        args.extend(['--license', ns.license])
    if getattr(ns, 'pypi', False):
        args.append('--pypi')
    return args


def main(argv: list[str] | None = None) -> int:
    """Entry point for the pypkgkit CLI.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Exit code (0 = success).
    """
    ns = parse_args(argv)

    if ns.version:
        print(f'pypkgkit {__version__}')
        return 0

    if ns.command != 'new':
        parse_args(['--help'])
        return 1  # pragma: no cover

    init_args = _build_passthrough_args(ns)
    template_version = getattr(ns, 'template_version', None)

    return scaffold(
        ns.project_dir,
        template_version=template_version,
        init_args=init_args,
        github=getattr(ns, 'github', False),
        github_owner=getattr(ns, 'github_owner', None),
        private=getattr(ns, 'private', False),
        require_reviews=getattr(ns, 'require_reviews', 0),
        description=getattr(ns, 'description', '') or '',
    )


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
