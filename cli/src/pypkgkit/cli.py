"""CLI entry point for pypkgkit."""

from __future__ import annotations

import argparse
import sys

from pypkgkit import __version__
from pypkgkit.prompt import is_interactive
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
        action='version',
        version=f'%(prog)s {__version__}',
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


_CONFIG_FIELDS = (
    'name',
    'author',
    'email',
    'github_owner',
    'description',
)


def _collect_config_kwargs(ns: argparse.Namespace) -> dict[str, object]:
    """Extract init config fields from parsed namespace.

    Args:
        ns: Parsed CLI namespace from ``parse_args``.

    Returns:
        Dict of config kwargs. Missing fields have None values.
    """
    kwargs: dict[str, object] = {}
    for field in _CONFIG_FIELDS:
        kwargs[field] = getattr(ns, field, None)

    # license flag maps to license_key
    kwargs['license_key'] = getattr(ns, 'license', None)

    # pypi flag maps to enable_pypi
    kwargs['enable_pypi'] = getattr(ns, 'pypi', False) or None

    return kwargs


def _needs_interactive(kwargs: dict) -> bool:
    """Check whether interactive prompts are needed.

    Args:
        kwargs: Config kwargs dict.

    Returns:
        True if any required field is None.
    """
    required = ('name', 'author', 'email', 'github_owner', 'description')
    return any(kwargs.get(f) is None for f in required)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the pypkgkit CLI.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Exit code (0 = success).
    """
    ns = parse_args(argv)

    if ns.command != 'new':
        parse_args(['--help'])
        return 1  # pragma: no cover

    config_kwargs = _collect_config_kwargs(ns)
    interactive = _needs_interactive(config_kwargs) and is_interactive()

    return scaffold(
        ns.project_dir,
        template_version=ns.template_version,
        config_kwargs=config_kwargs,
        interactive=interactive,
        github=ns.github,
        github_owner=ns.github_owner,
        private=ns.private,
        require_reviews=ns.require_reviews,
        description=ns.description or '',
    )


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
