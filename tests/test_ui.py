"""Tests for ui module."""

import pytest
from unittest.mock import Mock, patch, call
import curses

from somafm_tui.ui import (
    UIScreen,
    get_listener_icon,
    get_bitrate_icon,
    get_volume_icon,
    get_play_symbol,
    get_music_symbol,
    get_favorite_icon,
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
        """Should clear expired volume indicator."""
        screen = UIScreen()
        screen.volume_display = 75
        screen.volume_display_time = 0  # Expired
        mock_stdscr = Mock()
        mock_stdscr.getmaxyx.return_value = (24, 80)

        screen._handle_volume_display(mock_stdscr)

        assert screen.volume_display is None
