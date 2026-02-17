"""Terminal utilities module"""

import curses
import re
from typing import Optional


# ANSI escape sequences for colors that might cause issues
ANSI_ESCAPE_PATTERN = re.compile(r'\x1b\[[0-9;]*m')


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text"""
    return ANSI_ESCAPE_PATTERN.sub('', text)


def truncate(text: str, max_length: int, ellipsis: str = "...") -> str:
    """Truncate text to maximum length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(ellipsis)] + ellipsis


def escape_for_display(text: str, max_length: Optional[int] = None) -> str:
    """
    Escape text for safe display in terminal.
    Removes ANSI sequences and truncates to required length.
    """
    # First strip any ANSI sequences
    text = strip_ansi(text)

    # Then truncate if needed
    if max_length is not None:
        text = truncate(text, max_length)

    return text


def safe_addstr(
    window: curses.window,
    y: int,
    x: int,
    text: str,
    attr: int = 0,
    max_width: Optional[int] = None,
) -> None:
    """
    Safely write text to curses window with automatic escaping.
    """
    # Prepare the text
    safe_text = escape_for_display(text, max_width)

    try:
        window.addstr(y, x, safe_text, attr)
    except curses.error:
        pass  # Ignore errors at edge of screen


def safe_addstr_with_truncate(
    window: curses.window,
    y: int,
    x: int,
    text: str,
    max_width: int,
    attr: int = 0,
) -> None:
    """Write text with automatic truncation to screen width"""
    max_y, max_x = window.getmaxyx()

    # Ensure we don't go beyond screen bounds
    if y >= max_y or x >= max_x:
        return

    # Adjust width to fit
    available_width = max_x - x
    actual_width = min(max_width, available_width)

    safe_addstr(window, y, x, text, attr, actual_width)
