"""Playback controller module.

Manages audio playback including play, pause, stop, volume control, and bitrate cycling.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Callable, Tuple

from ..models import Channel, TrackMetadata
from ..mpris_service import MPRISService
from ..ui import UIScreen
from ..channels import (
    load_channel_usage,
    save_channel_usage,
    clean_channel_usage,
    load_favorite_tracks,
    add_favorite_track,
    is_track_favorite,
    toggle_favorite,
)
from .state import StateManager


class PlaybackController:
    """Controller for audio playback management.
    
    Responsibilities:
    - Play/pause/stop channels
    - Volume control
    - Bitrate cycling
    - MPRIS integration
    - Track metadata management
    """

    def __init__(
        self,
        player_instance: Any,
        mpv_player: Any,
        ui_screen: UIScreen,
        state_manager: StateManager,
        config: Dict[str, Any],
        cache_dir: str,
        channel_usage_file: str,
        channel_favorites_file: str,
        track_favorites_file: str,
    ):
        self.player_instance = player_instance
        self.player = mpv_player
        self.ui_screen = ui_screen
        self.state_manager = state_manager
        self.config = config
        self.cache_dir = cache_dir
        self.channel_usage_file = channel_usage_file
        self.channel_favorites_file = channel_favorites_file
        self.track_favorites_file = track_favorites_file

        self.mpris_service: Optional[MPRISService] = None
        self.current_channel: Optional[Channel] = None
        self.current_metadata = TrackMetadata()
        self.current_bitrate = ""
        self.is_playing = False
        self.is_paused = False

        self._on_playback_change: Optional[Callable] = None

    def set_mpris_service(self, mpris_service: Optional[MPRISService]) -> None:
        """Set MPRIS service reference."""
        self.mpris_service = mpris_service

    def set_on_playback_change(self, callback: Callable) -> None:
        """Set callback for playback state changes."""
        self._on_playback_change = callback

    def play_channel(self, channel: Channel, current_index: int) -> None:
        """Play a channel.
        
        Args:
            channel: Channel to play
            current_index: Index of channel in the list
        """
        try:
            # Update usage
            now = int(time.time())
            usage = load_channel_usage(self.channel_usage_file)
            channels = getattr(self.player_instance, 'channels', [])
            valid_ids = {ch.id for ch in channels}
            usage[channel.id] = now
            usage = clean_channel_usage(usage, valid_ids)
            save_channel_usage(self.channel_usage_file, usage)

            # Get stream URL
            stream_url = channel.get_stream_url()
            if not stream_url:
                raise ValueError(f"No MP3 stream found for channel {channel.title}")

            # Stop current playback
            if self.player:
                self.player.stop()

            # Start playback
            self.player.pause = False
            self.player.play(stream_url)

            self.current_channel = channel
            self.is_playing = True
            self.is_paused = False

            # Set initial bitrate - use first available bitrate (highest quality mp3)
            available = channel.get_available_bitrates()
            self.current_bitrate = available[0] if available else "mp3:128k"

            self.ui_screen.current_channel = channel
            self.ui_screen.player = self.player

            logging.info(f"Playing channel: {channel.title}")

            # Set initial metadata
            initial_metadata = TrackMetadata()
            self.current_metadata = initial_metadata
            self.ui_screen.update_metadata(initial_metadata)

            # Update MPRIS
            if self.mpris_service:
                self.mpris_service.update_playback_status("Playing")
                if self.config.get("dbus_send_metadata", False):
                    self.mpris_service.update_metadata(initial_metadata.to_dict())

            # Trigger callback
            if self._on_playback_change:
                self._on_playback_change()

        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Error saving channel usage: {e}")
            self.is_playing = False
            self.is_paused = False
            self.current_channel = None
        except ValueError as e:
            logging.error(f"Invalid channel configuration: {e}")
            self.is_playing = False
            self.is_paused = False
            self.current_channel = None
        except (OSError, IOError) as e:
            logging.error(f"Playback I/O error: {e}")
            self.is_playing = False
            self.is_paused = False
            self.current_channel = None

            if self.mpris_service:
                self.mpris_service.update_playback_status("Stopped")

            if self._on_playback_change:
                self._on_playback_change()

    def toggle_playback(self) -> None:
        """Toggle pause/playback."""
        if not self.is_playing:
            return

        if self.is_paused:
            self.player.pause = False
            self.is_paused = False
            if self.mpris_service:
                self.mpris_service.update_playback_status("Playing")
        else:
            self.player.pause = True
            self.is_paused = True
            if self.mpris_service:
                self.mpris_service.update_playback_status("Paused")

        if self._on_playback_change:
            self._on_playback_change()

    def stop_playback(self) -> None:
        """Stop playback."""
        if not self.is_playing:
            return

        self.player.stop()
        self.is_playing = False
        self.is_paused = False
        self.current_channel = None

        self.current_metadata = TrackMetadata()
        self.ui_screen.current_metadata = self.current_metadata
        self.ui_screen.clear_history()

        if self.mpris_service:
            self.mpris_service.update_playback_status("Stopped")

        if self._on_playback_change:
            self._on_playback_change()

    def set_volume(self, volume: int) -> None:
        """Set volume (0-100).
        
        Args:
            volume: Volume level (0-100)
        """
        self.volume = max(0, min(100, volume))
        self.config["volume"] = self.volume

        if self.player:
            self.player.volume = self.volume

    def get_volume(self) -> int:
        """Get current volume level."""
        return getattr(self, 'volume', self.config.get("volume", 100))

    def increase_volume(self, step: int = 5) -> None:
        """Increase volume by step."""
        self.set_volume(self.get_volume() + step)

    def decrease_volume(self, step: int = 5) -> None:
        """Decrease volume by step."""
        self.set_volume(self.get_volume() - step)

    def cycle_bitrate(self) -> None:
        """Cycle to next available bitrate for current channel."""
        if not self.current_channel:
            return

        available = self.current_channel.get_available_bitrates()
        if len(available) <= 1:
            return

        try:
            current_index = available.index(self.current_bitrate)
            next_index = (current_index + 1) % len(available)
        except ValueError:
            next_index = 0

        self.current_bitrate = available[next_index]
        new_url = self.current_channel.get_stream_url_for_bitrate(self.current_bitrate)

        if new_url and self.is_playing:
            # Restart playback with new bitrate
            self.player.stop()
            self.player.pause = False
            self.player.play(new_url)

            logging.info(f"Switched to bitrate: {self.current_bitrate}")

    def toggle_channel_favorite(self) -> Tuple[bool, str]:
        """Toggle favorite status for selected channel.

        Returns:
            Tuple of (success, message)
        """
        channels = getattr(self.player_instance, 'channels', [])
        if not channels:
            return False, "No channels available"

        # Get selected channel from state manager (correct index)
        current_index = self.state_manager.current_index
        if current_index < len(channels):
            channel_id = channels[current_index].id
            favorites = toggle_favorite(channel_id, self.channel_favorites_file)

            is_favorite = channel_id in favorites
            message = "Added to favorites" if is_favorite else "Removed from favorites"

            # Trigger UI update
            if self._on_playback_change:
                self._on_playback_change()

            return True, message

        return False, "Cannot toggle favorite"

    def toggle_favorite_track(self) -> Tuple[bool, str]:
        """Add current track to favorites.

        Requires track metadata to be available.

        Returns:
            Tuple of (success, message)
        """
        if not self.is_playing or not self.current_channel:
            return False, "No channel playing"

        # Add current track to favorites
        artist = self.current_metadata.artist
        title = self.current_metadata.title

        # Don't add if metadata is not available
        if artist in ("Loading...", "Unknown") or title in ("Loading...", "Unknown"):
            return False, "No track metadata available"

        add_favorite_track(
            self.track_favorites_file,
            artist=artist,
            title=title,
            channel_id=self.current_channel.id,
            channel_name=self.current_channel.title,
        )
        return True, f"Added to favorites: {artist} - {title}"

    def update_metadata(self, metadata: TrackMetadata) -> None:
        """Update current track metadata.
        
        Args:
            metadata: New track metadata
        """
        if metadata.artist != self.current_metadata.artist or metadata.title != self.current_metadata.title:
            self.ui_screen.add_to_history(self.current_metadata)
            self.current_metadata = metadata
            self.ui_screen.update_metadata(metadata)

            # Update MPRIS if enabled
            if self.mpris_service and self.config.get("dbus_send_metadata", False):
                self.mpris_service.update_metadata(metadata.to_dict())

    def get_playback_status(self) -> str:
        """Get current playback status."""
        if not self.is_playing:
            return "Stopped"
        return "Paused" if self.is_paused else "Playing"
