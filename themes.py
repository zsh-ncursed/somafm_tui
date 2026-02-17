"""Color themes module"""

import curses
import json
import logging
import os
from typing import Dict, Any, Optional

# Path to themes JSON
THEMES_FILE = os.path.join(os.path.dirname(__file__), "themes.json")

# Curses color IDs (these must be initialized before use)
# We'll map custom colors to IDs 10-174
_color_id_counter = 10
_color_map: Dict[str, int] = {}
_theme_cache: Optional[Dict[str, Dict[str, Any]]] = None


def _hex_to_curses_color(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple (0-1000)"""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    # Convert to 0-1000 scale
    return (r * 1000 // 255, g * 1000 // 255, b * 1000 // 255)


def _get_color_id(hex_color: str) -> int:
    """Get or create a curses color ID for a hex color"""
    global _color_id_counter, _color_map

    if hex_color in _color_map:
        return _color_map[hex_color]

    # Create new color
    if _color_id_counter > 254:
        # Reuse gray as fallback
        return 8

    color_id = _color_id_counter
    _color_map[hex_color] = color_id
    _color_id_counter += 1

    # Initialize the color
    rgb = _hex_to_curses_color(hex_color)
    curses.init_color(color_id, *rgb)

    return color_id


def load_themes() -> Dict[str, Dict[str, Any]]:
    """Load themes from JSON file"""
    global _theme_cache

    if _theme_cache is not None:
        return _theme_cache

    try:
        with open(THEMES_FILE, "r") as f:
            raw_themes = json.load(f)

        # Convert hex colors to curses color IDs
        themes = {}
        for theme_id, theme_data in raw_themes.items():
            theme = {
                "name": theme_data.get("name", theme_id),
                "bg_color": _get_color_id(theme_data.get("bg_color", "#000000")),
                "header": _get_color_id(theme_data.get("header", "#ffffff")),
                "selected": _get_color_id(theme_data.get("selected", "#ffffff")),
                "info": _get_color_id(theme_data.get("info", "#ffffff")),
                "metadata": _get_color_id(theme_data.get("metadata", "#ffffff")),
                "instructions": _get_color_id(theme_data.get("instructions", "#ffffff")),
                "favorite": _get_color_id(theme_data.get("favorite", "#ffffff")),
                "is_light": theme_data.get("is_light", False),
            }
            themes[theme_id] = theme

        _theme_cache = themes
        return themes

    except Exception as e:
        logging.error(f"Failed to load themes: {e}")
        # Return minimal default theme
        _theme_cache = {
            "default": {
                "name": "Default Dark",
                "bg_color": curses.COLOR_BLACK,
                "header": curses.COLOR_CYAN,
                "selected": curses.COLOR_GREEN,
                "info": curses.COLOR_YELLOW,
                "metadata": curses.COLOR_MAGENTA,
                "instructions": curses.COLOR_BLUE,
                "favorite": curses.COLOR_RED,
                "is_light": False,
            }
        }
        return _theme_cache


def get_color_themes() -> Dict[str, Dict[str, int]]:
    """Returns dictionary of available color themes (for compatibility)"""
    themes = load_themes()
    # Return dict with color IDs as integers
    return {
        theme_id: {
            "name": theme["name"],
            "bg_color": theme["bg_color"],
            "header": theme["header"],
            "selected": theme["selected"],
            "info": theme["info"],
            "metadata": theme["metadata"],
            "instructions": theme["instructions"],
            "favorite": theme["favorite"],
        }
        for theme_id, theme in themes.items()
    }


def get_theme_names() -> list:
    """Returns list of all theme names, sorted: dark themes first, light themes last"""
    themes = load_themes()
    # Sort: dark themes (is_light=False) first, then light themes (is_light=True)
    return sorted(themes.keys(), key=lambda t: themes[t].get("is_light", False))


def is_light_theme(theme_name: str) -> bool:
    """Check if theme is light"""
    themes = load_themes()
    return themes.get(theme_name, {}).get("is_light", False)


def init_custom_colors() -> None:
    """Initialize custom colors for themes"""
    # Load themes to initialize colors
    load_themes()


def init_color_pairs(bg_color: int) -> None:
    """Initialize color pairs for current theme (legacy function)"""
    pass  # Now handled in apply_theme


def apply_theme(theme_name: str, bg_color: int) -> None:
    """Apply color theme"""
    themes = load_themes()

    if theme_name not in themes:
        theme_name = "default"

    theme = themes[theme_name]

    # Determine if this is a light theme
    is_light = theme.get("is_light", False)

    # Initialize color pairs based on theme
    curses.init_pair(1, theme["header"], bg_color)  # Header
    curses.init_pair(2, theme["selected"], bg_color)  # Selected channel
    curses.init_pair(3, theme["info"], bg_color)  # Channel info
    curses.init_pair(4, theme["metadata"], bg_color)  # Track metadata
    curses.init_pair(5, theme["instructions"], bg_color)  # Instructions
    curses.init_pair(6, theme["favorite"], bg_color)  # Favorite icon

    # Volume indicator colors
    if is_light:
        curses.init_pair(60, 128, bg_color)  # Volume bar - dark gray
        curses.init_pair(61, 128, bg_color)  # Speaker icon - dark gray
    else:
        # Orange/yellow for dark themes
        curses.init_pair(60, 208, bg_color)  # Volume bar - orange
        curses.init_pair(61, 220, bg_color)  # Speaker icon - yellow

    # Special handling for monochrome themes
    if theme_name in ("monochrome", "monochrome-dark"):
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)  # Selected channel
