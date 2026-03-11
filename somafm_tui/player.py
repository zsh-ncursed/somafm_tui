"""SomaFM TUI Player main module.

Refactored architecture with separated concerns:
- PlaybackController: Audio playback management
- StateManager: Application state management
- InputHandler: User input handling
- UIScreen: Display rendering
"""

import os
import sys
import time
import logging
import signal
import threading
import locale
from typing import Optional, Any, Dict, List

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
    fetch_channels_async,
    load_favorites,
    load_channel_usage,
    save_channel_usage,
    clean_channel_usage,
    sort_channels_by_usage,
)
from somafm_tui.ui import UIScreen
from somafm_tui.timer import SleepTimer
from somafm_tui.mpris_service import MPRISService, run_mpris_loop
from somafm_tui.core import PlaybackController, StateManager, InputHandler
from somafm_tui.cli import (
    parse_args,
    validate_args,
    print_channels,
    print_favorites,
    print_themes,
)


# Constants
TEMP_DIR = "/tmp/.somafmtmp"
CACHE_DIR = os.path.join(TEMP_DIR, "cache")
CHANNEL_CACHE_FILE = os.path.join(CACHE_DIR, "channels.json")
CHANNEL_USAGE_FILE = os.path.join(CONFIG_DIR, "channel_usage.json")
CHANNEL_FAVORITES_FILE = os.path.join(CONFIG_DIR, "channel_favorites.json")
TRACK_FAVORITES_FILE = os.path.join(CONFIG_DIR, "track_favorites.json")


def ensure_directories() -> None:
    """Create required directories."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)


def setup_logging() -> None:
    """Configure logging."""
    os.makedirs(TEMP_DIR, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(TEMP_DIR, "somafm.log"),
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def check_mpv() -> bool:
    """Check if MPV is available."""
    try:
        import subprocess

        result = subprocess.run(
            ["mpv", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        return result.returncode == 0
    except Exception:
        return False


def _create_signal_handler(player_instance: "SomaFMPlayer"):
    """Create a signal handler closure for the given player instance.
    
    Args:
        player_instance: The SomaFMPlayer instance to handle signals for
        
    Returns:
        Signal handler function
    """
    def handler(signum, frame):
        """Handle termination signals."""
        signal_name = signal.Signals(signum).name
        logging.info(f"Received {signal_name}, shutting down...")
        player_instance._signal_received = True
        player_instance.running = False
    return handler


class SomaFMPlayer:
    """Main player class - orchestrates application components.

    This class is now a thin wrapper that:
    - Initializes components (MPV, MPRIS, controllers)
    - Runs the main curses loop
    - Handles signals and cleanup
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        channels: Optional[List[Channel]] = None,
    ):
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

        # Load configuration
        self.config = config if config is not None else validate_config(load_config())

        # Initialize MPV player
        self._init_mpv()

        # Fetch or use provided channels
        if channels is not None:
            self.channels = channels
        else:
            self._fetch_channels()

        # Initialize UI
        self.ui_screen = UIScreen()
        self.stdscr: Optional[curses.window] = None

        # Initialize core components
        self._init_components()

        # Initialize MPRIS
        self._init_mpris()

        # Setup metadata observer
        self._setup_metadata_observer()

    def _init_mpv(self) -> None:
        """Initialize MPV player."""
        self.player = mpv.MPV(input_default_bindings=True, input_vo_keyboard=True, osc=True)

    def _init_components(self) -> None:
        """Initialize core application components."""
        # Initialize state manager first (needed by playback controller)
        self.state = StateManager(
            config=self.config,
            channels=self.channels,
            cache_dir=CACHE_DIR,
            config_file=CONFIG_FILE,
        )

        # Playback controller
        self.playback = PlaybackController(
            player_instance=self,
            mpv_player=self.player,
            ui_screen=self.ui_screen,
            state_manager=self.state,
            config=self.config,
            cache_dir=CACHE_DIR,
            channel_usage_file=CHANNEL_USAGE_FILE,
            channel_favorites_file=CHANNEL_FAVORITES_FILE,
            track_favorites_file=TRACK_FAVORITES_FILE,
        )

        # Input handler
        self.input_handler = InputHandler(
            playback_controller=self.playback,
            state_manager=self.state,
            ui_screen=self.ui_screen,
        )

        # Wire up callbacks
        self.playback.set_mpris_service(None)  # Will be set after MPRIS init
        self.state.set_on_state_change(self._on_state_change)
        self.state.set_on_theme_change(self._on_theme_change)
        self.playback.set_on_playback_change(self._on_state_change)

    def _init_mpris(self) -> None:
        """Initialize MPRIS service."""
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

            # Wire up MPRIS to playback controller
            self.playback.set_mpris_service(self.mpris_service)

        except Exception as e:
            logging.error(f"Failed to start MPRIS service: {e}")

    def _fetch_channels(self, async_mode: bool = False) -> None:
        """Fetch channel list.
        
        Args:
            async_mode: If True, fetch channels asynchronously (non-blocking)
        """
        if async_mode:
            self._fetch_channels_async()
        else:
            self._fetch_channels_sync()

    def _fetch_channels_sync(self) -> None:
        """Fetch channel list synchronously (blocking)."""
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

    def _fetch_channels_async(self) -> None:
        """Fetch channel list asynchronously (non-blocking).
        
        Shows loading message and updates UI when complete.
        """
        # Start with empty channels, show loading message
        self.channels = []
        
        def on_channels_loaded(channels_opt: Optional[List[Channel]]):
            """Callback when channels are loaded."""
            if channels_opt:
                try:
                    # Load usage and sort
                    usage = load_channel_usage(CHANNEL_USAGE_FILE)
                    valid_ids = {ch.id for ch in channels_opt}
                    usage = clean_channel_usage(usage, valid_ids)

                    self.channels = sort_channels_by_usage(channels_opt, usage)
                    save_channel_usage(CHANNEL_USAGE_FILE, usage)

                    # Re-initialize components with loaded channels
                    if hasattr(self, 'state'):
                        self.state.channels = self.channels
                except Exception as e:
                    logging.error(f"Error processing loaded channels: {e}")

    def _setup_metadata_observer(self) -> None:
        """Setup MPV metadata observer."""
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
                                self.playback.update_metadata(metadata)
                                if self.stdscr:
                                    self._display_interface()

                                if self.mpris_service and self.config.get("dbus_send_metadata", False):
                                    self.mpris_service.update_metadata(metadata.to_dict())
                                break

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        handler = _create_signal_handler(self)
        signal.signal(signal.SIGTERM, handler)
        signal.signal(signal.SIGINT, handler)

    def init_colors(self) -> None:
        """Initialize colors."""
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
        """Display the interface."""
        if not self.stdscr:
            return

        channel_favorites = self.state.get_channel_favorites(CHANNEL_FAVORITES_FILE)
        channels_to_display = self.state.get_channels_to_display()

        # Update scroll offset
        max_y, max_x = self.stdscr.getmaxyx()
        panel_height = max_y - 2
        self.state.update_scroll_offset(panel_height)

        # Clear sleep overlay area if overlay is not active (prevent ghost overlay)
        if not self.state.sleep_overlay_active:
            try:
                overlay_width = 30
                overlay_height = 7
                start_y = (max_y - overlay_height) // 2
                start_x = (max_x - overlay_width) // 2
                for y in range(start_y, min(start_y + overlay_height, max_y)):
                    self.stdscr.move(y, start_x)
                    self.stdscr.clrtoeol()
            except curses.error:
                pass

        # Clear help overlay area if help is not active (prevent ghost overlay)
        if not self.state.show_help:
            try:
                help_height = 32  # len(help_text) + 2
                help_width = min(50, max_x - 10)
                help_y = (max_y - help_height) // 2
                help_x = (max_x - help_width) // 2
                for y in range(help_y, min(help_y + help_height, max_y)):
                    self.stdscr.move(y, help_x)
                    self.stdscr.clrtoeol()
            except curses.error:
                pass

        self.ui_screen.display(
            self.stdscr,
            channels_to_display,
            self.state.current_index,
            self.state.scroll_offset,
            channel_favorites,
            self.playback.current_channel,
            self.player,
            self.playback.is_playing,
            is_searching=self.state.is_searching,
            search_query=self.state.search_query,
            show_help=self.state.show_help,
            current_bitrate=self.playback.current_bitrate,
        )

        # Show sleep overlay if active
        if self.state.sleep_overlay_active:
            self.ui_screen.display_sleep_overlay(self.stdscr, self.state.sleep_input)
        else:
            # Hide cursor when overlay is not active
            try:
                curses.curs_set(0)
            except curses.error:
                pass

        # Show sleep timer countdown if active
        if self.state.sleep_timer.is_active():
            self.ui_screen.display_sleep_timer(
                self.stdscr, self.state.get_timer_remaining()
            )

    def _on_state_change(self) -> None:
        """Callback for state changes."""
        if self.stdscr:
            self._display_interface()

    def _on_theme_change(self, new_theme: str) -> None:
        """Callback for theme changes."""
        # Сбрасываем кэш UI для принудительной полной перерисовки
        self.ui_screen.invalidate_cache()
        
        # Переинициализируем цвета
        self.init_colors()

        if self.stdscr:
            # Полная очистка и перерисовка с новым фоном
            self.stdscr.clear()
            self.stdscr.bkgd(" ", curses.color_pair(1))
            self._display_interface()
            self.stdscr.refresh()

    def _cleanup(self) -> None:
        """Clean up resources."""
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

    def run(self) -> None:
        """Run main application loop."""

        def main(stdscr: curses.window) -> None:
            try:
                self.stdscr = stdscr
                self.input_handler.set_stdscr(stdscr)
                self.init_colors()

                stdscr.keypad(True)
                curses.raw()
                stdscr.nodelay(True)

                self._display_interface()

                # Cache time for the main loop iteration
                _last_timer_check = 0.0

                while self.state.is_running():
                    current_time = time.time()

                    # Check sleep timer every 10 seconds (not every cycle)
                    if current_time - _last_timer_check >= 10:
                        if self.state.check_sleep_timer():
                            break
                        _last_timer_check = current_time

                    # Update timer display if needed
                    if self.state.should_update_timer_display():
                        self.ui_screen.display_sleep_timer(
                            self.stdscr, self.state.get_timer_remaining()
                        )
                        stdscr.refresh()

                    # Check volume display timeout
                    if (
                        self.ui_screen.volume_display is not None
                        and current_time - self.ui_screen.volume_display_time >= 3
                    ):
                        self.ui_screen.volume_display = None
                        self._display_interface()

                    # Get user input
                    try:
                        key = stdscr.get_wch()
                        if key is not None:
                            # Handle terminal resize - invalidate cache and force full redraw
                            if key == curses.KEY_RESIZE:
                                self.ui_screen.invalidate_cache()
                                self.input_handler.handle_input(key)
                            else:
                                self.input_handler.handle_input(key)
                            # Redraw interface (full redraw if cache was invalidated)
                            self._display_interface()
                        else:
                            # Short sleep for responsive UI (50ms = 20 FPS)
                            time.sleep(0.05)
                    except curses.error:
                        time.sleep(0.05)
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


def main() -> None:
    """Entry point with CLI argument support."""
    args = parse_args()

    if not validate_args(args):
        sys.exit(1)

    # Handle list-themes (no initialization needed)
    if args.list_themes:
        from somafm_tui.themes import load_themes_raw
        themes = load_themes_raw()
        print_themes(themes)
        sys.exit(0)

    # For other commands, we need to initialize the player
    ensure_directories()
    setup_logging()

    if not check_mpv():
        print("Error: MPV player is not installed or not in PATH")
        print("Please install MPV using your package manager:")
        print("  - Arch Linux: sudo pacman -S mpv")
        print("  - Ubuntu/Debian: sudo apt-get install mpv")
        print("  - Fedora: sudo dnf install mpv")
        sys.exit(1)

    # Load configuration
    config = validate_config(load_config())

    # Apply CLI overrides to config
    if args.theme:
        config["theme"] = args.theme
    if args.volume is not None:
        config["volume"] = args.volume
    if args.no_dbus:
        config["dbus_allowed"] = False
    if args.config:
        # Alternative config file handling
        pass

    # Fetch channels
    try:
        channels = fetch_channels(cache_file=CHANNEL_CACHE_FILE)
        usage = load_channel_usage(CHANNEL_USAGE_FILE)
        valid_ids = {ch.id for ch in channels}
        usage = clean_channel_usage(usage, valid_ids)
        channels = sort_channels_by_usage(channels, usage)
    except Exception as e:
        print(f"Error fetching channel list: {e}")
        sys.exit(1)

    # Handle list-channels
    if args.list_channels:
        print_channels(channels)
        sys.exit(0)

    # Handle search
    if args.search:
        from somafm_tui.channels import filter_channels_by_query
        filtered = filter_channels_by_query(channels, args.search)
        if filtered:
            print(f"\nSearch results for '{args.search}':")
            print_channels(filtered)
        else:
            print(f"No channels found matching '{args.search}'")
        sys.exit(0)

    # Handle favorites
    if args.favorites:
        favorites = load_favorites(CHANNEL_FAVORITES_FILE)
        print_favorites(channels, favorites)
        sys.exit(0)

    # Create player with configured settings
    player = SomaFMPlayer(config=config, channels=channels)

    # Handle sleep timer from CLI
    if args.sleep:
        player.state.set_sleep_timer(args.sleep)
        print(f"Sleep timer set for {args.sleep} minutes")

    # Handle play argument
    if args.play:
        # Find channel by ID or name
        play_channel = None
        for ch in player.channels:
            if ch.id == args.play or ch.title.lower() == args.play.lower():
                play_channel = ch
                break

        if play_channel:
            print(f"Playing: {play_channel.title}")
            # Will be played when UI starts
        else:
            print(f"Channel '{args.play}' not found")
            print("Use --list-channels to see available channels")
            sys.exit(1)

    # Run interactive mode
    player.run()


if __name__ == "__main__":
    main()
