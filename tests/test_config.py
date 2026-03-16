"""Tests for config module."""

import pytest
import os
from unittest.mock import patch, Mock

from somafm_tui.config import (
    DEFAULT_CONFIG,
    CONFIG_VALIDATORS,
    ALLOWED_THEMES,
    set_allowed_themes,
    get_default_config,
    ensure_config_dir,
    load_config,
    save_config,
    update_config,
    validate_config,
)


class TestGetDefaultConfig:
    """Tests for get_default_config function."""

    def test_returns_copy_not_reference(self):
        """Should return a copy, not the original dict."""
        config1 = get_default_config()
        config2 = get_default_config()
        
        config1["volume"] = 50
        assert config2["volume"] == 100, "Should return independent copies"

    def test_contains_all_required_keys(self):
        """Should contain all required configuration keys."""
        config = get_default_config()
        
        assert "theme" in config
        assert "dbus_allowed" in config
        assert "dbus_send_metadata" in config
        assert "dbus_send_metadata_artworks" in config
        assert "dbus_cache_metadata_artworks" in config
        assert "volume" in config

    def test_default_values(self):
        """Should have correct default values."""
        config = get_default_config()
        
        assert config["theme"] == "default"
        assert config["dbus_allowed"] is False
        assert config["dbus_send_metadata"] is False
        assert config["dbus_send_metadata_artworks"] is False
        assert config["dbus_cache_metadata_artworks"] is True
        assert config["volume"] == 100


class TestSetAllowedThemes:
    """Tests for set_allowed_themes function."""

    def test_sets_allowed_themes(self):
        """Should set the ALLOWED_THEMES global."""
        themes = {"default", "monochrome", "dark"}
        set_allowed_themes(themes)
        
        # Import the module to get updated global
        from somafm_tui import config
        assert config.ALLOWED_THEMES == themes

    def test_accepts_set(self):
        """Should accept a set of theme names."""
        themes = {"theme1", "theme2", "theme3"}
        set_allowed_themes(themes)
        
        from somafm_tui import config
        assert "theme1" in config.ALLOWED_THEMES
        assert "theme2" in config.ALLOWED_THEMES


class TestEnsureConfigDir:
    """Tests for ensure_config_dir function."""

    def test_creates_directory_if_not_exists(self, tmp_path):
        """Should create config directory if it doesn't exist."""
        with patch('somafm_tui.config.CONFIG_DIR', str(tmp_path / "new_dir")):
            ensure_config_dir()
            assert os.path.exists(tmp_path / "new_dir")

    def test_no_error_if_exists(self, tmp_path):
        """Should not raise error if directory already exists."""
        config_dir = tmp_path / "existing_dir"
        config_dir.mkdir()
        
        with patch('somafm_tui.config.CONFIG_DIR', str(config_dir)):
            # Should not raise
            ensure_config_dir()


class TestValidateConfig:
    """Tests for validate_config function."""

    def test_valid_config_unchanged(self):
        """Should keep valid config unchanged."""
        config = {
            "theme": "default",
            "volume": 75,
            "dbus_allowed": True,
        }
        
        result = validate_config(config)
        
        assert result["theme"] == "default"
        assert result["volume"] == 75
        assert result["dbus_allowed"] is True

    def test_missing_keys_get_defaults(self):
        """Should add missing keys with default values."""
        config = {"volume": 50}  # Missing other keys
        
        result = validate_config(config)
        
        assert result["theme"] == "default"
        assert result["dbus_allowed"] is False
        assert result["volume"] == 50

    def test_volume_clamped_to_range(self):
        """Should clamp volume to 0-100 range."""
        # Too low
        config = {"volume": -10}
        result = validate_config(config)
        assert result["volume"] == 0
        
        # Too high
        config = {"volume": 150}
        result = validate_config(config)
        assert result["volume"] == 100

    def test_volume_string_conversion(self):
        """Should convert string volume to int."""
        config = {"volume": "75"}
        result = validate_config(config)
        
        assert result["volume"] == 75
        assert isinstance(result["volume"], int)

    def test_boolean_string_conversion(self):
        """Should convert string booleans."""
        config = {
            "dbus_allowed": "true",
            "dbus_send_metadata": "TRUE",
            "dbus_cache_metadata_artworks": "1",
        }
        result = validate_config(config)
        
        assert result["dbus_allowed"] is True
        assert result["dbus_send_metadata"] is True
        assert result["dbus_cache_metadata_artworks"] is True

    def test_invalid_theme_uses_default(self):
        """Should use default theme for invalid theme name."""
        set_allowed_themes({"default", "monochrome"})
        config = {"theme": "invalid_theme"}
        
        result = validate_config(config)
        
        assert result["theme"] == "default"

    def test_valid_theme_accepted(self):
        """Should accept valid theme from whitelist."""
        set_allowed_themes({"default", "monochrome", "custom"})
        config = {"theme": "custom"}
        
        result = validate_config(config)
        
        assert result["theme"] == "custom"

    def test_unknown_key_skipped(self):
        """Should skip unknown configuration keys."""
        config = {
            "volume": 50,
            "unknown_key": "value",
            "another_unknown": 123,
        }
        
        result = validate_config(config)
        
        assert "unknown_key" not in result
        assert "another_unknown" not in result

    def test_invalid_type_uses_default(self):
        """Should use default value for invalid types."""
        config = {"volume": "not_a_number"}
        result = validate_config(config)
        
        assert result["volume"] == 100  # Default value

    def test_sanitizes_string_value(self):
        """Should sanitize string values (strip, limit length)."""
        long_theme = "a" * 200
        config = {"theme": long_theme}
        
        # First set allowed themes to include a short one
        set_allowed_themes({"default", "a" * 100})
        result = validate_config(config)
        
        # Should be truncated to 100 chars
        assert len(result["theme"]) <= 100


class TestUpdateConfig:
    """Tests for update_config function."""

    def test_updates_single_value(self, tmp_path):
        """Should update a single configuration value."""
        config_dir = tmp_path / ".somafm_tui"
        config_dir.mkdir()
        
        with patch('somafm_tui.config.CONFIG_DIR', str(config_dir)):
            with patch('somafm_tui.config.CONFIG_FILE', str(config_dir / "somafm.cfg")):
                result = update_config("volume", 80)
                
                assert result["volume"] == 80

    def test_saves_after_update(self, tmp_path):
        """Should save configuration after update."""
        config_dir = tmp_path / ".somafm_tui"
        config_dir.mkdir()
        config_file = config_dir / "somafm.cfg"
        
        with patch('somafm_tui.config.CONFIG_DIR', str(config_dir)):
            with patch('somafm_tui.config.CONFIG_FILE', str(config_file)):
                update_config("volume", 80)
                
                assert config_file.exists()


class TestLoadAndSaveConfig:
    """Tests for load_config and save_config functions."""

    def test_load_creates_default_if_missing(self, tmp_path):
        """Should create default config if file doesn't exist."""
        config_dir = tmp_path / ".somafm_tui"
        config_dir.mkdir()
        config_file = config_dir / "somafm.cfg"
        
        with patch('somafm_tui.config.CONFIG_DIR', str(config_dir)):
            with patch('somafm_tui.config.CONFIG_FILE', str(config_file)):
                config = load_config()
                
                assert config == get_default_config()
                assert config_file.exists()

    def test_load_reads_existing_config(self, temp_config_file):
        """Should read values from existing config file."""
        with patch('somafm_tui.config.CONFIG_FILE', temp_config_file):
            config = load_config()
            
            assert config["theme"] == "monochrome"
            assert config["volume"] == 50
            assert config["dbus_allowed"] is True

    def test_save_writes_config_file(self, tmp_path):
        """Should write configuration to file."""
        config_dir = tmp_path / ".somafm_tui"
        config_dir.mkdir()
        config_file = config_dir / "somafm.cfg"
        
        with patch('somafm_tui.config.CONFIG_DIR', str(config_dir)):
            with patch('somafm_tui.config.CONFIG_FILE', str(config_file)):
                config = {"volume": 60, "theme": "default"}
                save_config(config)
                
                assert config_file.exists()
                content = config_file.read_text()
                assert "volume" in content
                assert "60" in content
