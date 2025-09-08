#!/usr/bin/env python3
import os
import curses
import mpv
import requests
import json
import sys
import time
import logging
import threading
from typing import List, Dict, Set
from datetime import datetime
from stream_buffer import StreamBuffer

# Setup paths
HOME = os.path.expanduser("~")
CONFIG_DIR = os.path.join(HOME, ".somafm_tui")
CONFIG_FILE = os.path.join(CONFIG_DIR, "somafm.cfg")
TEMP_DIR = "/tmp/.somafmtmp"
CACHE_DIR = os.path.join(TEMP_DIR, "cache")
CHANNEL_USAGE_FILE = os.path.join(CONFIG_DIR, "channel_usage.json")
CHANNEL_FAVORITES_FILE = os.path.join(CONFIG_DIR, "channel_favorites.json")

# Create necessary directories
os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# Logging setup
logging.basicConfig(
    filename=os.path.join(TEMP_DIR, 'somafm.log'),
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class CombinedScreen:
    def __init__(self):
        self.current_metadata = {
            'artist': 'Loading...',
            'title': 'Loading...',
            'duration': '--:--',
            'timestamp': None
        }
        self.max_history = 10
        self.track_history = []
        self.current_channel = None
        self.player = None

    def display(self, stdscr, channels, selected_index, scroll_offset, channel_favorites, current_channel=None, player=None, is_playing=False, is_searching=False, search_query=""):
        """Display combined interface with channels on left and playback on right"""
        max_y, max_x = stdscr.getmaxyx()

        # Fixed width for channels panel (30 characters), rest for playback
        split_x = 30

        # Clear screen completely and fill background
        stdscr.clear()
        stdscr.bkgd(' ', curses.color_pair(1))

        # Fill entire screen to avoid gaps
        for y in range(max_y):
            try:
                stdscr.addstr(y, 0, " " * max_x, curses.color_pair(1))
            except curses.error:
                # Handle the bottom-right corner issue in curses
                if y == max_y - 1:
                    try:
                        stdscr.addstr(y, 0, " " * (max_x - 1), curses.color_pair(1))
                    except curses.error:
                        pass

        # Draw vertical separator
        for y in range(max_y):
            try:
                stdscr.addstr(y, split_x, "│", curses.color_pair(1))
            except curses.error:
                pass

        # Calculate panel height (leave space for 2 lines of instructions)
        panel_height = max_y - 2

        # LEFT PANEL: Channel list
        self._display_channels_panel(stdscr, channels, selected_index, scroll_offset,
                                   channel_favorites, 0, 0, split_x, panel_height,
                                   is_searching, search_query)

        # RIGHT PANEL: Playback info
        self._display_playback_panel(stdscr, split_x + 1, 0, max_x - split_x - 1, panel_height,
                                   current_channel, player, is_playing)

        # Display adaptive instructions at bottom (stack when needed)
        try:
            # List of instruction items
            instruction_items = [
                "↑↓/jk - select",
                "Enter/l - play",
                "/ - search",
                "Space - pause",
                "h - stop",
                "f - favorite",
                "t - theme",
                "a - alt bg",
                "q - quit"
            ]

            available_width = max_x - 1
            available_lines = 2  # Maximum lines we can use for instructions

            # Try to fit instructions in available space
            lines = []
            current_line = ""

            for item in instruction_items:
                # Check if we can add this item to current line
                separator = " | " if current_line else ""
                test_line = current_line + separator + item

                if len(test_line) <= available_width:
                    current_line = test_line
                else:
                    # Start new line if we have space
                    if current_line:
                        lines.append(current_line)
                        current_line = item
                    else:
                        # Item too long for line, truncate it
                        current_line = item[:available_width-3] + "..." if available_width > 3 else item[:available_width]

                    # If we've used all available lines, break
                    if len(lines) >= available_lines:
                        break

            # Add the last line if it exists
            if current_line and len(lines) < available_lines:
                lines.append(current_line)

            # Display the instruction lines
            for i, line in enumerate(lines):
                if i >= available_lines:
                    break
                y_pos = max_y - available_lines + i
                # Pad line to full width
                padded_line = line.ljust(available_width)
                stdscr.addstr(y_pos, 0, padded_line, curses.color_pair(5) | curses.A_DIM)

        except curses.error:
            pass

        stdscr.refresh()

    def _display_channels_panel(self, stdscr, channels, selected_index, scroll_offset,
                              channel_favorites, start_x, start_y, width, height,
                              is_searching=False, search_query=""):
        """Display channels in left panel"""
        # Header
        try:
            header = f"Channels ({len(channels)})"
            if len(header) > width - 2:
                header = header[:width-5] + "..."
            stdscr.addstr(start_y, start_x, header, curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            pass

        # Calculate visible channels (leave space for header and instructions)
        visible_channels = height - 3

        # Display channels
        for i, channel in enumerate(channels[scroll_offset:scroll_offset + visible_channels]):
            display_y = start_y + 1 + i
            if display_y >= height - 1:
                break

            # Prepare channel title
            fav_icon = "♥ " if channel['id'] in channel_favorites else "  "
            title = channel['title']
            max_title_len = width - 6  # Space for fav icon and selection marker
            if len(title) > max_title_len:
                title = title[:max_title_len-3] + "..."
            display_title = f"{fav_icon}{title}"

            try:
                if i + scroll_offset == selected_index:
                    stdscr.addstr(display_y, start_x, f"> {display_title}"[:width-1],
                                 curses.color_pair(2) | curses.A_REVERSE)
                else:
                    stdscr.addstr(display_y, start_x, f"  {display_title}"[:width-1],
                                 curses.color_pair(1))
            except curses.error:
                continue

        # Display search prompt if searching
        if is_searching:
            prompt = f"Search: {search_query}"
            prompt_y = start_y + height - 2 # Use one of the empty lines at the bottom
            try:
                # Clear the line first
                stdscr.addstr(prompt_y, start_x, " " * (width - 1), curses.color_pair(1))
                stdscr.addstr(prompt_y, start_x, prompt[:width-1], curses.color_pair(2) | curses.A_BOLD)
                # Show cursor and move it to the end of the query
                curses.curs_set(1)
                stdscr.move(prompt_y, start_x + len(prompt))
            except curses.error:
                curses.curs_set(0) # Hide cursor on error
        else:
            curses.curs_set(0)

    def _display_playback_panel(self, stdscr, start_x, start_y, width, height,
                              current_channel, player, is_playing):
        """Display playback info in right panel"""
        # Get actual screen dimensions to respect boundaries
        max_y, max_x = stdscr.getmaxyx()

        # Calculate available width (don't exceed screen boundaries)
        available_width = min(width, max_x - start_x)

        if not current_channel or not is_playing:
            # No playback
            if available_width > 0:
                try:
                    text = "No channel playing"
                    if len(text) <= available_width:
                        stdscr.addstr(start_y, start_x, text, curses.color_pair(3))

                    text2 = "Select a channel and press Enter to start"
                    if len(text2) <= available_width and start_y + 2 < max_y:
                        stdscr.addstr(start_y + 2, start_x, text2, curses.color_pair(5) | curses.A_DIM)
                except curses.error:
                    pass
            return

        # Channel info
        if available_width > 0:
            try:
                channel_title = f"♪ {current_channel['title']}"
                if len(channel_title) > available_width:
                    channel_title = channel_title[:available_width-3] + "..." if available_width > 3 else channel_title[:available_width]
                if len(channel_title) <= available_width:
                    stdscr.addstr(start_y, start_x, channel_title, curses.color_pair(1) | curses.A_BOLD)
            except curses.error:
                pass

        # Channel description
        if available_width > 0 and start_y + 1 < max_y:
            try:
                description = current_channel.get('description', 'No description')
                if len(description) > available_width:
                    description = description[:available_width-3] + "..." if available_width > 3 else description[:available_width]
                if len(description) <= available_width:
                    stdscr.addstr(start_y + 1, start_x, description, curses.color_pair(3))
            except curses.error:
                pass

        # Current track
        if available_width > 0 and start_y + 3 < max_y:
            try:
                play_symbol = "▶" if not (player and player.pause) else "⏸"
                current_track = f"{play_symbol} {self.current_metadata['artist']} - {self.current_metadata['title']}"
                if len(current_track) > available_width:
                    current_track = current_track[:available_width-3] + "..." if available_width > 3 else current_track[:available_width]
                if len(current_track) <= available_width:
                    stdscr.addstr(start_y + 3, start_x, current_track, curses.color_pair(4) | curses.A_BOLD)
            except curses.error:
                pass

        # Track history
        y = start_y + 5
        for track in self.track_history:
            if y >= height - 2 or y >= max_y:
                break
            if available_width > 0:
                try:
                    timestamp = track.get('timestamp', '')
                    if timestamp:
                        timestamp = f"[{timestamp}] "
                    track_info = f"  {timestamp}{track['artist']} - {track['title']}"
                    if len(track_info) > available_width:
                        track_info = track_info[:available_width-3] + "..." if available_width > 3 else track_info[:available_width]
                    if len(track_info) <= available_width:
                        stdscr.addstr(y, start_x, track_info, curses.color_pair(4))
                    y += 1
                except curses.error:
                    continue

    def add_to_history(self, metadata):
        """Add track to history"""
        metadata['timestamp'] = datetime.now().strftime("%H:%M:%S")
        self.track_history.insert(0, metadata)
        if len(self.track_history) > self.max_history:
            self.track_history.pop()

    def update_metadata(self, metadata):
        """Update current track metadata"""
        logging.debug(f"CombinedScreen.update_metadata() called with: {metadata}")
        if metadata != self.current_metadata:
            logging.debug("Metadata changed, updating...")
            self.add_to_history(self.current_metadata)
            self.current_metadata = metadata.copy()
            logging.debug(f"Updated current_metadata: {self.current_metadata}")
        else:
            logging.debug("Metadata unchanged, skipping update")

    def show_notification(self, stdscr, message, timeout=1.5):
        """Show notification overlay"""
        max_y, max_x = stdscr.getmaxyx()
        win_width = min(len(message) + 4, max_x)
        win_height = 3
        start_y = max_y // 2 - win_height // 2
        start_x = max_x // 2 - win_width // 2
        try:
            notif_win = curses.newwin(win_height, win_width, start_y, start_x)
            notif_win.bkgd(' ', curses.color_pair(3) | curses.A_BOLD)
            notif_win.box()
            notif_win.addstr(1, 2, message[:win_width-4])
            notif_win.refresh()
            curses.napms(int(timeout * 1000))
            notif_win.clear()
            notif_win.refresh()
        except curses.error:
            pass

class SomaFMPlayer:
    def __init__(self):
        self.had_error = False
        # Check if MPV is installed
        if not self._check_mpv():
            print("Error: MPV player is not installed or not in PATH")
            print("Please install MPV using your package manager:")
            print("  - Arch Linux: sudo pacman -S mpv")
            print("  - Ubuntu/Debian: sudo apt-get install mpv")
            print("  - Fedora: sudo dnf install mpv")
            sys.exit(1)

        self._init_config()
        self.channels = self._fetch_channels()

        self.buffer = None
        self.player = mpv.MPV(
            input_default_bindings=True,
            input_vo_keyboard=True,
            osc=True
        )
        self._init_mpris()

        self.current_channel = None
        self.current_index = 0
        self.is_playing = False
        self.is_paused = False
        self.scroll_offset = 0
        self.current_metadata = {
            'artist': 'Loading...',
            'title': 'Loading...',
            'duration': '--:--'
        }
        self.running = True
        self.combined_screen = CombinedScreen()
        self.stdscr = None  # Store stdscr for updates
        self.alternative_bg_mode = self.config.get('alternative_bg_mode', False)  # Alternative background mode (pure black instead of dark gray)

        # Search state
        self.is_searching = False
        self.search_query = ""
        self.filtered_channels = []

        # Set up metadata observer
        @self.player.property_observer('metadata')
        def metadata_handler(name, value):
            if value:
                logging.debug(f"Received metadata: {value}")
                # Try to get track info from metadata
                track_info = value.get('icy-title', '')

                if track_info:
                    # Try to split by different separators
                    for separator in [' - ', ' – ']:
                        if separator in track_info:
                            parts = track_info.split(separator, 1)
                            if len(parts) == 2:
                                artist, title = parts
                                metadata = {
                                    'artist': artist.strip(),
                                    'title': title.strip(),
                                    'duration': '--:--',
                                    'timestamp': datetime.now().strftime("%H:%M:%S")
                                }
                                logging.debug(f"Updated metadata: {metadata}")
                                self.current_metadata = metadata
                                if self.combined_screen:
                                    self.combined_screen.update_metadata(metadata)
                                    # Force screen refresh after metadata update
                                    if self.stdscr:
                                        self._display_combined_interface(self.stdscr)

                                # Update MPRIS service with new metadata
                                if self.mpris_service and self.config.get('dbus_send_metadata', False):
                                    self.mpris_service.update_metadata(metadata)
                                break

    def _check_mpv(self) -> bool:
        """Check if MPV is installed and accessible"""
        try:
            import subprocess
            result = subprocess.run(['mpv', '--version'],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            return result.returncode == 0
        except Exception:
            return False

    def _get_color_themes(self):
        """Define available color themes"""
        # 5 light themes, 15 dark themes
        return {
            # Light Themes
            'light': {
                'name': 'Light',
                'bg_color': curses.COLOR_WHITE, 'header': curses.COLOR_BLUE, 'selected': curses.COLOR_BLACK,
                'info': curses.COLOR_BLACK, 'metadata': curses.COLOR_MAGENTA, 'instructions': curses.COLOR_BLUE,
                'favorite': curses.COLOR_RED
            },
            'solarized-light': {
                'name': 'Solarized Light',
                'bg_color': curses.COLOR_WHITE, 'header': curses.COLOR_BLUE, 'selected': curses.COLOR_BLACK,
                'info': curses.COLOR_BLACK, 'metadata': curses.COLOR_GREEN, 'instructions': curses.COLOR_CYAN,
                'favorite': curses.COLOR_RED
            },
            'paper': {
                'name': 'Paper',
                'bg_color': curses.COLOR_WHITE, 'header': curses.COLOR_BLACK, 'selected': curses.COLOR_BLUE,
                'info': curses.COLOR_BLACK, 'metadata': curses.COLOR_BLUE, 'instructions': curses.COLOR_BLACK,
                'favorite': curses.COLOR_RED
            },
            'light-plus': {
                'name': 'Light Plus',
                'bg_color': curses.COLOR_WHITE, 'header': curses.COLOR_MAGENTA, 'selected': curses.COLOR_BLACK,
                'info': curses.COLOR_BLACK, 'metadata': curses.COLOR_BLUE, 'instructions': curses.COLOR_BLACK,
                'favorite': curses.COLOR_RED
            },
            'github-light': {
                'name': 'GitHub Light',
                'bg_color': curses.COLOR_WHITE, 'header': curses.COLOR_BLUE, 'selected': curses.COLOR_BLACK,
                'info': curses.COLOR_BLACK, 'metadata': curses.COLOR_GREEN, 'instructions': curses.COLOR_BLUE,
                'favorite': curses.COLOR_RED
            },
            # Dark Themes
            'default': {
                'name': 'Default Dark',
                'bg_color': curses.COLOR_BLACK, 'header': curses.COLOR_CYAN, 'selected': curses.COLOR_GREEN,
                'info': curses.COLOR_YELLOW, 'metadata': curses.COLOR_MAGENTA, 'instructions': curses.COLOR_BLUE,
                'favorite': curses.COLOR_RED
            },
            'darcula': {
                'name': 'Darcula',
                'bg_color': curses.COLOR_BLACK, 'header': curses.COLOR_CYAN, 'selected': curses.COLOR_YELLOW,
                'info': curses.COLOR_WHITE, 'metadata': curses.COLOR_GREEN, 'instructions': curses.COLOR_BLUE,
                'favorite': curses.COLOR_RED
            },
            'monokai': {
                'name': 'Monokai',
                'bg_color': curses.COLOR_BLACK, 'header': curses.COLOR_YELLOW, 'selected': curses.COLOR_GREEN,
                'info': curses.COLOR_WHITE, 'metadata': curses.COLOR_CYAN, 'instructions': curses.COLOR_MAGENTA,
                'favorite': curses.COLOR_RED
            },
            'matrix': {
                'name': 'Matrix',
                'bg_color': curses.COLOR_BLACK, 'header': curses.COLOR_GREEN, 'selected': curses.COLOR_WHITE,
                'info': curses.COLOR_GREEN, 'metadata': curses.COLOR_GREEN, 'instructions': curses.COLOR_GREEN,
                'favorite': curses.COLOR_RED
            },
            'ocean': {
                'name': 'Ocean',
                'bg_color': curses.COLOR_BLACK, 'header': curses.COLOR_CYAN, 'selected': curses.COLOR_WHITE,
                'info': curses.COLOR_BLUE, 'metadata': curses.COLOR_CYAN, 'instructions': curses.COLOR_BLUE,
                'favorite': curses.COLOR_YELLOW
            },
            'sunset': {
                'name': 'Sunset',
                'bg_color': curses.COLOR_BLACK, 'header': curses.COLOR_YELLOW, 'selected': curses.COLOR_WHITE,
                'info': curses.COLOR_RED, 'metadata': curses.COLOR_YELLOW, 'instructions': curses.COLOR_RED,
                'favorite': curses.COLOR_RED
            },
            'monochrome': {
                'name': 'Monochrome',
                'bg_color': curses.COLOR_BLACK, 'header': curses.COLOR_WHITE, 'selected': curses.COLOR_BLACK,
                'info': curses.COLOR_WHITE, 'metadata': curses.COLOR_WHITE, 'instructions': curses.COLOR_WHITE,
                'favorite': curses.COLOR_WHITE
            },
            'nord': {
                'name': 'Nord',
                'bg_color': curses.COLOR_BLACK, 'header': curses.COLOR_BLUE, 'selected': curses.COLOR_WHITE,
                'info': curses.COLOR_CYAN, 'metadata': curses.COLOR_MAGENTA, 'instructions': curses.COLOR_BLUE,
                'favorite': curses.COLOR_YELLOW
            },
            'gruvbox': {
                'name': 'Gruvbox',
                'bg_color': curses.COLOR_BLACK, 'header': curses.COLOR_YELLOW, 'selected': curses.COLOR_GREEN,
                'info': curses.COLOR_WHITE, 'metadata': curses.COLOR_RED, 'instructions': curses.COLOR_BLUE,
                'favorite': curses.COLOR_YELLOW
            },
            'dracula': {
                'name': 'Dracula',
                'bg_color': curses.COLOR_BLACK, 'header': curses.COLOR_MAGENTA, 'selected': curses.COLOR_CYAN,
                'info': curses.COLOR_WHITE, 'metadata': curses.COLOR_GREEN, 'instructions': curses.COLOR_YELLOW,
                'favorite': curses.COLOR_RED
            },
            'cobalt': {
                'name': 'Cobalt',
                'bg_color': curses.COLOR_BLACK, 'header': curses.COLOR_BLUE, 'selected': curses.COLOR_YELLOW,
                'info': curses.COLOR_WHITE, 'metadata': curses.COLOR_CYAN, 'instructions': curses.COLOR_BLUE,
                'favorite': curses.COLOR_RED
            },
            'onedark': {
                'name': 'One Dark',
                'bg_color': curses.COLOR_BLACK, 'header': curses.COLOR_CYAN, 'selected': curses.COLOR_RED,
                'info': curses.COLOR_WHITE, 'metadata': curses.COLOR_GREEN, 'instructions': curses.COLOR_BLUE,
                'favorite': curses.COLOR_YELLOW
            },
            'night-owl': {
                'name': 'Night Owl',
                'bg_color': curses.COLOR_BLACK, 'header': curses.COLOR_MAGENTA, 'selected': curses.COLOR_YELLOW,
                'info': curses.COLOR_WHITE, 'metadata': curses.COLOR_CYAN, 'instructions': curses.COLOR_BLUE,
                'favorite': curses.COLOR_RED
            },
            'ayu': {
                'name': 'Ayu',
                'bg_color': curses.COLOR_BLACK, 'header': curses.COLOR_YELLOW, 'selected': curses.COLOR_GREEN,
                'info': curses.COLOR_WHITE, 'metadata': curses.COLOR_CYAN, 'instructions': curses.COLOR_BLUE,
                'favorite': curses.COLOR_RED
            },
            'tokyo-night': {
                'name': 'Tokyo Night',
                'bg_color': curses.COLOR_BLACK, 'header': curses.COLOR_BLUE, 'selected': curses.COLOR_CYAN,
                'info': curses.COLOR_WHITE, 'metadata': curses.COLOR_MAGENTA, 'instructions': curses.COLOR_BLUE,
                'favorite': curses.COLOR_RED
            }
        }

    def _init_colors(self):
        """Initialize colors based on selected theme"""
        curses.start_color()

        # Get theme from config
        theme_name = self.config.get('theme', 'default')
        themes = self._get_color_themes()

        if theme_name not in themes:
            theme_name = 'default'

        theme = themes[theme_name]
        bg_color = theme['bg_color']

        # For dark themes, try to create a darker background if possible
        # In alternative background mode, keep pure black background
        if bg_color == curses.COLOR_BLACK and curses.can_change_color() and not self.alternative_bg_mode:
            curses.init_color(10, 80, 80, 80)  # Very dark gray
            bg_color = 10

        # Initialize color pairs based on theme
        curses.init_pair(1, theme['header'], bg_color)      # Header
        curses.init_pair(2, theme['selected'], bg_color)    # Selected channel
        curses.init_pair(3, theme['info'], bg_color)        # Channel info
        curses.init_pair(4, theme['metadata'], bg_color)    # Track metadata
        curses.init_pair(5, theme['instructions'], bg_color) # Instructions
        curses.init_pair(6, theme['favorite'], bg_color)    # Favorite icon

        # For light themes, reverse the selected item colors
        if theme_name in ['light', 'solarized-light', 'paper', 'light-plus', 'github-light']:
            curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)  # Selected channel
        elif theme_name == 'monochrome':
            curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)  # Selected channel

    def _init_config(self):
        """Initialize configuration file if it doesn't exist"""
        themes = self._get_color_themes()
        theme_names = ", ".join(themes.keys())
        default_config = {
            "# Configuration file for SomaFM TUI Player": "",
            "# buffer_minutes: Duration of audio buffering in minutes": "",
            "# buffer_size_mb: Maximum size of buffer in megabytes": "",
            f"# theme: Color theme ({theme_names})": "",
            "# alternative_bg_mode: Use pure black background instead of dark gray (true/false)": "",
            "# dbus_allowed: Enable MPRIS/D-Bus support for media keys (true/false)": "",
            "# dbus_send_metadata: Send channel metadata over D-Bus (true/false)": "",
            "# dbus_send_metadata_artworks: Send channel picture with metadata over D-Bus (true/false)": "",
            "# dbus_cache_metadata_artworks: Cache channel picture locally for D-Bus (true/false)": "",
            "buffer_minutes": 5,
            "buffer_size_mb": 50,
            "theme": "default",
            "alternative_bg_mode": False,
            "dbus_allowed": False,
            "dbus_send_metadata": False,
            "dbus_send_metadata_artworks": False,
            "dbus_cache_metadata_artworks": True,
        }

        try:
            if not os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'w') as f:
                    for key, value in default_config.items():
                        if key.startswith('#'):
                            f.write(f"{key}\n")
                        else:
                            f.write(f"{key}: {value}\n")

            # Read actual config values (skip comments)
            with open(CONFIG_FILE) as f:
                config_lines = f.readlines()
                config_dict = {}
                for line in config_lines:
                    if not line.startswith('#') and ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()

                        # Handle different value types
                        if key in ['buffer_minutes', 'buffer_size_mb']:
                            config_dict[key] = int(value)
                        elif key in ['alternative_bg_mode', 'dbus_allowed', 'dbus_send_metadata', 'dbus_send_metadata_artworks', 'dbus_cache_metadata_artworks']:
                            config_dict[key] = value.lower() in ['true', '1', 'yes', 'on']
                        else:
                            config_dict[key] = value
                self.config = config_dict
        except Exception as e:
            logging.error(f"Error initializing config: {e}")
            # Use only actual config values, not comments
            self.config = {k: v for k, v in default_config.items() if not k.startswith('#')}

    def _init_mpris(self):
        """Initialize MPRIS service if enabled in config"""
        self.mpris_service = None
        self.mpris_loop = None
        self.mpris_thread = None
        dbus_allowed = self.config.get('dbus_allowed', False)

        if not dbus_allowed:
            logging.info("MPRIS service disabled by configuration")
            return

        try:
            from mpris_service import MPRISService, run_mpris_loop

            self.mpris_service = MPRISService(self, cache_dir=CACHE_DIR)
            self.mpris_thread = threading.Thread(target=run_mpris_loop, args=(self.mpris_service,), daemon=True)
            self.mpris_thread.start()
            logging.info("MPRIS service thread started")
        except Exception as e:
            logging.error(f"Failed to start MPRIS service: {e}")

    def _fetch_channels(self) -> List[Dict]:
        """Fetch channel list from SomaFM and sort by last played"""
        try:
            response = requests.get('https://api.somafm.com/channels.json')
            channels = response.json()['channels']
            # Загрузка usage
            if os.path.exists(CHANNEL_USAGE_FILE):
                with open(CHANNEL_USAGE_FILE, 'r') as f:
                    usage = json.load(f)
            else:
                usage = {}
            # Очищаем usage от несуществующих каналов
            valid_ids = {c['id'] for c in channels}
            usage = {k: v for k, v in usage.items() if k in valid_ids}
            # Сортировка каналов
            def sort_key(ch):
                last = usage.get(ch['id'])
                return -(last if last else 0)
            channels.sort(key=sort_key, reverse=False)
            # Сохраняем очищенный usage
            with open(CHANNEL_USAGE_FILE, 'w') as f:
                json.dump(usage, f)
            return channels
        except Exception as e:
            print(f"Error fetching channel list: {e}")
            sys.exit(1)

    def _display_combined_interface(self, stdscr):
        """Display combined interface with channels and playback"""
        channel_favorites = self._load_channel_favorites()

        # Filter channels if in search mode
        if self.is_searching:
            if self.search_query:
                self.filtered_channels = [
                    c for c in self.channels if self.search_query.lower() in c['title'].lower()
                ]
            else:
                # Show all channels if search query is empty but search mode is active
                self.filtered_channels = self.channels
            channels_to_display = self.filtered_channels
        else:
            channels_to_display = self.channels

        # Update scroll offset
        max_y, max_x = stdscr.getmaxyx()
        panel_height = max_y - 2
        visible_channels = panel_height - 3

        # Ensure we don't scroll beyond the available channels
        max_scroll = max(0, len(channels_to_display) - visible_channels)

        if self.current_index < self.scroll_offset:
            self.scroll_offset = self.current_index
        elif self.current_index >= self.scroll_offset + visible_channels:
            self.scroll_offset = min(max_scroll, self.current_index - visible_channels + 1)

        # Ensure scroll_offset is within bounds
        self.scroll_offset = max(0, min(max_scroll, self.scroll_offset))

        # Final check: ensure current selection is visible
        if self.current_index >= len(channels_to_display):
            self.current_index = max(0, len(channels_to_display) - 1)

        if self.current_index < self.scroll_offset:
            self.scroll_offset = self.current_index
        elif self.current_index >= self.scroll_offset + visible_channels:
            self.scroll_offset = max(0, min(max_scroll, self.current_index - visible_channels + 1))

        # Debug logging
        logging.debug(f"Navigation: current_index={self.current_index}, scroll_offset={self.scroll_offset}, visible_channels={visible_channels}, max_scroll={max_scroll}, total_channels={len(channels_to_display)}")

        self.combined_screen.display(
            stdscr,
            channels_to_display,
            self.current_index,
            self.scroll_offset,
            channel_favorites,
            self.current_channel,
            self.player,
            self.is_playing,
            is_searching=self.is_searching,
            search_query=self.search_query
        )

    def _play_channel(self, channel: Dict):
        """Play selected channel and update last played time"""
        try:
            # Update last played
            now = int(time.time())
            if os.path.exists(CHANNEL_USAGE_FILE):
                with open(CHANNEL_USAGE_FILE, 'r') as f:
                    usage = json.load(f)
            else:
                usage = {}
            usage[channel['id']] = now
            # Clean up usage (удаляем несуществующие)
            valid_ids = {c['id'] for c in self.channels}
            usage = {k: v for k, v in usage.items() if k in valid_ids}
            with open(CHANNEL_USAGE_FILE, 'w') as f:
                json.dump(usage, f)

            # Get stream URL from playlists
            stream_url = None
            for playlist in channel.get('playlists', []):
                if playlist.get('format') == 'mp3':
                    stream_url = playlist.get('url')
                    break

            if not stream_url:
                raise Exception(f"No MP3 stream found for channel {channel['title']}")

            # Stop current playback and buffering if any
            if self.player:
                self.player.stop()
            if self.buffer:
                self.buffer.stop_buffering()
                self.buffer.clear()

            # Initialize new buffer
            self.buffer = StreamBuffer(
                url=stream_url,
                buffer_minutes=self.config['buffer_minutes'],
                buffer_size_mb=self.config['buffer_size_mb'],
                cache_dir=CACHE_DIR
            )

            # Start buffering
            self.buffer.start_buffering()

            # Start playback
            self.player.pause = False
            self.player.play(stream_url)
            self.current_channel = channel
            self.is_playing = True
            self.is_paused = False

            # Update combined screen with channel info
            self.combined_screen.current_channel = channel
            self.combined_screen.player = self.player

            # Log channel change
            logging.info(f"Playing channel: {channel['title']}")
            logging.debug(f"Stream URL: {stream_url}")

            # Set initial metadata
            initial_metadata = {
                'artist': 'Loading...',
                'title': 'Loading...',
                'duration': '--:--',
                'timestamp': datetime.now().strftime("%H:%M:%S")
            }
            self.combined_screen.update_metadata(initial_metadata)

            # Update MPRIS service
            if self.mpris_service:
                self.mpris_service.update_playback_status("Playing")
                if self.config.get('dbus_send_metadata', False):
                    self.mpris_service.update_metadata(initial_metadata)

        except Exception as e:
            logging.error(f"Error playing channel: {e}")
            print(f"Error playing channel: {e}")
            self.is_playing = False
            self.is_paused = False
            self.current_channel = None
            # Update MPRIS service on error
            if self.mpris_service:
                self.mpris_service.update_playback_status("Stopped")

    def _toggle_playback(self):
        """Toggle playback pause/resume"""
        if self.is_playing:
            if self.is_paused:
                self.player.pause = False
                self.is_paused = False
                if self.mpris_service:
                    self.mpris_service.update_playback_status("Playing")
            else:
                self.player.pause = True
                self.is_paused = True
                # Update MPRIS service
                if self.mpris_service:
                    self.mpris_service.update_playback_status("Paused")

    def _cleanup(self):
        """Clean up resources"""
        if self.buffer:
            self.buffer.stop_buffering()
            self.buffer.clear()
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

    def run(self):
        """Main application loop"""
        def main(stdscr):
            try:
                # Store stdscr globally for updates
                self.stdscr = stdscr

                # Initialize colors
                self._init_colors()

                # Enable keypad mode for special keys
                stdscr.keypad(True)
                # Enable Unicode support
                curses.raw()
                # Enable non-blocking mode
                stdscr.nodelay(False)

                # Main loop
                while self.running:
                    self._display_combined_interface(stdscr)

                    # Get user input
                    try:
                        key = stdscr.get_wch()
                        logging.debug(f"Pressed key: {key} (type: {type(key)})")

                        if self.is_searching:
                            if key == chr(27):  # ESC
                                self.is_searching = False
                                self.search_query = ""
                            elif key in [curses.KEY_BACKSPACE, '\b', '\x7f']:
                                self.search_query = self.search_query[:-1]
                            elif isinstance(key, str) and len(key) == 1 and key.isprintable():
                                self.search_query += key
                                self.current_index = 0
                            # Navigation
                            elif key == curses.KEY_UP or (isinstance(key, str) and key == 'k'):
                                self.current_index = max(0, self.current_index - 1)
                            elif key == curses.KEY_DOWN or (isinstance(key, str) and key == 'j'):
                                if self.filtered_channels:
                                    self.current_index = min(len(self.filtered_channels) - 1, self.current_index + 1)
                            # Selection
                            elif key in [curses.KEY_ENTER, '\n', '\r'] or (isinstance(key, str) and key == 'l'):
                                if self.filtered_channels:
                                    selected_channel = self.filtered_channels[self.current_index]
                                    self._play_channel(selected_channel)
                                    # Find original index to restore view
                                    for i, ch in enumerate(self.channels):
                                        if ch['id'] == selected_channel['id']:
                                            self.current_index = i
                                            break
                                self.is_searching = False
                                self.search_query = ""
                        else:
                            # Normal mode
                            if isinstance(key, str):
                                if key == '/':
                                    self.is_searching = True
                                    self.search_query = ""
                                    self.current_index = 0
                                elif key in ['q', 'й', 'Q', 'Й', chr(27)]:
                                    self.running = False
                                elif key in ['h', 'H']:  # Stop playback
                                    if self.is_playing:
                                        self.player.stop()
                                        self.is_playing = False
                                        self.is_paused = False
                                        self.current_channel = None
                                        if self.buffer:
                                            self.buffer.stop_buffering()
                                            self.buffer.clear()
                                        self.current_metadata = {'artist': 'Loading...', 'title': 'Loading...', 'duration': '--:'}
                                        self.combined_screen.current_metadata = self.current_metadata.copy()
                                elif key in ['\n', '\r', 'l']:
                                    self._play_channel(self.channels[self.current_index])
                                elif key == ' ':
                                    if self.is_playing:
                                        self._toggle_playback()
                                elif key in ['f', 'F']:
                                    if self.is_playing:
                                        fav_dir = os.path.join(HOME, ".somafm_tui")
                                        fav_file = os.path.join(fav_dir, "favorites.list")
                                        os.makedirs(fav_dir, exist_ok=True)
                                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        meta = self.combined_screen.current_metadata
                                        fav_line = f"{meta['artist']} - {meta['title']} ({now})\n"
                                        with open(fav_file, "a") as f: f.write(fav_line)
                                        self.combined_screen.show_notification(stdscr, f"Added to favorites: {meta['title']}")
                                    else:
                                        self._toggle_channel_favorite(self.channels[self.current_index]['id'])
                                elif key == 'k':
                                    self.current_index = max(0, self.current_index - 1)
                                elif key == 'j':
                                    self.current_index = min(len(self.channels) - 1, self.current_index + 1)
                                elif key in ['t', 'T']:
                                    self._cycle_theme()
                                    self._init_colors()
                                    stdscr.clear()
                                    stdscr.refresh()
                                elif key in ['a', 'A']:
                                    self._toggle_alternative_bg()
                                    stdscr.clear()
                                    stdscr.refresh()
                            else:  # Handle special keys
                                if key == curses.KEY_UP:
                                    self.current_index = max(0, self.current_index - 1)
                                elif key == curses.KEY_DOWN:
                                    self.current_index = min(len(self.channels) - 1, self.current_index + 1)
                                elif key == curses.KEY_ENTER:
                                    self._play_channel(self.channels[self.current_index])
                    except curses.error:
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

    def _load_channel_favorites(self) -> Set[str]:
        """Load favorite channel IDs from file"""
        if os.path.exists(CHANNEL_FAVORITES_FILE):
            with open(CHANNEL_FAVORITES_FILE, 'r') as f:
                try:
                    return set(json.load(f))
                except json.JSONDecodeError:
                    return set()
        return set()

    def _save_channel_favorites(self, favorites: Set[str]):
        """Save favorite channel IDs to file"""
        with open(CHANNEL_FAVORITES_FILE, 'w') as f:
            json.dump(list(favorites), f)

    def _toggle_channel_favorite(self, channel_id: str):
        """Toggle favorite status for a channel"""
        favorites = self._load_channel_favorites()
        if channel_id in favorites:
            favorites.remove(channel_id)
            logging.debug(f"Channel {channel_id} removed from favorites.")
        else:
            favorites.add(channel_id)
            logging.debug(f"Channel {channel_id} added to favorites.")
        self._save_channel_favorites(favorites)

    def _cycle_theme(self):
        """Cycle through available themes"""
        themes = list(self._get_color_themes().keys())
        current_theme = self.config.get('theme', 'default')

        try:
            current_index = themes.index(current_theme)
            next_index = (current_index + 1) % len(themes)
        except ValueError:
            next_index = 0

        new_theme = themes[next_index]
        self.config['theme'] = new_theme

        # Save new theme to config file
        self._save_config()

        # Show notification about theme change
        theme_info = self._get_color_themes()[new_theme]
        bg_mode = " (Alt BG)" if self.alternative_bg_mode else ""
        if self.stdscr and self.combined_screen:
            self.combined_screen.show_notification(
                self.stdscr,
                f"Theme: {theme_info['name']}{bg_mode}",
                timeout=1.0
            )

    def _toggle_alternative_bg(self):
        """Toggle alternative background mode (pure black vs dark gray)"""
        self.alternative_bg_mode = not self.alternative_bg_mode

        # Save to config
        self.config['alternative_bg_mode'] = self.alternative_bg_mode
        self._save_config()

        # Reinitialize colors with new background mode
        self._init_colors()

        # Show notification about background mode change
        current_theme = self.config.get('theme', 'default')
        theme_info = self._get_color_themes()[current_theme]
        bg_mode = "Alternative BG" if self.alternative_bg_mode else "Normal BG"
        if self.stdscr and self.combined_screen:
            self.combined_screen.show_notification(
                self.stdscr,
                f"{theme_info['name']}: {bg_mode}",
                timeout=1.0
            )

    def _save_config(self):
        """Save current configuration to file"""
        try:
            # Read existing config to preserve comments
            config_lines = []
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config_lines = f.readlines()

            # Update or add config values
            updated_lines = []
            updated_keys = set()

            for line in config_lines:
                if line.startswith('#') or ':' not in line:
                    updated_lines.append(line)
                else:
                    key, _ = line.split(':', 1)
                    key = key.strip()
                    if key in self.config:
                        value = self.config[key]
                        # Convert boolean to lowercase string for config file
                        if isinstance(value, bool):
                            value = str(value).lower()
                        updated_lines.append(f"{key}: {value}\n")
                        updated_keys.add(key)
                    else:
                        updated_lines.append(line)

            # Add any new config keys
            for key, value in self.config.items():
                if key not in updated_keys:
                    # Convert boolean to lowercase string for config file
                    if isinstance(value, bool):
                        value = str(value).lower()
                    updated_lines.append(f"{key}: {value}\n")

            # Write updated config
            with open(CONFIG_FILE, 'w') as f:
                f.writelines(updated_lines)

        except Exception as e:
            logging.error(f"Error saving config: {e}")

if __name__ == "__main__":
    player = SomaFMPlayer()
    player.run()
