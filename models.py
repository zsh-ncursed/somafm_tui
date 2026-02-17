"""Data types module"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class TrackMetadata:
    """Current track metadata"""
    artist: str = "Loading..."
    title: str = "Loading..."
    duration: str = "--:--"
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "artist": self.artist,
            "title": self.title,
            "duration": self.duration,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrackMetadata":
        """Create from dictionary."""
        return cls(
            artist=data.get("artist", "Loading..."),
            title=data.get("title", "Loading..."),
            duration=data.get("duration", "--:--"),
            timestamp=data.get("timestamp"),
        )


@dataclass
class Channel:
    """SomaFM channel"""
    id: str
    title: str
    description: str = ""
    stream_url: Optional[str] = None
    largeimage: Optional[str] = None
    image: Optional[str] = None
    playlists: List[Dict[str, Any]] = field(default_factory=list)
    listeners: int = 0
    bitrate: str = ""
    last_playing: str = ""

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "Channel":
        """Create channel from API response."""
        # Get MP3 stream URL and bitrate
        stream_url = None
        bitrate = "128k"  # Default
        for playlist in data.get("playlists", []):
            if playlist.get("format") == "mp3":
                stream_url = playlist.get("url")
                # Extract bitrate from URL if possible
                url = playlist.get("url", "")
                # Check for bitrate in URL (order matters - check longer first)
                if "320" in url:
                    bitrate = "320k"
                elif "256" in url:
                    bitrate = "256k"
                elif "192" in url:
                    bitrate = "192k"
                elif "128" in url:
                    bitrate = "128k"
                elif "96" in url:
                    bitrate = "96k"
                elif "64" in url:
                    bitrate = "64k"
                elif "32" in url:
                    bitrate = "32k"
                break

        # Parse listeners
        listeners = 0
        try:
            listeners = int(data.get("listeners", "0"))
        except ValueError:
            pass

        return cls(
            id=data.get("id", ""),
            title=data.get("title", "Unknown"),
            description=data.get("description", ""),
            stream_url=stream_url,
            largeimage=data.get("largeimage"),
            image=data.get("image"),
            playlists=data.get("playlists", []),
            listeners=listeners,
            bitrate=bitrate,
            last_playing=data.get("lastPlaying", ""),
        )

    def get_stream_url(self) -> Optional[str]:
        """Get stream URL."""
        if self.stream_url:
            return self.stream_url

        for playlist in self.playlists:
            if playlist.get("format") == "mp3":
                return playlist.get("url")

        return None


@dataclass
class TrackHistoryEntry:
    """Track history entry"""
    artist: str
    title: str
    timestamp: str

    @classmethod
    def from_metadata(cls, metadata: TrackMetadata) -> "TrackHistoryEntry":
        """Create from metadata."""
        return cls(
            artist=metadata.artist,
            title=metadata.title,
            timestamp=metadata.timestamp or datetime.now().strftime("%H:%M:%S"),
        )


@dataclass
class AppConfig:
    """Application configuration"""
    buffer_minutes: int = 5
    buffer_size_mb: int = 50
    theme: str = "default"
    alternative_bg_mode: bool = False
    dbus_allowed: bool = False
    dbus_send_metadata: bool = False
    dbus_send_metadata_artworks: bool = False
    dbus_cache_metadata_artworks: bool = True
    volume: int = 100

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """Create from dictionary."""
        return cls(
            buffer_minutes=data.get("buffer_minutes", 5),
            buffer_size_mb=data.get("buffer_size_mb", 50),
            theme=data.get("theme", "default"),
            alternative_bg_mode=data.get("alternative_bg_mode", False),
            dbus_allowed=data.get("dbus_allowed", False),
            dbus_send_metadata=data.get("dbus_send_metadata", False),
            dbus_send_metadata_artworks=data.get("dbus_send_metadata_artworks", False),
            dbus_cache_metadata_artworks=data.get("dbus_cache_metadata_artworks", True),
            volume=data.get("volume", 100),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "buffer_minutes": self.buffer_minutes,
            "buffer_size_mb": self.buffer_size_mb,
            "theme": self.theme,
            "alternative_bg_mode": self.alternative_bg_mode,
            "dbus_allowed": self.dbus_allowed,
            "dbus_send_metadata": self.dbus_send_metadata,
            "dbus_send_metadata_artworks": self.dbus_send_metadata_artworks,
            "dbus_cache_metadata_artworks": self.dbus_cache_metadata_artworks,
            "volume": self.volume,
        }
