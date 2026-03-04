"""SomaFM TUI Player main module"""

import os
import sys
import time
import logging
import signal
import threading
import locale
from typing import Optional, List, Any

# Set locale to C for MPV compatibility
locale.setlocale(locale.LC_NUMERIC, "C")

# Python version check
if sys.version_info < (3, 8):
    print("Error: Python 3.8 or higher is required")
    sys.exit(1)

import curses
import mpv
import requests

from somafm_tui.config import load_config, save_config, validate_config, CONFIG_DIR, CONFIG_FILE
from somafm_tui.themes import get_color_themes, get_theme_names, init_custom_colors, apply_theme
from somafm_tui.models import TrackMetadata, Channel, AppConfig
from somafm_tui.channels import (
    fetch_channels,
    filter_channels_by_query,
    load_favorites,
    save_favorites,
    toggle_favorite,
    load_channel_usage,
    save_channel_usage,
    clean_channel_usage,
    sort_channels_by_usage,
    load_favorite_tracks,
    add_favorite_track,
    is_track_favorite,
)
from somafm_tui.ui import UIScreen
from somafm_tui.timer import SleepTimer
from somafm_tui.mpris_service import MPRISService, run_mpris_loop


# Constants
TEMP_DIR = "/tmp/.somafmtmp"
CACHE_DIR = os.path.join(TEMP_DIR, "cache")
CHANNEL_CACHE_FILE = os.path.join(CACHE_DIR, "channels.json")
CHANNEL_USAGE_FILE = os.path.join(CONFIG_DIR, "channel_usage.json")
CHANNEL_FAVORITES_FILE = os.path.join(CONFIG_DIR, "channel_favorites.json")
TRACK_FAVORITES_FILE = os.path.join(CONFIG_DIR, "track_favorites.json")


def ensure_directories() -> None:
    """Create required directories"""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)


def setup_logging() -> None:
    """Configure logging"""
    os.makedirs(TEMP_DIR, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(TEMP_DIR, "somafm.log"),
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def check_mpv() -> bool:
    """Check if MPV is available"""
    try:
        import subprocess

        result = subprocess.run(
            ["mpv", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        return result.returncode == 0
    except Exception:
        return False


def _signal_handler(signum, frame):
    """Handle termination signals"""
    signal_name = signal.Signals(signum).name
    logging.info(f"Received {signal_name}, shutting down...")
    # Set flag to stop the main loop
    if hasattr(_global_player, '_signal_received'):
        _global_player._signal_received = True
        _global_player.running = False


_global_player: Optional["SomaFMPlayer"] = None


class SomaFMPlayer:
    """Main player class"""

    def __init__(self):
        self.had_error = False
        self._signal_received = False
        ensure_directories()
        setup_logging()
        self._setup_signal_handlers()

        if not check_mpv():
            print("Error: MPV player is not installed or not in PATH")
            print("Please install MPV using your package manager:")
            print("  - Arch Linux: sudo pacman -S mpv")
            print("  - Ubuntu/Debian: sudo apt-get install mpv")
            print("  - Fedora: sudo dnf install mpv")
            sys.exit(1)

        self.config = validate_config(load_config())
        self._init_mpv()
        self._init_mpris()
        self._fetch_channels()

        # Player state
        self.current_channel: Optional[Channel] = None
        self.current_index = 0
        self.is_playing = False
        self.is_paused = False
        self.scroll_offset = 0
        self.running = True

        # UI state
        self.ui_screen = UIScreen()
        self.stdscr: Optional[curses.window] = None
        self.volume = self.config.get("volume", 100)

        # Search state
        self.is_searching = False
        self.search_query = ""
        self.filtered_channels: List[Channel] = []

        # Help state
        self.show_help = False

        # Sleep timer state
        self.sleep_timer = SleepTimer()
        self.sleep_overlay_active = False
        self.sleep_input = ""
        self._last_timer_display = 0
        self._last_timer_check = 0

        # Bitrate state
        self.current_bitrate = ""

        # Metadata observer
        @self.player.property_observer("metadata")
        def metadata_handler(name: str, value: Any) -> None:
            if value:
                track_info = value.get("icy-title", "")
                if track_info:
                    for separator in [" - ", " – "]:
                        if separator in track_info:
                            parts = track_info.split(separator, 1)
                            if len(parts) == 2:
                                metadata = TrackMetadata(
                                    artist=parts[0].strip(),
                                    title=parts[1].strip(),
                                    duration="--:--",
                                )
                                self.current_metadata = metadata
                                self.ui_screen.update_metadata(metadata)
                                if self.stdscr:
                                    self._display_interface()

                                if self.mpris_service and self.config.get("dbus_send_metadata", False):
                                    self.mpris_service.update_metadata(metadata.to_dict())
                                break

        self.current_metadata = TrackMetadata()

    def _init_mpv(self) -> None:
        """Initialize MPV"""
        self.player = mpv.MPV(input_default_bindings=True, input_vo_keyboard=True, osc=True)

    def _init_mpris(self) -> None:
        """Initialize MPRIS service"""
        self.mpris_service: Optional[MPRISService] = None
        self.mpris_thread: Optional[threading.Thread] = None

        if not self.config.get("dbus_allowed", False):
            logging.info("MPRIS service disabled by configuration")
            return

        try:
            self.mpris_service = MPRISService(self, cache_dir=CACHE_DIR)
            self.mpris_thread = threading.Thread(
                target=run_mpris_loop, args=(self.mpris_service,), daemon=True
            )
            self.mpris_thread.start()
            logging.info("MPRIS service thread started")
        except Exception as e:
            logging.error(f"Failed to start MPRIS service: {e}")

    def _fetch_channels(self) -> None:
        """Fetch channel list"""
        try:
            channels = fetch_channels(cache_file=CHANNEL_CACHE_FILE)

            # Load usage and sort
            usage = load_channel_usage(CHANNEL_USAGE_FILE)
            valid_ids = {ch.id for ch in channels}
            usage = clean_channel_usage(usage, valid_ids)

            self.channels = sort_channels_by_usage(channels, usage)
            save_channel_usage(CHANNEL_USAGE_FILE, usage)

        except Exception as e:
            print(f"Error fetching channel list: {e}")
            sys.exit(1)

    def init_colors(self) -> None:
        """Initialize colors"""
        curses.start_color()
        init_custom_colors()

        theme_name = self.config.get("theme", "default")
        themes = get_color_themes()

        if theme_name not in themes:
            theme_name = "default"

        theme = themes[theme_name]
        bg_color = theme["bg_color"]

        apply_theme(theme_name, bg_color)

    def _display_interface(self) -> None:
        """Display the interface"""
        channel_favorites = load_favorites(CHANNEL_FAVORITES_FILE)

        # Filter channels if searching
        if self.is_searching:
            if self.search_query:
                self.filtered_channels = filter_channels_by_query(self.channels, self.search_query)
            else:
                self.filtered_channels = self.channels
            channels_to_display = self.filtered_channels
        else:
            channels_to_display = self.channels

        # Update scroll offset
        if self.stdscr:
            max_y, max_x = self.stdscr.getmaxyx()
            panel_height = max_y - 2
            visible_channels = panel_height - 3
            max_scroll = max(0, len(channels_to_display) - visible_channels)

            if self.current_index < self.scroll_offset:
                self.scroll_offset = self.current_index
            elif self.current_index >= self.scroll_offset + visible_channels:
                self.scroll_offset = min(max_scroll, self.current_index - visible_channels + 1)

            self.scroll_offset = max(0, min(max_scroll, self.scroll_offset))

            # Ensure current selection is visible
            if self.current_index >= len(channels_to_display):
                self.current_index = max(0, len(channels_to_display) - 1)

            self.ui_screen.display(
                self.stdscr,
                channels_to_display,
                self.current_index,
                self.scroll_offset,
                channel_favorites,
                self.current_channel,
                self.player,
                self.is_playing,
                is_searching=self.is_searching,
                search_query=self.search_query,
                show_help=self.show_help,
                current_bitrate=self.current_bitrate,
            )

            # Show sleep overlay if active
            if self.sleep_overlay_active:
                self.ui_screen.display_sleep_overlay(self.stdscr, self.sleep_input)

            # Show sleep timer countdown if active
            if self.sleep_timer.is_active():
                self.ui_screen.display_sleep_timer(self.stdscr, self.sleep_timer.format_remaining())

    def _play_channel(self, channel: Channel) -> None:
        """Play channel"""
        try:
            # Update usage
            now = int(time.time())
            usage = load_channel_usage(CHANNEL_USAGE_FILE)
            valid_ids = {ch.id for ch in self.channels}
            usage[channel.id] = now
            usage = clean_channel_usage(usage, valid_ids)
            save_channel_usage(CHANNEL_USAGE_FILE, usage)

            # Get stream URL
            stream_url = channel.get_stream_url()
            if not stream_url:
                raise Exception(f"No MP3 stream found for channel {channel.title}")

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
            self.ui_screen.update_metadata(initial_metadata)

            # Update MPRIS
            if self.mpris_service:
                self.mpris_service.update_playback_status("Playing")
                if self.config.get("dbus_send_metadata", False):
                    self.mpris_service.update_metadata(initial_metadata.to_dict())

        except Exception as e:
            logging.error(f"Error playing channel: {e}")
            print(f"Error playing channel: {e}")
            self.is_playing = False
            self.is_paused = False
            self.current_channel = None

            if self.mpris_service:
                self.mpris_service.update_playback_status("Stopped")

    def _toggle_playback(self) -> None:
        """Toggle pause/playback"""
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

    def _set_volume(self, volume: int) -> None:
        """Set volume (0-100)"""
        self.volume = max(0, min(100, volume))
        self.config["volume"] = self.volume
        save_config(self.config)

        if self.player:
            self.player.volume = self.volume

    def _increase_volume(self, step: int = 5) -> None:
        """Increase volume"""
        self._set_volume(self.volume + step)
        if self.stdscr:
            self.ui_screen.show_volume(self.stdscr, self.volume)
            self._display_interface()

    def _decrease_volume(self, step: int = 5) -> None:
        """Decrease volume"""
        self._set_volume(self.volume - step)
        if self.stdscr:
            self.ui_screen.show_volume(self.stdscr, self.volume)
            self._display_interface()

    def _stop_playback(self) -> None:
        """Stop playback"""
        if not self.is_playing:
            return

        self.player.stop()
        self.is_playing = False
        self.is_paused = False
        self.current_channel = None

        self.current_metadata = TrackMetadata()
        self.ui_screen.current_metadata = self.current_metadata

        if self.mpris_service:
            self.mpris_service.update_playback_status("Stopped")

    def _cycle_theme(self) -> None:
        """Cycle through themes"""
        themes = get_theme_names()
        current_theme = self.config.get("theme", "default")

        try:
            current_index = themes.index(current_theme)
            next_index = (current_index + 1) % len(themes)
        except ValueError:
            next_index = 0

        new_theme = themes[next_index]
        self.config["theme"] = new_theme
        save_config(self.config)

        self.init_colors()

        if self.stdscr:
            self.stdscr.clear()
            self.stdscr.refresh()

        themes_dict = get_color_themes()
        theme_info = themes_dict[new_theme]

        if self.stdscr:
            self.ui_screen.show_notification(
                self.stdscr, f"Theme: {theme_info['name']}", timeout=1.0
            )

    def _cleanup(self) -> None:
        """Clean up resources"""
        if self.player:
            self.player.terminate()

        if not self.had_error and os.path.exists(TEMP_DIR):
            try:
                for root, dirs, files in os.walk(TEMP_DIR, topdown=False):
                    for name in files:
                        os.remove(os.path.join(root, name))
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                os.rmdir(TEMP_DIR)
            except Exception as e:
                logging.error(f"Error cleaning up temp directory: {e}")

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown"""
        global _global_player
        _global_player = self

        signal.signal(signal.SIGTERM, _signal_handler)
        signal.signal(signal.SIGINT, _signal_handler)

    def run(self) -> None:
        """Run main application loop"""

        def main(stdscr: curses.window) -> None:
            try:
                self.stdscr = stdscr
                self.init_colors()

                stdscr.keypad(True)
                curses.raw()
                stdscr.nodelay(True)

                self._display_interface()

                while self.running and not self._signal_received:
                    current_time = time.time()

                    # Check timer expiration every minute
                    if self.sleep_timer.is_active():
                        if current_time - self._last_timer_check >= 60:
                            self._last_timer_check = current_time
                        if self.sleep_timer.get_remaining_seconds() <= 0:
                            logging.info("Sleep timer expired, shutting down")
                            self.running = False
                            break

                    # Update timer display every second
                    if self.sleep_timer.is_active():
                        if current_time - self._last_timer_display >= 1:
                            self._last_timer_display = current_time
                            self.ui_screen.display_sleep_timer(
                                self.stdscr, self.sleep_timer.format_remaining()
                            )
                            stdscr.refresh()

                    # Check volume display timeout
                    needs_refresh = False
                    if (
                        self.ui_screen.volume_display is not None
                        and time.time() - self.ui_screen.volume_display_time >= 3
                    ):
                        self.ui_screen.volume_display = None
                        needs_refresh = True

                    if needs_refresh:
                        self._display_interface()

                    # Get user input
                    try:
                        key = stdscr.get_wch()
                        if key is not None:
                            self._handle_input(key)
                        else:
                            time.sleep(0.1)
                    except curses.error:
                        time.sleep(0.1)
                        continue

            except Exception as e:
                self.had_error = True
                logging.error(f"Application error: {e}")
                raise
            finally:
                self._cleanup()

        try:
            curses.wrapper(main)
        except Exception as e:
            self.had_error = True
            logging.error(f"Fatal error: {e}")
            print(f"An error occurred. Check logs at {os.path.join(TEMP_DIR, 'somafm.log')}")
            sys.exit(1)

    def _handle_input(self, key: Any) -> None:
        """Handle user input"""
        if self.sleep_overlay_active:
            self._handle_sleep_input(key)
        elif self.is_searching:
            self._handle_search_input(key)
        else:
            self._handle_normal_input(key)

        self._display_interface()

    def _handle_sleep_input(self, key: Any) -> None:
        """Handle input in sleep overlay mode"""
        if key == chr(27):  # ESC
            self.sleep_overlay_active = False
            self.sleep_input = ""
        elif key in (curses.KEY_BACKSPACE, "\b", "\x7f"):
            self.sleep_input = self.sleep_input[:-1]
        elif isinstance(key, str) and key.isdigit():
            # Limit to 3 digits (max 999 minutes)
            if len(self.sleep_input) < 3:
                self.sleep_input += key
        elif key in (curses.KEY_ENTER, "\n", "\r"):
            # Set timer
            if self.sleep_input:
                try:
                    minutes = int(self.sleep_input)
                    if minutes > 0:
                        self.sleep_timer.set(minutes)
                        if self.stdscr:
                            self.ui_screen.show_notification(self.stdscr, f"Sleep timer: {minutes} min")
                except ValueError:
                    pass
            self.sleep_overlay_active = False
            self.sleep_input = ""

    def _handle_search_input(self, key: Any) -> None:
        """Handle input in search mode"""
        if key == chr(27):  # ESC
            self.is_searching = False
            self.search_query = ""
        elif key == "?":
            self.is_searching = False
            self.show_help = not self.show_help
        elif key in (curses.KEY_BACKSPACE, "\b", "\x7f"):
            self.search_query = self.search_query[:-1]
        elif isinstance(key, str) and len(key) == 1 and key.isprintable():
            self.search_query += key
            self.current_index = 0
        elif key == curses.KEY_UP or (isinstance(key, str) and key == "k"):
            self.current_index = max(0, self.current_index - 1)
        elif key == curses.KEY_DOWN or (isinstance(key, str) and key == "j"):
            if self.filtered_channels:
                self.current_index = min(len(self.filtered_channels) - 1, self.current_index + 1)
        elif key == curses.KEY_PPAGE:
            if self.is_playing:
                self._increase_volume()
        elif key == curses.KEY_NPAGE:
            if self.is_playing:
                self._decrease_volume()
        elif key in (curses.KEY_ENTER, "\n", "\r") or (isinstance(key, str) and key == "l"):
            if self.filtered_channels:
                selected_channel = self.filtered_channels[self.current_index]
                self._play_channel(selected_channel)
                # Find original index
                for i, ch in enumerate(self.channels):
                    if ch.id == selected_channel.id:
                        self.current_index = i
                        break
                self.is_searching = False
                self.search_query = ""

    def _handle_normal_input(self, key: Any) -> None:
        """Handle input in normal mode"""
        if isinstance(key, str):
            if key == "/":
                self.is_searching = True
                self.search_query = ""
                self.current_index = 0
            elif key == "?":
                self.show_help = not self.show_help
            elif key == chr(27):  # ESC - close help
                if self.show_help:
                    self.show_help = False
            elif key in ("q", "Q"):
                self.running = False
            elif key in ("h", "H"):
                self._stop_playback()
            elif key in ("\n", "\r", "l"):
                self._play_channel(self.channels[self.current_index])
            elif key == " ":
                if self.is_playing:
                    self._toggle_playback()
            elif key in ("f", "F"):
                self._toggle_favorite()
            elif key == "k":
                self.current_index = max(0, self.current_index - 1)
            elif key == "j":
                self.current_index = min(len(self.channels) - 1, self.current_index + 1)
            elif key in ("t", "T"):
                self._cycle_theme()
            elif key in ("v", "V"):
                self._decrease_volume()
            elif key in ("b", "B"):
                self._increase_volume()
            elif key in ("s", "S"):
                self.sleep_overlay_active = True
                self.sleep_input = ""
            elif key in ("r", "R"):
                self._cycle_bitrate()
        else:
            # Special keys
            if key == curses.KEY_UP:
                self.current_index = max(0, self.current_index - 1)
            elif key == curses.KEY_DOWN:
                self.current_index = min(len(self.channels) - 1, self.current_index + 1)
            elif key == curses.KEY_ENTER:
                self._play_channel(self.channels[self.current_index])
            elif key == curses.KEY_PPAGE:
                self._increase_volume()
            elif key == curses.KEY_NPAGE:
                self._decrease_volume()

    def _toggle_favorite(self) -> None:
        """Toggle favorite status (track if playing, channel if not)"""
        if not self.channels:
            return

        if self.is_playing and self.current_channel and self.current_metadata:
            # Add current track to favorites
            artist = self.current_metadata.artist
            title = self.current_metadata.title
            
            # Don't add if metadata is not available
            if artist in ("Loading...", "Unknown") or title in ("Loading...", "Unknown"):
                if self.stdscr:
                    self.ui_screen.show_notification(self.stdscr, "No track metadata available")
                return
            
            add_favorite_track(
                TRACK_FAVORITES_FILE,
                artist=artist,
                title=title,
                channel_id=self.current_channel.id,
                channel_name=self.current_channel.title,
            )
            
            if self.stdscr:
                self.ui_screen.show_notification(
                    self.stdscr, 
                    f"Added to favorites: {artist} - {title}"
                )
        else:
            # Toggle channel favorite
            channel_id = self.channels[self.current_index].id
            favorites = toggle_favorite(channel_id, CHANNEL_FAVORITES_FILE)

            is_favorite = channel_id in favorites
            message = "Added to favorites" if is_favorite else "Removed from favorites"

            if self.stdscr:
                self.ui_screen.show_notification(self.stdscr, message)

    def _cycle_bitrate(self) -> None:
        """Cycle to next available bitrate"""
        if not self.current_channel or not self.is_playing:
            return

        available = self.current_channel.get_available_bitrates()
        if len(available) <= 1:
            return

        # Find current bitrate index
        current = self.current_bitrate if self.current_bitrate else self.current_channel.bitrate

        try:
            current_idx = available.index(current)
            # Move to next (lower quality), wrap around to highest
            next_idx = (current_idx + 1) % len(available)
        except ValueError:
            # Current bitrate not in list, use first (highest)
            next_idx = 0

        new_bitrate = available[next_idx]
        new_url = self.current_channel.get_stream_url_for_bitrate(new_bitrate)

        if new_url:
            # Restart playback with new bitrate
            was_paused = self.is_paused
            self.player.stop()
            self.player.play(new_url)
            if was_paused:
                self.player.pause = True

            self.current_bitrate = new_bitrate

            # Extract bitrate label for notification (e.g., 'mp3:128k' -> '128k')
            bitrate_label = new_bitrate.split(":")[1] if ":" in new_bitrate else new_bitrate

            if self.stdscr:
                # Show notification without blocking
                self.ui_screen.show_notification(self.stdscr, f"Bitrate: {bitrate_label}", timeout=0.5)


def main() -> None:
    """Entry point"""
    player = SomaFMPlayer()
    player.run()


if __name__ == "__main__":
    main()
