"""Tests for channels module."""

import pytest
from unittest.mock import Mock, patch, call, mock_open
import json
import time
import os
from concurrent.futures import Future

from somafm_tui.channels import (
    fetch_channels,
    fetch_channels_async,
    load_channel_usage,
    save_channel_usage,
    clean_channel_usage,
    sort_channels_by_usage,
    get_valid_channel_ids,
    filter_channels_by_query,
    load_favorites,
    save_favorites,
    toggle_favorite,
    update_channel_usage,
    FavoriteTrack,
    load_favorite_tracks,
    save_favorite_tracks,
    add_favorite_track,
    is_track_favorite,
    API_URL,
    DEFAULT_TIMEOUT,
    CACHE_MAX_AGE,
)
from somafm_tui.models import Channel


class TestFetchChannels:
    """Tests for fetch_channels function."""

    def test_fetch_channels_uses_cache_when_valid(self):
        """Should use cached channels when cache is valid."""
        cache_data = {
            "channels": [
                {"id": "test", "title": "Test Channel", "playlists": []}
            ]
        }

        with patch('os.path.exists', return_value=True), \
             patch('os.path.getmtime', return_value=time.time() - 100), \
             patch('builtins.open', mock_open(read_data=json.dumps(cache_data))):

            channels = fetch_channels(cache_file="/tmp/cache.json")

            assert len(channels) == 1
            assert channels[0].id == "test"

    def test_fetch_channels_fetches_from_api_when_no_cache(self):
        """Should fetch from API when no cache."""
        api_data = {
            "channels": [
                {"id": "test", "title": "Test Channel", "playlists": []}
            ]
        }

        with patch('os.path.exists', return_value=False), \
             patch('somafm_tui.channels.fetch_json') as mock_fetch:
            mock_fetch.return_value = api_data

            channels = fetch_channels()

            mock_fetch.assert_called_once_with(API_URL, timeout=DEFAULT_TIMEOUT)
            assert len(channels) == 1

    def test_fetch_channels_fetches_from_api_when_cache_expired(self):
        """Should fetch from API when cache is expired."""
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getmtime', return_value=time.time() - 7200), \
             patch('somafm_tui.channels.fetch_json') as mock_fetch:
            mock_fetch.return_value = {"channels": []}

            fetch_channels(cache_file="/tmp/cache.json")

            mock_fetch.assert_called_once()

    def test_fetch_channels_saves_cache(self):
        """Should save fetched channels to cache."""
        api_data = {"channels": [{"id": "test", "title": "Test", "playlists": []}]}

        with patch('os.path.exists', return_value=False), \
             patch('somafm_tui.channels.fetch_json', return_value=api_data), \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.makedirs') as mock_makedirs:

            fetch_channels(cache_file="/tmp/cache/channels.json")

            mock_makedirs.assert_called_once()
            mock_file.assert_called()

    def test_fetch_channels_handles_json_error(self):
        """Should handle JSON decode error in cache."""
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getmtime', return_value=time.time() - 100), \
             patch('builtins.open', mock_open(read_data="invalid json")), \
             patch('somafm_tui.channels.fetch_json') as mock_fetch:
            mock_fetch.return_value = {"channels": []}

            channels = fetch_channels(cache_file="/tmp/cache.json")

            assert channels == []

    def test_fetch_channels_handles_io_error(self):
        """Should handle IO error reading cache."""
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getmtime', return_value=time.time() - 100), \
             patch('builtins.open', side_effect=IOError("File error")), \
             patch('somafm_tui.channels.fetch_json') as mock_fetch:
            mock_fetch.return_value = {"channels": []}

            channels = fetch_channels(cache_file="/tmp/cache.json")

            assert channels == []

    def test_fetch_channels_uses_stale_cache_on_network_error(self):
        """Should use stale cache when network fails."""
        cache_data = {"channels": [{"id": "test", "title": "Test", "playlists": [{"format": "mp3", "url": "http://test.com/stream.pls"}]}]}

        with patch('os.path.exists', side_effect=[True, True]), \
             patch('os.path.getmtime', return_value=time.time() - 7200), \
             patch('somafm_tui.channels.fetch_json', return_value=None), \
             patch('builtins.open', mock_open(read_data=json.dumps(cache_data))):

            channels = fetch_channels(cache_file="/tmp/cache.json")

            assert len(channels) == 1

    def test_fetch_channels_raises_on_network_error_no_cache(self):
        """Should raise ConnectionError when network fails and no cache."""
        with patch('os.path.exists', return_value=False), \
             patch('somafm_tui.channels.fetch_json', return_value=None):

            with pytest.raises(ConnectionError):
                fetch_channels()

    def test_fetch_channels_handles_cache_write_error(self):
        """Should handle error writing cache."""
        api_data = {"channels": []}

        with patch('os.path.exists', return_value=False), \
             patch('somafm_tui.channels.fetch_json', return_value=api_data), \
             patch('os.makedirs'), \
             patch('builtins.open', side_effect=IOError("Write error")):

            # Should not raise
            channels = fetch_channels(cache_file="/tmp/cache.json")
            assert channels == []


class TestFetchChannelsAsync:
    """Tests for fetch_channels_async function."""

    def test_fetch_channels_async_returns_future(self):
        """Should return Future object."""
        with patch('somafm_tui.channels.fetch_channels') as mock_fetch:
            mock_fetch.return_value = []

            future = fetch_channels_async()

            assert isinstance(future, Future)

    def test_fetch_channels_async_calls_callback_on_success(self):
        """Should call callback with channels on success."""
        callback = Mock()
        channels = [Channel(id="test", title="Test")]

        with patch('somafm_tui.channels.fetch_channels', return_value=channels):
            future = fetch_channels_async(callback=callback)
            future.result()  # Wait for completion

            callback.assert_called_once_with(channels)

    def test_fetch_channels_async_calls_callback_on_network_error(self):
        """Should call callback with None on network error."""
        callback = Mock()

        with patch('somafm_tui.channels.fetch_channels', side_effect=ConnectionError()):
            future = fetch_channels_async(callback=callback)
            future.result()

            callback.assert_called_once_with(None)

    def test_fetch_channels_async_calls_callback_on_json_error(self):
        """Should call callback with None on JSON error."""
        callback = Mock()

        with patch('somafm_tui.channels.fetch_channels', side_effect=json.JSONDecodeError("msg", "doc", 0)):
            future = fetch_channels_async(callback=callback)
            future.result()

            callback.assert_called_once_with(None)

    def test_fetch_channels_async_calls_callback_on_io_error(self):
        """Should call callback with None on IO error."""
        callback = Mock()

        with patch('somafm_tui.channels.fetch_channels', side_effect=IOError("error")):
            future = fetch_channels_async(callback=callback)
            future.result()

            callback.assert_called_once_with(None)

    def test_fetch_channels_async_calls_callback_on_generic_error(self):
        """Should call callback with None on generic error."""
        callback = Mock()

        with patch('somafm_tui.channels.fetch_channels', side_effect=OSError("error")):
            future = fetch_channels_async(callback=callback)
            future.result()

            callback.assert_called_once_with(None)

    def test_fetch_channels_async_without_callback(self):
        """Should work without callback."""
        with patch('somafm_tui.channels.fetch_channels', return_value=[]):
            future = fetch_channels_async()
            result = future.result()

            assert result == []


class TestChannelUsage:
    """Tests for channel usage functions."""

    def test_load_channel_usage_file_not_exists(self):
        """Should return empty dict when file doesn't exist."""
        with patch('os.path.exists', return_value=False):
            usage = load_channel_usage("/nonexistent.json")

            assert usage == {}

    def test_load_channel_usage_success(self):
        """Should load usage from file."""
        usage_data = {"ch1": 100, "ch2": 200}

        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(usage_data))):

            usage = load_channel_usage("/tmp/usage.json")

            assert usage == usage_data

    def test_load_channel_usage_json_error(self):
        """Should return empty dict on JSON error."""
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data="invalid")):

            usage = load_channel_usage("/tmp/usage.json")

            assert usage == {}

    def test_save_channel_usage_success(self):
        """Should save usage to file."""
        usage_data = {"ch1": 100}

        with patch('os.makedirs'), \
             patch('builtins.open', mock_open()) as mock_file:

            save_channel_usage("/tmp/usage.json", usage_data)

            mock_file.assert_called()

    def test_save_channel_usage_io_error(self):
        """Should handle IO error on save."""
        with patch('os.makedirs'), \
             patch('builtins.open', side_effect=IOError("error")):

            # Should not raise
            save_channel_usage("/tmp/usage.json", {"ch1": 100})

    def test_clean_channel_usage(self):
        """Should remove non-existent channels."""
        usage = {"ch1": 100, "ch2": 200, "ch3": 300}
        valid_ids = {"ch1", "ch2"}

        result = clean_channel_usage(usage, valid_ids)

        assert result == {"ch1": 100, "ch2": 200}

    def test_clean_channel_usage_all_valid(self):
        """Should keep all channels when all valid."""
        usage = {"ch1": 100, "ch2": 200}
        valid_ids = {"ch1", "ch2"}

        result = clean_channel_usage(usage, valid_ids)

        assert result == usage

    def test_sort_channels_by_usage(self):
        """Should sort channels by usage (most recent first)."""
        channels = [
            Channel(id="ch1", title="Channel 1"),
            Channel(id="ch2", title="Channel 2"),
            Channel(id="ch3", title="Channel 3"),
        ]
        usage = {"ch1": 100, "ch2": 300, "ch3": 200}

        result = sort_channels_by_usage(channels, usage)

        # ch2 (300) should be first, then ch3 (200), then ch1 (100)
        assert result[0].id == "ch2"
        assert result[1].id == "ch3"
        assert result[2].id == "ch1"

    def test_sort_channels_by_usage_no_usage(self):
        """Should put channels without usage at end."""
        channels = [
            Channel(id="ch1", title="Channel 1"),
            Channel(id="ch2", title="Channel 2"),
        ]
        usage = {"ch1": 100}

        result = sort_channels_by_usage(channels, usage)

        assert result[0].id == "ch1"
        assert result[1].id == "ch2"

    def test_get_valid_channel_ids(self):
        """Should return set of channel IDs."""
        channels = [
            Channel(id="ch1", title="Channel 1"),
            Channel(id="ch2", title="Channel 2"),
        ]

        result = get_valid_channel_ids(channels)

        assert result == {"ch1", "ch2"}

    def test_filter_channels_by_query_empty(self):
        """Should return all channels when query is empty."""
        channels = [
            Channel(id="ch1", title="Channel 1"),
            Channel(id="ch2", title="Channel 2"),
        ]

        result = filter_channels_by_query(channels, "")

        assert result == channels

    def test_filter_channels_by_query_title_match(self):
        """Should filter by title match."""
        channels = [
            Channel(id="ch1", title="Drone Zone"),
            Channel(id="ch2", title="Beat Blender"),
        ]

        result = filter_channels_by_query(channels, "drone")

        assert len(result) == 1
        assert result[0].id == "ch1"

    def test_filter_channels_by_query_description_match(self):
        """Should filter by description match."""
        channels = [
            Channel(id="ch1", title="Ch1", description="Ambient music"),
            Channel(id="ch2", title="Ch2", description="Rock music"),
        ]

        result = filter_channels_by_query(channels, "ambient")

        assert len(result) == 1
        assert result[0].id == "ch1"

    def test_filter_channels_by_query_no_match(self):
        """Should return empty list when no match."""
        channels = [
            Channel(id="ch1", title="Channel 1"),
        ]

        result = filter_channels_by_query(channels, "nonexistent")

        assert result == []


class TestFavorites:
    """Tests for favorites functions."""

    def test_load_favorites_file_not_exists(self):
        """Should return empty set when file doesn't exist."""
        with patch('os.path.exists', return_value=False):
            favorites = load_favorites("/nonexistent.json")

            assert favorites == set()

    def test_load_favorites_success(self):
        """Should load favorites from file."""
        favorites_data = ["ch1", "ch2"]

        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(favorites_data))):

            favorites = load_favorites("/tmp/favorites.json")

            assert favorites == {"ch1", "ch2"}

    def test_load_favorites_json_error(self):
        """Should return empty set on JSON error."""
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data="invalid")):

            favorites = load_favorites("/tmp/favorites.json")

            assert favorites == set()

    def test_save_favorites_success(self):
        """Should save favorites to file."""
        favorites = {"ch1", "ch2"}

        with patch('os.makedirs'), \
             patch('builtins.open', mock_open()) as mock_file:

            save_favorites("/tmp/favorites.json", favorites)

            mock_file.assert_called()

    def test_save_favorites_io_error(self):
        """Should handle IO error on save."""
        with patch('os.makedirs'), \
             patch('builtins.open', side_effect=IOError("error")):

            # Should not raise
            save_favorites("/tmp/favorites.json", {"ch1"})

    def test_toggle_favorite_add(self):
        """Should add channel to favorites."""
        with patch('somafm_tui.channels.load_favorites', return_value=set()), \
             patch('somafm_tui.channels.save_favorites') as mock_save:

            favorites = toggle_favorite("ch1", "/tmp/favorites.json")

            assert "ch1" in favorites
            mock_save.assert_called_once()

    def test_toggle_favorite_remove(self):
        """Should remove channel from favorites."""
        with patch('somafm_tui.channels.load_favorites', return_value={"ch1"}), \
             patch('somafm_tui.channels.save_favorites') as mock_save:

            favorites = toggle_favorite("ch1", "/tmp/favorites.json")

            assert "ch1" not in favorites
            mock_save.assert_called_once()

    def test_update_channel_usage(self):
        """Should update channel usage timestamp."""
        with patch('somafm_tui.channels.load_channel_usage', return_value={}), \
             patch('somafm_tui.channels.clean_channel_usage') as mock_clean, \
             patch('somafm_tui.channels.save_channel_usage') as mock_save:
            mock_clean.return_value = {"ch1": int(time.time())}

            result = update_channel_usage("ch1", "/tmp/usage.json", {"ch1"})

            assert "ch1" in result
            mock_save.assert_called_once()


class TestFavoriteTrack:
    """Tests for FavoriteTrack dataclass."""

    def test_favorite_track_default_values(self):
        """Should have correct default values."""
        track = FavoriteTrack(
            artist="Artist",
            title="Title",
            channel_id="ch1",
            channel_name="Channel",
        )

        assert track.artist == "Artist"
        assert track.title == "Title"
        assert track.channel_id == "ch1"
        assert track.channel_name == "Channel"
        assert track.added_at is not None

    def test_favorite_track_to_dict(self):
        """Should convert to dictionary."""
        track = FavoriteTrack(
            artist="Artist",
            title="Title",
            channel_id="ch1",
            channel_name="Channel",
            added_at="2024-01-01 12:00:00",
        )

        result = track.to_dict()

        assert result["artist"] == "Artist"
        assert result["title"] == "Title"
        assert result["channel_id"] == "ch1"
        assert result["channel_name"] == "Channel"
        assert result["added_at"] == "2024-01-01 12:00:00"

    def test_favorite_track_from_dict(self):
        """Should create from dictionary."""
        data = {
            "artist": "Artist",
            "title": "Title",
            "channel_id": "ch1",
            "channel_name": "Channel",
            "added_at": "2024-01-01 12:00:00",
        }

        track = FavoriteTrack.from_dict(data)

        assert track.artist == "Artist"
        assert track.title == "Title"
        assert track.channel_id == "ch1"
        assert track.channel_name == "Channel"

    def test_favorite_track_from_dict_with_defaults(self):
        """Should use defaults for missing fields."""
        data = {"artist": "Artist"}

        track = FavoriteTrack.from_dict(data)

        assert track.artist == "Artist"
        assert track.title == "Unknown"
        assert track.channel_id == ""
        assert track.channel_name == ""


class TestFavoriteTracksFunctions:
    """Tests for favorite tracks functions."""

    def test_load_favorite_tracks_file_not_exists(self):
        """Should return empty list when file doesn't exist."""
        with patch('os.path.exists', return_value=False):
            tracks = load_favorite_tracks("/nonexistent.json")

            assert tracks == []

    def test_load_favorite_tracks_success(self):
        """Should load tracks from file."""
        tracks_data = [
            {
                "artist": "Artist",
                "title": "Title",
                "channel_id": "ch1",
                "channel_name": "Channel",
            }
        ]

        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(tracks_data))):

            tracks = load_favorite_tracks("/tmp/tracks.json")

            assert len(tracks) == 1
            assert tracks[0].artist == "Artist"

    def test_load_favorite_tracks_json_error(self):
        """Should return empty list on JSON error."""
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data="invalid")):

            tracks = load_favorite_tracks("/tmp/tracks.json")

            assert tracks == []

    def test_save_favorite_tracks_success(self):
        """Should save tracks to file."""
        tracks = [
            FavoriteTrack(
                artist="Artist",
                title="Title",
                channel_id="ch1",
                channel_name="Channel",
            )
        ]

        with patch('os.makedirs'), \
             patch('builtins.open', mock_open()) as mock_file:

            save_favorite_tracks("/tmp/tracks.json", tracks)

            mock_file.assert_called()

    def test_save_favorite_tracks_io_error(self):
        """Should handle IO error on save."""
        tracks = [FavoriteTrack(artist="A", title="T", channel_id="ch1", channel_name="C")]

        with patch('os.makedirs'), \
             patch('builtins.open', side_effect=IOError("error")):

            # Should not raise
            save_favorite_tracks("/tmp/tracks.json", tracks)

    def test_add_favorite_track_new(self):
        """Should add new track to favorites."""
        with patch('somafm_tui.channels.load_favorite_tracks', return_value=[]), \
             patch('somafm_tui.channels.save_favorite_tracks') as mock_save:

            tracks = add_favorite_track(
                "/tmp/tracks.json",
                artist="Artist",
                title="Title",
                channel_id="ch1",
                channel_name="Channel",
            )

            assert len(tracks) == 1
            assert tracks[0].artist == "Artist"
            mock_save.assert_called_once()

    def test_add_favorite_track_duplicate(self):
        """Should not add duplicate track."""
        existing_track = FavoriteTrack(
            artist="Artist",
            title="Title",
            channel_id="ch1",
            channel_name="Channel",
        )

        with patch('somafm_tui.channels.load_favorite_tracks', return_value=[existing_track]), \
             patch('somafm_tui.channels.save_favorite_tracks') as mock_save:

            tracks = add_favorite_track(
                "/tmp/tracks.json",
                artist="Artist",
                title="Title",
                channel_id="ch1",
                channel_name="Channel",
            )

            assert len(tracks) == 1
            mock_save.assert_not_called()

    def test_add_favorite_track_inserts_at_beginning(self):
        """Should insert new track at beginning."""
        existing_track = FavoriteTrack(
            artist="Old Artist",
            title="Old Title",
            channel_id="ch1",
            channel_name="Channel",
        )

        with patch('somafm_tui.channels.load_favorite_tracks', return_value=[existing_track]), \
             patch('somafm_tui.channels.save_favorite_tracks'):

            tracks = add_favorite_track(
                "/tmp/tracks.json",
                artist="New Artist",
                title="New Title",
                channel_id="ch1",
                channel_name="Channel",
            )

            assert len(tracks) == 2
            assert tracks[0].artist == "New Artist"
            assert tracks[1].artist == "Old Artist"

    def test_is_track_favorite_true(self):
        """Should return True when track is favorite."""
        tracks = [
            FavoriteTrack(
                artist="Artist",
                title="Title",
                channel_id="ch1",
                channel_name="Channel",
            )
        ]

        with patch('somafm_tui.channels.load_favorite_tracks', return_value=tracks):

            result = is_track_favorite(
                "/tmp/tracks.json",
                artist="Artist",
                title="Title",
                channel_id="ch1",
            )

            assert result is True

    def test_is_track_favorite_false(self):
        """Should return False when track is not favorite."""
        tracks = [
            FavoriteTrack(
                artist="Artist",
                title="Title",
                channel_id="ch1",
                channel_name="Channel",
            )
        ]

        with patch('somafm_tui.channels.load_favorite_tracks', return_value=tracks):

            result = is_track_favorite(
                "/tmp/tracks.json",
                artist="Different",
                title="Track",
                channel_id="ch1",
            )

            assert result is False

    def test_is_track_favorite_empty_list(self):
        """Should return False when no favorites."""
        with patch('somafm_tui.channels.load_favorite_tracks', return_value=[]):

            result = is_track_favorite(
                "/tmp/tracks.json",
                artist="Artist",
                title="Title",
                channel_id="ch1",
            )

            assert result is False
