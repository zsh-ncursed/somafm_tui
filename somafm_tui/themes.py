"""Color themes module"""

import curses
import json
import logging
import os
from typing import Dict, Any, Optional, List

from .constants import MAX_CURSES_COLOR_ID, MIN_CURSES_COLOR_ID

# Path to themes JSON
THEMES_FILE = os.path.join(os.path.dirname(__file__), "themes.json")

# Curses color IDs (these must be initialized before use)
# We'll map custom colors to IDs 10-174
_color_id_counter = MIN_CURSES_COLOR_ID
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
    if _color_id_counter > MAX_CURSES_COLOR_ID:
        # Reuse gray as fallback
        return 8

    color_id = _color_id_counter
    _color_map[hex_color] = color_id
    _color_id_counter += 1

    # Initialize the color
    rgb = _hex_to_curses_color(hex_color)
    curses.init_color(color_id, *rgb)

    return color_id


def _update_color(hex_color: str) -> int:
    """Update or create a curses color ID for a hex color.
    
    Unlike _get_color_id, this function updates the color even if it already exists.
    This is useful for theme changes without restarting the application.
    
    Returns:
        Color ID for the hex color
    """
    global _color_id_counter, _color_map

    # Convert hex to RGB
    rgb = _hex_to_curses_color(hex_color)

    if hex_color in _color_map:
        # Update existing color
        color_id = _color_map[hex_color]
        try:
            curses.init_color(color_id, *rgb)
            logging.debug(f"Updated color {color_id} to {hex_color} (RGB: {rgb})")
        except curses.error as e:
            logging.warning(f"Color update failed for {hex_color}: {e}")
        return color_id

    # Create new color (same as _get_color_id)
    if _color_id_counter > MAX_CURSES_COLOR_ID:
        return 8

    color_id = _color_id_counter
    _color_map[hex_color] = color_id
    _color_id_counter += 1

    curses.init_color(color_id, *rgb)
    logging.debug(f"Created new color {color_id} for {hex_color} (RGB: {rgb})")
    return color_id


def load_themes_raw() -> Dict[str, Dict[str, Any]]:
    """Load themes from JSON file without curses color initialization.
    
    This is useful for CLI commands that run outside curses environment.
    Returns themes with hex colors instead of color IDs.
    """
    try:
        with open(THEMES_FILE, "r") as f:
            raw_themes = json.load(f)
        
        # Return raw theme data without curses color IDs
        themes = {}
        for theme_id, theme_data in raw_themes.items():
            themes[theme_id] = {
                "name": theme_data.get("name", theme_id),
                "bg_color": theme_data.get("bg_color", "#000000"),
                "header": theme_data.get("header", "#ffffff"),
                "selected": theme_data.get("selected", "#ffffff"),
                "info": theme_data.get("info", "#ffffff"),
                "metadata": theme_data.get("metadata", "#ffffff"),
                "instructions": theme_data.get("instructions", "#ffffff"),
                "favorite": theme_data.get("favorite", "#ffffff"),
                "is_light": theme_data.get("is_light", False),
            }
        return themes

    except (json.JSONDecodeError, IOError, OSError) as e:
        logging.error(f"Failed to load themes: {e}")
        # Return minimal default theme
        return {
            "default": {
                "name": "Default Dark",
                "bg_color": "#000000",
                "header": "#00ffff",
                "selected": "#00ff00",
                "info": "#ffff00",
                "metadata": "#ff00ff",
                "instructions": "#0000ff",
                "favorite": "#ff0000",
                "is_light": False,
            }
        }


def load_themes() -> Dict[str, Dict[str, Any]]:
    """Load themes from JSON file with curses color initialization.
    
    Uses cache for performance. Call reload_themes() to force reload from file.
    """
    global _theme_cache

    if _theme_cache is not None:
        return _theme_cache

    try:
        raw_themes = load_themes_raw()

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

    except (json.JSONDecodeError, IOError, OSError) as e:
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
    except curses.error as e:
        logging.error(f"Curses color initialization failed: {e}")
        # Return minimal default theme with standard curses colors
        _theme_cache = {
            "default": {
                "name": "Default Dark",
                "bg_color": curses.COLOR_BLACK,
                "header": curses.COLOR_WHITE,
                "selected": curses.COLOR_GREEN,
                "info": curses.COLOR_YELLOW,
                "metadata": curses.COLOR_MAGENTA,
                "instructions": curses.COLOR_BLUE,
                "favorite": curses.COLOR_RED,
                "is_light": False,
            }
        }
        return _theme_cache


def reload_themes() -> Dict[str, Dict[str, Any]]:
    """Reload themes from JSON file, updating colors.
    
    This function clears the cache and reloads themes from the file.
    It also updates existing colors using curses.init_color().
    Call this function after modifying themes.json to apply changes.
    
    Returns:
        Dictionary of themes with updated color IDs
    """
    global _theme_cache

    logging.info("Reloading themes from file")
    
    # Clear cache to force reload
    _theme_cache = None
    
    # Note: We don't reset _color_map and _color_id_counter to preserve
    # existing color IDs. Instead, we use _update_color() to update them.
    
    try:
        raw_themes = load_themes_raw()
        logging.info(f"Loaded {len(raw_themes)} themes from {THEMES_FILE}")

        # Convert hex colors to curses color IDs (updating existing colors)
        themes = {}
        for theme_id, theme_data in raw_themes.items():
            theme = {
                "name": theme_data.get("name", theme_id),
                "bg_color": _update_color(theme_data.get("bg_color", "#000000")),
                "header": _update_color(theme_data.get("header", "#ffffff")),
                "selected": _update_color(theme_data.get("selected", "#ffffff")),
                "info": _update_color(theme_data.get("info", "#ffffff")),
                "metadata": _update_color(theme_data.get("metadata", "#ffffff")),
                "instructions": _update_color(theme_data.get("instructions", "#ffffff")),
                "favorite": _update_color(theme_data.get("favorite", "#ffffff")),
                "is_light": theme_data.get("is_light", False),
            }
            themes[theme_id] = theme

        _theme_cache = themes
        logging.info("Themes reloaded successfully")
        return themes

    except (json.JSONDecodeError, IOError, OSError) as e:
        logging.error(f"Failed to reload themes: {e}")
        # Return cached themes or default
        if _theme_cache:
            return _theme_cache
        return {
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


def reset_theme_cache() -> None:
    """Reset all theme and color caches.
    
    This function clears both the theme cache and the color map.
    Useful for testing or when you want to completely reinitialize themes.
    Note: This should only be called outside of curses environment or
    when you plan to reinitialize all colors.
    """
    global _theme_cache, _color_map, _color_id_counter
    _theme_cache = None
    _color_map = {}
    _color_id_counter = 10


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


def get_theme_names() -> List[str]:
    """Returns list of all theme names, sorted: dark themes first, light themes last"""
    # Use load_themes_raw() to work without curses initialization
    themes = load_themes_raw()
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


def apply_theme(theme_name: str, bg_color: Any = None) -> None:
    """Apply color theme.
    
    This function now reloads themes from the JSON file to pick up any changes.
    
    Args:
        theme_name: Name of the theme to apply
        bg_color: Optional background color (int or None). 
                  If None, will use the theme's bg_color from file.
    """
    # Reload themes from file to pick up any changes
    themes = reload_themes()

    if theme_name not in themes:
        theme_name = "default"

    theme = themes[theme_name]

    # Use provided bg_color or theme's bg_color
    # If bg_color is provided as int (from old cache), we need to get hex from raw themes
    if bg_color is None:
        # Get bg_color from reloaded themes
        effective_bg_color = theme["bg_color"]
    else:
        # bg_color was provided - use it (for backward compatibility)
        effective_bg_color = bg_color

    # Determine if this is a light theme
    is_light = theme.get("is_light", False)

    # Initialize color pairs based on theme
    curses.init_pair(1, theme["header"], effective_bg_color)  # Header
    curses.init_pair(2, theme["selected"], effective_bg_color)  # Selected channel
    curses.init_pair(3, theme["info"], effective_bg_color)  # Channel info
    curses.init_pair(4, theme["metadata"], effective_bg_color)  # Track metadata
    curses.init_pair(5, theme["instructions"], effective_bg_color)  # Instructions
    curses.init_pair(6, theme["favorite"], effective_bg_color)  # Favorite icon

    # Volume indicator colors
    if is_light:
        curses.init_pair(60, 128, effective_bg_color)  # Volume bar - dark gray
        curses.init_pair(61, 128, effective_bg_color)  # Speaker icon - dark gray
    else:
        # Orange/yellow for dark themes
        curses.init_pair(60, 208, effective_bg_color)  # Volume bar - orange
        curses.init_pair(61, 220, effective_bg_color)  # Speaker icon - yellow

    # Special handling for monochrome themes
    if theme_name in ("monochrome", "monochrome-dark"):
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)  # Selected channel
