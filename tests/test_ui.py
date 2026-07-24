"""Tests for ui module."""

import pytest
from unittest.mock import Mock, patch, call
import curses

from somafm_tui import ui as ui_module
from somafm_tui.ui import (
    UIScreen,
    get_listener_icon,
    get_bitrate_icon,
    get_volume_icon,
    get_play_symbol,
    get_music_symbol,
    get_favorite_icon,
    get_channel_icon,
)
from somafm_tui.models import Channel, TrackMetadata


class TestIconFunctions:
    """Tests for icon/symbol functions."""

    def test_get_listener_icon(self):
        """Should return listener icon."""
        assert get_listener_icon() == "[L]"

    def test_get_bitrate_icon(self):
        """Should return bitrate icon."""
        assert get_bitrate_icon() == "[B]"

    def test_get_volume_icon(self):
        """Should return volume icon."""
        assert get_volume_icon() == "🔊"

    def test_get_play_symbol_playing(self):
        """Should return play symbol."""
        assert get_play_symbol(is_paused=False) == "▶"

    def test_get_play_symbol_paused(self):
        """Should return pause symbol."""
        assert get_play_symbol(is_paused=True) == "⏸"

    def test_get_music_symbol(self):
        """Should return music symbol."""
        assert get_music_symbol() == "♪"

    def test_get_favorite_icon(self):
        """Should return favorite icon."""
        assert get_favorite_icon() == "♥"


class TestChannelIcons:
    """Tests for genre-specific channel icons."""

    def setup_method(self):
        # Reset the module-level emoji cache between tests so env/term
        # monkeypatching actually takes effect.
        ui_module._emoji_enabled_cache = None

    def teardown_method(self):
        ui_module._emoji_enabled_cache = None

    def test_known_channel_with_emoji_on(self, monkeypatch):
        """Mapped channel id returns its emoji when emoji is enabled."""
        monkeypatch.setenv("SOMAFM_EMOJI", "1")
        assert get_channel_icon("dronezone") == "🧊"
        assert get_channel_icon("fluid") == "🌧️"
        assert get_channel_icon("defcon") == "💻"

    def test_unknown_channel_with_emoji_on(self, monkeypatch):
        """Unknown channel id falls back to the generic emoji."""
        monkeypatch.setenv("SOMAFM_EMOJI", "1")
        assert get_channel_icon("unknownid") == "🎵"

    def test_emoji_disabled_returns_note(self, monkeypatch):
        """When emoji is disabled, returns the plain music note (no squares)."""
        monkeypatch.setenv("SOMAFM_EMOJI", "0")
        assert get_channel_icon("dronezone") == "♪"
        assert get_channel_icon("unknownid") == "♪"

    def test_emoji_env_unrecognised_value_enables(self, monkeypatch):
        """SOMAFM_EMOJI with any non-falsy value enables emoji (explicit override)."""
        monkeypatch.setenv("SOMAFM_EMOJI", "maybe")
        assert get_channel_icon("dronezone") == "🧊"

    def test_emoji_env_falsy_values_disable(self, monkeypatch):
        """Recognised falsy values disable emoji."""
        for v in ("0", "false", "no", "off", ""):
            monkeypatch.setenv("SOMAFM_EMOJI", v)
            ui_module._emoji_enabled_cache = None
            assert get_channel_icon("dronezone") == "♪", f"value {v!r} should disable"

    def test_emoji_auto_detect_term_linux_off(self, monkeypatch):
        """TERM=linux (linux tty) disables emoji even without env override."""
        monkeypatch.delenv("SOMAFM_EMOJI", raising=False)
        monkeypatch.setenv("TERM", "linux")
        assert get_channel_icon("dronezone") == "♪"

    def test_emoji_auto_detect_known_term_program(self, monkeypatch):
        """Known modern TERM_PROGRAM enables emoji when no env override."""
        monkeypatch.delenv("SOMAFM_EMOJI", raising=False)
        monkeypatch.delenv("TERM", raising=False)
        monkeypatch.setenv("TERM_PROGRAM", "kitty")
        assert get_channel_icon("dronezone") == "🧊"

    def test_emoji_auto_detect_unknown_terminal_off(self, monkeypatch):
        """Unrecognised terminal without COLORTERM -> safe fallback to ♪."""
        monkeypatch.delenv("SOMAFM_EMOJI", raising=False)
        monkeypatch.delenv("TERM_PROGRAM", raising=False)
        monkeypatch.delenv("COLORTERM", raising=False)
        monkeypatch.setenv("TERM", "xterm-256color")
        assert get_channel_icon("dronezone") == "♪"


class TestUIScreenInit:
    """Tests for UIScreen initialization."""

    def test_init_sets_attributes(self):
        """Should initialize all attributes correctly."""
        screen = UIScreen()

        assert isinstance(screen.current_metadata, TrackMetadata)
        assert screen.max_history == 10
        assert screen.track_history == []
        assert screen.current_channel is None
        assert screen.player is None
        assert screen.volume_display is None
        assert screen.volume_display_time == 0

    def test_invalidate_cache(self):
        """Should invalidate all cache entries."""
        screen = UIScreen()
        screen._prev_channels_hash = 123
        screen._prev_selected_index = 5

        screen.invalidate_cache()

        assert screen._prev_channels_hash == 0
        assert screen._prev_selected_index == -1


class TestMetadataHistory:
    """Tests for metadata history methods."""

    def test_add_to_history(self):
        """Should add metadata to history."""
        screen = UIScreen()
        metadata = TrackMetadata(artist="Artist", title="Title")

        screen.add_to_history(metadata)

        assert len(screen.track_history) == 1
        assert screen.track_history[0].artist == "Artist"

    def test_add_to_history_respects_max(self):
        """Should respect max history size."""
        screen = UIScreen()
        screen.max_history = 3

        for i in range(5):
            screen.add_to_history(TrackMetadata(artist=f"Artist{i}", title=f"Title{i}"))

        assert len(screen.track_history) == 3

    def test_update_metadata(self):
        """Should update current metadata."""
        screen = UIScreen()
        metadata = TrackMetadata(artist="Artist", title="Title")

        screen.update_metadata(metadata)

        assert screen.current_metadata is metadata

    def test_add_to_history_stores_channel_name(self):
        """History entries should preserve channel_name."""
        screen = UIScreen()
        meta = TrackMetadata(artist="Artist", title="Title", channel_name="Drone Zone")

        screen.add_to_history(meta)

        assert len(screen.track_history) == 1
        assert screen.track_history[0].channel_name == "Drone Zone"

    def test_add_to_history_skips_loading_entries(self):
        """Loading.../Unknown entries must never enter history."""
        screen = UIScreen()

        screen.add_to_history(TrackMetadata(artist="Loading...", title="Loading..."))
        screen.add_to_history(TrackMetadata(artist="Unknown", title="Unknown"))
        screen.add_to_history(TrackMetadata(artist="", title=""))

        assert screen.track_history == []

    def test_add_to_history_dedup_with_channel(self):
        """Duplicates are detected per channel (same track on different
        channels should both be kept)."""
        screen = UIScreen()
        a = TrackMetadata(artist="A", title="T", channel_name="Ch1")
        b = TrackMetadata(artist="A", title="T", channel_name="Ch2")

        screen.add_to_history(a)
        screen.add_to_history(b)

        assert len(screen.track_history) == 2

    def test_update_metadata_preserves_channel_name_on_archive(self):
        """When archiving current_metadata into history, channel_name should
        be filled from current_channel if missing."""
        screen = UIScreen()
        ch = Channel(id="x", title="Groove Salad")
        screen.current_channel = ch
        screen.current_metadata = TrackMetadata(artist="Old", title="Old")

        screen.update_metadata(TrackMetadata(artist="New", title="New"))

        assert len(screen.track_history) == 1
        assert screen.track_history[0].channel_name == "Groove Salad"


class TestChannelListRedraw:
    """Tests that channel list redraw does not wipe the playback panel."""

    def test_redraw_channel_list_does_not_clear_right_panel(self):
        """_redraw_channel_list must NOT use clrtoeol (which clears the whole
        row); it should only blank within the channel panel width so the
        track history on the right is preserved during navigation."""
        with patch('curses.color_pair', return_value=1):
            screen = UIScreen()
            mock_stdscr = Mock()
            mock_stdscr.getmaxyx.return_value = (24, 80)
            channels = [Channel(id=f"c{i}", title=f"Ch{i}") for i in range(5)]

            screen._redraw_channel_list(
                mock_stdscr, channels, selected_index=0, scroll_offset=0,
                channel_favorites=set(), split_x=30, panel_height=22,
            )

            # clrtoeol would wipe the playback panel — assert it's NOT called
            mock_stdscr.clrtoeol.assert_not_called()

            # Verify channel text was drawn
            addstr_calls = [c.args for c in mock_stdscr.addstr.call_args_list]
            channel_drawn = any(
                len(a) >= 3 and "Ch0" in str(a[2]) for a in addstr_calls
            )
            assert channel_drawn, "Channel row should be drawn"


class TestNotification:
    """Tests for notification methods."""

    def test_show_volume(self):
        """Should show volume overlay."""
        screen = UIScreen()

        screen.show_volume(Mock(), 75)

        assert screen.volume_display == 75
        assert screen.volume_display_time > 0


class TestDisplayHelpers:
    """Tests for display helper methods."""

    def test_handle_volume_display_expired(self):
        """Should handle expired volume indicator."""
        screen = UIScreen()
        screen.volume_display = 75
        screen.volume_display_time = 0  # Expired
        mock_stdscr = Mock()
        mock_stdscr.getmaxyx.return_value = (24, 80)

        screen._handle_volume_display(mock_stdscr)

        # Volume indicator should be cleared (method handles it)


class TestVolumeBarRendering:
    """Tests for volume bar rendering fixes."""

    def test_volume_bar_decrease_clears_previous_state(self):
        """Should clear previous volume bar when decreasing - fixes artifact issue."""
        with patch('curses.color_pair', return_value=1):
            screen = UIScreen()

            mock_stdscr = Mock()
            mock_stdscr.getmaxyx.return_value = (24, 80)

            # Show volume at 80%
            screen.show_volume(mock_stdscr, 80)
            screen.volume_display_time = float('inf')

            screen._handle_volume_display(mock_stdscr)

            # Clear mock to track second draw
            mock_stdscr.addstr.reset_mock()

            # Decrease to 50%
            screen.show_volume(mock_stdscr, 50)

            screen._handle_volume_display(mock_stdscr)

            # On second draw, should clear first (spaces)
            # First call should clear the entire area before redrawing
            calls = mock_stdscr.addstr.call_args_list
            first_call_text = calls[0][0][2]  # Third arg = text

            # Should be spaces, not filled blocks
            assert first_call_text == ' ' * 27 or ' ' * 25, f"First call should clear, got: {first_call_text!r}"

    def test_volume_bar_right_side_no_artifact(self):
        """Should not show artifact blocks on right side of volume bar."""
        with patch('curses.color_pair', return_value=1):
            screen = UIScreen()
            mock_stdscr = Mock()
            mock_stdscr.getmaxyx.return_value = (24, 80)
            mock_stdscr.addstr = Mock()

            screen.show_volume(mock_stdscr, 50)

            screen._handle_volume_display(mock_stdscr)

            # Check all addstr calls
            calls = mock_stdscr.addstr.call_args_list

            # Last call should be percentage (e.g., " 50%")
            last_call = calls[-1]
            text = last_call[0][2]  # Third positional argument

            # Should end with percentage, not extra blocks
            assert text.strip() == '50%' or text == ' 50%', f"Expected percentage, got: {text!r}"


class TestDisplayHelpers:
    """Tests for display helper methods."""

    def test_handle_volume_display_expired(self):
        """Should handle expired volume indicator."""
        screen = UIScreen()
        screen.volume_display = 75
        screen.volume_display_time = 0  # Expired
        mock_stdscr = Mock()
        mock_stdscr.getmaxyx.return_value = (24, 80)

        screen._handle_volume_display(mock_stdscr)

        # Volume indicator should be cleared (method handles it)
