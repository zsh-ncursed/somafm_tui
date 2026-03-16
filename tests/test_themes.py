"""Tests for themes module."""

import pytest
from unittest.mock import patch, Mock, MagicMock

from somafm_tui.themes import (
    load_themes_raw,
    load_themes,
    get_theme_names,
    is_light_theme,
    get_color_themes,
    init_custom_colors,
    apply_theme,
    THEMES_FILE,
)


class TestLoadThemesRaw:
    """Tests for load_themes_raw function."""

    def test_loads_themes_from_json(self):
        """Should load themes from JSON file."""
        themes = load_themes_raw()
        
        assert isinstance(themes, dict)
        assert "default" in themes

    def test_theme_has_required_fields(self):
        """Each theme should have required fields."""
        themes = load_themes_raw()
        
        required_fields = [
            "name",
            "bg_color",
            "header",
            "selected",
            "info",
            "metadata",
            "instructions",
            "favorite",
            "is_light",
        ]
        
        for theme_id, theme_data in themes.items():
            for field in required_fields:
                assert field in theme_data, f"Theme {theme_id} missing {field}"

    def test_hex_colors_are_valid(self):
        """Hex colors should be valid format."""
        themes = load_themes_raw()
        
        import re
        hex_pattern = re.compile(r'^#[0-9a-fA-F]{6}$')
        
        for theme_id, theme_data in themes.items():
            bg_color = theme_data.get("bg_color", "")
            assert hex_pattern.match(bg_color), \
                f"Theme {theme_id} has invalid bg_color: {bg_color}"

    def test_returns_fallback_on_error(self):
        """Should return default theme on file read error."""
        with patch('somafm_tui.themes.open', side_effect=IOError("File not found")):
            themes = load_themes_raw()
            
            assert "default" in themes
            assert themes["default"]["name"] == "Default Dark"


class TestLoadThemes:
    """Tests for load_themes function."""

    def test_loads_themes_with_curses_ids(self, mock_curses):
        """Should load themes with curses color IDs."""
        with patch('somafm_tui.themes.curses', mock_curses):
            themes = load_themes()
            
            assert isinstance(themes, dict)
            assert "default" in themes

    def test_caches_result(self, mock_curses):
        """Should cache loaded themes."""
        with patch('somafm_tui.themes.curses', mock_curses):
            themes1 = load_themes()
            themes2 = load_themes()
            
            # Should return same object (cached)
            assert themes1 is themes2

    def test_returns_fallback_on_curses_error(self):
        """Should return fallback theme on curses initialization error."""
        mock_curses_error = Mock()
        mock_curses_error.error = Exception
        mock_curses_error.init_color = Mock(side_effect=Exception("Curses error"))
        mock_curses_error.COLOR_BLACK = 0
        mock_curses_error.COLOR_WHITE = 1
        mock_curses_error.COLOR_GREEN = 3
        
        with patch('somafm_tui.themes.curses', mock_curses_error):
            themes = load_themes()
            
            assert "default" in themes


class TestGetThemeNames:
    """Tests for get_theme_names function."""

    def test_returns_list(self):
        """Should return list of theme names."""
        names = get_theme_names()
        
        assert isinstance(names, list)
        assert len(names) > 0

    def test_sorted_dark_first(self):
        """Should sort themes: dark first, light last."""
        names = get_theme_names()
        themes = load_themes_raw()
        
        # Find first light theme index
        first_light_index = None
        for i, name in enumerate(names):
            if themes.get(name, {}).get("is_light", False):
                first_light_index = i
                break
        
        # If there are light themes, they should be at the end
        if first_light_index is not None:
            for i in range(first_light_index, len(names)):
                name = names[i]
                assert themes.get(name, {}).get("is_light", False) is True


class TestIsLightTheme:
    """Tests for is_light_theme function."""

    def test_detects_light_theme(self):
        """Should detect light themes."""
        themes = load_themes_raw()
        
        # Find a light theme if exists
        for theme_id, theme_data in themes.items():
            if theme_data.get("is_light", False):
                assert is_light_theme(theme_id) is True
                break

    def test_detects_dark_theme(self):
        """Should detect dark themes."""
        themes = load_themes_raw()
        
        # Find a dark theme
        for theme_id, theme_data in themes.items():
            if not theme_data.get("is_light", False):
                assert is_light_theme(theme_id) is False
                break

    def test_returns_false_for_unknown_theme(self):
        """Should return False for unknown theme."""
        result = is_light_theme("nonexistent_theme")
        assert result is False


class TestGetColorThemes:
    """Tests for get_color_themes function."""

    def test_returns_dict_with_color_ids(self, mock_curses):
        """Should return dict with color IDs."""
        with patch('somafm_tui.themes.curses', mock_curses):
            themes = get_color_themes()
            
            assert isinstance(themes, dict)
            assert "default" in themes

    def test_theme_has_name(self, mock_curses):
        """Each theme should have a name."""
        with patch('somafm_tui.themes.curses', mock_curses):
            themes = get_color_themes()
            
            for theme_id, theme_data in themes.items():
                assert "name" in theme_data


class TestApplyTheme:
    """Tests for apply_theme function."""

    def test_initializes_color_pairs(self, mock_curses):
        """Should initialize curses color pairs."""
        with patch('somafm_tui.themes.curses', mock_curses):
            apply_theme("default", mock_curses.COLOR_BLACK)
            
            # Should call init_pair for each color pair (1-6, 60, 61)
            assert mock_curses.init_pair.call_count >= 6

    def test_falls_back_to_default_for_unknown_theme(self, mock_curses):
        """Should use default theme for unknown theme name."""
        with patch('somafm_tui.themes.curses', mock_curses):
            apply_theme("nonexistent", mock_curses.COLOR_BLACK)
            
            # Should still initialize color pairs
            assert mock_curses.init_pair.call_count >= 6

    def test_handles_monochrome_theme(self, mock_curses):
        """Should handle monochrome theme specially."""
        with patch('somafm_tui.themes.curses', mock_curses):
            apply_theme("monochrome", mock_curses.COLOR_BLACK)
            
            # Should initialize color pairs
            assert mock_curses.init_pair.call_count >= 6


class TestInitCustomColors:
    """Tests for init_custom_colors function."""

    def test_loads_themes(self, mock_curses):
        """Should load themes."""
        with patch('somafm_tui.themes.curses', mock_curses):
            with patch('somafm_tui.themes.load_themes') as mock_load:
                init_custom_colors()
                
                mock_load.assert_called_once()
