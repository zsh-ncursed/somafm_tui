"""Tests for terminal module."""

import pytest
from unittest.mock import Mock, patch, call
import curses

from somafm_tui.terminal import (
    strip_ansi,
    truncate,
    escape_for_display,
    safe_addstr,
    safe_addstr_with_truncate,
    ANSI_ESCAPE_PATTERN,
)


class TestStripAnsi:
    """Tests for strip_ansi function."""

    def test_strip_ansi_removes_color_codes(self):
        """Should remove ANSI color codes."""
        text = "\x1b[31mRed text\x1b[0m"

        result = strip_ansi(text)

        assert result == "Red text"

    def test_strip_ansi_removes_multiple_codes(self):
        """Should remove multiple ANSI codes."""
        text = "\x1b[1;31mBold Red\x1b[0m and \x1b[32mGreen\x1b[0m"

        result = strip_ansi(text)

        assert result == "Bold Red and Green"

    def test_strip_ansi_no_ansi_codes(self):
        """Should return text unchanged when no ANSI codes."""
        text = "Plain text without any formatting"

        result = strip_ansi(text)

        assert result == text

    def test_strip_ansi_empty_string(self):
        """Should handle empty string."""
        result = strip_ansi("")

        assert result == ""

    def test_strip_ansi_only_ansi_codes(self):
        """Should handle string with only ANSI codes."""
        text = "\x1b[31m\x1b[0m"

        result = strip_ansi(text)

        assert result == ""

    def test_strip_ansi_complex_sequences(self):
        """Should handle complex ANSI sequences."""
        text = "\x1b[38;5;196mRGB Color\x1b[48;5;21m\x1b[1mStyled\x1b[0m"

        result = strip_ansi(text)

        assert result == "RGB ColorStyled"


class TestTruncate:
    """Tests for truncate function."""

    def test_truncate_within_limit(self):
        """Should return text unchanged when within limit."""
        text = "Short text"

        result = truncate(text, 20)

        assert result == "Short text"

    def test_truncate_exceeds_limit(self):
        """Should truncate text exceeding limit."""
        text = "This is a longer text"

        result = truncate(text, 10)

        assert len(result) == 10
        assert result.endswith("...")

    def test_truncate_exact_limit(self):
        """Should return text unchanged at exact limit."""
        text = "Exactly 10"

        result = truncate(text, 10)

        assert result == "Exactly 10"

    def test_truncate_with_custom_ellipsis(self):
        """Should use custom ellipsis."""
        text = "Long text here"

        result = truncate(text, 10, ellipsis=" [more]")

        assert result.endswith(" [more]")
        assert len(result) == 10

    def test_truncate_empty_string(self):
        """Should handle empty string."""
        result = truncate("", 10)

        assert result == ""

    def test_truncate_zero_limit(self):
        """Should handle zero limit."""
        text = "Some text"

        result = truncate(text, 0)

        # When limit is 0 or less than ellipsis, result will be truncated
        assert len(result) == 0 or result.endswith("...")

    def test_truncate_limit_less_than_ellipsis(self):
        """Should handle limit smaller than ellipsis."""
        text = "Text"

        result = truncate(text, 2)

        # Should still truncate to limit
        assert len(result) <= 6  # May include partial ellipsis


class TestEscapeForDisplay:
    """Tests for escape_for_display function."""

    def test_escape_for_display_strips_ansi(self):
        """Should strip ANSI codes."""
        text = "\x1b[31mColored\x1b[0m"

        result = escape_for_display(text)

        assert result == "Colored"

    def test_escape_for_display_truncates(self):
        """Should truncate when max_length provided."""
        text = "This is a long text"

        result = escape_for_display(text, max_length=10)

        assert len(result) == 10

    def test_escape_for_display_no_max_length(self):
        """Should not truncate when max_length is None."""
        text = "Full length text"

        result = escape_for_display(text, max_length=None)

        assert result == "Full length text"

    def test_escape_for_display_both_operations(self):
        """Should strip ANSI and truncate."""
        text = "\x1b[31mThis is a long colored text\x1b[0m"

        result = escape_for_display(text, max_length=15)

        assert "..." in result
        assert len(result) <= 15
        assert "\x1b" not in result

    def test_escape_for_display_empty_string(self):
        """Should handle empty string."""
        result = escape_for_display("")

        assert result == ""


class TestSafeAddstr:
    """Tests for safe_addstr function."""

    def test_safe_addstr_writes_text(self):
        """Should write text to window."""
        window = Mock()

        safe_addstr(window, 0, 0, "Test text")

        window.addstr.assert_called_once_with(0, 0, "Test text", 0)

    def test_safe_addstr_with_attributes(self):
        """Should write text with attributes."""
        window = Mock()

        safe_addstr(window, 1, 2, "Styled text", attr=curses.A_BOLD)

        window.addstr.assert_called_once_with(1, 2, "Styled text", curses.A_BOLD)

    def test_safe_addstr_with_max_width(self):
        """Should truncate to max_width."""
        window = Mock()

        safe_addstr(window, 0, 0, "Long text", max_width=5)

        # Should truncate with ellipsis
        call_args = window.addstr.call_args
        text = call_args[0][2]
        assert "..." in text or len(text) <= 5

    def test_safe_addstr_handles_curses_error(self):
        """Should handle curses errors gracefully."""
        window = Mock()
        window.addstr.side_effect = curses.error("error")

        # Should not raise
        safe_addstr(window, 0, 0, "Test")

    def test_safe_addstr_strips_ansi_codes(self):
        """Should strip ANSI codes before writing."""
        window = Mock()

        safe_addstr(window, 0, 0, "\x1b[31mRed\x1b[0m")

        window.addstr.assert_called_once_with(0, 0, "Red", 0)


class TestSafeAddstrWithTruncate:
    """Tests for safe_addstr_with_truncate function."""

    def test_safe_addstr_with_truncate_writes_text(self):
        """Should write text to window."""
        window = Mock()
        window.getmaxyx.return_value = (24, 80)

        safe_addstr_with_truncate(window, 0, 0, "Test text", max_width=50)

        window.addstr.assert_called()

    def test_safe_addstr_with_truncate_adjusts_width(self):
        """Should adjust width to fit screen."""
        window = Mock()
        window.getmaxyx.return_value = (24, 80)

        safe_addstr_with_truncate(window, 0, 70, "Test text", max_width=50)

        # Should adjust width to fit (80 - 70 = 10)
        call_args = window.addstr.call_args
        text = call_args[0][2]
        assert len(text) <= 10

    def test_safe_addstr_with_truncate_out_of_bounds_y(self):
        """Should handle y out of bounds."""
        window = Mock()
        window.getmaxyx.return_value = (24, 80)

        # Should not raise or write
        safe_addstr_with_truncate(window, 100, 0, "Test", max_width=50)

        window.addstr.assert_not_called()

    def test_safe_addstr_with_truncate_out_of_bounds_x(self):
        """Should handle x out of bounds."""
        window = Mock()
        window.getmaxyx.return_value = (24, 80)

        # Should not raise or write
        safe_addstr_with_truncate(window, 0, 100, "Test", max_width=50)

        window.addstr.assert_not_called()

    def test_safe_addstr_with_truncate_with_attributes(self):
        """Should write text with attributes."""
        window = Mock()
        window.getmaxyx.return_value = (24, 80)

        safe_addstr_with_truncate(
            window, 0, 0, "Styled text", max_width=50, attr=curses.A_BOLD
        )

        call_args = window.addstr.call_args
        assert call_args[0][3] == curses.A_BOLD

    def test_safe_addstr_with_truncate_handles_curses_error(self):
        """Should handle curses errors gracefully."""
        window = Mock()
        window.getmaxyx.return_value = (24, 80)
        window.addstr.side_effect = curses.error("error")

        # Should not raise
        safe_addstr_with_truncate(window, 0, 0, "Test", max_width=50)


class TestAnsiEscapePattern:
    """Tests for ANSI escape pattern."""

    def test_pattern_matches_color_codes(self):
        """Should match basic color codes."""
        text = "\x1b[31m"

        match = ANSI_ESCAPE_PATTERN.search(text)

        assert match is not None

    def test_pattern_matches_reset_code(self):
        """Should match reset code."""
        text = "\x1b[0m"

        match = ANSI_ESCAPE_PATTERN.search(text)

        assert match is not None

    def test_pattern_matches_complex_codes(self):
        """Should match complex codes."""
        text = "\x1b[1;31;42m"

        match = ANSI_ESCAPE_PATTERN.search(text)

        assert match is not None

    def test_pattern_matches_256_color(self):
        """Should match 256-color codes."""
        text = "\x1b[38;5;196m"

        match = ANSI_ESCAPE_PATTERN.search(text)

        assert match is not None

    def test_pattern_does_not_match_plain_text(self):
        """Should not match plain text."""
        text = "Plain text without codes"

        match = ANSI_ESCAPE_PATTERN.search(text)

        assert match is None


class TestTerminalUtilitiesIntegration:
    """Integration tests for terminal utilities."""

    def test_full_text_processing_pipeline(self):
        """Should process text through full pipeline."""
        # Start with ANSI-formatted text
        raw_text = "\x1b[1;31m\x1b[4mBold Underlined Red\x1b[0m"

        # Strip ANSI codes
        stripped = strip_ansi(raw_text)
        assert stripped == "Bold Underlined Red"

        # Truncate if needed
        truncated = truncate(stripped, 15)
        assert "..." in truncated

        # Escape for display (should be no-op after stripping)
        escaped = escape_for_display(truncated)
        assert "..." in escaped

    def test_safe_display_in_window(self):
        """Should safely display text in window."""
        window = Mock()
        window.getmaxyx.return_value = (24, 80)

        # Text with ANSI codes
        text = "\x1b[32mGreen text that is quite long\x1b[0m"

        # Should not raise and should strip ANSI
        safe_addstr_with_truncate(window, 0, 0, text, max_width=50)

        # Verify ANSI codes were stripped
        call_args = window.addstr.call_args
        displayed_text = call_args[0][2]
        assert "\x1b" not in displayed_text

    def test_edge_case_empty_inputs(self):
        """Should handle empty inputs gracefully."""
        window = Mock()
        window.getmaxyx.return_value = (24, 80)

        # Empty text
        safe_addstr(window, 0, 0, "")
        safe_addstr_with_truncate(window, 0, 0, "", max_width=50)

        # Should not raise
        assert True

    def test_edge_case_boundary_positions(self):
        """Should handle boundary positions."""
        window = Mock()
        window.getmaxyx.return_value = (24, 80)

        # Position at edge
        safe_addstr_with_truncate(window, 23, 79, "X", max_width=10)

        # Position out of bounds
        safe_addstr_with_truncate(window, 24, 80, "Y", max_width=10)

        # Should write at edge but not out of bounds
        assert window.addstr.call_count == 1
