"""SomaFM channels module"""

import json
import logging
import os
import time
from concurrent.futures import Future
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Set, Optional, Callable

import requests

from .models import Channel
from .http_client import fetch_json, fetch_json_async

API_URL = "https://api.somafm.com/channels.json"
DEFAULT_TIMEOUT = 10  # seconds
CACHE_MAX_AGE = 3600  # 1 hour in seconds


def fetch_channels(
    timeout: int = DEFAULT_TIMEOUT,
    cache_file: Optional[str] = None,
    cache_max_age: int = CACHE_MAX_AGE,
) -> List[Channel]:
    """
    Fetch channels from SomaFM API.
    Uses caching to reduce API load.
    """
    # Try to use cache first
    if cache_file and os.path.exists(cache_file):
        try:
            cache_age = time.time() - os.path.getmtime(cache_file)
            if cache_age < cache_max_age:
                logging.debug(f"Using cached channels (age: {cache_age:.0f}s)")
                with open(cache_file, "r") as f:
                    data = json.load(f)
                    channels_data = data.get("channels", [])
                    return [Channel.from_api_response(ch) for ch in channels_data]
        except (json.JSONDecodeError, IOError) as e:
            logging.warning(f"Failed to read cache: {e}")

    # Fetch from API
    data = fetch_json(API_URL, timeout=timeout)

    if data is None:
        # Try to use stale cache if network fails
        if cache_file and os.path.exists(cache_file):
            logging.warning("Using stale cache due to network error")
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                    channels_data = data.get("channels", [])
                    return [Channel.from_api_response(ch) for ch in channels_data]
            except (json.JSONDecodeError, IOError):
                pass
        raise ConnectionError(f"Failed to fetch channels from {API_URL}")

    # Save to cache
    if cache_file:
        try:
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with open(cache_file, "w") as f:
                json.dump(data, f)
            logging.debug("Channels cached successfully")
        except IOError as e:
            logging.warning(f"Failed to write cache: {e}")

    channels_data = data.get("channels", [])
    return [Channel.from_api_response(ch) for ch in channels_data]


def fetch_channels_async(
    timeout: int = DEFAULT_TIMEOUT,
    cache_file: Optional[str] = None,
    cache_max_age: int = CACHE_MAX_AGE,
    callback: Optional[Callable[[Optional[List[Channel]]], None]] = None,
) -> Future:
    """
    Fetch channels asynchronously from SomaFM API.
    Uses caching to reduce API load.
    Non-blocking: returns immediately with a Future.

    Args:
        timeout: Request timeout in seconds
        cache_file: Path to cache file
        cache_max_age: Maximum age of cache in seconds
        callback: Optional callback function to call with result

    Returns:
        Future object that will contain the list of channels

    Example:
        future = fetch_channels_async(callback=on_channels_loaded)
        # UI remains responsive while fetching...
        channels = future.result()  # Blocks until complete
    """
    # Use HttpClient's singleton executor for consistency and proper resource management
    from .http_client import HttpClient

    def _fetch():
        try:
            channels = fetch_channels(
                timeout=timeout,
                cache_file=cache_file,
                cache_max_age=cache_max_age,
            )
            if callback:
                callback(channels)
            return channels
        except (requests.RequestException, requests.Timeout) as e:
            # Specific network errors
            logging.error(f"Network error fetching channels: {type(e).__name__}: {e}")
            if callback:
                callback(None)
            return None
        except (json.JSONDecodeError, IOError) as e:
            # Data processing errors
            logging.error(f"Error processing channel data: {type(e).__name__}: {e}")
            if callback:
                callback(None)
            return None
        except (OSError, ValueError) as e:
            # Channel data validation errors
            logging.error(f"Channel data error: {type(e).__name__}: {e}")
            if callback:
                callback(None)
            return None
        except Exception as e:
            # Catch-all for unexpected errors with full traceback
            logging.exception(f"Unexpected error fetching channels: {type(e).__name__}: {e}")
            if callback:
                callback(None)
            return None

    # Submit to singleton executor using public method (will be properly shut down on application exit)
    return HttpClient.get_instance().get_executor().submit(_fetch)


def load_channel_usage(usage_file: str) -> Dict[str, int]:
    """Load channel usage history."""
    if not os.path.exists(usage_file):
        return {}

    try:
        with open(usage_file, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def save_channel_usage(usage_file: str, usage: Dict[str, int]) -> None:
    """Save channel usage history."""
    try:
        os.makedirs(os.path.dirname(usage_file), exist_ok=True)
        with open(usage_file, "w") as f:
            json.dump(usage, f)
    except IOError as e:
        logging.error(f"Error saving channel usage: {e}")


def clean_channel_usage(usage: Dict[str, int], valid_ids: Set[str]) -> Dict[str, int]:
    """Remove non-existent channels from history."""
    return {k: v for k, v in usage.items() if k in valid_ids}


def sort_channels_by_usage(channels: List[Channel], usage: Dict[str, int]) -> List[Channel]:
    """Sort channels by usage (most recently listened first)."""
    def sort_key(ch: Channel) -> tuple:
        last = usage.get(ch.id, 0)
        if last == 0:
            # Channels without usage go to the end
            return (1, 0)
        else:
            # Channels with usage go to the beginning, sorted by descending usage (most recent first)
            return (0, -last)

    return sorted(channels, key=sort_key)


def get_valid_channel_ids(channels: List[Channel]) -> Set[str]:
    """Get set of all channel IDs."""
    return {ch.id for ch in channels}


def filter_channels_by_query(channels: List[Channel], query: str) -> List[Channel]:
    """Filter channels by search query."""
    if not query:
        return channels

    query_lower = query.lower()
    return [
        ch for ch in channels
        if query_lower in ch.title.lower()
        or (ch.description and query_lower in ch.description.lower())
    ]


def load_favorites(favorites_file: str) -> Set[str]:
    """Load favorite channels list."""
    if not os.path.exists(favorites_file):
        return set()

    try:
        with open(favorites_file, "r") as f:
            return set(json.load(f))
    except json.JSONDecodeError:
        return set()


def save_favorites(favorites_file: str, favorites: Set[str]) -> None:
    """Save favorite channels list."""
    try:
        os.makedirs(os.path.dirname(favorites_file), exist_ok=True)
        with open(favorites_file, "w") as f:
            json.dump(list(favorites), f)
    except IOError as e:
        logging.error(f"Error saving favorites: {e}")


def toggle_favorite(channel_id: str, favorites_file: str) -> Set[str]:
    """Toggle channel favorite status."""
    favorites = load_favorites(favorites_file)

    if channel_id in favorites:
        favorites.remove(channel_id)
    else:
        favorites.add(channel_id)

    save_favorites(favorites_file, favorites)
    return favorites


def update_channel_usage(channel_id: str, usage_file: str, valid_ids: Set[str]) -> Dict[str, int]:
    """Update channel last usage time."""
    import time

    usage = load_channel_usage(usage_file)
    now = int(time.time())
    usage[channel_id] = now

    # Clean up non-existent channels
    usage = clean_channel_usage(usage, valid_ids)
    save_channel_usage(usage_file, usage)

    return usage


# Track favorites functions


@dataclass
class FavoriteTrack:
    """Favorite track data"""
    artist: str
    title: str
    channel_id: str
    channel_name: str
    added_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "artist": self.artist,
            "title": self.title,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "added_at": self.added_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FavoriteTrack":
        """Create from dictionary."""
        return cls(
            artist=data.get("artist", "Unknown"),
            title=data.get("title", "Unknown"),
            channel_id=data.get("channel_id", ""),
            channel_name=data.get("channel_name", ""),
            added_at=data.get("added_at", ""),
        )


def load_favorite_tracks(tracks_file: str) -> List[FavoriteTrack]:
    """Load favorite tracks list."""
    if not os.path.exists(tracks_file):
        return []

    try:
        with open(tracks_file, "r") as f:
            data = json.load(f)
            return [FavoriteTrack.from_dict(item) for item in data]
    except (json.JSONDecodeError, IOError):
        return []


def save_favorite_tracks(tracks_file: str, tracks: List[FavoriteTrack]) -> None:
    """Save favorite tracks list."""
    try:
        os.makedirs(os.path.dirname(tracks_file), exist_ok=True)
        with open(tracks_file, "w") as f:
            json.dump([track.to_dict() for track in tracks], f, indent=2)
    except IOError as e:
        logging.error(f"Error saving favorite tracks: {e}")


def add_favorite_track(
    tracks_file: str,
    artist: str,
    title: str,
    channel_id: str,
    channel_name: str,
) -> List[FavoriteTrack]:
    """Add a track to favorites."""
    tracks = load_favorite_tracks(tracks_file)

    # Check if track already exists
    for track in tracks:
        if (track.artist == artist and track.title == title and track.channel_id == channel_id):
            logging.info(f"Track already in favorites: {artist} - {title}")
            return tracks

    new_track = FavoriteTrack(
        artist=artist,
        title=title,
        channel_id=channel_id,
        channel_name=channel_name,
    )
    tracks.insert(0, new_track)  # Add to beginning
    save_favorite_tracks(tracks_file, tracks)
    return tracks


def is_track_favorite(
    tracks_file: str,
    artist: str,
    title: str,
    channel_id: str,
) -> bool:
    """Check if a track is in favorites."""
    tracks = load_favorite_tracks(tracks_file)
    for track in tracks:
        if (track.artist == artist and track.title == title and track.channel_id == channel_id):
            return True
    return False
