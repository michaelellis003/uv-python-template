"""Shared utility functions."""

from __future__ import annotations

import sys


def err(msg: str) -> int:
    """Print an error message and return 1.

    Args:
        msg: Error message.

    Returns:
        Always returns 1.
    """
    print(f'error: {msg}', file=sys.stderr)  # noqa: T201
    return 1
