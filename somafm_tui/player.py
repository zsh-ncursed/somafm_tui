"""SomaFM TUI Player main module.

Refactored architecture with separated concerns:
- PlaybackController: Audio playback management
- StateManager: Application state management
- InputHandler: User input handling
- UIScreen: Display rendering
"""

import json
import os
import shutil
import sys
import time
import logging
import signal
import threading
import locale
from typing import Optional, Any, Dict, List, Callable

# Set locale to C for MPV compatibility
locale.setlocale(locale.LC_NUMERIC, "C")

# Python version check
if sys.version_info < (3, 8):
    print("Error: Python 3.8 or higher is required")
    print(f"Current Python version: {sys.version_info.major}.{sys.version_info.minor}")
    sys.exit(1)


def check_dependencies() -> None:
    """Check if all required dependencies are installed.

    Provides helpful error messages with installation instructions for different distributions.
    """
    missing_deps = []
    install_instructions = {
        "mpv": {
            "import": "mpv",  # python-mpv package imports as 'mpv'
            "package": "python-mpv",
            "arch": "sudo pacman -S python-mpv mpv",
            "ubuntu": "sudo apt-get install python3-mpv mpv",
            "fedora": "sudo dnf install python-mpv mpv",
            "macos": "brew install mpv && pip install python-mpv",
        },
        "requests": {
            "import": "requests",
            "package": "requests",
            "arch": "pip install requests",
            "ubuntu": "pip install requests",
            "fedora": "pip install requests",
            "macos": "pip install requests",
        },
        "dbus_next": {
            "import": "dbus_next",  # dbus-next package imports as 'dbus_next'
            "package": "dbus-next",
            "arch": "pip install dbus-next",
            "ubuntu": "pip install dbus-next",
            "fedora": "pip install dbus-next",
            "macos": "Not required on macOS",
            "optional": True,
        },
    }

    # Check each dependency
    for dep_name, dep_info in install_instructions.items():
        try:
            __import__(dep_info["import"])
        except ImportError:
            missing_deps.append((dep_name, dep_info))

    # Report missing dependencies
    if missing_deps:
        print("\n" + "=" * 60)
        print("ERROR: Missing required dependencies")
        print("=" * 60)

        for dep_name, dep_info in missing_deps:
            optional_marker = " (optional)" if dep_info.get("optional") else ""
            package_name = dep_info.get("package", dep_info["import"])
            print(f"\n❌ {dep_name}{optional_marker}")
            print(f"   Required module: {package_name}")
            print("   Installation instructions:")
            print(f"   - Arch Linux:   {dep_info['arch']}")
            print(f"   - Ubuntu/Debian: {dep_info['ubuntu']}")
            print(f"   - Fedora:       {dep_info['fedora']}")
            if dep_info.get("macos"):
                print(f"   - macOS:        {dep_info['macos']}")

        required_missing = [d for d, info in missing_deps if not info.get("optional")]
        if required_missing:
            print("\n" + "=" * 60)
            print("Install missing dependencies and try again.")
            print("=" * 60)
            sys.exit(1)
        else:
            print("\n" + "=" * 60)
            print("Note: Optional dependencies are missing. The app will work,")
            print("but some features may be disabled.")
            print("=" * 60)
            input("\nPress Enter to continue...")


# Module-level imports (after dependency check function definition)
# These are safe to import at module level because check_dependencies() is defined above
import curses
import mpv
import requests

# Imports for module-level constants and functions
from somafm_tui.config import CONFIG_DIR, CONFIG_FILE, HOME, set_allowed_themes
from somafm_tui.themes import get_theme_names, apply_theme
from somafm_tui.models import TrackMetadata, Channel
from somafm_tui.ui import UIScreen
from somafm_tui.timer import SleepTimer
from somafm_tui.core import PlaybackController, StateManager, InputHandler
from somafm_tui.cli import (
    parse_args,
    validate_args,
    print_channels,
    print_favorites,
    print_themes,
)
from somafm_tui.constants import HELP_OVERLAY_WIDTH, HELP_OVERLAY_HEIGHT


# Constants
TEMP_DIR = "/tmp/.somafmtmp"
CACHE_DIR = os.path.join(TEMP_DIR, "cache")
CHANNEL_CACHE_FILE = os.path.join(CACHE_DIR, "channels.json")
CHANNEL_USAGE_FILE = os.path.join(CONFIG_DIR, "channel_usage.json")
CHANNEL_FAVORITES_FILE = os.path.join(CONFIG_DIR, "channel_favorites.json")
TRACK_FAVORITES_FILE = os.path.join(CONFIG_DIR, "track_favorites.json")


def ensure_directories() -> None:
    """Create required directories and migrate old config if needed."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    # Migrate from old ~/.somafm_tui to XDG ~/.config/somafm_tui
    old_config_dir = os.path.join(HOME, ".somafm_tui")
    if os.path.exists(old_config_dir) and old_config_dir != CONFIG_DIR:
        _migrate_old_config(old_config_dir)


def _migrate_old_config(old_dir: str) -> None:
    """Migrate configuration files from old directory to new XDG location."""
    files_to_migrate = [
        "somafm.cfg",
        "channel_favorites.json",
        "channel_usage.json",
        "track_favorites.json",
    ]

    for filename in files_to_migrate:
        old_path = os.path.join(old_dir, filename)
        new_path = os.path.join(CONFIG_DIR, filename)

        if os.path.exists(old_path) and not os.path.exists(new_path):
            try:
                shutil.copy2(old_path, new_path)
                logging.info(f"Migrated {filename} from {old_dir} to {CONFIG_DIR}")
            except (IOError, OSError) as e:
                logging.warning(f"Failed to migrate {filename}: {e}")


def setup_logging() -> None:
    """Configure logging."""
    ensure_directories()
    logging.basicConfig(
        filename=os.path.join(TEMP_DIR, "somafm.log"),
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def _create_signal_handler(player_instance: "SomaFMPlayer") -> Callable[[int, Any], None]:
    """Create a signal handler closure for the given player instance.

    Uses weakref to prevent reference cycles and memory leaks.

    Args:
        player_instance: The SomaFMPlayer instance to handle signals for

    Returns:
        Signal handler function
    """
    import weakref

    # Use weak reference to avoid reference cycles
    weak_player = weakref.ref(player_instance)

    def handler(signum, frame):
        """Handle termination signals."""
        signal_name = signal.Signals(signum).name
        logging.info(f"Received {signal_name}, shutting down...")

        # Get the actual object from weak reference
        player = weak_player()
        if player is not None:
            player._signal_received = True
            player.running = False
        # If player is None, it was already garbage collected - nothing to do

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
        self._data_lock = threading.Lock()  # Lock for thread-safe data access
        ensure_directories()
        setup_logging()
        self._setup_signal_handlers()

        # Dependencies already checked by check_dependencies() at module load
        # Initialize allowed themes whitelist for security
        theme_names = get_theme_names()
        set_allowed_themes(set(theme_names))

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

        except (ImportError, ModuleNotFoundError) as e:
            logging.warning(f"MPRIS/D-Bus not available: {e}. Install dbus-next for media keys support.")
        except (OSError, IOError) as e:
            logging.error(f"MPRIS service I/O error: {e}")

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

            # Thread-safe update of shared data
            with self._data_lock:
                self.channels = sort_channels_by_usage(channels, usage)
            save_channel_usage(CHANNEL_USAGE_FILE, usage)

        except (ConnectionError, TimeoutError) as e:
            logging.error(f"Network error fetching channels: {e}")
            print(f"Error: Cannot connect to SomaFM API. Check your internet connection.")
            sys.exit(1)
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Error processing channel data: {e}")
            print(f"Error: Failed to process channel data.")
            sys.exit(1)
        except Exception as e:
            logging.error(f"Unexpected error fetching channels: {e}")
            print(f"Error fetching channel list: {e}")
            sys.exit(1)

    def _fetch_channels_async(self) -> None:
        """Fetch channel list asynchronously (non-blocking).

        Shows loading message and updates UI when complete.
        """
        # Start with empty channels, show loading message
        with self._data_lock:
            self.channels = []

        def on_channels_loaded(channels_opt: Optional[List[Channel]]):
            """Callback when channels are loaded."""
            if channels_opt:
                try:
                    # Load usage and sort
                    usage = load_channel_usage(CHANNEL_USAGE_FILE)
                    valid_ids = {ch.id for ch in channels_opt}
                    usage = clean_channel_usage(usage, valid_ids)

                    # Thread-safe update of shared data
                    with self._data_lock:
                        self.channels = sort_channels_by_usage(channels_opt, usage)
                        save_channel_usage(CHANNEL_USAGE_FILE, usage)

                        # Re-initialize components with loaded channels
                        if hasattr(self, 'state'):
                            self.state.channels = self.channels
                except (json.JSONDecodeError, IOError) as e:
                    logging.error(f"Error processing loaded channels: {e}")
                except (OSError, ValueError) as e:
                    logging.error(f"Channel data error: {e}")

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
        
        # Apply theme directly - this will reload themes from file and initialize colors
        theme_name = self.config.get("theme", "default")
        apply_theme(theme_name)

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

# Clear sleep overlay area if overlay is not active (prevent ghost overlay)
        if not self.state.sleep_overlay_active:
            try:
                # Must match _display_help centering exactly
                help_width = min(HELP_OVERLAY_WIDTH, max_x - 10)
                help_text_lines = 28  # Number of lines in help_text from _display_help
                help_height = help_text_lines + 2
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
            theme_name=self.state._current_theme,
            show_help=self.state.show_help,
            current_bitrate=self.playback.current_bitrate,
            show_footer=self.state.show_footer,
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

        # Shutdown HTTP client executor
        from somafm_tui.http_client import shutdown_http
        shutdown_http()

        if not self.had_error and os.path.exists(TEMP_DIR):
            try:
                for root, dirs, files in os.walk(TEMP_DIR, topdown=False):
                    for name in files:
                        os.remove(os.path.join(root, name))
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                os.rmdir(TEMP_DIR)
            except (IOError, OSError, PermissionError) as e:
                logging.warning(f"Error cleaning up temp directory: {e}")

    def run(self) -> None:
        """Run main application loop."""

        def main(stdscr: curses.window) -> None:
            try:
                self.stdscr = stdscr
                self.input_handler.set_stdscr(stdscr)
                self.init_colors()

                stdscr.keypad(True)
                curses.cbreak()  # Use cbreak instead of raw for proper key handling
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
                        # Just reset display state, UI will handle clearing
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

            except (KeyboardInterrupt, SystemExit):
                # Normal shutdown on user request or signal
                logging.info("Application shutdown requested")
            except (curses.error, OSError) as e:
                self.had_error = True
                logging.error(f"UI error: {e}")
                raise
            except (ValueError, TypeError) as e:
                self.had_error = True
                logging.error(f"Application configuration error: {e}")
                raise
            finally:
                self._cleanup()

        try:
            curses.wrapper(main)
        except (KeyboardInterrupt, SystemExit):
            # Normal shutdown
            logging.info("Application terminated by user")
        except (curses.error, OSError) as e:
            self.had_error = True
            logging.error(f"Fatal UI error: {e}")
            print(f"An error occurred. Check logs at {os.path.join(TEMP_DIR, 'somafm.log')}")
            sys.exit(1)
        except (ValueError, TypeError) as e:
            self.had_error = True
            logging.error(f"Fatal configuration error: {e}")
            print(f"An error occurred. Check logs at {os.path.join(TEMP_DIR, 'somafm.log')}")
            sys.exit(1)


def main() -> None:
    """Entry point with CLI argument support."""
    # Check dependencies first (before any imports that might fail)
    check_dependencies()

    # Runtime imports are now at module level (after check_dependencies function)
    # Additional imports that depend on runtime configuration
    from somafm_tui.config import load_config, save_config, validate_config
    from somafm_tui.themes import get_color_themes, init_custom_colors, apply_theme, load_themes_raw
    from somafm_tui.channels import (
        fetch_channels,
        fetch_channels_async,
        load_favorites,
        load_channel_usage,
        save_channel_usage,
        clean_channel_usage,
        sort_channels_by_usage,
        filter_channels_by_query,
    )
    from somafm_tui.mpris_service import MPRISService, run_mpris_loop

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

    # Load configuration
    config = validate_config(load_config())

    # Initialize allowed themes whitelist for security (CLI mode)
    theme_names = get_theme_names()
    set_allowed_themes(set(theme_names))

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
    except (ConnectionError, TimeoutError) as e:
        logging.error(f"Network error fetching channels: {e}")
        print(f"Error: Cannot connect to SomaFM API. Check your internet connection.")
        sys.exit(1)
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Error processing channel data: {e}")
        print(f"Error: Failed to process channel data.")
        sys.exit(1)
    except (OSError, ValueError) as e:
        logging.error(f"Channel data error: {e}")
        print(f"Error: Invalid channel data.")
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
