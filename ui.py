"""User interface module"""

import curses
import os
import time
from typing import Any, Dict, List, Optional, Set

from .models import TrackMetadata, Channel


# Check if terminal supports emoji - not used anymore, kept for compatibility
def _supports_emoji() -> bool:
    """Check if terminal supports Unicode emoji (kept for compatibility)"""
    return False  # Always use ASCII for reliability


# Icon functions - listeners/bitrate use ASCII, others use Unicode
def get_listener_icon() -> str:
    """Get listener icon"""
    return "[L]"


def get_bitrate_icon() -> str:
    """Get bitrate icon"""
    return "[B]"


def get_volume_icon() -> str:
    """Get volume icon"""
    return "🔊"


def get_play_symbol(is_paused: bool = False) -> str:
    """Get play/pause symbol"""
    return "⏸" if is_paused else "▶"


def get_music_symbol() -> str:
    """Get music note symbol"""
    return "♪"


def get_favorite_icon() -> str:
    """Get favorite icon"""
    return "♥"


class UIScreen:
    """Base UI screen class"""

    def __init__(self):
        self.current_metadata = TrackMetadata()
        self.max_history = 10
        self.track_history: List[TrackMetadata] = []
        self.current_channel: Optional[Channel] = None
        self.player: Any = None
        self.volume_display: Optional[int] = None
        self.volume_display_time: float = 0
        self.volume_display_was_visible: bool = False

    def display(
        self,
        stdscr: curses.window,
        channels: List[Channel],
        selected_index: int,
        scroll_offset: int,
        channel_favorites: Set[str],
        current_channel: Optional[Channel] = None,
        player: Any = None,
        is_playing: bool = False,
        is_searching: bool = False,
        search_query: str = "",
        theme_name: str = "default",
        show_help: bool = False,
    ) -> None:
        """Display combined interface"""
        max_y, max_x = stdscr.getmaxyx()

        # Show help overlay if enabled
        if show_help:
            self._display_help(stdscr, max_y, max_x)
            stdscr.refresh()
            return

        # Adaptive width for channels panel (25-40 chars, max 1/3 of screen)
        split_x = min(max(25, max_x // 3), 40)

        # Clear screen and fill background
        stdscr.clear()
        stdscr.bkgd(" ", curses.color_pair(1))

        # Fill entire screen to avoid gaps
        for y in range(max_y):
            try:
                stdscr.addstr(y, 0, " " * max_x, curses.color_pair(1))
            except curses.error:
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

        # Calculate panel height
        panel_height = max_y - 2

        # Left panel: Channel list
        self._display_channels_panel(
            stdscr,
            channels,
            selected_index,
            scroll_offset,
            channel_favorites,
            0,
            0,
            split_x,
            panel_height,
            is_searching,
            search_query,
        )

        # Right panel: Playback info
        self._display_playback_panel(
            stdscr,
            split_x + 1,
            0,
            max_x - split_x - 1,
            panel_height,
            current_channel,
            player,
            is_playing,
        )

        # Display instructions at bottom
        self._display_instructions(stdscr, max_y, max_x)

        # Display volume indicator
        self._handle_volume_display(stdscr)

        stdscr.refresh()

    def _display_channels_panel(
        self,
        stdscr: curses.window,
        channels: List[Channel],
        selected_index: int,
        scroll_offset: int,
        channel_favorites: Set[str],
        start_x: int,
        start_y: int,
        width: int,
        height: int,
        is_searching: bool = False,
        search_query: str = "",
    ) -> None:
        """Display channels panel"""
        # Header
        try:
            header = f"Channels ({len(channels)})"
            if len(header) > width - 2:
                header = header[: width - 5] + "..."
            stdscr.addstr(start_y, start_x, header, curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            pass

        # Visible channels
        visible_channels = height - 3

        # Display channels
        for i, channel in enumerate(channels[scroll_offset : scroll_offset + visible_channels]):
            display_y = start_y + 1 + i
            if display_y >= height - 1:
                break

            # Prepare channel title
            fav_icon = f"{get_favorite_icon()} " if channel.id in channel_favorites else "  "
            title = channel.title
            max_title_len = width - 6
            if len(title) > max_title_len:
                title = title[: max_title_len - 3] + "..."
            display_title = f"{fav_icon}{title}"

            try:
                if i + scroll_offset == selected_index:
                    stdscr.addstr(
                        display_y, start_x, f"> {display_title}"[: width - 1], curses.color_pair(2) | curses.A_REVERSE
                    )
                else:
                    stdscr.addstr(display_y, start_x, f"  {display_title}"[: width - 1], curses.color_pair(1))
            except curses.error:
                continue

        # Search prompt
        if is_searching:
            prompt = f"Search: {search_query}"
            prompt_y = start_y + height - 2
            try:
                stdscr.addstr(prompt_y, start_x, " " * (width - 1), curses.color_pair(1))
                stdscr.addstr(prompt_y, start_x, prompt[: width - 1], curses.color_pair(2) | curses.A_BOLD)
                curses.curs_set(1)
                stdscr.move(prompt_y, start_x + len(prompt))
            except curses.error:
                curses.curs_set(0)
        else:
            curses.curs_set(0)

    def _display_playback_panel(
        self,
        stdscr: curses.window,
        start_x: int,
        start_y: int,
        width: int,
        height: int,
        current_channel: Optional[Channel],
        player: Any,
        is_playing: bool,
    ) -> None:
        """Display playback panel"""
        max_y, max_x = stdscr.getmaxyx()
        available_width = min(width, max_x - start_x)

        if not current_channel or not is_playing:
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
                channel_title = f"{get_music_symbol()} {current_channel.title}"
                if len(channel_title) > available_width:
                    channel_title = channel_title[: available_width - 3] + "..."
                if len(channel_title) <= available_width:
                    stdscr.addstr(start_y, start_x, channel_title, curses.color_pair(1) | curses.A_BOLD)
            except curses.error:
                pass

        # Channel description
        if available_width > 0 and start_y + 1 < max_y:
            try:
                description = current_channel.description or "No description"
                if len(description) > available_width:
                    description = description[: available_width - 3] + "..."
                if len(description) <= available_width:
                    stdscr.addstr(start_y + 1, start_x, description, curses.color_pair(3))
            except curses.error:
                pass

        # Channel stats (listeners and bitrate)
        if available_width > 0 and start_y + 2 < max_y:
            try:
                stats_parts = []
                if current_channel.listeners > 0:
                    stats_parts.append(f"{get_listener_icon()} {current_channel.listeners}")
                if current_channel.bitrate:
                    stats_parts.append(f"{get_bitrate_icon()} {current_channel.bitrate}")
                if stats_parts:
                    stats = " | ".join(stats_parts)
                    if len(stats) > available_width:
                        stats = stats[: available_width - 3] + "..."
                    stdscr.addstr(start_y + 2, start_x, stats, curses.color_pair(5) | curses.A_DIM)
            except curses.error:
                pass

        # Current track
        if available_width > 0 and start_y + 4 < max_y:
            try:
                is_paused = player and player.pause
                play_symbol = get_play_symbol(is_paused)
                current_track = f"{play_symbol} {self.current_metadata.artist} - {self.current_metadata.title}"
                if len(current_track) > available_width:
                    current_track = current_track[: available_width - 3] + "..."
                if len(current_track) <= available_width:
                    stdscr.addstr(start_y + 3, start_x, current_track, curses.color_pair(4) | curses.A_BOLD)
            except curses.error:
                pass

        # Track history
        y = start_y + 6
        for track in self.track_history:
            if y >= height - 2 or y >= max_y:
                break
            if available_width > 0:
                try:
                    timestamp = f"[{track.timestamp}] " if track.timestamp else "  "
                    track_info = f"  {timestamp}{track.artist} - {track.title}"
                    if len(track_info) > available_width:
                        track_info = track_info[: available_width - 3] + "..."
                    if len(track_info) <= available_width:
                        stdscr.addstr(y, start_x, track_info, curses.color_pair(4))
                    y += 1
                except curses.error:
                    continue

    def _display_instructions(self, stdscr: curses.window, max_y: int, max_x: int) -> None:
        """Display instructions at bottom of screen"""
        try:
            instruction_items = [
                "↑↓/jk - select",
                "Enter/l - play",
                "/ - search",
                "Space - pause",
                "h - stop",
                "f - favorite",
                "t - theme",
                "PgUp/Dn - volume",
                "q - quit",
            ]

            available_width = max_x - 1
            available_lines = 2

            lines = []
            current_line = ""

            for item in instruction_items:
                separator = " | " if current_line else ""
                test_line = current_line + separator + item

                if len(test_line) <= available_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                        current_line = item
                    else:
                        current_line = item[: available_width - 3] + "..." if available_width > 3 else item[: available_width]

                    if len(lines) >= available_lines:
                        break

            if current_line and len(lines) < available_lines:
                lines.append(current_line)

            for i, line in enumerate(lines):
                if i >= available_lines:
                    break
                y_pos = max_y - available_lines + i
                padded_line = line.ljust(available_width)
                stdscr.addstr(y_pos, 0, padded_line, curses.color_pair(5) | curses.A_DIM)

        except curses.error:
            pass

    def _handle_volume_display(self, stdscr: curses.window) -> None:
        """Handle volume indicator display"""
        # Always draw volume indicator if it was recently updated
        if self.volume_display is not None:
            elapsed = time.time() - self.volume_display_time
            if elapsed < 3:
                # Draw directly
                self._draw_volume_indicator(stdscr)
            else:
                # Time expired, clear and reset
                self.volume_display = None
                self.volume_display_time = 0

    def _draw_volume_indicator(self, stdscr: curses.window) -> None:
        """Draw volume indicator"""
        max_y, max_x = stdscr.getmaxyx()
        bar_width = 20
        start_y = 1
        start_x = max_x - bar_width - 5

        volume = self.volume_display
        vol_bar_color = 60
        vol_icon_color = 61

        # Draw speaker icon
        vol_icon = get_volume_icon()
        stdscr.addstr(start_y, start_x - len(vol_icon), vol_icon, curses.color_pair(vol_icon_color) | curses.A_BOLD)

        # Draw filled blocks
        filled_blocks = int((volume / 100) * bar_width)
        empty_blocks = bar_width - filled_blocks

        if filled_blocks > 0:
            filled_bar = "█" * filled_blocks
            stdscr.addstr(start_y, start_x, filled_bar, curses.color_pair(vol_bar_color) | curses.A_BOLD)

        if empty_blocks > 0:
            empty_bar = "▁" * empty_blocks
            stdscr.addstr(start_y, start_x + filled_blocks, empty_bar, curses.color_pair(vol_bar_color) | curses.A_DIM)

        # Draw percentage
        vol_text = f"{volume:3d}%"
        stdscr.addstr(start_y, start_x + bar_width, vol_text, curses.color_pair(vol_icon_color) | curses.A_BOLD)

    def add_to_history(self, metadata: TrackMetadata) -> None:
        """Add track to history"""
        metadata.timestamp = time.strftime("%H:%M:%S")
        self.track_history.insert(0, metadata)
        if len(self.track_history) > self.max_history:
            self.track_history.pop()

    def update_metadata(self, metadata: TrackMetadata) -> None:
        """Update current track metadata"""
        if metadata.artist != self.current_metadata.artist or metadata.title != self.current_metadata.title:
            self.add_to_history(self.current_metadata)
            self.current_metadata = metadata

    def show_volume(self, stdscr: curses.window, volume: int) -> None:
        """Show volume indicator"""
        self.volume_display = volume
        self.volume_display_time = time.time()

    def show_notification(self, stdscr: curses.window, message: str, timeout: float = 1.5) -> None:
        """Show notification"""
        max_y, max_x = stdscr.getmaxyx()
        win_width = min(len(message) + 4, max_x)
        win_height = 3
        start_y = max_y // 2 - win_height // 2
        start_x = max_x // 2 - win_width // 2

        try:
            notif_win = curses.newwin(win_height, win_width, start_y, start_x)
            notif_win.bkgd(" ", curses.color_pair(3) | curses.A_BOLD)
            notif_win.box()
            notif_win.addstr(1, 2, message[: win_width - 4])
            notif_win.refresh()
            curses.napms(int(timeout * 1000))
            notif_win.clear()
            notif_win.refresh()
        except curses.error:
            pass

    def _display_volume(self, stdscr: curses.window) -> None:
        """Display volume level"""
        max_y, max_x = stdscr.getmaxyx()
        bar_width = 20
        start_y = 1
        start_x = max_x - bar_width - 5

        volume = self.volume_display
        vol_bar_color = 60
        vol_icon_color = 61

        # Draw filled blocks
        filled_blocks = int((volume / 100) * bar_width)
        empty_blocks = bar_width - filled_blocks

        if filled_blocks > 0:
            filled_bar = "█" * filled_blocks
            stdscr.addstr(start_y, start_x, filled_bar, curses.color_pair(vol_bar_color) | curses.A_BOLD)

        if empty_blocks > 0:
            empty_bar = "▁" * empty_blocks
            stdscr.addstr(start_y, start_x + filled_blocks, empty_bar, curses.color_pair(vol_bar_color) | curses.A_DIM)

        # Draw speaker icon
        vol_icon = get_volume_icon()
        icon_x = start_x - len(vol_icon)
        stdscr.addstr(start_y, icon_x, vol_icon, curses.color_pair(vol_icon_color) | curses.A_BOLD)

        # Draw percentage
        vol_text = f"{volume:3d}%"
        text_x = start_x + bar_width
        stdscr.addstr(start_y, text_x, vol_text, curses.color_pair(vol_icon_color) | curses.A_BOLD)

    def _clear_volume(self, stdscr: curses.window) -> None:
        """Clear volume indicator"""
        max_y, max_x = stdscr.getmaxyx()
        bar_width = 20
        start_y = 1
        start_x = max_x - bar_width - 5

        try:
            width = bar_width + 10
            clear_line = " " * width
            stdscr.addstr(start_y, start_x - 5, clear_line, curses.color_pair(1))
        except curses.error:
            pass

    def _display_help(self, stdscr: curses.window, max_y: int, max_x: int) -> None:
        """Display help screen"""
        help_text = [
            ("SomaFM TUI - Keyboard Shortcuts", "header"),
            ("", ""),
            ("Navigation", "section"),
            ("  ↑/k  - Move up", "normal"),
            ("  ↓/j  - Move down", "normal"),
            ("  Enter/l - Play selected channel", "normal"),
            ("", ""),
            ("Playback", "section"),
            ("  Space - Pause/Resume", "normal"),
            ("  h     - Stop playback", "normal"),
            ("  v/b   - Decrease/Increase volume", "normal"),
            ("  PgUp  - Increase volume", "normal"),
            ("  PgDn  - Decrease volume", "normal"),
            ("", ""),
            ("Channels", "section"),
            ("  /     - Search channels", "normal"),
            ("  f     - Toggle favorite", "normal"),
            ("", ""),
            ("Appearance", "section"),
            ("  t     - Cycle theme", "normal"),
            ("", ""),
            ("Other", "section"),
            ("  ?     - Toggle this help", "normal"),
            ("  q     - Quit", "normal"),
            ("  ESC   - Close search/help", "normal"),
        ]

        # Calculate box size
        box_height = len(help_text) + 2
        box_width = min(50, max_x - 10)  # Limit width to 50 chars
        box_y = (max_y - box_height) // 2
        box_x = (max_x - box_width) // 2  # Center horizontally

        try:
            # Create a subwindow for the help box
            help_win = curses.newwin(box_height, box_width, box_y, box_x)

            # Draw box border on the subwindow
            help_win.attron(curses.color_pair(3) | curses.A_BOLD)
            help_win.border(0)
            help_win.attroff(curses.color_pair(3) | curses.A_BOLD)

            # Draw help content
            for i, (text, style) in enumerate(help_text):
                y = 1 + i

                if style == "header":
                    attr = curses.color_pair(1) | curses.A_BOLD
                elif style == "section":
                    attr = curses.color_pair(2) | curses.A_BOLD
                else:
                    attr = curses.color_pair(1)

                help_win.addstr(y, 2, text.ljust(box_width - 4)[:box_width - 4], attr)

            # Draw footer
            footer = "Press ? or ESC to close"
            help_win.addstr(box_height - 2, 2, footer.ljust(box_width - 4), curses.color_pair(5) | curses.A_DIM)

            help_win.refresh()

        except curses.error:
            pass
