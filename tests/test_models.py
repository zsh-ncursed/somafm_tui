"""Tests for models module."""

import pytest
from datetime import datetime

from somafm_tui.models import (
    TrackMetadata,
    Channel,
    TrackHistoryEntry,
    AppConfig,
)


class TestTrackMetadata:
    """Tests for TrackMetadata dataclass."""

    def test_default_values(self):
        """Should have correct default values."""
        metadata = TrackMetadata()
        
        assert metadata.artist == "Loading..."
        assert metadata.title == "Loading..."
        assert metadata.duration == "--:--"
        assert metadata.timestamp is None

    def test_custom_values(self):
        """Should accept custom values."""
        metadata = TrackMetadata(
            artist="Artist Name",
            title="Track Title",
            duration="3:45",
            timestamp="2024-01-01T12:00:00Z",
        )
        
        assert metadata.artist == "Artist Name"
        assert metadata.title == "Track Title"
        assert metadata.duration == "3:45"
        assert metadata.timestamp == "2024-01-01T12:00:00Z"

    def test_to_dict(self):
        """Should convert to dictionary."""
        metadata = TrackMetadata(
            artist="Artist",
            title="Title",
            duration="4:00",
            timestamp="2024-01-01T12:00:00Z",
        )
        
        result = metadata.to_dict()
        
        assert result["artist"] == "Artist"
        assert result["title"] == "Title"
        assert result["duration"] == "4:00"
        assert result["timestamp"] == "2024-01-01T12:00:00Z"

    def test_from_dict(self):
        """Should create from dictionary."""
        data = {
            "artist": "Artist",
            "title": "Title",
            "duration": "4:00",
            "timestamp": "2024-01-01T12:00:00Z",
        }
        
        metadata = TrackMetadata.from_dict(data)
        
        assert metadata.artist == "Artist"
        assert metadata.title == "Title"
        assert metadata.duration == "4:00"
        assert metadata.timestamp == "2024-01-01T12:00:00Z"

    def test_from_dict_with_missing_fields(self):
        """Should use defaults for missing fields."""
        data = {"artist": "Artist"}
        
        metadata = TrackMetadata.from_dict(data)
        
        assert metadata.artist == "Artist"
        assert metadata.title == "Loading..."
        assert metadata.duration == "--:--"
        assert metadata.timestamp is None

    def test_roundtrip(self):
        """Should preserve data through to_dict/from_dict."""
        original = TrackMetadata(
            artist="Artist",
            title="Title",
            duration="4:00",
            timestamp="2024-01-01T12:00:00Z",
        )
        
        data = original.to_dict()
        restored = TrackMetadata.from_dict(data)
        
        assert restored.artist == original.artist
        assert restored.title == original.title
        assert restored.duration == original.duration
        assert restored.timestamp == original.timestamp


class TestChannel:
    """Tests for Channel dataclass."""

    def test_default_values(self):
        """Should have correct default values."""
        channel = Channel(id="test", title="Test Channel")
        
        assert channel.id == "test"
        assert channel.title == "Test Channel"
        assert channel.description == ""
        assert channel.stream_url is None
        assert channel.largeimage is None
        assert channel.image is None
        assert channel.playlists == []
        assert channel.listeners == 0
        assert channel.bitrate == ""
        assert channel.last_playing == ""

    def test_from_api_response_basic(self, sample_channel_data):
        """Should create channel from API response."""
        channel = Channel.from_api_response(sample_channel_data)
        
        assert channel.id == "dronezone"
        assert channel.title == "Drone Zone"
        assert channel.description == "Served best chilled, a space music experience"
        assert channel.listeners == 1234
        assert channel.last_playing == "Last track"

    def test_from_api_response_extracts_mp3_stream(self, sample_channel_data):
        """Should extract MP3 stream URL from playlists."""
        channel = Channel.from_api_response(sample_channel_data)
        
        assert channel.stream_url == "https://somafm.com/dronezone130.pls"
        assert channel.bitrate == "128k"

    def test_from_api_response_handles_missing_listeners(self):
        """Should handle missing or invalid listeners."""
        data = {
            "id": "test",
            "title": "Test",
            "listeners": "invalid",
            "playlists": [],
        }
        
        channel = Channel.from_api_response(data)
        assert channel.listeners == 0

    def test_from_api_response_handles_missing_listeners_key(self):
        """Should handle missing listeners key."""
        data = {
            "id": "test",
            "title": "Test",
            "playlists": [],
        }
        
        channel = Channel.from_api_response(data)
        assert channel.listeners == 0

    def test_get_stream_url_from_field(self):
        """Should return stream_url field if set."""
        channel = Channel(
            id="test",
            title="Test",
            stream_url="https://example.com/stream.pls",
        )
        
        assert channel.get_stream_url() == "https://example.com/stream.pls"

    def test_get_stream_url_from_playlists(self):
        """Should extract stream URL from playlists if field not set."""
        channel = Channel(
            id="test",
            title="Test",
            stream_url=None,
            playlists=[
                {"format": "mp3", "url": "https://example.com/mp3.pls"},
                {"format": "aac", "url": "https://example.com/aac.pls"},
            ],
        )
        
        assert channel.get_stream_url() == "https://example.com/mp3.pls"

    def test_get_stream_url_returns_none_when_empty(self):
        """Should return None when no stream URL available."""
        channel = Channel(
            id="test",
            title="Test",
            stream_url=None,
            playlists=[],
        )
        
        assert channel.get_stream_url() is None

    def test_get_available_bitrates(self, sample_channel_data):
        """Should return list of available bitrates."""
        channel = Channel.from_api_response(sample_channel_data)
        
        bitrates = channel.get_available_bitrates()
        
        assert isinstance(bitrates, list)
        assert len(bitrates) > 0
        # Should be sorted by format priority then bitrate
        assert "mp3:320k" in bitrates or "mp3:128k" in bitrates
        assert "aac:64k" in bitrates

    def test_get_stream_url_for_bitrate(self, sample_channel_data):
        """Should return stream URL for specific bitrate."""
        channel = Channel.from_api_response(sample_channel_data)
        
        url = channel.get_stream_url_for_bitrate("mp3:320k")
        assert url == "https://somafm.com/dronezone320.pls"

    def test_get_stream_url_for_bitrate_fallback(self, sample_channel_data):
        """Should fallback to first matching format."""
        channel = Channel.from_api_response(sample_channel_data)
        
        # Request non-existent bitrate, should fallback
        url = channel.get_stream_url_for_bitrate("mp3:256k")
        assert url is not None
        assert url.endswith(".pls")

    def test_get_bitrate_label(self):
        """Should return bitrate label."""
        channel = Channel(
            id="test",
            title="Test",
            bitrate="192k",
        )
        
        assert channel.get_bitrate_label() == "192k"

    def test_get_bitrate_label_default(self):
        """Should return default 128k when bitrate not set."""
        channel = Channel(
            id="test",
            title="Test",
            bitrate="",
        )
        
        assert channel.get_bitrate_label() == "128k"


class TestTrackHistoryEntry:
    """Tests for TrackHistoryEntry dataclass."""

    def test_basic_creation(self):
        """Should create history entry with required fields."""
        entry = TrackHistoryEntry(
            artist="Artist",
            title="Title",
            timestamp="2024-01-01T12:00:00Z",
        )
        
        assert entry.artist == "Artist"
        assert entry.title == "Title"
        assert entry.timestamp == "2024-01-01T12:00:00Z"

    def test_from_metadata(self, sample_track_metadata):
        """Should create from TrackMetadata."""
        metadata = TrackMetadata(
            artist="Artist",
            title="Title",
            duration="3:45",
            timestamp="2024-01-01T12:00:00Z",
        )
        
        entry = TrackHistoryEntry.from_metadata(metadata)
        
        assert entry.artist == "Artist"
        assert entry.title == "Title"
        assert entry.timestamp == "2024-01-01T12:00:00Z"

    def test_from_metadata_generates_timestamp(self):
        """Should generate timestamp if not provided."""
        metadata = TrackMetadata(
            artist="Artist",
            title="Title",
            duration="3:45",
            timestamp=None,
        )
        
        entry = TrackHistoryEntry.from_metadata(metadata)
        
        assert entry.artist == "Artist"
        assert entry.title == "Title"
        assert entry.timestamp is not None


class TestAppConfig:
    """Tests for AppConfig dataclass."""

    def test_default_values(self):
        """Should have correct default values."""
        config = AppConfig()
        
        assert config.theme == "default"
        assert config.alternative_bg_mode is False
        assert config.dbus_allowed is False
        assert config.dbus_send_metadata is False
        assert config.dbus_send_metadata_artworks is False
        assert config.dbus_cache_metadata_artworks is True
        assert config.volume == 100

    def test_custom_values(self):
        """Should accept custom values."""
        config = AppConfig(
            theme="monochrome",
            alternative_bg_mode=True,
            dbus_allowed=True,
            volume=75,
        )
        
        assert config.theme == "monochrome"
        assert config.alternative_bg_mode is True
        assert config.dbus_allowed is True
        assert config.volume == 75

    def test_from_dict(self):
        """Should create from dictionary."""
        data = {
            "theme": "dark",
            "dbus_allowed": True,
            "volume": 50,
            "unknown_field": "ignored",
        }
        
        config = AppConfig.from_dict(data)
        
        assert config.theme == "dark"
        assert config.dbus_allowed is True
        assert config.volume == 50
        # Unknown fields should be ignored

    def test_from_dict_with_defaults(self):
        """Should use defaults for missing fields."""
        data = {"volume": 80}
        
        config = AppConfig.from_dict(data)
        
        assert config.theme == "default"
        assert config.volume == 80
        assert config.dbus_allowed is False

    def test_to_dict(self):
        """Should convert to dictionary."""
        config = AppConfig(
            theme="custom",
            dbus_allowed=True,
            volume=60,
        )
        
        result = config.to_dict()
        
        assert result["theme"] == "custom"
        assert result["dbus_allowed"] is True
        assert result["volume"] == 60
        assert "alternative_bg_mode" in result

    def test_roundtrip(self):
        """Should preserve data through to_dict/from_dict."""
        original = AppConfig(
            theme="monochrome",
            alternative_bg_mode=True,
            dbus_allowed=True,
            dbus_send_metadata=True,
            volume=75,
        )
        
        data = original.to_dict()
        restored = AppConfig.from_dict(data)
        
        assert restored.theme == original.theme
        assert restored.alternative_bg_mode == original.alternative_bg_mode
        assert restored.dbus_allowed == original.dbus_allowed
        assert restored.volume == original.volume
