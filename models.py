"""Data types module"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import re


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

    def get_available_bitrates(self) -> List[str]:
        """Get list of available bitrates for this channel.
        
        Returns bitrates from all playlist formats (mp3, aac, aacp).
        Bitrate is extracted from playlist URL filename.
        """
        bitrates = set()
        
        for playlist in self.playlists:
            fmt = playlist.get("format", "")
            url = playlist.get("url", "")
            
            # Extract bitrate from playlist filename
            # Patterns: bootliquor320.pls, beatblender130.pls, 7soul64.pls
            match = re.search(r'(\d{2,3})\.pls$', url)
            if match:
                br_num = int(match.group(1))
                # Map to standard bitrate labels
                if br_num >= 256:
                    br_label = "320k"
                elif br_num >= 128:
                    br_label = "128k"
                elif br_num >= 64:
                    br_label = "64k"
                else:
                    br_label = "32k"
                bitrates.add(f"{fmt}:{br_label}")
            else:
                # Default bitrate for playlists without number in name
                bitrates.add(f"{fmt}:128k")
        
        # Sort by format priority (mp3 first) then by bitrate
        format_priority = {"mp3": 0, "aac": 1, "aacp": 2}
        bitrate_order = {"320k": 0, "256k": 1, "192k": 2, "128k": 3, "96k": 4, "64k": 5, "32k": 6}
        
        def sort_key(item):
            fmt, br = item.split(":")
            return (format_priority.get(fmt, 99), bitrate_order.get(br, 99))
        
        sorted_bitrates = sorted(bitrates, key=sort_key)
        return sorted_bitrates if sorted_bitrates else ["mp3:128k"]

    def get_stream_url_for_bitrate(self, bitrate: str) -> Optional[str]:
        """Get stream URL for specific bitrate.

        Bitrate format: 'mp3:128k', 'aac:128k', etc.
        """
        if ":" in bitrate:
            target_fmt, target_br = bitrate.split(":")
        else:
            target_fmt = "mp3"
            target_br = bitrate

        # Map bitrate label back to filename pattern
        # SomaFM uses: 320, 130 (for 128k), 64, etc.
        br_to_num = {
            "320k": "320",
            "256k": "256",
            "192k": "192",
            "128k": "130",  # SomaFM uses 130 for 128k
            "96k": "96",
            "64k": "64",
            "32k": "32",
        }
        target_num = br_to_num.get(target_br, "130")

        # Also map back from standard numbers (for non-SomaFM playlists)
        br_alt_map = {
            "128k": ["128", "130"],  # Accept both 128 and 130
            "320k": ["320"],
            "64k": ["64"],
            "32k": ["32"],
        }
        alt_nums = br_alt_map.get(target_br, [target_num])

        # Find matching playlist
        for playlist in self.playlists:
            fmt = playlist.get("format", "")
            url = playlist.get("url", "")

            if fmt == target_fmt:
                # Check if any of the bitrate numbers match
                for num in alt_nums:
                    if num in url:
                        return url
                # Also accept default if no bitrate in URL
                if url.endswith(".pls") and not re.search(r'\d{2,3}\.pls$', url):
                    return url

        # Fallback to first playlist of target format
        for playlist in self.playlists:
            if playlist.get("format") == target_fmt:
                return playlist.get("url")

        # Final fallback to any playlist
        for playlist in self.playlists:
            if playlist.get("url"):
                return playlist.get("url")

        return None

    def get_bitrate_label(self) -> str:
        """Get human-readable bitrate label for current stream."""
        if self.bitrate:
            return self.bitrate
        return "128k"


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
