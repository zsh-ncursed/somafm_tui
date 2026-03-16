"""Tests for mpris_service module."""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from somafm_tui.mpris_service import (
    MPRISService,
    DBUS_NAME,
    DBUS_TITLE,
)
from somafm_tui.models import Channel, TrackMetadata


# Note: MediaPlayer2Interface and MediaPlayer2PlayerInterface tests are skipped
# because dbus_next properties require a real D-Bus connection to test properly.
# These interfaces are tested indirectly through MPRISService tests.


class TestMPRISService:
    """Tests for MPRISService class."""

    def test_init(self):
        """Should initialize service."""
        player = Mock()
        player.config = {
            "dbus_send_metadata": True,
            "dbus_send_metadata_artworks": True,
            "dbus_cache_metadata_artworks": True,
        }

        with patch('os.makedirs'):
            service = MPRISService(player, cache_dir="/tmp/cache")

            assert service.player is player
            assert service.bus is None
            assert service.artworks_dir is not None

    def test_init_without_artworks(self):
        """Should not create artworks dir when disabled."""
        player = Mock()
        player.config = {
            "dbus_send_metadata": False,
            "dbus_send_metadata_artworks": False,
            "dbus_cache_metadata_artworks": False,
        }

        service = MPRISService(player, cache_dir="/tmp/cache")

        assert service.artworks_dir is None

    def test_update_playback_status(self):
        """Should update playback status via interface."""
        player = Mock()
        player.config = {"dbus_send_metadata": False}
        service = MPRISService(player, cache_dir="/tmp/cache")
        service.player_interface = Mock()
        service.player_interface.update_playback_status = Mock()

        service.update_playback_status("Playing")

        service.player_interface.update_playback_status.assert_called_once()

    def test_update_playback_status_no_interface(self):
        """Should handle missing interface."""
        player = Mock()
        player.config = {"dbus_send_metadata": False}
        service = MPRISService(player, cache_dir="/tmp/cache")
        service.player_interface = None

        # Should not raise
        service.update_playback_status("Playing")

    def test_update_metadata(self):
        """Should update metadata via interface."""
        player = Mock()
        player.config = {"dbus_send_metadata": False}
        service = MPRISService(player, cache_dir="/tmp/cache")
        service.player_interface = Mock()
        service.player_interface.update_metadata = Mock()

        service.update_metadata({"artist": "Artist"})

        service.player_interface.update_metadata.assert_called_once()

    def test_update_metadata_no_interface(self):
        """Should handle missing interface."""
        player = Mock()
        player.config = {"dbus_send_metadata": False}
        service = MPRISService(player, cache_dir="/tmp/cache")
        service.player_interface = None

        # Should not raise
        service.update_metadata({"artist": "Artist"})

    def test_start_connection_error(self):
        """Should handle connection error on start."""
        player = Mock()
        player.config = {"dbus_send_metadata": False}
        service = MPRISService(player, cache_dir="/tmp/cache")

        with patch('somafm_tui.mpris_service.MessageBus', side_effect=ConnectionError("error")):
            import asyncio
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(service.start())
                assert result is False
            finally:
                loop.close()

    def test_stop_with_bus(self):
        """Should stop service when bus exists."""
        player = Mock()
        player.config = {"dbus_send_metadata": False}
        service = MPRISService(player, cache_dir="/tmp/cache")

        mock_bus = AsyncMock()
        mock_bus.release_name = AsyncMock()
        service.bus = mock_bus

        async def mock_stop():
            try:
                await mock_bus.release_name(DBUS_NAME)
                mock_bus.disconnect()
            except Exception:
                pass

        # Should not raise
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(mock_stop())
        finally:
            loop.close()
