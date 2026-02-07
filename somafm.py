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
        self.volume_display = None  # Current volume to display (None = hide)
        self.volume_display_time = 0  # Time when volume was last changed
        self.volume_display_was_visible = False  # Track if volume indicator was visible in previous frame

    def display(self, stdscr, channels, selected_index, scroll_offset, channel_favorites, current_channel=None, player=None, is_playing=False, is_searching=False, search_query=""):
        """Display combined interface with channels on left and playback on right"""
        import time
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
                "PgUp/Dn - volume",
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

        # Display volume indicator - show for 3 seconds after last change
        should_show_volume = False
        if self.volume_display is not None:
            # Show if volume was set less than 3 seconds ago
            if time.time() - self.volume_display_time < 3:
                should_show_volume = True
            else:
                # Hide after timeout
                self.volume_display = None
                self.volume_display_time = 0

        # First, clear volume display if it was visible in the previous frame but shouldn't be anymore
        if not should_show_volume and self.volume_display_was_visible:
            self._clear_volume(stdscr)
            self.volume_display_was_visible = False

        # Then, display volume if needed
        if should_show_volume:
            self._display_volume(stdscr)
            self.volume_display_was_visible = True

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

    def show_volume(self, stdscr, volume: int):
        """Set volume to display (will be shown on next display() call)"""
        import time
        self.volume_display = volume
        self.volume_display_time = time.time()  # Remember when volume was changed

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


    def _display_volume(self, stdscr):
        """Draw volume level at top-right corner with orange bar and speaker icon"""
        max_y, max_x = stdscr.getmaxyx()
        bar_width = 20
        start_y = 1
        start_x = max_x - bar_width - 5  # Positioned at top-right (closer to edge)

        try:
            volume = self.volume_display

            # Orange color for the bar (one solid color)
            vol_bar_color = 60  # color_pair 60 - orange
            vol_icon_color = 61  # color_pair 61 - yellow

            # Draw volume bar (filled part with orange)
            filled_blocks = int((volume / 100) * bar_width)
            empty_blocks = bar_width - filled_blocks

            # Draw filled blocks with orange (no space between icon and bar)
            if filled_blocks > 0:
                filled_bar = "█" * filled_blocks
                try:
                    stdscr.addstr(start_y, start_x, filled_bar, curses.color_pair(vol_bar_color) | curses.A_BOLD)
                except curses.error:
                    pass

            # Draw empty blocks with dimmed orange
            if empty_blocks > 0:
                empty_bar = "▁" * empty_blocks
                try:
                    stdscr.addstr(start_y, start_x + filled_blocks, empty_bar, curses.color_pair(vol_bar_color) | curses.A_DIM)
                except curses.error:
                    pass

            # Draw speaker icon (immediately to the left of bar, no space)
            vol_icon = "🔊"
            icon_x = start_x - len(vol_icon)
            try:
                stdscr.addstr(start_y, icon_x, vol_icon, curses.color_pair(vol_icon_color) | curses.A_BOLD)
            except curses.error:
                pass

            # Draw percentage (immediately to the right of bar, no space)
            vol_text = f"{volume:3d}%"
            text_x = start_x + bar_width
            try:
                stdscr.addstr(start_y, text_x, vol_text, curses.color_pair(vol_icon_color) | curses.A_BOLD)
            except curses.error:
                pass

        except curses.error:
            pass

    def _clear_volume(self, stdscr):
        """Clear volume display from screen"""
        max_y, max_x = stdscr.getmaxyx()
        bar_width = 20
        start_y = 1
        start_x = max_x - bar_width - 5

        try:
            # Clear the line where volume is displayed
            width = bar_width + 10  # Include space for icon and text
            clear_line = " " * width
            stdscr.addstr(start_y, start_x - 5, clear_line, curses.color_pair(1))
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
        self.volume = self.config.get('volume', 100)  # Load volume from config, default 100

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
        # 5 light themes, 16 dark themes (including default)
        return {
            # Light Themes
            'one-light': {
                'name': 'One Light',
                'bg_color': 10,  # Custom color: #fafafa (250, 250, 250) -> (1000, 1000, 1000)
                'header': 11,    # Custom color: #e45649 (228, 86, 73) -> (912, 344, 292)
                'selected': 12,  # Custom color: #383a42 (56, 58, 66) -> (224, 232, 264)
                'info': 13,      # Custom color: #50a14f (80, 161, 79) -> (320, 644, 316)
                'metadata': 14,  # Custom color: #4078f2 (64, 120, 242) -> (256, 480, 968)
                'instructions': 15, # Custom color: #0184bc (1, 132, 188) -> (4, 528, 752)
                'favorite': 16   # Custom color: #c18401 (193, 132, 1) -> (772, 528, 4)
            },
            'github-light': {
                'name': 'GitHub Light',
                'bg_color': curses.COLOR_WHITE,
                'header': 17,    # Custom color: #0969da (9, 105, 218) -> (36, 420, 872)
                'selected': 18,  # Custom color: #24292f (36, 41, 47) -> (144, 164, 188)
                'info': 19,      # Custom color: #28a745 (40, 167, 69) -> (160, 668, 276)
                'metadata': 20,  # Custom color: #d29922 (210, 153, 34) -> (840, 612, 136)
                'instructions': 21, # Custom color: #cb2431 (203, 36, 49) -> (812, 144, 196)
                'favorite': 21   # Same as instructions
            },
            'solarized-light': {
                'name': 'Solarized Light',
                'bg_color': 22,  # Custom color: #fdf6e3 (253, 246, 227) -> (1000, 984, 908)
                'header': 23,    # Custom color: #b58900 (181, 137, 0) -> (724, 548, 0)
                'selected': 24,  # Custom color: #586e75 (88, 110, 117) -> (352, 440, 468)
                'info': 25,      # Custom color: #93a1a1 (147, 161, 161) -> (588, 644, 644)
                'metadata': 26,  # Custom color: #268bd2 (38, 139, 210) -> (152, 556, 840)
                'instructions': 27, # Custom color: #859900 (133, 153, 0) -> (532, 612, 0)
                'favorite': 28   # Custom color: #dc322f (220, 50, 47) -> (880, 200, 188)
            },

            'ayu-light': {
                'name': 'Ayu Light',
                'bg_color': 41,  # Custom color: #fafafa (250, 250, 250) -> (1000, 1000, 1000)
                'header': 42,    # Custom color: #e6b450 (230, 180, 80) -> (920, 720, 320)
                'selected': 43,  # Custom color: #575f66 (87, 95, 102) -> (348, 380, 408)
                'info': 44,      # Custom color: #8a9199 (138, 145, 153) -> (552, 580, 612)
                'metadata': 45,  # Custom color: #409c50 (64, 156, 80) -> (256, 624, 320)
                'instructions': 46, # Custom color: #686868 (104, 104, 104) -> (416, 416, 416)
                'favorite': 47   # Custom color: #ff9940 (255, 153, 64) -> (1000, 612, 256)
            },
            'material-light': {
                'name': 'Material Light',
                'bg_color': 48,  # Custom color: #fafafa (250, 250, 250) -> (1000, 1000, 1000)
                'header': 49,    # Custom color: #42a5f5 (66, 165, 245) -> (264, 660, 980)
                'selected': 50,  # Custom color: #263238 (38, 50, 56) -> (152, 200, 224)
                'info': 51,      # Custom color: #43a047 (67, 160, 71) -> (268, 640, 284)
                'metadata': 52,  # Custom color: #f57c00 (245, 124, 0) -> (980, 496, 0)
                'instructions': 53, # Custom color: #546e7a (84, 110, 122) -> (336, 440, 488)
                'favorite': 54   # Custom color: #e53935 (229, 57, 53) -> (916, 228, 212)
            },


            # Dark Themes
            'one-dark': {
                'name': 'One Dark',
                'bg_color': 76,  # Custom color: #282c34 (40, 44, 52) -> (160, 176, 208)
                'header': 77,    # Custom color: #e06c75 (224, 108, 117) -> (896, 432, 468)
                'selected': 78,  # Custom color: #abb2bf (171, 178, 191) -> (684, 712, 764)
                'info': 79,      # Custom color: #98c379 (152, 195, 121) -> (608, 780, 484)
                'metadata': 80,  # Custom color: #56b6c2 (86, 182, 194) -> (344, 728, 776)
                'instructions': 81, # Custom color: #61afef (97, 175, 239) -> (388, 700, 956)
                'favorite': 82   # Custom color: #e5c07b (229, 192, 123) -> (916, 768, 492)
            },
            'dracula': {
                'name': 'Dracula',
                'bg_color': 83,  # Custom color: #282a36 (40, 42, 54) -> (160, 168, 216)
                'header': 84,    # Custom color: #f8f8f2 (248, 248, 242) -> (992, 992, 968)
                'selected': 85,  # Custom color: #ff79c6 (255, 121, 198) -> (1000, 484, 792)
                'info': 86,      # Custom color: #50fa7b (80, 250, 123) -> (320, 1000, 492)
                'metadata': 87,  # Custom color: #8be9fd (139, 233, 253) -> (556, 932, 1000)
                'instructions': 88, # Custom color: #bd93f9 (189, 147, 249) -> (756, 588, 996)
                'favorite': 89   # Custom color: #ffb86c (255, 184, 108) -> (1000, 736, 432)
            },
            'tokyo-night': {
                'name': 'Tokyo Night',
                'bg_color': 90,  # Custom color: #1e1a38 (30, 26, 56) -> (120, 104, 224)
                'header': 91,    # Custom color: #c0caf5 (192, 202, 245) -> (768, 808, 980)
                'selected': 92,  # Custom color: #f03d55 (240, 61, 85) -> (960, 244, 340)
                'info': 93,      # Custom color: #00d4ff (0, 212, 255) -> (0, 848, 1000)
                'metadata': 94,  # Custom color: #8a7b9d (138, 123, 157) -> (552, 492, 628)
                'instructions': 95, # Custom color: #a9b1d6 (169, 177, 214) -> (676, 708, 856)
                'favorite': 96   # Custom color: #7aa2f7 (122, 162, 247) -> (488, 648, 988)
            },
            'monokai': {
                'name': 'Monokai',
                'bg_color': 97,  # Custom color: #2e2e2e (46, 46, 46) -> (184, 184, 184)
                'header': 98,    # Custom color: #f8f8f2 (248, 248, 242) -> (992, 992, 968)
                'selected': 99,  # Custom color: #e5b567 (229, 181, 103) -> (916, 724, 412)
                'info': 100,     # Custom color: #b4d273 (180, 210, 115) -> (720, 840, 460)
                'metadata': 101, # Custom color: #e87d3e (232, 125, 62) -> (928, 500, 248)
                'instructions': 102, # Custom color: #9e86c8 (158, 134, 200) -> (632, 536, 800)
                'favorite': 103  # Custom color: #b05279 (176, 82, 121) -> (704, 328, 484)
            },
            'gruvbox': {
                'name': 'Gruvbox',
                'bg_color': 104, # Custom color: #282828 (40, 40, 40) -> (160, 160, 160)
                'header': 105,   # Custom color: #ebdbb2 (235, 219, 178) -> (940, 876, 712)
                'selected': 106, # Custom color: #fb4934 (251, 73, 52) -> (1000, 292, 208)
                'info': 107,     # Custom color: #b8bb26 (184, 187, 38) -> (736, 748, 152)
                'metadata': 108, # Custom color: #fabd2f (250, 189, 47) -> (1000, 756, 188)
                'instructions': 109, # Custom color: #83a598 (131, 165, 152) -> (524, 660, 608)
                'favorite': 110  # Custom color: #d3869b (211, 134, 155) -> (844, 536, 620)
            },
            'ayu-dark': {
                'name': 'Ayu Dark',
                'bg_color': 111, # Custom color: #0f1419 (15, 20, 25) -> (60, 80, 100)
                'header': 112,   # Custom color: #c7cdd9 (199, 205, 217) -> (796, 820, 868)
                'selected': 113, # Custom color: #ff3333 (255, 51, 51) -> (1000, 204, 204)
                'info': 114,     # Custom color: #bae67e (186, 230, 126) -> (744, 920, 504)
                'metadata': 115, # Custom color: #73d0ff (115, 208, 255) -> (460, 832, 1000)
                'instructions': 116, # Custom color: #c792ea (199, 146, 234) -> (796, 584, 936)
                'favorite': 117  # Custom color: #ffcc66 (255, 204, 102) -> (1000, 816, 408)
            },
            'solarized-dark': {
                'name': 'Solarized Dark',
                'bg_color': 118, # Custom color: #002b36 (0, 43, 54) -> (0, 172, 216)
                'header': 119,   # Custom color: #839496 (131, 148, 150) -> (524, 592, 600)
                'selected': 120, # Custom color: #b58900 (181, 137, 0) -> (724, 548, 0)
                'info': 121,     # Custom color: #2aa198 (42, 161, 152) -> (168, 644, 608)
                'metadata': 122, # Custom color: #268bd2 (38, 139, 210) -> (152, 556, 840)
                'instructions': 123, # Custom color: #6c71c4 (108, 113, 196) -> (432, 452, 784)
                'favorite': 124  # Custom color: #d33682 (211, 54, 130) -> (844, 216, 520)
            },
            'github-dark': {
                'name': 'GitHub Dark',
                'bg_color': 125, # Custom color: #0d1117 (13, 17, 23) -> (52, 68, 92)
                'header': 126,   # Custom color: #c9d1d9 (201, 209, 217) -> (804, 836, 868)
                'selected': 127, # Custom color: #539bf5 (83, 155, 245) -> (332, 620, 980)
                'info': 128,     # Custom color: #56d364 (86, 211, 100) -> (344, 844, 400)
                'metadata': 129, # Custom color: #d29922 (210, 153, 34) -> (840, 612, 136)
                'instructions': 130, # Custom color: #f0f6fc (240, 246, 252) -> (960, 984, 1000)
                'favorite': 131  # Custom color: #f85149 (248, 81, 73) -> (992, 324, 292)
            },
            'monochrome-dark': {
                'name': 'Monochrome Dark',
                'bg_color': curses.COLOR_BLACK,
                'header': curses.COLOR_WHITE,
                'selected': curses.COLOR_WHITE,  # Changed from curses.COLOR_BLACK to curses.COLOR_WHITE
                'info': curses.COLOR_WHITE,
                'metadata': curses.COLOR_WHITE,
                'instructions': curses.COLOR_WHITE,
                'favorite': curses.COLOR_WHITE
            },
            'nord': {
                'name': 'Nord',
                'bg_color': 133,  # Custom color: #2e3440 (46, 52, 64) -> (184, 208, 256)
                'header': 134,    # Custom color: #88c0d0 (136, 192, 208) -> (544, 768, 832)
                'selected': 135,  # Custom color: #d8dee9 (216, 222, 233) -> (864, 888, 932)
                'info': 136,      # Custom color: #8fbcbb (143, 188, 187) -> (572, 752, 748)
                'metadata': 137,  # Custom color: #5e81ac (94, 129, 172) -> (376, 516, 688)
                'instructions': 138, # Custom color: #6c71c4 (108, 113, 196) -> (432, 452, 784)
                'favorite': 139  # Custom color: #d08770 (208, 135, 112) -> (832, 540, 448)
            },
            'night-owl': {
                'name': 'Night Owl',
                'bg_color': 140,  # Custom color: #011627 (1, 22, 39) -> (4, 88, 156)
                'header': 141,    # Custom color: #c792ea (199, 146, 234) -> (796, 584, 936)
                'selected': 142,  # Custom color: #ffffff (255, 255, 255) -> (1000, 1000, 1000)
                'info': 143,      # Custom color: #82aaff (130, 170, 255) -> (520, 680, 1000)
                'metadata': 144,  # Custom color: #addb67 (173, 219, 103) -> (692, 876, 412)
                'instructions': 145, # Custom color: #637777 (99, 119, 119) -> (396, 476, 476)
                'favorite': 146  # Custom color: #ff5874 (255, 88, 116) -> (1000, 352, 464)
            },
            'catppuccin': {
                'name': 'Catppuccin',
                'bg_color': 147,  # Custom color: #1e1d2b (30, 29, 43) -> (120, 116, 172)
                'header': 148,    # Custom color: #b4befe (180, 190, 254) -> (720, 760, 1000)
                'selected': 149,  # Custom color: #f5e0dc (245, 224, 220) -> (980, 896, 880)
                'info': 150,      # Custom color: #a6e3a1 (166, 227, 161) -> (664, 908, 644)
                'metadata': 151,  # Custom color: #74c7ec (116, 199, 236) -> (464, 796, 944)
                'instructions': 152, # Custom color: #9399b2 (147, 153, 178) -> (588, 612, 712)
                'favorite': 153  # Custom color: #f38ba8 (243, 139, 168) -> (972, 556, 672)
            },
            'cobalt': {
                'name': 'Cobalt',
                'bg_color': 154,  # Custom color: #002240 (0, 34, 64) -> (0, 136, 256)
                'header': 155,    # Custom color: #ffffff (255, 255, 255) -> (1000, 1000, 1000)
                'selected': 156,  # Custom color: #e6f0ff (230, 240, 255) -> (920, 960, 1000)
                'info': 157,      # Custom color: #a9cfff (169, 207, 255) -> (676, 828, 1000)
                'metadata': 158,  # Custom color: #90c0f0 (144, 192, 240) -> (576, 768, 960)
                'instructions': 159, # Custom color: #80a0d0 (128, 160, 208) -> (512, 640, 832)
                'favorite': 160  # Custom color: #ff6480 (255, 100, 128) -> (1000, 400, 512)
            },
            'zenburn': {
                'name': 'Zenburn',
                'bg_color': 161,  # Custom color: #3f3f3f (63, 63, 63) -> (252, 252, 252)
                'header': 162,    # Custom color: #dcdccc (220, 220, 204) -> (880, 880, 816)
                'selected': 163,  # Custom color: #f0dfaf (240, 223, 175) -> (960, 892, 700)
                'info': 164,      # Custom color: #ccffaf (204, 255, 175) -> (816, 1000, 700)
                'metadata': 165,  # Custom color: #7f9f7f (127, 159, 127) -> (508, 636, 508)
                'instructions': 166, # Custom color: #d0d0a0 (208, 208, 160) -> (832, 832, 640)
                'favorite': 167  # Custom color: #dca3a3 (220, 163, 163) -> (880, 652, 652)
            },
            'ayu-mirage': {
                'name': 'Ayu Mirage',
                'bg_color': 168,  # Custom color: #202734 (32, 39, 52) -> (128, 156, 208)
                'header': 169,    # Custom color: #f28779 (242, 135, 121) -> (968, 540, 484)
                'selected': 170,  # Custom color: #ffcc66 (255, 204, 102) -> (1000, 816, 408)
                'info': 171,      # Custom color: #bae67e (186, 230, 126) -> (744, 920, 504)
                'metadata': 172,  # Custom color: #73d0ff (115, 208, 255) -> (460, 832, 1000)
                'instructions': 173, # Custom color: #c792ea (199, 146, 234) -> (796, 584, 936)
                'favorite': 174  # Custom color: #ffd700 (255, 215, 0) -> (1000, 860, 0)
            },

            'default': {
                'name': 'Default Dark',
                'bg_color': curses.COLOR_BLACK,
                'header': curses.COLOR_CYAN,
                'selected': curses.COLOR_GREEN,
                'info': curses.COLOR_YELLOW,
                'metadata': curses.COLOR_MAGENTA,
                'instructions': curses.COLOR_BLUE,
                'favorite': curses.COLOR_RED
            }
        }

    def _init_colors(self):
        """Initialize colors based on selected theme"""
        curses.start_color()

        # Initialize custom colors based on themes
        # Light themes
        curses.init_color(10, 1000, 1000, 1000)  # #fafafa (One Light bg)
        curses.init_color(11, 912, 344, 292)     # #e45649 (One Light header)
        curses.init_color(12, 224, 232, 264)     # #383a42 (One Light selected)
        curses.init_color(13, 320, 644, 316)     # #50a14f (One Light info)
        curses.init_color(14, 256, 480, 968)     # #4078f2 (One Light metadata)
        curses.init_color(15, 4, 528, 752)       # #0184bc (One Light instructions)
        curses.init_color(16, 772, 528, 4)       # #c18401 (One Light favorite)
        curses.init_color(17, 36, 420, 872)      # #0969da (GitHub Light header)
        curses.init_color(18, 144, 164, 188)     # #24292f (GitHub Light selected)
        curses.init_color(19, 160, 668, 276)     # #28a745 (GitHub Light info)
        curses.init_color(20, 840, 612, 136)     # #d29922 (GitHub Light metadata)
        curses.init_color(21, 812, 144, 196)     # #cb2431 (GitHub Light instructions/favorite)
        curses.init_color(22, 1000, 984, 908)    # #fdf6e3 (Solarized Light bg)
        curses.init_color(23, 724, 548, 0)       # #b58900 (Solarized Light header)
        curses.init_color(24, 352, 440, 468)     # #586e75 (Solarized Light selected)
        curses.init_color(25, 588, 644, 644)     # #93a1a1 (Solarized Light info)
        curses.init_color(26, 152, 556, 840)     # #268bd2 (Solarized Light metadata)
        curses.init_color(27, 532, 612, 0)       # #859900 (Solarized Light instructions)
        curses.init_color(28, 880, 200, 188)     # #dc322f (Solarized Light favorite)
        curses.init_color(29, 836, 616, 408)     # #d19a66 (Light Plus header)
        curses.init_color(30, 224, 232, 264)     # #383a42 (Light Plus selected)
        curses.init_color(31, 896, 432, 468)     # #e06c75 (Light Plus info)
        curses.init_color(32, 388, 700, 956)     # #61afef (Light Plus metadata)
        curses.init_color(33, 684, 712, 764)     # #abb2bf (Light Plus instructions)
        curses.init_color(34, 792, 480, 884)     # #c678dd (Light Plus favorite)
        curses.init_color(35, 144, 164, 184)     # #24292e (Paper header)
        curses.init_color(36, 12, 408, 856)      # #0366d6 (Paper selected)
        curses.init_color(37, 160, 668, 276)     # #28a745 (Paper info)
        curses.init_color(38, 0, 368, 788)       # #005cc5 (Paper metadata)
        curses.init_color(39, 352, 384, 420)     # #586069 (Paper instructions)
        curses.init_color(40, 908, 392, 36)      # #e36209 (Paper favorite)
        curses.init_color(41, 1000, 1000, 1000)  # #fafafa (Ayu Light bg)
        curses.init_color(42, 920, 720, 320)     # #e6b450 (Ayu Light header)
        curses.init_color(43, 348, 380, 408)     # #575f66 (Ayu Light selected)
        curses.init_color(44, 552, 580, 612)     # #8a9199 (Ayu Light info)
        curses.init_color(45, 256, 624, 320)     # #409c50 (Ayu Light metadata)
        curses.init_color(46, 416, 416, 416)     # #686868 (Ayu Light instructions)
        curses.init_color(47, 1000, 612, 256)    # #ff9940 (Ayu Light favorite)
        curses.init_color(48, 1000, 1000, 1000)  # #fafafa (Material Light bg)
        curses.init_color(49, 264, 660, 980)     # #42a5f5 (Material Light header)
        curses.init_color(50, 152, 200, 224)     # #263238 (Material Light selected)
        curses.init_color(51, 268, 640, 284)     # #43a047 (Material Light info)
        curses.init_color(52, 980, 496, 0)       # #f57c00 (Material Light metadata)
        curses.init_color(53, 336, 440, 488)     # #546e7a (Material Light instructions)
        curses.init_color(54, 916, 228, 212)     # #e53935 (Material Light favorite)

        curses.init_color(55, 1000, 1000, 1000)  # #ffffff (IntelliJ Light bg)
        curses.init_color(56, 836, 616, 408)     # #d19a66 (IntelliJ Light header)
        curses.init_color(57, 240, 252, 260)     # #3c3f41 (IntelliJ Light selected)
        curses.init_color(58, 608, 780, 484)     # #98c379 (IntelliJ Light info)
        curses.init_color(59, 388, 700, 956)     # #61afef (IntelliJ Light metadata)
        curses.init_color(60, 684, 712, 764)     # #abb2bf (IntelliJ Light instructions)
        curses.init_color(61, 896, 432, 468)     # #e06c75 (IntelliJ Light favorite)
        curses.init_color(62, 1000, 1000, 1000)  # #ffffff (Xcode Light bg)
        curses.init_color(63, 860, 744, 500)     # #d7ba7d (Xcode Light header)
        curses.init_color(64, 216, 216, 216)     # #363636 (Xcode Light selected)
        curses.init_color(65, 312, 804, 704)     # #4ec9b0 (Xcode Light info)
        curses.init_color(66, 624, 880, 1000)    # #9cdcfe (Xcode Light metadata)
        curses.init_color(67, 848, 848, 848)     # #d4d4d4 (Xcode Light instructions)
        curses.init_color(68, 976, 284, 284)     # #f44747 (Xcode Light favorite)
        curses.init_color(69, 1000, 1000, 1000)  # #ffffff (VSCode Light bg)
        curses.init_color(70, 0, 488, 816)       # #007acc (VSCode Light header)
        curses.init_color(71, 240, 240, 240)     # #3c3c3c (VSCode Light selected)
        curses.init_color(72, 468, 760, 1000)    # #75beff (VSCode Light info)
        curses.init_color(73, 412, 600, 920)     # #6796e6 (VSCode Light metadata)
        curses.init_color(74, 556, 592, 632)     # #8b949e (VSCode Light instructions)
        curses.init_color(75, 916, 80, 0)        # #e51400 (VSCode Light favorite)

        # Dark themes
        curses.init_color(76, 160, 176, 208)     # #282c34 (One Dark bg)
        curses.init_color(77, 896, 432, 468)     # #e06c75 (One Dark header)
        curses.init_color(78, 684, 712, 764)     # #abb2bf (One Dark selected)
        curses.init_color(79, 608, 780, 484)     # #98c379 (One Dark info)
        curses.init_color(80, 344, 728, 776)     # #56b6c2 (One Dark metadata)
        curses.init_color(81, 388, 700, 956)     # #61afef (One Dark instructions)
        curses.init_color(82, 916, 768, 492)     # #e5c07b (One Dark favorite)
        curses.init_color(83, 160, 168, 216)     # #282a36 (Dracula bg)
        curses.init_color(84, 992, 992, 968)     # #f8f8f2 (Dracula header)
        curses.init_color(85, 1000, 484, 792)    # #ff79c6 (Dracula selected)
        curses.init_color(86, 320, 1000, 492)    # #50fa7b (Dracula info)
        curses.init_color(87, 556, 932, 1000)    # #8be9fd (Dracula metadata)
        curses.init_color(88, 756, 588, 996)     # #bd93f9 (Dracula instructions)
        curses.init_color(89, 1000, 736, 432)    # #ffb86c (Dracula favorite)
        curses.init_color(90, 120, 104, 224)     # #1e1a38 (Tokyo Night bg)
        curses.init_color(91, 768, 808, 980)     # #c0caf5 (Tokyo Night header)
        curses.init_color(92, 960, 244, 340)     # #f03d55 (Tokyo Night selected)
        curses.init_color(93, 0, 848, 1000)      # #00d4ff (Tokyo Night info)
        curses.init_color(94, 552, 492, 628)     # #8a7b9d (Tokyo Night metadata)
        curses.init_color(95, 676, 708, 856)     # #a9b1d6 (Tokyo Night instructions)
        curses.init_color(96, 488, 648, 988)     # #7aa2f7 (Tokyo Night favorite)
        curses.init_color(97, 184, 184, 184)     # #2e2e2e (Monokai bg)
        curses.init_color(98, 992, 992, 968)     # #f8f8f2 (Monokai header)
        curses.init_color(99, 916, 724, 412)     # #e5b567 (Monokai selected)
        curses.init_color(100, 720, 840, 460)    # #b4d273 (Monokai info)
        curses.init_color(101, 928, 500, 248)    # #e87d3e (Monokai metadata)
        curses.init_color(102, 632, 536, 800)    # #9e86c8 (Monokai instructions)
        curses.init_color(103, 704, 328, 484)    # #b05279 (Monokai favorite)
        curses.init_color(104, 160, 160, 160)    # #282828 (Gruvbox bg)
        curses.init_color(105, 940, 876, 712)    # #ebdbb2 (Gruvbox header)
        curses.init_color(106, 1000, 292, 208)   # #fb4934 (Gruvbox selected)
        curses.init_color(107, 736, 748, 152)    # #b8bb26 (Gruvbox info)
        curses.init_color(108, 1000, 756, 188)   # #fabd2f (Gruvbox metadata)
        curses.init_color(109, 524, 660, 608)    # #83a598 (Gruvbox instructions)
        curses.init_color(110, 844, 536, 620)    # #d3869b (Gruvbox favorite)
        curses.init_color(111, 60, 80, 100)      # #0f1419 (Ayu Dark bg)
        curses.init_color(112, 796, 820, 868)    # #c7cdd9 (Ayu Dark header)
        curses.init_color(113, 1000, 204, 204)   # #ff3333 (Ayu Dark selected)
        curses.init_color(114, 744, 920, 504)    # #bae67e (Ayu Dark info)
        curses.init_color(115, 460, 832, 1000)   # #73d0ff (Ayu Dark metadata)
        curses.init_color(116, 796, 584, 936)    # #c792ea (Ayu Dark instructions)
        curses.init_color(117, 1000, 816, 408)   # #ffcc66 (Ayu Dark favorite)
        curses.init_color(118, 0, 172, 216)      # #002b36 (Solarized Dark bg)
        curses.init_color(119, 524, 592, 600)    # #839496 (Solarized Dark header)
        curses.init_color(120, 724, 548, 0)      # #b58900 (Solarized Dark selected)
        curses.init_color(121, 168, 644, 608)    # #2aa198 (Solarized Dark info)
        curses.init_color(122, 152, 556, 840)    # #268bd2 (Solarized Dark metadata)
        curses.init_color(123, 432, 452, 784)    # #6c71c4 (Solarized Dark instructions)
        curses.init_color(124, 844, 216, 520)    # #d33682 (Solarized Dark favorite)
        curses.init_color(125, 52, 68, 92)       # #0d1117 (GitHub Dark bg)
        curses.init_color(126, 804, 836, 868)    # #c9d1d9 (GitHub Dark header)
        curses.init_color(127, 332, 620, 980)    # #539bf5 (GitHub Dark selected)
        curses.init_color(128, 344, 844, 400)    # #56d364 (GitHub Dark info)
        curses.init_color(129, 840, 612, 136)    # #d29922 (GitHub Dark metadata)
        curses.init_color(130, 960, 984, 1000)   # #f0f6fc (GitHub Dark instructions)
        curses.init_color(131, 992, 324, 292)    # #f85149 (GitHub Dark favorite)
        curses.init_color(133, 184, 208, 256)    # #2e3440 (Nord bg)
        curses.init_color(134, 544, 768, 832)    # #88c0d0 (Nord header)
        curses.init_color(135, 864, 888, 932)    # #d8dee9 (Nord selected)
        curses.init_color(136, 572, 752, 748)    # #8fbcbb (Nord info)
        curses.init_color(137, 376, 516, 688)    # #5e81ac (Nord metadata)
        curses.init_color(138, 432, 452, 784)    # #6c71c4 (Nord instructions)
        curses.init_color(139, 832, 540, 448)    # #d08770 (Nord favorite)
        curses.init_color(140, 4, 88, 156)       # #011627 (Night Owl bg)
        curses.init_color(141, 796, 584, 936)    # #c792ea (Night Owl header)
        curses.init_color(142, 1000, 1000, 1000) # #ffffff (Night Owl selected)
        curses.init_color(143, 520, 680, 1000)   # #82aaff (Night Owl info)
        curses.init_color(144, 692, 876, 412)    # #addb67 (Night Owl metadata)
        curses.init_color(145, 396, 476, 476)    # #637777 (Night Owl instructions)
        curses.init_color(146, 1000, 352, 464)   # #ff5874 (Night Owl favorite)
        curses.init_color(147, 120, 116, 172)    # #1e1d2b (Catppuccin bg)
        curses.init_color(148, 720, 760, 1000)   # #b4befe (Catppuccin header)
        curses.init_color(149, 980, 896, 880)    # #f5e0dc (Catppuccin selected)
        curses.init_color(150, 664, 908, 644)    # #a6e3a1 (Catppuccin info)
        curses.init_color(151, 464, 796, 944)    # #74c7ec (Catppuccin metadata)
        curses.init_color(152, 588, 612, 712)    # #9399b2 (Catppuccin instructions)
        curses.init_color(153, 972, 556, 672)    # #f38ba8 (Catppuccin favorite)
        curses.init_color(154, 0, 136, 256)      # #002240 (Cobalt bg)
        curses.init_color(155, 1000, 1000, 1000) # #ffffff (Cobalt header)
        curses.init_color(156, 920, 960, 1000)   # #e6f0ff (Cobalt selected)
        curses.init_color(157, 676, 828, 1000)   # #a9cfff (Cobalt info)
        curses.init_color(158, 576, 768, 960)    # #90c0f0 (Cobalt metadata)
        curses.init_color(159, 512, 640, 832)    # #80a0d0 (Cobalt instructions)
        curses.init_color(160, 1000, 400, 512)   # #ff6480 (Cobalt favorite)
        curses.init_color(161, 252, 252, 252)    # #3f3f3f (Zenburn bg)
        curses.init_color(162, 880, 880, 816)    # #dcdccc (Zenburn header)
        curses.init_color(163, 960, 892, 700)    # #f0dfaf (Zenburn selected)
        curses.init_color(164, 816, 1000, 700)   # #ccffaf (Zenburn info)
        curses.init_color(165, 508, 636, 508)    # #7f9f7f (Zenburn metadata)
        curses.init_color(166, 832, 832, 640)    # #d0d0a0 (Zenburn instructions)
        curses.init_color(167, 880, 652, 652)    # #dca3a3 (Zenburn favorite)
        curses.init_color(168, 128, 156, 208)    # #202734 (Ayu Mirage bg)
        curses.init_color(169, 968, 540, 484)    # #f28779 (Ayu Mirage header)
        curses.init_color(170, 1000, 816, 408)   # #ffcc66 (Ayu Mirage selected)
        curses.init_color(171, 744, 920, 504)    # #bae67e (Ayu Mirage info)
        curses.init_color(172, 460, 832, 1000)   # #73d0ff (Ayu Mirage metadata)
        curses.init_color(173, 796, 584, 936)    # #c792ea (Ayu Mirage instructions)
        curses.init_color(174, 1000, 860, 0)     # #ffd700 (Ayu Mirage favorite)

        # Get theme from config
        theme_name = self.config.get('theme', 'default')
        themes = self._get_color_themes()

        if theme_name not in themes:
            theme_name = 'default'

        theme = themes[theme_name]
        bg_color = theme['bg_color']

        # For dark themes with black background, try to create a darker background if possible
        # In alternative background mode, keep pure black background
        if bg_color == curses.COLOR_BLACK and curses.can_change_color() and not self.alternative_bg_mode:
            curses.init_color(132, 80, 80, 80)  # Very dark gray
            bg_color = 132

        # Initialize color pairs based on theme
        curses.init_pair(1, theme['header'], bg_color)      # Header
        curses.init_pair(2, theme['selected'], bg_color)    # Selected channel
        curses.init_pair(3, theme['info'], bg_color)        # Channel info
        curses.init_pair(4, theme['metadata'], bg_color)    # Track metadata
        curses.init_pair(5, theme['instructions'], bg_color) # Instructions
        curses.init_pair(6, theme['favorite'], bg_color)    # Favorite icon

        # Volume gradient colors
        curses.init_pair(50, 21, bg_color)   # Volume 0% - dark blue
        curses.init_pair(51, 27, bg_color)   # Volume 25% - medium blue
        curses.init_pair(52, 69, bg_color)   # Volume 50% - light blue
        curses.init_pair(53, 79, bg_color)   # Volume 75% - cyan
        curses.init_pair(54, 88, bg_color)   # Volume 100% - red
        curses.init_pair(55, 214, bg_color)  # Volume icon - yellow

        # Volume indicator colors (separate from themes)
        curses.init_color(175, 1000, 600, 0)   # Orange for volume bar
        curses.init_color(176, 980, 820, 0)    # Yellow for speaker icon
        curses.init_pair(60, 175, bg_color)    # Volume bar - orange
        curses.init_pair(61, 176, bg_color)    # Speaker icon - yellow

        # Special handling for monochrome themes to ensure selected text is visible
        if theme_name == 'monochrome' or theme_name == 'monochrome-dark':
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
            "# volume: Default volume (0-100)": "",
            "volume": 100,
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
                        if key in ['buffer_minutes', 'buffer_size_mb', 'volume']:
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
            # Load usage
            if os.path.exists(CHANNEL_USAGE_FILE):
                with open(CHANNEL_USAGE_FILE, 'r') as f:
                    usage = json.load(f)
            else:
                usage = {}
            # Clean up usage from non-existent channels
            valid_ids = {c['id'] for c in channels}
            usage = {k: v for k, v in usage.items() if k in valid_ids}
            # Sort channels
            def sort_key(ch):
                last = usage.get(ch['id'])
                return -(last if last else 0)
            channels.sort(key=sort_key, reverse=False)
            # Save cleaned usage
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

    def _set_volume(self, volume: int):
        """Set volume (0-100)"""
        self.volume = max(0, min(100, volume))
        # Update config and save
        self.config['volume'] = self.volume
        self._save_config()
        if self.player:
            self.player.volume = self.volume

    def _increase_volume(self, step: int = 5):
        """Increase volume by step"""
        self._set_volume(self.volume + step)
        self.combined_screen.show_volume(self.stdscr, self.volume)

    def _decrease_volume(self, step: int = 5):
        """Decrease volume by step"""
        self._set_volume(self.volume - step)
        self.combined_screen.show_volume(self.stdscr, self.volume)

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
                stdscr.nodelay(True)

                # Initial display of the interface
                self._display_combined_interface(stdscr)

                # Main loop
                last_input_time = time.time()

                while self.running:
                    # Check if we need to refresh the screen due to volume indicator timeout
                    needs_refresh = False

                    # Check if volume indicator should be hidden
                    if (self.combined_screen.volume_display is not None and
                        time.time() - self.combined_screen.volume_display_time >= 3):
                        # Update the volume display state to hide it
                        self.combined_screen.volume_display = None
                        needs_refresh = True

                    # Only redraw if needed
                    if needs_refresh:
                        self._display_combined_interface(stdscr)

                    # Get user input
                    try:
                        key = stdscr.get_wch()
                        if key is not None:
                            last_input_time = time.time()
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
                                elif key == curses.KEY_PPAGE:  # PAGE_UP (inverted in terminal)
                                    if self.is_playing:
                                        self._increase_volume()
                                        last_input_time = time.time()  # Update last input time when changing volume
                                elif key == curses.KEY_NPAGE:  # PAGE_DOWN (inverted in terminal)
                                    if self.is_playing:
                                        self._decrease_volume()
                                        last_input_time = time.time()  # Update last input time when changing volume
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
                                    elif key in ['q', 'Q', chr(27)]:
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
                                    elif key in ['v', 'V']:  # Volume controls
                                        if self.is_playing:
                                            self._decrease_volume()
                                            last_input_time = time.time()  # Update last input time when changing volume
                                    elif key in ['b', 'B']:
                                        if self.is_playing:
                                            self._increase_volume()
                                            last_input_time = time.time()  # Update last input time when changing volume
                                else:  # Handle special keys
                                    if key == curses.KEY_UP:
                                        self.current_index = max(0, self.current_index - 1)
                                    elif key == curses.KEY_DOWN:
                                        self.current_index = min(len(self.channels) - 1, self.current_index + 1)
                                    elif key == curses.KEY_ENTER:
                                        self._play_channel(self.channels[self.current_index])
                                    elif key == curses.KEY_PPAGE:  # PAGE_UP (inverted in terminal)
                                        if self.is_playing:
                                            self._increase_volume()
                                            last_input_time = time.time()  # Update last input time when changing volume
                                    elif key == curses.KEY_NPAGE:  # PAGE_DOWN (inverted in terminal)
                                        if self.is_playing:
                                            self._decrease_volume()
                                            last_input_time = time.time()  # Update last input time when changing volume

                            # Redraw after handling input
                            self._display_combined_interface(stdscr)
                        else:
                            # No key pressed, check if we need to refresh due to timeout
                            # Only sleep briefly to check again soon
                            time.sleep(0.1)  # Sleep briefly before checking again
                    except curses.error:
                        # Handle case where no input is available
                        time.sleep(0.1)  # Sleep briefly before checking again
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
