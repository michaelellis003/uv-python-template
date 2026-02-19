"""Tests for pypkgkit.prompt module."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from pypkgkit.prompt import (
    is_interactive,
    print_bar,
    print_divider,
    print_error,
    print_field,
    print_header,
    print_intro,
    print_next_steps,
    print_outro,
    print_step,
    print_success,
    print_warning,
    print_welcome,
    prompt_choice,
    prompt_confirm,
    prompt_text,
)


def _no_color():
    """Context manager to disable ANSI color."""
    return patch('pypkgkit.prompt._use_color', return_value=False)


class TestIsInteractive:
    def test_returns_true_when_tty(self):
        with patch('pypkgkit.prompt.sys.stdin') as mock_stdin:
            mock_stdin.isatty.return_value = True
            assert is_interactive() is True

    def test_returns_false_when_not_tty(self):
        with patch('pypkgkit.prompt.sys.stdin') as mock_stdin:
            mock_stdin.isatty.return_value = False
            assert is_interactive() is False


# -------------------------------------------------------------------
# New Clack-style print helpers
# -------------------------------------------------------------------


class TestPrintWelcome:
    def test_shows_version_and_tagline(self, capsys):
        with _no_color():
            print_welcome('1.2.3')
        out = capsys.readouterr().out
        assert 'pypkgkit' in out
        assert '1.2.3' in out
        assert 'Python package' in out

    def test_shows_default_version(self, capsys):
        with _no_color():
            print_welcome()
        out = capsys.readouterr().out
        assert 'pypkgkit' in out


class TestPrintIntro:
    def test_starts_with_bar_start(self, capsys):
        with _no_color():
            print_intro('Setup')
        out = capsys.readouterr().out
        assert '\u250c' in out  # ┌
        assert 'Setup' in out

    def test_followed_by_bar(self, capsys):
        with _no_color():
            print_intro('Setup')
        out = capsys.readouterr().out
        assert '\u2502' in out  # │


class TestPrintOutro:
    def test_ends_with_bar_end(self, capsys):
        with _no_color():
            print_outro('Done!')
        out = capsys.readouterr().out
        assert '\u2514' in out  # └
        assert 'Done!' in out


class TestPrintBar:
    def test_prints_bar(self, capsys):
        with _no_color():
            print_bar()
        out = capsys.readouterr().out
        assert '\u2502' in out  # │


class TestPrintDivider:
    def test_prints_bar_t(self, capsys):
        with _no_color():
            print_divider()
        out = capsys.readouterr().out
        assert '\u251c' in out  # ├
        assert '\u2500' in out  # ─


class TestPrintWarning:
    def test_prints_warning_with_triangle(self, capsys):
        with _no_color():
            print_warning('Caution!')
        out = capsys.readouterr().out
        assert '\u25b2' in out  # ▲
        assert 'Caution!' in out
        assert '\u2502' in out  # │


class TestPrintNextSteps:
    def test_prints_numbered_items(self, capsys):
        with _no_color():
            print_next_steps(
                ['cd my-project', 'uv sync', 'uv run pytest'],
            )
        out = capsys.readouterr().out
        assert 'Next steps' in out
        assert '1.' in out
        assert 'cd my-project' in out
        assert '2.' in out
        assert 'uv sync' in out
        assert '3.' in out
        assert 'uv run pytest' in out


# -------------------------------------------------------------------
# Rewritten print helpers (bar-prefixed)
# -------------------------------------------------------------------


class TestPrintHelpers:
    def test_print_header_calls_intro(self, capsys):
        with _no_color():
            print_header('Test Header')
        out = capsys.readouterr().out
        assert 'Test Header' in out
        assert '\u250c' in out  # ┌

    def test_print_field_bar_prefixed(self, capsys):
        with _no_color():
            print_field('Name', 'Jane')
        out = capsys.readouterr().out
        assert 'Name' in out
        assert 'Jane' in out
        assert '\u2502' in out  # │

    def test_print_error_with_cross(self, capsys):
        with _no_color():
            print_error('Something broke')
        captured = capsys.readouterr()
        assert 'Something broke' in captured.err
        assert '\u2716' in captured.err  # ✖

    def test_print_step_with_check(self, capsys):
        with _no_color():
            print_step('Downloading template')
        out = capsys.readouterr().out
        assert 'Downloading template' in out
        assert '\u2714' in out  # ✔
        assert '\u2502' in out  # │

    def test_print_success_with_check(self, capsys):
        with _no_color():
            print_success('All done')
        out = capsys.readouterr().out
        assert 'All done' in out


# -------------------------------------------------------------------
# Interactive prompts (Clack-style)
# -------------------------------------------------------------------


class TestPromptText:
    def test_returns_user_input(self):
        with (
            patch('builtins.input', return_value='hello'),
            patch('builtins.print'),
        ):
            result = prompt_text('Name')
        assert result == 'hello'

    def test_uses_default_when_empty(self):
        with (
            patch('builtins.input', return_value=''),
            patch('builtins.print'),
        ):
            result = prompt_text('Name', default='Jane')
        assert result == 'Jane'

    def test_retries_on_validation_failure(self):
        calls = iter(['bad', 'good'])
        validator_calls = iter([ValueError('nope'), None])

        def mock_validator(val):
            exc = next(validator_calls)
            if exc:
                raise exc

        with (
            patch('builtins.input', side_effect=calls),
            patch('builtins.print'),
        ):
            result = prompt_text('Name', validator=mock_validator)
        assert result == 'good'

    def test_strips_whitespace(self):
        with (
            patch('builtins.input', return_value='  hello  '),
            patch('builtins.print'),
        ):
            result = prompt_text('Name')
        assert result == 'hello'

    def test_retries_on_empty_no_default(self):
        calls = iter(['', 'valid'])
        with (
            patch('builtins.input', side_effect=calls),
            patch('builtins.print'),
        ):
            result = prompt_text('Name')
        assert result == 'valid'

    def test_keyboard_interrupt_exits(self):
        with (
            patch('builtins.input', side_effect=KeyboardInterrupt),
            patch('builtins.print'),
            pytest.raises(SystemExit, match='130'),
        ):
            prompt_text('Name')

    def test_eof_error_exits(self):
        with (
            patch('builtins.input', side_effect=EOFError),
            patch('builtins.print'),
            pytest.raises(SystemExit, match='130'),
        ):
            prompt_text('Name')

    def test_shows_diamond_marker(self, capsys):
        with (
            patch('builtins.input', return_value='val'),
            _no_color(),
        ):
            prompt_text('Name')
        out = capsys.readouterr().out
        assert '\u25c6' in out  # ◆

    def test_shows_value_on_bar_line(self, capsys):
        with (
            patch('builtins.input', return_value='hello'),
            _no_color(),
        ):
            prompt_text('Name')
        out = capsys.readouterr().out
        assert '\u2502' in out  # │
        assert 'hello' in out


class TestPromptConfirm:
    def test_default_true_returns_true_on_empty(self):
        with (
            patch('builtins.input', return_value=''),
            patch('builtins.print'),
        ):
            assert prompt_confirm('Continue?', default=True) is True

    def test_default_false_returns_false_on_empty(self):
        with (
            patch('builtins.input', return_value=''),
            patch('builtins.print'),
        ):
            assert prompt_confirm('Continue?', default=False) is False

    def test_y_returns_true(self):
        with (
            patch('builtins.input', return_value='y'),
            patch('builtins.print'),
        ):
            assert prompt_confirm('Continue?') is True

    def test_yes_returns_true(self):
        with (
            patch('builtins.input', return_value='yes'),
            patch('builtins.print'),
        ):
            assert prompt_confirm('Continue?') is True

    def test_n_returns_false(self):
        with (
            patch('builtins.input', return_value='n'),
            patch('builtins.print'),
        ):
            assert prompt_confirm('Continue?') is False

    def test_keyboard_interrupt_exits(self):
        with (
            patch('builtins.input', side_effect=KeyboardInterrupt),
            patch('builtins.print'),
            pytest.raises(SystemExit, match='130'),
        ):
            prompt_confirm('Continue?')

    def test_shows_diamond_and_answer(self, capsys):
        with (
            patch('builtins.input', return_value='y'),
            _no_color(),
        ):
            prompt_confirm('Continue?')
        out = capsys.readouterr().out
        assert '\u25c6' in out  # ◆
        assert 'Yes' in out


class TestPromptChoice:
    def test_returns_selected_index(self):
        with (
            patch('builtins.input', return_value='2'),
            patch('builtins.print'),
        ):
            result = prompt_choice(
                'Pick one',
                ['Alpha', 'Beta', 'Gamma'],
            )
        assert result == 1

    def test_default_on_empty_input(self):
        with (
            patch('builtins.input', return_value=''),
            patch('builtins.print'),
        ):
            result = prompt_choice(
                'Pick one',
                ['Alpha', 'Beta'],
                default=0,
            )
        assert result == 0

    def test_retries_on_invalid_input(self):
        calls = iter(['99', '1'])
        with (
            patch('builtins.input', side_effect=calls),
            patch('builtins.print'),
        ):
            result = prompt_choice('Pick one', ['Alpha', 'Beta'])
        assert result == 0

    def test_retries_on_non_numeric_input(self):
        calls = iter(['abc', '1'])
        with (
            patch('builtins.input', side_effect=calls),
            patch('builtins.print'),
        ):
            result = prompt_choice('Pick one', ['Alpha', 'Beta'])
        assert result == 0

    def test_keyboard_interrupt_exits(self):
        with (
            patch('builtins.input', side_effect=KeyboardInterrupt),
            patch('builtins.print'),
            pytest.raises(SystemExit, match='130'),
        ):
            prompt_choice('Pick', ['A', 'B'])

    def test_shows_diamond_and_bullets(self, capsys):
        with (
            patch('builtins.input', return_value='1'),
            _no_color(),
        ):
            prompt_choice('Pick one', ['Alpha', 'Beta'])
        out = capsys.readouterr().out
        assert '\u25c6' in out  # ◆
        assert '\u25cf' in out or '\u25cb' in out  # ● or ○


class TestNoColor:
    def test_no_color_disables_ansi(self):
        with patch.dict('os.environ', {'NO_COLOR': '1'}):
            from pypkgkit.prompt import _use_color

            assert _use_color() is False
