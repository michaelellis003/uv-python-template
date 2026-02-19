"""Styled terminal prompts for interactive project setup.

Uses a Clack-inspired visual style with vertical bar connectors,
diamond markers for prompts, and checkmark/cross step indicators.
"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING, NoReturn

if TYPE_CHECKING:
    from collections.abc import Callable

# ---------------------------------------------------------------------------
# ANSI escape codes
# ---------------------------------------------------------------------------

_BOLD = '\033[1m'
_CYAN = '\033[36m'
_GREEN = '\033[32m'
_RED = '\033[31m'
_YELLOW = '\033[33m'
_DIM = '\033[2m'
_RESET = '\033[0m'

# ---------------------------------------------------------------------------
# Box-drawing & symbol characters
# ---------------------------------------------------------------------------

_BAR = '\u2502'  # │
_BAR_START = '\u250c'  # ┌
_BAR_END = '\u2514'  # └
_BAR_T = '\u251c'  # ├
_RULE_CHAR = '\u2500'  # ─

_DIAMOND = '\u25c6'  # ◆
_DIAMOND_OPEN = '\u25c7'  # ◇

_CHECK = '\u2714'  # ✔
_CROSS = '\u2716'  # ✖
_WARNING = '\u25b2'  # ▲

_BULLET = '\u25cf'  # ●
_BULLET_OPEN = '\u25cb'  # ○


def _use_color() -> bool:
    """Check whether to emit ANSI color codes.

    Returns:
        False if NO_COLOR is set or stdout is not a tty.
    """
    if os.environ.get('NO_COLOR'):
        return False
    return sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    """Wrap *text* with an ANSI code if color is enabled.

    Args:
        code: ANSI escape sequence.
        text: Text to wrap.

    Returns:
        Colored or plain text.
    """
    if _use_color():
        return f'{code}{text}{_RESET}'
    return text


# ---------------------------------------------------------------------------
# Public helpers — Clack-style output
# ---------------------------------------------------------------------------


def is_interactive() -> bool:
    """Check whether stdin is a terminal.

    Returns:
        True if stdin is a tty.
    """
    return sys.stdin.isatty()


def print_welcome(version: str = '') -> None:
    """Print the welcome banner with tool name, version, and tagline.

    Args:
        version: Version string to display.
    """
    ver = f' v{version}' if version else ''
    print()
    print(f'  {_c(_BOLD, f"pypkgkit{ver}")}')
    print(
        f'  {_c(_DIM, "Create a production-ready Python package in seconds.")}'
    )
    print()


def print_intro(text: str) -> None:
    """Print a session-start line: ``┌  text``.

    Args:
        text: Intro text.
    """
    print(f'{_c(_DIM, _BAR_START)}  {_c(_BOLD, text)}')
    print(f'{_c(_DIM, _BAR)}')


def print_outro(text: str) -> None:
    """Print a session-end line: ``└  text``.

    Args:
        text: Outro text.
    """
    print(f'{_c(_DIM, _BAR_END)}  {_c(_GREEN, text)}')


def print_bar() -> None:
    """Print a bare vertical bar line for spacing."""
    print(f'{_c(_DIM, _BAR)}')


def print_divider() -> None:
    """Print a section divider: ``├──────``."""
    print(f'{_c(_DIM, _BAR_T)}{_c(_DIM, _RULE_CHAR * 36)}')


def print_header(text: str) -> None:
    """Print a styled section header using Clack intro style.

    Args:
        text: Header text.
    """
    print_intro(text)


def print_field(label: str, value: str) -> None:
    """Print a label-value pair prefixed with a bar.

    Args:
        label: Field label.
        value: Field value.
    """
    print(f'{_c(_DIM, _BAR)}  {label + ":":<16}{_c(_CYAN, value)}')


def print_error(text: str) -> None:
    """Print an error message to stderr with cross marker.

    Args:
        text: Error message.
    """
    print(
        f'{_c(_DIM, _BAR)}  {_c(_RED, _CROSS)} {_c(_RED, text)}',
        file=sys.stderr,
    )


def print_step(text: str) -> None:
    """Print a progress step with checkmark.

    Args:
        text: Step description.
    """
    print(f'{_c(_DIM, _BAR)}  {_c(_GREEN, _CHECK)} {text}')


def print_success(text: str) -> None:
    """Print a success message with checkmark.

    Args:
        text: Success message.
    """
    print(f'{_c(_DIM, _BAR)}  {_c(_GREEN, _CHECK)} {_c(_GREEN, text)}')


def print_warning(text: str) -> None:
    """Print a warning message with triangle marker.

    Args:
        text: Warning message.
    """
    print(f'{_c(_DIM, _BAR)}  {_c(_YELLOW, _WARNING)} {_c(_YELLOW, text)}')


def print_next_steps(items: list[str]) -> None:
    """Print numbered next-steps after the outro.

    Args:
        items: List of step strings.
    """
    print()
    print(f'   {_c(_BOLD, "Next steps")}')
    for i, item in enumerate(items, 1):
        print(f'   {_c(_DIM, f"{i}.")} {item}')
    print()


# ---------------------------------------------------------------------------
# Interactive prompts — Clack-style
# ---------------------------------------------------------------------------


def _abort() -> NoReturn:
    """Print 'Aborted.' and exit with code 130."""
    print(f'\n{_c(_DIM, _BAR_END)}  Aborted.')
    raise SystemExit(130)


def prompt_text(
    label: str,
    *,
    default: str | None = None,
    validator: Callable[[str], None] | None = None,
    hint: str | None = None,
) -> str:
    """Prompt for text input with Clack-style diamond marker.

    Args:
        label: Prompt label.
        default: Default value shown in parentheses.
        validator: Callable that raises ValueError on bad input.
        hint: Dim text shown after the label.

    Returns:
        Validated, stripped user input.
    """
    default_str = f' {_c(_DIM, f"({default})")}' if default else ''
    hint_str = f' {_c(_DIM, hint)}' if hint else ''
    print(f'{_c(_CYAN, _DIAMOND)}  {_c(_BOLD, label)}{default_str}{hint_str}')

    while True:
        prompt_str = f'{_c(_DIM, _BAR)}  '
        try:
            raw = input(prompt_str).strip()
        except (KeyboardInterrupt, EOFError):
            _abort()

        value = raw or (default or '')
        if not value:
            print(f'{_c(_DIM, _BAR)}  {_c(_RED, f"{label} cannot be empty.")}')
            continue

        if validator:
            try:
                validator(value)
            except ValueError as exc:
                print(f'{_c(_DIM, _BAR)}  {_c(_RED, str(exc))}')
                continue

        # Echo the accepted value
        print(f'{_c(_DIM, _BAR)}  {_c(_DIM, value)}')
        print(f'{_c(_DIM, _BAR)}')
        return value


def prompt_confirm(
    label: str,
    *,
    default: bool = True,
) -> bool:
    """Prompt for a yes/no confirmation with diamond marker.

    Args:
        label: Prompt label.
        default: Default value (True = Y, False = N).

    Returns:
        True for yes, False for no.
    """
    hint = _c(_DIM, '[Y/n]') if default else _c(_DIM, '[y/N]')
    print(f'{_c(_CYAN, _DIAMOND)}  {label} {hint}')

    prompt_str = f'{_c(_DIM, _BAR)}  '
    try:
        raw = input(prompt_str).strip().lower()
    except (KeyboardInterrupt, EOFError):
        _abort()

    result = default if not raw else raw in ('y', 'yes')

    answer = 'Yes' if result else 'No'
    print(f'{_c(_DIM, _BAR)}  {_c(_DIM, answer)}')
    print(f'{_c(_DIM, _BAR)}')
    return result


def prompt_choice(
    label: str,
    options: list[str],
    *,
    default: int = 0,
) -> int:
    """Prompt for a menu choice with diamond and bullet markers.

    Args:
        label: Menu header text.
        options: List of option labels (1-indexed display).
        default: Default 0-based index.

    Returns:
        0-based index of the selected option.
    """
    print(f'{_c(_CYAN, _DIAMOND)}  {_c(_BOLD, label)}')
    for i, opt in enumerate(options):
        if i == default:
            print(f'{_c(_DIM, _BAR)}  {_c(_CYAN, _BULLET)} {opt}')
        else:
            print(f'{_c(_DIM, _BAR)}  {_c(_DIM, _BULLET_OPEN)} {opt}')

    while True:
        prompt_str = (
            f'{_c(_DIM, _BAR)}  '
            f'{_c(_DIM, f"Choose [1-{len(options)}]")} '
            f'{_c(_DIM, f"({default + 1})")}: '
        )
        try:
            raw = input(prompt_str).strip()
        except (KeyboardInterrupt, EOFError):
            _abort()

        if not raw:
            print(f'{_c(_DIM, _BAR)}')
            return default

        try:
            idx = int(raw)
            if 1 <= idx <= len(options):
                print(f'{_c(_DIM, _BAR)}')
                return idx - 1
        except ValueError:
            pass

        print(
            f'{_c(_DIM, _BAR)}  '
            f'{_c(_RED, f"Invalid choice. Enter 1-{len(options)}.")}'
        )
