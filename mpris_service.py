"""MPRIS D-Bus service for media keys integration"""

import asyncio
import logging
import os
import hashlib
import threading
from typing import Optional, Any, Dict

import requests
from dbus_next.aio.message_bus import MessageBus
from dbus_next.signature import Variant
from dbus_next.constants import BusType
from dbus_next.service import ServiceInterface, method, dbus_property

DBUS_NAME = "org.mpris.MediaPlayer2.somafm_tui"
DBUS_TITLE = "SomaFM TUI Player"
ARTWORKS_TIMEOUT = 10


class MediaPlayer2Interface(ServiceInterface):
    """MediaPlayer2 interface"""

    def __init__(self, player_instance):
        super().__init__("org.mpris.MediaPlayer2")
        self.player = player_instance

    @method()
    def Raise(self) -> None:
        pass

    @method()
    def Quit(self) -> None:
        self.player.running = False

    @dbus_property()
    def CanQuit(self) -> "b":
        return True

    @dbus_property()
    def CanRaise(self) -> "b":
        return False

    @dbus_property()
    def HasTrackList(self) -> "b":
        return False

    @dbus_property()
    def Identity(self) -> "s":
        return DBUS_TITLE

    @dbus_property()
    def SupportedUriSchemes(self) -> "as":
        return ["http", "https"]

    @dbus_property()
    def SupportedMimeTypes(self) -> "as":
        return ["audio/mpeg", "audio/mp3"]


class MediaPlayer2PlayerInterface(ServiceInterface):
    """MediaPlayer2.Player interface"""

    def __init__(self, player_instance, artworks_dir: Optional[str], with_artworks: bool):
        super().__init__("org.mpris.MediaPlayer2.Player")
        self.player = player_instance
        self.with_artworks = with_artworks
        self.artworks_dir = artworks_dir
        self._playback_status = "Stopped"
        self._metadata: Dict[str, Any] = {}
        self._playback_rate = 1.0
        self._position = 0  # microseconds

    @method()
    def Next(self) -> None:
        if hasattr(self.player, "channels") and self.player.channels:
            total_channels = len(self.player.channels)
            self.player.current_index = (self.player.current_index + 1) % total_channels
            self.player._play_channel(self.player.channels[self.player.current_index])
            if self.player.stdscr:
                self.player._display_interface()

    @method()
    def Previous(self) -> None:
        if hasattr(self.player, "channels") and self.player.channels:
            total_channels = len(self.player.channels)
            self.player.current_index = (self.player.current_index - 1) % total_channels
            self.player._play_channel(self.player.channels[self.player.current_index])
            if self.player.stdscr:
                self.player._display_interface()

    @method()
    def Pause(self) -> None:
        if self.player.is_playing and not self.player.is_paused:
            self.player.player.pause = True
            self.player.is_paused = True
            self._playback_status = "Paused"
            self._emit_properties_changed({"PlaybackStatus": self._playback_status})

    @method()
    def PlayPause(self) -> None:
        if self.player.is_playing:
            self.player._toggle_playback()
            self._playback_status = "Paused" if self.player.is_paused else "Playing"
            self._emit_properties_changed({"PlaybackStatus": self._playback_status})
        elif hasattr(self.player, "channels") and self.player.channels and self.player.current_index < len(
            self.player.channels
        ):
            self.player._play_channel(self.player.channels[self.player.current_index])

    @method()
    def Stop(self) -> None:
        if self.player.is_playing:
            self.player.player.stop()
            self.player.is_playing = False
            self.player.is_paused = False
            self.player.current_channel = None
            if self.player.buffer:
                self.player.buffer.stop_buffering()
                self.player.buffer.clear()
            self._playback_status = "Stopped"
            self._metadata = {}
            self._position = 0
            self._emit_properties_changed(
                {"PlaybackStatus": self._playback_status, "Metadata": self._metadata}
            )

    @method()
    def Play(self) -> None:
        if self.player.is_playing and self.player.is_paused:
            self.player.player.pause = False
            self.player.is_paused = False
            self._playback_status = "Playing"
            self._emit_properties_changed({"PlaybackStatus": self._playback_status})
        elif not self.player.is_playing and hasattr(self.player, "channels") and self.player.channels:
            self.player._play_channel(self.player.channels[self.player.current_index])

    @method()
    def Seek(self, offset: "x") -> None:
        """Seek by offset in microseconds"""
        # For live streams, seeking is not supported, but we acknowledge the request
        # In a real implementation, this would seek within the buffer
        pass

    @method()
    def SetPosition(self, track_id: "o", position: "x") -> None:
        """Set position to position microseconds"""
        # For live streams, position setting is not supported
        pass

    @dbus_property()
    def PlaybackStatus(self) -> "s":
        return self._playback_status

    @dbus_property()
    def Metadata(self) -> "a{sv}":
        return self._metadata

    @dbus_property()
    def Volume(self) -> "d":
        return 1.0

    @Volume.setter
    def Volume(self, value: "d") -> None:
        """Set volume (0.0 - 1.0)"""
        if self.player and hasattr(self.player, 'player'):
            self.player.player.volume = int(value * 100)

    @dbus_property()
    def Position(self) -> "x":
        return self._position

    @dbus_property()
    def PlaybackRate(self) -> "d":
        return self._playback_rate

    @PlaybackRate.setter
    def PlaybackRate(self, value: "d") -> None:
        """Set playback rate"""
        # Clamp to valid range (0.1 - 10.0)
        self._playback_rate = max(0.1, min(10.0, value))

    @dbus_property()
    def CanGoNext(self) -> "b":
        return bool(hasattr(self.player, "channels") and self.player.channels)

    @dbus_property()
    def CanGoPrevious(self) -> "b":
        return bool(hasattr(self.player, "channels") and self.player.channels)

    @dbus_property()
    def CanPlay(self) -> "b":
        return True

    @dbus_property()
    def CanPause(self) -> "b":
        return True

    @dbus_property()
    def CanSeek(self) -> "b":
        return True

    @dbus_property()
    def CanControl(self) -> "b":
        return True

    def update_playback_status(self, status: str) -> None:
        """Update playback status"""
        if self._playback_status != status:
            self._playback_status = status
            self._emit_properties_changed({"PlaybackStatus": status})

    def update_metadata(self, metadata_dict: Dict[str, Any]) -> None:
        """Update track metadata"""
        mpris_metadata: Dict[str, Any] = {}

        if "artist" in metadata_dict and metadata_dict["artist"] != "Loading...":
            mpris_metadata["xesam:artist"] = Variant("as", [metadata_dict["artist"]])

        if "title" in metadata_dict and metadata_dict["title"] != "Loading...":
            mpris_metadata["xesam:title"] = Variant("s", metadata_dict["title"])

        if self.player.current_channel:
            channel = self.player.current_channel
            mpris_metadata["xesam:album"] = Variant("s", channel.title)
            mpris_metadata["mpris:trackid"] = Variant(
                "o", f"/org/somafm/track/{channel.id}"
            )

            if channel.description:
                mpris_metadata["xesam:comment"] = Variant(
                    "s", channel.description
                )

            if self.with_artworks:
                artwork_url = None
                if channel.largeimage:
                    artwork_url = channel.largeimage
                elif channel.image:
                    artwork_url = channel.image

                if artwork_url:
                    local_img_or_url = self._cache_artwork(artwork_url)
                    mpris_metadata["mpris:artUrl"] = Variant("s", local_img_or_url)

        self._metadata = mpris_metadata
        self._emit_properties_changed({"Metadata": mpris_metadata})

    def _cache_artwork(self, artwork_url: str) -> str:
        """Cache artwork image"""
        if not self.artworks_dir:
            return artwork_url

        ext = os.path.splitext(artwork_url)[1] or ".jpg"
        filename = hashlib.sha256(artwork_url.encode()).hexdigest() + ext
        filepath = os.path.join(self.artworks_dir, filename)

        if not os.path.exists(filepath):
            # Try async cache in background, but return URL immediately
            thread = threading.Thread(target=self._async_cache_artwork, args=(artwork_url, filepath))
            thread.daemon = True
            thread.start()
            return artwork_url

        return filepath

    def _async_cache_artwork(self, artwork_url: str, filepath: str) -> None:
        """Asynchronously cache artwork"""
        try:
            response = requests.get(artwork_url, timeout=ARTWORKS_TIMEOUT)
            response.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(response.content)
            logging.debug(f"Artwork cached: {filepath}")
        except requests.RequestException as e:
            logging.error(f"Failed to cache artwork: {e}")
        except IOError as e:
            logging.error(f"Failed to save artwork: {e}")

    def _emit_properties_changed(self, changed_properties: Dict[str, Any]) -> None:
        """Emit properties changed signal"""
        try:
            self.emit_properties_changed(changed_properties, [])
        except Exception as e:
            logging.error(f"Failed to emit properties changed signal: {e}")


class MPRISService:
    """MPRIS service"""

    def __init__(self, player_instance, cache_dir: str):
        self.player = player_instance
        self.bus: Optional[MessageBus] = None
        self.player_interface: Optional[MediaPlayer2PlayerInterface] = None
        self.root_interface: Optional[MediaPlayer2Interface] = None
        self.cache_dir = cache_dir
        self.dbus_send_metadata = player_instance.config.get("dbus_send_metadata", False)
        self.dbus_send_metadata_artworks = player_instance.config.get(
            "dbus_send_metadata_artworks", False
        )
        self.dbus_cache_metadata_artworks = player_instance.config.get(
            "dbus_cache_metadata_artworks", False
        )

        if self.dbus_send_metadata and self.dbus_send_metadata_artworks and self.dbus_cache_metadata_artworks:
            self.artworks_dir = os.path.join(self.cache_dir, "artworks")
            os.makedirs(self.artworks_dir, exist_ok=True)
        else:
            self.artworks_dir = None

    async def start(self) -> bool:
        """Start MPRIS service"""
        try:
            self.bus = await MessageBus(bus_type=BusType.SESSION).connect()
            self.root_interface = MediaPlayer2Interface(self.player)
            self.player_interface = MediaPlayer2PlayerInterface(
                self.player,
                artworks_dir=self.artworks_dir,
                with_artworks=self.dbus_send_metadata_artworks,
            )
            self.bus.export("/org/mpris/MediaPlayer2", self.root_interface)
            self.bus.export("/org/mpris/MediaPlayer2", self.player_interface)
            await self.bus.request_name(DBUS_NAME)
            logging.info("MPRIS service started")
            return True
        except Exception as e:
            logging.error(f"Failed to start MPRIS service: {e}")
            return False

    async def stop(self) -> None:
        """Stop MPRIS service"""
        if self.bus:
            try:
                await self.bus.release_name(DBUS_NAME)
                self.bus.disconnect()
            except Exception as e:
                logging.error(f"Error stopping MPRIS service: {e}")

    def update_playback_status(self, status: str) -> None:
        """Update playback status"""
        if self.player_interface:
            self.player_interface.update_playback_status(status)

    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """Update metadata"""
        if self.player_interface:
            self.player_interface.update_metadata(metadata)


def run_mpris_loop(mpris_service: MPRISService) -> None:
    """Run MPRIS loop"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(mpris_service.start())
        loop.run_forever()
    except Exception as e:
        logging.error(f"MPRIS loop error: {e}")
