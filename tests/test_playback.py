"""Tests for PlaybackController module."""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
import json
import time

from somafm_tui.core.playback import PlaybackController
from somafm_tui.core.state import StateManager
from somafm_tui.ui import UIScreen
from somafm_tui.models import Channel, TrackMetadata


class TestPlaybackControllerInit:
    """Tests for PlaybackController initialization."""

    def test_init_sets_attributes(self):
        """Should initialize all attributes correctly."""
        player_instance = Mock()
        mpv_player = Mock()
        ui_screen = Mock(spec=UIScreen)
        state_manager = Mock(spec=StateManager)
        config = {"volume": 75}

        controller = PlaybackController(
            player_instance=player_instance,
            mpv_player=mpv_player,
            ui_screen=ui_screen,
            state_manager=state_manager,
            config=config,
            cache_dir="/tmp/cache",
            channel_usage_file="/tmp/usage.json",
            channel_favorites_file="/tmp/favorites.json",
            track_favorites_file="/tmp/tracks.json",
        )

        assert controller.player_instance is player_instance
        assert controller.player is mpv_player
        assert controller.ui_screen is ui_screen
        assert controller.state_manager is state_manager
        assert controller.config == config
        assert controller.cache_dir == "/tmp/cache"
        assert controller.channel_usage_file == "/tmp/usage.json"
        assert controller.channel_favorites_file == "/tmp/favorites.json"
        assert controller.track_favorites_file == "/tmp/tracks.json"
        assert controller.mpris_service is None
        assert controller.current_channel is None
        assert isinstance(controller.current_metadata, TrackMetadata)
        assert controller.current_bitrate == ""
        assert controller.is_playing is False
        assert controller.is_paused is False
        assert controller._on_playback_change is None

    def test_set_mpris_service(self):
        """Should set MPRIS service."""
        controller = self._create_controller()
        mpris_service = Mock()

        controller.set_mpris_service(mpris_service)

        assert controller.mpris_service is mpris_service

    def test_set_on_playback_change(self):
        """Should set playback change callback."""
        controller = self._create_controller()
        callback = Mock()

        controller.set_on_playback_change(callback)

        assert controller._on_playback_change is callback

    def _create_controller(self):
        """Helper to create a controller with mocks."""
        return PlaybackController(
            player_instance=Mock(),
            mpv_player=Mock(),
            ui_screen=Mock(spec=UIScreen),
            state_manager=Mock(spec=StateManager),
            config={"volume": 75},
            cache_dir="/tmp/cache",
            channel_usage_file="/tmp/usage.json",
            channel_favorites_file="/tmp/favorites.json",
            track_favorites_file="/tmp/tracks.json",
        )


class TestPlayChannel:
    """Tests for play_channel method."""

    def test_play_channel_success(self):
        """Should play channel successfully."""
        player_instance = Mock()
        player_instance.channels = [
            Channel(id="test", title="Test Channel", stream_url="https://test.com/stream.pls")
        ]
        mpv_player = Mock()
        ui_screen = Mock(spec=UIScreen)
        state_manager = Mock(spec=StateManager)
        state_manager.current_index = 0
        config = {"volume": 75}

        controller = PlaybackController(
            player_instance=player_instance,
            mpv_player=mpv_player,
            ui_screen=ui_screen,
            state_manager=state_manager,
            config=config,
            cache_dir="/tmp/cache",
            channel_usage_file="/tmp/usage.json",
            channel_favorites_file="/tmp/favorites.json",
            track_favorites_file="/tmp/tracks.json",
        )

        channel = player_instance.channels[0]

        with patch('somafm_tui.core.playback.load_channel_usage') as mock_load_usage, \
             patch('somafm_tui.core.playback.clean_channel_usage') as mock_clean, \
             patch('somafm_tui.core.playback.save_channel_usage') as mock_save_usage:
            mock_load_usage.return_value = {}
            mock_clean.return_value = {"test": int(time.time())}

            controller.play_channel(channel, 0)

        assert controller.is_playing is True
        assert controller.is_paused is False
        assert controller.current_channel is channel
        assert controller.current_bitrate == "mp3:128k"
        assert ui_screen.current_channel is channel
        assert ui_screen.player is mpv_player
        mpv_player.stop.assert_called_once()
        mpv_player.play.assert_called_once_with("https://test.com/stream.pls")

    def test_play_channel_updates_usage(self):
        """Should update channel usage."""
        player_instance = Mock()
        channel = Channel(id="test", title="Test", stream_url="https://test.com/stream.pls")
        player_instance.channels = [channel]
        mpv_player = Mock()

        controller = PlaybackController(
            player_instance=player_instance,
            mpv_player=mpv_player,
            ui_screen=Mock(),
            state_manager=Mock(),
            config={},
            cache_dir="/tmp/cache",
            channel_usage_file="/tmp/usage.json",
            channel_favorites_file="/tmp/favorites.json",
            track_favorites_file="/tmp/tracks.json",
        )

        with patch('somafm_tui.core.playback.load_channel_usage') as mock_load, \
             patch('somafm_tui.core.playback.clean_channel_usage') as mock_clean, \
             patch('somafm_tui.core.playback.save_channel_usage') as mock_save:
            mock_load.return_value = {}
            mock_clean.return_value = {"test": int(time.time())}

            controller.play_channel(channel, 0)

            mock_load.assert_called_once()
            mock_clean.assert_called_once()
            mock_save.assert_called_once()

    def test_play_channel_no_stream_url(self):
        """Should handle missing stream URL."""
        player_instance = Mock()
        player_instance.channels = [
            Channel(id="test", title="Test Channel", stream_url=None, playlists=[])
        ]
        mpv_player = Mock()
        callback = Mock()

        controller = PlaybackController(
            player_instance=player_instance,
            mpv_player=mpv_player,
            ui_screen=Mock(),
            state_manager=Mock(),
            config={},
            cache_dir="/tmp/cache",
            channel_usage_file="/tmp/usage.json",
            channel_favorites_file="/tmp/favorites.json",
            track_favorites_file="/tmp/tracks.json",
        )
        controller.set_on_playback_change(callback)

        controller.play_channel(player_instance.channels[0], 0)

        assert controller.is_playing is False
        assert controller.current_channel is None
        mpv_player.play.assert_not_called()

    def test_play_channel_json_error(self):
        """Should handle JSON decode error gracefully."""
        player_instance = Mock()
        channel = Channel(id="test", title="Test", stream_url="https://test.com/stream.pls")
        player_instance.channels = [channel]
        mpv_player = Mock()

        controller = PlaybackController(
            player_instance=player_instance,
            mpv_player=mpv_player,
            ui_screen=Mock(),
            state_manager=Mock(),
            config={},
            cache_dir="/tmp/cache",
            channel_usage_file="/tmp/usage.json",
            channel_favorites_file="/tmp/favorites.json",
            track_favorites_file="/tmp/tracks.json",
        )

        with patch('somafm_tui.core.playback.load_channel_usage') as mock_load:
            mock_load.side_effect = json.JSONDecodeError("msg", "doc", 0)

            controller.play_channel(channel, 0)

        assert controller.is_playing is False
        assert controller.current_channel is None

    def test_play_channel_io_error(self):
        """Should handle IO error gracefully."""
        player_instance = Mock()
        channel = Channel(id="test", title="Test", stream_url="https://test.com/stream.pls")
        player_instance.channels = [channel]
        mpv_player = Mock()

        controller = PlaybackController(
            player_instance=player_instance,
            mpv_player=mpv_player,
            ui_screen=Mock(),
            state_manager=Mock(),
            config={},
            cache_dir="/tmp/cache",
            channel_usage_file="/tmp/usage.json",
            channel_favorites_file="/tmp/favorites.json",
            track_favorites_file="/tmp/tracks.json",
        )

        with patch('somafm_tui.core.playback.load_channel_usage') as mock_load:
            mock_load.side_effect = IOError("File not found")

            controller.play_channel(channel, 0)

        assert controller.is_playing is False
        assert controller.current_channel is None

    def test_play_channel_updates_mpris(self):
        """Should update MPRIS service if available."""
        player_instance = Mock()
        player_instance.channels = [
            Channel(id="test", title="Test", stream_url="https://test.com/stream.pls")
        ]
        mpv_player = Mock()
        mpris_service = Mock()
        config = {"dbus_send_metadata": True}

        controller = PlaybackController(
            player_instance=player_instance,
            mpv_player=mpv_player,
            ui_screen=Mock(),
            state_manager=Mock(),
            config=config,
            cache_dir="/tmp/cache",
            channel_usage_file="/tmp/usage.json",
            channel_favorites_file="/tmp/favorites.json",
            track_favorites_file="/tmp/tracks.json",
        )
        controller.set_mpris_service(mpris_service)

        with patch('somafm_tui.core.playback.load_channel_usage', return_value={}), \
             patch('somafm_tui.core.playback.clean_channel_usage', return_value={}):
            controller.play_channel(player_instance.channels[0], 0)

        mpris_service.update_playback_status.assert_called_with("Playing")
        mpris_service.update_metadata.assert_called()

    def test_play_channel_triggers_callback(self):
        """Should trigger playback change callback."""
        player_instance = Mock()
        player_instance.channels = [
            Channel(id="test", title="Test", stream_url="https://test.com/stream.pls")
        ]
        mpv_player = Mock()
        callback = Mock()

        controller = PlaybackController(
            player_instance=player_instance,
            mpv_player=mpv_player,
            ui_screen=Mock(),
            state_manager=Mock(),
            config={},
            cache_dir="/tmp/cache",
            channel_usage_file="/tmp/usage.json",
            channel_favorites_file="/tmp/favorites.json",
            track_favorites_file="/tmp/tracks.json",
        )
        controller.set_on_playback_change(callback)

        with patch('somafm_tui.core.playback.load_channel_usage', return_value={}), \
             patch('somafm_tui.core.playback.clean_channel_usage', return_value={}):
            controller.play_channel(player_instance.channels[0], 0)

        callback.assert_called_once()


class TestTogglePlayback:
    """Tests for toggle_playback method."""

    def test_toggle_playback_when_not_playing(self):
        """Should do nothing when not playing."""
        controller = self._create_controller()
        controller.is_playing = False

        controller.toggle_playback()

        assert controller.player.pause is not True  # Should not change

    def test_toggle_playback_from_playing_to_paused(self):
        """Should toggle from playing to paused."""
        controller = self._create_controller()
        controller.is_playing = True
        controller.is_paused = False
        mpris_service = Mock()
        controller.set_mpris_service(mpris_service)

        controller.toggle_playback()

        assert controller.player.pause is True
        assert controller.is_paused is True
        mpris_service.update_playback_status.assert_called_with("Paused")

    def test_toggle_playback_from_paused_to_playing(self):
        """Should toggle from paused to playing."""
        controller = self._create_controller()
        controller.is_playing = True
        controller.is_paused = True
        mpris_service = Mock()
        controller.set_mpris_service(mpris_service)

        controller.toggle_playback()

        assert controller.player.pause is False
        assert controller.is_paused is False
        mpris_service.update_playback_status.assert_called_with("Playing")

    def test_toggle_playback_triggers_callback(self):
        """Should trigger callback on toggle."""
        controller = self._create_controller()
        controller.is_playing = True
        controller.is_paused = False
        callback = Mock()
        controller.set_on_playback_change(callback)

        controller.toggle_playback()

        callback.assert_called_once()

    def _create_controller(self):
        """Helper to create controller."""
        return PlaybackController(
            player_instance=Mock(),
            mpv_player=Mock(),
            ui_screen=Mock(),
            state_manager=Mock(),
            config={},
            cache_dir="/tmp/cache",
            channel_usage_file="/tmp/usage.json",
            channel_favorites_file="/tmp/favorites.json",
            track_favorites_file="/tmp/tracks.json",
        )


class TestStopPlayback:
    """Tests for stop_playback method."""

    def test_stop_playback_when_not_playing(self):
        """Should do nothing when not playing."""
        controller = self._create_controller()
        controller.is_playing = False

        controller.stop_playback()

        controller.player.stop.assert_not_called()

    def test_stop_playback_success(self):
        """Should stop playback successfully."""
        controller = self._create_controller()
        controller.is_playing = True
        controller.is_paused = False
        controller.current_channel = Channel(id="test", title="Test")
        mpris_service = Mock()
        controller.set_mpris_service(mpris_service)

        controller.stop_playback()

        controller.player.stop.assert_called_once()
        assert controller.is_playing is False
        assert controller.is_paused is False
        assert controller.current_channel is None
        assert isinstance(controller.current_metadata, TrackMetadata)
        mpris_service.update_playback_status.assert_called_with("Stopped")

    def test_stop_playback_triggers_callback(self):
        """Should trigger callback on stop."""
        controller = self._create_controller()
        controller.is_playing = True
        callback = Mock()
        controller.set_on_playback_change(callback)

        controller.stop_playback()

        callback.assert_called_once()

    def _create_controller(self):
        """Helper to create controller."""
        return PlaybackController(
            player_instance=Mock(),
            mpv_player=Mock(),
            ui_screen=Mock(),
            state_manager=Mock(),
            config={},
            cache_dir="/tmp/cache",
            channel_usage_file="/tmp/usage.json",
            channel_favorites_file="/tmp/favorites.json",
            track_favorites_file="/tmp/tracks.json",
        )


class TestVolumeControl:
    """Tests for volume control methods."""

    def test_set_volume_clamps_to_range(self):
        """Should clamp volume to 0-100 range."""
        controller = self._create_controller()

        controller.set_volume(-10)
        assert controller.volume == 0
        assert controller.config["volume"] == 0

        controller.set_volume(150)
        assert controller.volume == 100
        assert controller.config["volume"] == 100

        controller.set_volume(50)
        assert controller.volume == 50

    def test_set_volume_updates_player(self):
        """Should update player volume."""
        controller = self._create_controller()
        controller.player = Mock()

        controller.set_volume(75)

        controller.player.volume = 75

    def test_get_volume_returns_current(self):
        """Should return current volume."""
        controller = self._create_controller()
        controller.volume = 60

        assert controller.get_volume() == 60

    def test_get_volume_returns_config_default(self):
        """Should return config default if volume not set."""
        controller = self._create_controller()
        controller.config = {"volume": 80}

        assert controller.get_volume() == 80

    def test_get_volume_returns_hardcoded_default(self):
        """Should return hardcoded default if no volume set."""
        controller = self._create_controller()
        controller.config = {}

        assert controller.get_volume() == 100

    def test_increase_volume(self):
        """Should increase volume by step."""
        controller = self._create_controller()
        controller.volume = 50

        controller.increase_volume(10)

        assert controller.volume == 60

    def test_decrease_volume(self):
        """Should decrease volume by step."""
        controller = self._create_controller()
        controller.volume = 50

        controller.decrease_volume(10)

        assert controller.volume == 40

    def _create_controller(self):
        """Helper to create controller."""
        return PlaybackController(
            player_instance=Mock(),
            mpv_player=Mock(),
            ui_screen=Mock(),
            state_manager=Mock(),
            config={"volume": 75},
            cache_dir="/tmp/cache",
            channel_usage_file="/tmp/usage.json",
            channel_favorites_file="/tmp/favorites.json",
            track_favorites_file="/tmp/tracks.json",
        )


class TestCycleBitrate:
    """Tests for cycle_bitrate method."""

    def test_cycle_bitrate_no_channel(self):
        """Should do nothing when no channel."""
        controller = self._create_controller()
        controller.current_channel = None

        controller.cycle_bitrate()

        assert controller.current_bitrate == ""

    def test_cycle_bitrate_single_bitrate(self):
        """Should do nothing when only one bitrate available."""
        controller = self._create_controller()
        channel = Mock(spec=Channel)
        channel.get_available_bitrates.return_value = ["mp3:128k"]
        controller.current_channel = channel
        controller.current_bitrate = "mp3:128k"

        controller.cycle_bitrate()

        assert controller.current_bitrate == "mp3:128k"

    def test_cycle_bitrate_cycles_through_options(self):
        """Should cycle through available bitrates."""
        controller = self._create_controller()
        channel = Mock(spec=Channel)
        channel.get_available_bitrates.return_value = ["mp3:128k", "mp3:320k", "aac:64k"]
        channel.get_stream_url_for_bitrate.side_effect = [
            "https://test.com/128.pls",
            "https://test.com/320.pls",
            "https://test.com/64.pls",
        ]
        controller.current_channel = channel
        controller.current_bitrate = "mp3:128k"
        controller.is_playing = True

        controller.cycle_bitrate()

        assert controller.current_bitrate == "mp3:320k"

    def test_cycle_bitrate_wraps_around(self):
        """Should wrap around to first bitrate."""
        controller = self._create_controller()
        channel = Mock(spec=Channel)
        channel.get_available_bitrates.return_value = ["mp3:128k", "mp3:320k"]
        channel.get_stream_url_for_bitrate.return_value = "https://test.com/stream.pls"
        controller.current_channel = channel
        controller.current_bitrate = "mp3:320k"
        controller.is_playing = True

        controller.cycle_bitrate()

        assert controller.current_bitrate == "mp3:128k"

    def test_cycle_bitrate_handles_invalid_current(self):
        """Should handle invalid current bitrate."""
        controller = self._create_controller()
        channel = Mock(spec=Channel)
        channel.get_available_bitrates.return_value = ["mp3:128k", "mp3:320k"]
        channel.get_stream_url_for_bitrate.return_value = "https://test.com/stream.pls"
        controller.current_channel = channel
        controller.current_bitrate = "invalid:bitrate"
        controller.is_playing = True

        controller.cycle_bitrate()

        assert controller.current_bitrate == "mp3:128k"

    def _create_controller(self):
        """Helper to create controller."""
        return PlaybackController(
            player_instance=Mock(),
            mpv_player=Mock(),
            ui_screen=Mock(),
            state_manager=Mock(),
            config={},
            cache_dir="/tmp/cache",
            channel_usage_file="/tmp/usage.json",
            channel_favorites_file="/tmp/favorites.json",
            track_favorites_file="/tmp/tracks.json",
        )


class TestToggleFavorite:
    """Tests for toggle favorite methods."""

    def test_toggle_channel_favorite_no_channels(self):
        """Should return error when no channels."""
        controller = self._create_controller()
        controller.player_instance.channels = []

        success, message = controller.toggle_channel_favorite()

        assert success is False
        assert message == "No channels available"

    def test_toggle_channel_favorite_success_add(self):
        """Should add channel to favorites."""
        controller = self._create_controller()
        channel = Channel(id="test", title="Test")
        controller.player_instance.channels = [channel]
        controller.state_manager.current_index = 0
        callback = Mock()
        controller.set_on_playback_change(callback)

        with patch('somafm_tui.core.playback.toggle_favorite') as mock_toggle:
            mock_toggle.return_value = {"test"}

            success, message = controller.toggle_channel_favorite()

            assert success is True
            assert "Added" in message
            mock_toggle.assert_called_once_with("test", controller.channel_favorites_file)
            callback.assert_called_once()

    def test_toggle_channel_favorite_success_remove(self):
        """Should remove channel from favorites."""
        controller = self._create_controller()
        channel = Channel(id="test", title="Test")
        controller.player_instance.channels = [channel]
        controller.state_manager.current_index = 0

        with patch('somafm_tui.core.playback.toggle_favorite') as mock_toggle:
            mock_toggle.return_value = set()

            success, message = controller.toggle_channel_favorite()

            assert success is True
            assert "Removed" in message

    def test_toggle_channel_favorite_index_out_of_range(self):
        """Should handle index out of range."""
        controller = self._create_controller()
        controller.player_instance.channels = [Channel(id="test", title="Test")]
        controller.state_manager.current_index = 10

        success, message = controller.toggle_channel_favorite()

        assert success is False
        assert "Cannot toggle" in message

    def test_toggle_favorite_track_no_channel_playing(self):
        """Should return error when no channel playing."""
        controller = self._create_controller()
        controller.is_playing = False

        success, message = controller.toggle_favorite_track()

        assert success is False
        assert "No channel playing" in message

    def test_toggle_favorite_track_no_metadata(self):
        """Should return error when no metadata available."""
        controller = self._create_controller()
        controller.is_playing = True
        controller.current_channel = Channel(id="test", title="Test")
        controller.current_metadata = TrackMetadata(artist="Loading...", title="Loading...")

        success, message = controller.toggle_favorite_track()

        assert success is False
        assert "No track metadata" in message

    def test_toggle_favorite_track_success(self):
        """Should add track to favorites."""
        controller = self._create_controller()
        controller.is_playing = True
        controller.current_channel = Channel(id="test", title="Test Channel")
        controller.current_metadata = TrackMetadata(artist="Artist", title="Title")

        with patch('somafm_tui.core.playback.add_favorite_track') as mock_add:
            mock_add.return_value = []

            success, message = controller.toggle_favorite_track()

            assert success is True
            assert "Added" in message
            mock_add.assert_called_once()

    def _create_controller(self):
        """Helper to create controller."""
        return PlaybackController(
            player_instance=Mock(),
            mpv_player=Mock(),
            ui_screen=Mock(),
            state_manager=Mock(),
            config={},
            cache_dir="/tmp/cache",
            channel_usage_file="/tmp/usage.json",
            channel_favorites_file="/tmp/favorites.json",
            track_favorites_file="/tmp/tracks.json",
        )


class TestUpdateMetadata:
    """Tests for update_metadata method."""

    def test_update_metadata_no_change(self):
        """Should not update if metadata unchanged."""
        controller = self._create_controller()
        controller.current_metadata = TrackMetadata(artist="Artist", title="Title")
        ui_screen = Mock()
        controller.ui_screen = ui_screen

        new_metadata = TrackMetadata(artist="Artist", title="Title")
        controller.update_metadata(new_metadata)

        ui_screen.add_to_history.assert_not_called()
        ui_screen.update_metadata.assert_not_called()

    def test_update_metadata_with_change(self):
        """Should update metadata when changed."""
        controller = self._create_controller()
        controller.current_metadata = TrackMetadata(artist="Old", title="Old")
        ui_screen = Mock()
        controller.ui_screen = ui_screen
        mpris_service = Mock()
        controller.set_mpris_service(mpris_service)
        controller.config = {"dbus_send_metadata": True}

        new_metadata = TrackMetadata(artist="New", title="New")
        controller.update_metadata(new_metadata)

        ui_screen.add_to_history.assert_called_once()
        ui_screen.update_metadata.assert_called_once_with(new_metadata)
        assert controller.current_metadata is new_metadata

    def test_update_metadata_without_mpris(self):
        """Should work without MPRIS service."""
        controller = self._create_controller()
        controller.current_metadata = TrackMetadata(artist="Old", title="Old")
        controller.mpris_service = None
        ui_screen = Mock()
        controller.ui_screen = ui_screen

        new_metadata = TrackMetadata(artist="New", title="New")
        controller.update_metadata(new_metadata)

        ui_screen.add_to_history.assert_called_once()
        ui_screen.update_metadata.assert_called_once()

    def _create_controller(self):
        """Helper to create controller."""
        return PlaybackController(
            player_instance=Mock(),
            mpv_player=Mock(),
            ui_screen=Mock(),
            state_manager=Mock(),
            config={},
            cache_dir="/tmp/cache",
            channel_usage_file="/tmp/usage.json",
            channel_favorites_file="/tmp/favorites.json",
            track_favorites_file="/tmp/tracks.json",
        )


class TestGetPlaybackStatus:
    """Tests for get_playback_status method."""

    def test_get_playback_status_stopped(self):
        """Should return Stopped when not playing."""
        controller = self._create_controller()
        controller.is_playing = False

        status = controller.get_playback_status()

        assert status == "Stopped"

    def test_get_playback_status_playing(self):
        """Should return Playing."""
        controller = self._create_controller()
        controller.is_playing = True
        controller.is_paused = False

        status = controller.get_playback_status()

        assert status == "Playing"

    def test_get_playback_status_paused(self):
        """Should return Paused."""
        controller = self._create_controller()
        controller.is_playing = True
        controller.is_paused = True

        status = controller.get_playback_status()

        assert status == "Paused"

    def _create_controller(self):
        """Helper to create controller."""
        return PlaybackController(
            player_instance=Mock(),
            mpv_player=Mock(),
            ui_screen=Mock(),
            state_manager=Mock(),
            config={},
            cache_dir="/tmp/cache",
            channel_usage_file="/tmp/usage.json",
            channel_favorites_file="/tmp/favorites.json",
            track_favorites_file="/tmp/tracks.json",
        )
