"""Tests for cli module."""

import pytest
import argparse
from unittest.mock import patch, Mock

from somafm_tui.cli import (
    create_parser,
    parse_args,
    validate_args,
    print_channels,
    print_favorites,
    print_themes,
)


class TestCreateParser:
    """Tests for create_parser function."""

    def test_returns_argument_parser(self):
        """Should return an ArgumentParser instance."""
        parser = create_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_has_program_name(self):
        """Should have correct program name."""
        parser = create_parser()
        assert parser.prog == "somafm-tui"

    def test_has_description(self):
        """Should have description."""
        parser = create_parser()
        assert parser.description is not None
        assert "Terminal user interface" in parser.description

    def test_has_play_argument(self):
        """Should have --play argument."""
        parser = create_parser()
        args = parser.parse_args(["--play", "dronezone"])
        assert args.play == "dronezone"

    def test_has_volume_argument(self):
        """Should have --volume argument."""
        parser = create_parser()
        args = parser.parse_args(["--volume", "50"])
        assert args.volume == 50

    def test_has_theme_argument(self):
        """Should have --theme argument."""
        parser = create_parser()
        args = parser.parse_args(["--theme", "monochrome"])
        assert args.theme == "monochrome"

    def test_has_list_themes_flag(self):
        """Should have --list-themes flag."""
        parser = create_parser()
        args = parser.parse_args(["--list-themes"])
        assert args.list_themes is True

    def test_has_list_channels_flag(self):
        """Should have --list-channels flag."""
        parser = create_parser()
        args = parser.parse_args(["--list-channels"])
        assert args.list_channels is True

    def test_has_search_argument(self):
        """Should have --search argument."""
        parser = create_parser()
        args = parser.parse_args(["--search", "beat"])
        assert args.search == "beat"

    def test_has_favorites_flag(self):
        """Should have --favorites flag."""
        parser = create_parser()
        args = parser.parse_args(["--favorites"])
        assert args.favorites is True

    def test_has_sleep_argument(self):
        """Should have --sleep argument."""
        parser = create_parser()
        args = parser.parse_args(["--sleep", "30"])
        assert args.sleep == 30

    def test_has_no_dbus_flag(self):
        """Should have --no-dbus flag."""
        parser = create_parser()
        args = parser.parse_args(["--no-dbus"])
        assert args.no_dbus is True

    def test_has_version_flag(self):
        """Should have --version flag."""
        parser = create_parser()
        
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])
        
        assert exc_info.value.code == 0

    def test_has_verbose_flag(self):
        """Should have --verbose flag."""
        parser = create_parser()
        args = parser.parse_args(["--verbose"])
        assert args.verbose is True

    def test_short_options(self):
        """Should support short option aliases."""
        parser = create_parser()
        
        args = parser.parse_args(["-p", "dronezone"])
        assert args.play == "dronezone"
        
        args = parser.parse_args(["-v", "75"])
        assert args.volume == 75
        
        args = parser.parse_args(["-t", "dark"])
        assert args.theme == "dark"
        
        args = parser.parse_args(["-l"])
        assert args.list_channels is True
        
        args = parser.parse_args(["-s", "beat"])
        assert args.search == "beat"
        
        args = parser.parse_args(["-f"])
        assert args.favorites is True


class TestParseArgs:
    """Tests for parse_args function."""

    def test_uses_sys_argv_by_default(self):
        """Should use sys.argv when args is None."""
        with patch('somafm_tui.cli.sys.argv', ['somafm-tui', '--play', 'test']):
            args = parse_args()
            assert args.play == "test"

    def test_accepts_custom_args(self):
        """Should accept custom args list."""
        args = parse_args(["--volume", "80"])
        assert args.volume == 80

    def test_returns_namespace(self):
        """Should return argparse.Namespace."""
        args = parse_args(["--play", "test"])
        assert isinstance(args, argparse.Namespace)


class TestValidateArgs:
    """Tests for validate_args function."""

    def test_valid_args(self):
        """Should return True for valid arguments."""
        args = argparse.Namespace(
            volume=None,
            sleep=None,
        )
        assert validate_args(args) is True

    def test_valid_volume_in_range(self):
        """Should accept volume in 0-100 range."""
        for volume in [0, 50, 100]:
            args = argparse.Namespace(volume=volume, sleep=None)
            assert validate_args(args) is True, f"Volume {volume} should be valid"

    def test_invalid_volume_negative(self, capsys):
        """Should reject negative volume."""
        args = argparse.Namespace(volume=-10, sleep=None)
        result = validate_args(args)
        
        assert result is False
        captured = capsys.readouterr()
        assert "Error" in captured.err

    def test_invalid_volume_over_100(self, capsys):
        """Should reject volume over 100."""
        args = argparse.Namespace(volume=150, sleep=None)
        result = validate_args(args)
        
        assert result is False
        captured = capsys.readouterr()
        assert "Error" in captured.err

    def test_valid_sleep_in_range(self):
        """Should accept sleep timer in 1-480 range."""
        for sleep in [1, 30, 480]:
            args = argparse.Namespace(volume=None, sleep=sleep)
            assert validate_args(args) is True, f"Sleep {sleep} should be valid"

    def test_invalid_sleep_zero(self, capsys):
        """Should reject sleep timer of 0."""
        args = argparse.Namespace(volume=None, sleep=0)
        result = validate_args(args)
        
        assert result is False
        captured = capsys.readouterr()
        assert "Error" in captured.err

    def test_invalid_sleep_negative(self, capsys):
        """Should reject negative sleep timer."""
        args = argparse.Namespace(volume=None, sleep=-10)
        result = validate_args(args)
        
        assert result is False
        captured = capsys.readouterr()
        assert "Error" in captured.err

    def test_invalid_sleep_over_480(self, capsys):
        """Should reject sleep timer over 480 minutes."""
        args = argparse.Namespace(volume=None, sleep=500)
        result = validate_args(args)
        
        assert result is False
        captured = capsys.readouterr()
        assert "Error" in captured.err

    def test_both_volume_and_sleep_valid(self):
        """Should validate both volume and sleep."""
        args = argparse.Namespace(volume=75, sleep=30)
        assert validate_args(args) is True


class TestPrintChannels:
    """Tests for print_channels function."""

    def test_prints_header(self, capsys):
        """Should print table header."""
        channels = []
        print_channels(channels)
        
        captured = capsys.readouterr()
        assert "ID" in captured.out
        assert "Title" in captured.out
        assert "Listeners" in captured.out
        assert "Bitrate" in captured.out

    def test_prints_channel_data(self, capsys):
        """Should print channel data."""
        # Create mock channel objects
        channel = Mock()
        channel.id = "dronezone"
        channel.title = "Drone Zone"
        channel.listeners = 1234
        channel.bitrate = "128k"
        
        print_channels([channel])
        
        captured = capsys.readouterr()
        assert "dronezone" in captured.out
        assert "Drone Zone" in captured.out
        assert "1234" in captured.out
        assert "128k" in captured.out

    def test_handles_zero_listeners(self, capsys):
        """Should handle zero listeners."""
        channel = Mock()
        channel.id = "test"
        channel.title = "Test"
        channel.listeners = 0
        channel.bitrate = "128k"
        
        print_channels([channel])
        
        captured = capsys.readouterr()
        # Should show N/A for zero listeners
        assert "N/A" in captured.out or "0" in captured.out

    def test_prints_total_count(self, capsys):
        """Should print total channel count."""
        channel1 = Mock()
        channel1.id = "test1"
        channel1.title = "Test 1"
        channel1.listeners = 100
        channel1.bitrate = "128k"
        
        channel2 = Mock()
        channel2.id = "test2"
        channel2.title = "Test 2"
        channel2.listeners = 200
        channel2.bitrate = "320k"
        
        print_channels([channel1, channel2])
        
        captured = capsys.readouterr()
        assert "Total:" in captured.out
        assert "2" in captured.out


class TestPrintFavorites:
    """Tests for print_favorites function."""

    def test_prints_no_favorites_message(self, capsys):
        """Should print message when no favorites."""
        print_favorites([], set())
        
        captured = capsys.readouterr()
        assert "No favorite channels" in captured.out

    def test_prints_favorite_channels(self, capsys):
        """Should print favorite channels."""
        channel = Mock()
        channel.id = "dronezone"
        channel.title = "Drone Zone"
        
        print_favorites([channel], {"dronezone"})
        
        captured = capsys.readouterr()
        assert "Drone Zone" in captured.out
        assert "dronezone" in captured.out

    def test_filters_non_favorites(self, capsys):
        """Should only print favorite channels."""
        channel1 = Mock()
        channel1.id = "fav"
        channel1.title = "Favorite"
        
        channel2 = Mock()
        channel2.id = "notfav"
        channel2.title = "Not Favorite"
        
        print_favorites([channel1, channel2], {"fav"})
        
        captured = capsys.readouterr()
        assert "Favorite" in captured.out
        assert "Not Favorite" not in captured.out


class TestPrintThemes:
    """Tests for print_themes function."""

    def test_prints_header(self, capsys):
        """Should print header."""
        print_themes({})
        
        captured = capsys.readouterr()
        assert "Available themes" in captured.out

    def test_prints_dark_themes_section(self, capsys):
        """Should print dark themes section."""
        themes = {
            "default": {"name": "Default", "is_light": False},
            "monochrome": {"name": "Monochrome", "is_light": False},
        }
        
        with patch('somafm_tui.themes.get_theme_names', return_value=["default", "monochrome"]):
            print_themes(themes)
        
        captured = capsys.readouterr()
        assert "Dark themes" in captured.out

    def test_prints_light_themes_section(self, capsys):
        """Should print light themes section."""
        themes = {
            "light": {"name": "Light", "is_light": True},
        }
        
        with patch('somafm_tui.themes.get_theme_names', return_value=["light"]):
            print_themes(themes)
        
        captured = capsys.readouterr()
        assert "Light themes" in captured.out
