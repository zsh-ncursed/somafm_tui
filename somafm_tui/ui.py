"""User interface module"""

import curses
import os
import time
from typing import Any, Dict, List, Optional, Set

from .models import TrackMetadata, Channel
from .constants import (
    VOLUME_BAR_COLOR_PAIR,
    VOLUME_ICON_COLOR_PAIR,
    MAX_TRACK_HISTORY_ENTRIES,
    CHANNEL_PANEL_MIN_WIDTH,
    CHANNEL_PANEL_MAX_WIDTH,
    INSTRUCTION_LINES,
    VOLUME_DISPLAY_TIMEOUT,
    HELP_OVERLAY_WIDTH,
)

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
    """Base UI screen class with smart redraw optimization."""

    def __init__(self):
        self.current_metadata = TrackMetadata()
        self.max_history = MAX_TRACK_HISTORY_ENTRIES
        self.track_history: List[TrackMetadata] = []
        self.current_channel: Optional[Channel] = None
        self.player: Any = None
        self.volume_display: Optional[int] = None
        self.volume_display_time: float = 0
        self.volume_display_was_visible: bool = False
        
        # Smart redraw optimization - cache previous state
        self._prev_channels_hash: int = 0
        self._prev_selected_index: int = -1
        self._prev_scroll_offset: int = -1
        self._prev_favorites_hash: int = 0
        self._prev_current_channel_id: Optional[str] = None
        self._prev_is_playing: bool = False
        self._prev_metadata_hash: int = 0
        self._prev_search_query: str = ""
        self._prev_show_help: bool = False
        self._prev_bitrate: str = ""
        # No forced full redraw interval - partial redraw with clrtoeol() is sufficient

    def invalidate_cache(self) -> None:
        """Invalidate redraw cache to force full redraw.

        Call this when theme changes or screen is cleared.
        """
        self._prev_channels_hash = 0
        self._prev_selected_index = -1
        self._prev_scroll_offset = -1
        self._prev_favorites_hash = 0
        self._prev_current_channel_id = None
        self._prev_is_playing = False
        self._prev_metadata_hash = 0
        self._prev_search_query = ""
        self._prev_show_help = False
        self._prev_bitrate = ""

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
        current_bitrate: str = "",
        show_footer: bool = True,
    ) -> None:
        """Display combined interface with smart redraw optimization.

        Only redraws changed portions of the screen to improve performance.
        Full redraw is performed when:
        - Help overlay is shown
        - Search mode changes
        - Channels list changes
        - Cache is invalidated (resize, theme change)
        """
        import hashlib
        import time

        # Store current theme name for use in _display_instructions
        self._current_theme_name = theme_name

        max_y, max_x = stdscr.getmaxyx()
        current_time = time.time()

        # Show help overlay if enabled (always full redraw)
        if show_help:
            self._display_help(stdscr, max_y, max_x)
            stdscr.refresh()
            return

        # Calculate hashes for change detection
        channels_str = "|".join(f"{ch.id}:{ch.title}" for ch in channels)
        channels_hash = hash(channels_str)
        favorites_hash = hash(frozenset(channel_favorites))
        metadata_hash = hash(f"{self.current_metadata.artist}:{self.current_metadata.title}")
        
        # Detect what changed
        channels_changed = channels_hash != self._prev_channels_hash
        selection_changed = selected_index != self._prev_selected_index
        scroll_changed = scroll_offset != self._prev_scroll_offset
        favorites_changed = favorites_hash != self._prev_favorites_hash
        playback_changed = (
            current_channel != self._prev_current_channel_id or
            is_playing != self._prev_is_playing or
            current_bitrate != self._prev_bitrate
        )
        metadata_changed = metadata_hash != self._prev_metadata_hash
        search_changed = search_query != self._prev_search_query
        help_changed = show_help != self._prev_show_help
        
        # Cache was invalidated (e.g., after resize or theme change) - force full redraw
        cache_invalidated = self._prev_channels_hash == 0

        # Determine if we need full redraw
        needs_full_redraw = cache_invalidated or channels_changed or search_changed or help_changed
        
        # Adaptive width for channels panel (25-40 chars, max 1/3 of screen)
        split_x = min(max(25, max_x // 3), 40)
        panel_height = max_y - 2

        if needs_full_redraw:
            # Full redraw - clear and redraw everything
            self._full_redraw(
                stdscr, channels, selected_index, scroll_offset, channel_favorites,
                current_channel, player, is_playing, current_bitrate,
                split_x, panel_height, max_y, max_x, is_searching, search_query,
                show_footer
            )
        else:
            # Partial redraw - only update changed elements
            self._partial_redraw(
                stdscr, channels, selected_index, scroll_offset, channel_favorites,
                current_channel, player, is_playing, current_bitrate,
                split_x, panel_height, max_y, max_x, is_searching, search_query,
                show_footer,
                selection_changed, scroll_changed, favorites_changed,
                playback_changed, metadata_changed
            )

        # Display volume indicator (always)
        self._handle_volume_display(stdscr)

        # Show sleep timer countdown if active (always update)
        stdscr.refresh()

        # Update cache
        self._prev_channels_hash = channels_hash
        self._prev_selected_index = selected_index
        self._prev_scroll_offset = scroll_offset
        self._prev_favorites_hash = favorites_hash
        self._prev_current_channel_id = current_channel.id if current_channel else None
        self._prev_is_playing = is_playing
        self._prev_metadata_hash = metadata_hash
        self._prev_search_query = search_query
        self._prev_show_help = show_help
        self._prev_bitrate = current_bitrate

    def _full_redraw(
        self, stdscr: curses.window, channels: List[Channel],
        selected_index: int, scroll_offset: int, channel_favorites: Set[str],
        current_channel: Optional[Channel], player: Any, is_playing: bool,
        current_bitrate: str, split_x: int, panel_height: int,
        max_y: int, max_x: int, is_searching: bool, search_query: str,
        show_footer: bool = True
    ) -> None:
        """Perform full screen redraw."""
        # Clear screen and set background
        stdscr.clear()
        stdscr.bkgd(" ", curses.color_pair(1))

        # Left panel: Channel list
        self._display_channels_panel(
            stdscr, channels, selected_index, scroll_offset, channel_favorites,
            0, 0, split_x, panel_height, is_searching, search_query,
        )

        # Right panel: Playback info
        self._display_playback_panel(
            stdscr, split_x + 1, 0, max_x - split_x - 1, panel_height,
            current_channel, player, is_playing, current_bitrate,
        )

        # Display instructions at bottom
        if show_footer:
            self._display_instructions(stdscr, max_y, max_x)

    def _partial_redraw(
        self, stdscr: curses.window, channels: List[Channel],
        selected_index: int, scroll_offset: int, channel_favorites: Set[str],
        current_channel: Optional[Channel], player: Any, is_playing: bool,
        current_bitrate: str, split_x: int, panel_height: int,
        max_y: int, max_x: int, is_searching: bool, search_query: str,
        show_footer: bool = True,
        selection_changed: bool = False, scroll_changed: bool = False,
        favorites_changed: bool = False, playback_changed: bool = False,
        metadata_changed: bool = False
    ) -> None:
        """Perform partial redraw - only update changed elements.

        Note: This does NOT update background color. For theme changes,
        use _full_redraw() instead.
        """
        # Redraw channel list if selection, scroll, or favorites changed
        if selection_changed or scroll_changed or favorites_changed:
            self._redraw_channel_list(
                stdscr, channels, selected_index, scroll_offset, channel_favorites,
                split_x, panel_height,
            )

        # Redraw playback info if playback state or metadata changed
        if playback_changed or metadata_changed:
            self._redraw_playback_info(
                stdscr, split_x + 1, 0, max_x - split_x - 1, panel_height,
                current_channel, player, is_playing, current_bitrate,
            )

        # Redraw search prompt if searching
        if is_searching:
            self._redraw_search_prompt(stdscr, search_query, split_x, panel_height)

        # Redraw instructions if footer is shown
        if show_footer:
            self._redraw_instructions(stdscr, max_y, max_x)

        # Refresh screen to show changes
        stdscr.refresh()

    def _redraw_channel_list(
        self, stdscr: curses.window, channels: List[Channel],
        selected_index: int, scroll_offset: int, channel_favorites: Set[str],
        split_x: int, panel_height: int
    ) -> None:
        """Redraw only the channel list portion."""
        max_y, max_x = stdscr.getmaxyx()
        visible_channels = panel_height - 3
        start_y = 0  # Channel list always starts at y=0

        for i, channel in enumerate(channels[scroll_offset:scroll_offset + visible_channels]):
            display_y = start_y + 1 + i
            if display_y >= panel_height - 1 or display_y >= max_y:
                break

            # Prepare channel title
            fav_icon = f"{get_favorite_icon()} " if channel.id in channel_favorites else "  "
            title = channel.title
            max_title_len = split_x - 6
            if len(title) > max_title_len:
                title = title[:max_title_len - 3] + "..."
            display_title = f"{fav_icon}{title}"

            try:
                # Clear line using clrtoeol to prevent text remnants on resize
                stdscr.move(display_y, 0)
                stdscr.clrtoeol()

                if i + scroll_offset == selected_index:
                    stdscr.addstr(display_y, 0, f"> {display_title}"[:split_x - 1],
                        curses.color_pair(2) | curses.A_REVERSE
                    )
                else:
                    stdscr.addstr(display_y, 0, f"  {display_title}"[:split_x - 1], curses.color_pair(1))
            except curses.error:
                continue

    def _redraw_playback_info(
        self, stdscr: curses.window, start_x: int, start_y: int,
        width: int, height: int, current_channel: Optional[Channel],
        player: Any, is_playing: bool, current_bitrate: str = ""
    ) -> None:
        """Redraw only the playback info portion."""
        max_y, max_x = stdscr.getmaxyx()
        
        # Clear playback area using clrtoeol for each line (efficient and prevents artifacts)
        for y in range(start_y, min(start_y + 10, max_y)):
            try:
                stdscr.move(y, start_x)
                stdscr.clrtoeol()
            except curses.error:
                pass

        # Redraw playback info
        self._display_playback_panel(
            stdscr, start_x, start_y, width, height,
            current_channel, player, is_playing, current_bitrate,
        )

    def _redraw_search_prompt(
        self, stdscr: curses.window, search_query: str,
        split_x: int, panel_height: int
    ) -> None:
        """Redraw search prompt."""
        prompt = f"Search: {search_query}"
        prompt_y = panel_height - 2
        try:
            stdscr.move(prompt_y, 0)
            stdscr.clrtoeol()
            stdscr.addstr(prompt_y, 0, prompt[:split_x - 1], curses.color_pair(2) | curses.A_BOLD)
            curses.curs_set(1)
            stdscr.move(prompt_y, len(prompt))
        except curses.error:
            curses.curs_set(0)

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
            # Clear header line first using clrtoeol
            stdscr.move(start_y, start_x)
            stdscr.clrtoeol()
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
                # Clear line first using clrtoeol to prevent text remnants
                stdscr.move(display_y, start_x)
                stdscr.clrtoeol()

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
                stdscr.move(prompt_y, start_x)
                stdscr.clrtoeol()
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
        current_bitrate: str = "",
    ) -> None:
        """Display playback panel"""
        max_y, max_x = stdscr.getmaxyx()
        available_width = min(width, max_x - start_x)

        if not current_channel or not is_playing:
            if available_width > 0:
                try:
                    # Clear line using clrtoeol
                    stdscr.move(start_y, start_x)
                    stdscr.clrtoeol()
                    text = "No channel playing"
                    if len(text) <= available_width:
                        stdscr.addstr(start_y, start_x, text, curses.color_pair(3))

                    if start_y + 2 < max_y:
                        stdscr.move(start_y + 2, start_x)
                        stdscr.clrtoeol()
                        text2 = "Select a channel and press Enter to start"
                        if len(text2) <= available_width:
                            # Use same color as instructions (pair 5) without A_DIM for better visibility
                            stdscr.addstr(start_y + 2, start_x, text2, curses.color_pair(5))
                except curses.error:
                    pass
            return

        # Channel info - clear line first
        if available_width > 0:
            try:
                stdscr.move(start_y, start_x)
                stdscr.clrtoeol()
                channel_title = f"{get_music_symbol()} {current_channel.title}"
                if len(channel_title) > available_width:
                    channel_title = channel_title[: available_width - 3] + "..."
                if len(channel_title) <= available_width:
                    stdscr.addstr(start_y, start_x, channel_title, curses.color_pair(1) | curses.A_BOLD)
            except curses.error:
                pass

        # Channel description - clear line first
        if available_width > 0 and start_y + 1 < max_y:
            try:
                stdscr.move(start_y + 1, start_x)
                stdscr.clrtoeol()
                description = current_channel.description or "No description"
                if len(description) > available_width:
                    description = description[: available_width - 3] + "..."
                if len(description) <= available_width:
                    stdscr.addstr(start_y + 1, start_x, description, curses.color_pair(3))
            except curses.error:
                pass

        # Channel stats (listeners and bitrate) - clear line first
        if available_width > 0 and start_y + 2 < max_y:
            try:
                stdscr.move(start_y + 2, start_x)
                stdscr.clrtoeol()
                stats_parts = []
                if current_channel.listeners > 0:
                    stats_parts.append(f"{get_listener_icon()} {current_channel.listeners}")
                # Use current_bitrate if set, otherwise channel default
                # Extract bitrate label from format like 'mp3:128k' -> '128k'
                display_bitrate = current_bitrate if current_bitrate else current_channel.bitrate
                if display_bitrate:
                    if ":" in display_bitrate:
                        bitrate_label = display_bitrate.split(":")[1]
                    else:
                        bitrate_label = display_bitrate
                    stats_parts.append(f"{get_bitrate_icon()} {bitrate_label}")
                if stats_parts:
                    stats = " | ".join(stats_parts)
                    if len(stats) > available_width:
                        stats = stats[: available_width - 3] + "..."
                    # Use same style as instructions for consistency
                    stdscr.addstr(start_y + 2, start_x, stats, curses.color_pair(3))
            except curses.error:
                pass

        # Current track - clear line first
        if available_width > 0 and start_y + 4 < max_y:
            try:
                stdscr.move(start_y + 3, start_x)
                stdscr.clrtoeol()
                is_paused = player and player.pause
                play_symbol = get_play_symbol(is_paused)
                current_track = f"{play_symbol} {self.current_metadata.artist} - {self.current_metadata.title}"
                if len(current_track) > available_width:
                    current_track = current_track[: available_width - 3] + "..."
                if len(current_track) <= available_width:
                    stdscr.addstr(start_y + 3, start_x, current_track, curses.color_pair(4) | curses.A_BOLD)
            except curses.error:
                pass

        # Track history - clear lines first
        y = start_y + 6
        for track in self.track_history:
            if y >= height - 2 or y >= max_y:
                break
            if available_width > 0:
                try:
                    # Clear line using clrtoeol
                    stdscr.move(y, start_x)
                    stdscr.clrtoeol()
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
                "f - track fav",
                "Ctrl+f - channel fav",
                "z - only fav",
                "x - toggle footer",
                "r - bitrate",
                "s - sleep",
                "t/y - theme",
                "PgUp/Dn - volume",
                "q - quit",
            ]

            available_width = max_x - 1
            available_lines = 2

            # First, completely clear the instruction area to prevent artifacts
            for i in range(available_lines):
                y_pos = max_y - available_lines + i
                stdscr.move(y_pos, 0)
                stdscr.clrtoeol()

            lines = []
            current_line = ""

            for item in instruction_items:
                # Use space separator instead of " | "
                separator = "  " if current_line else ""
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

            # Determine if current theme is light - use different attributes for better visibility
            from .themes import is_light_theme
            theme_name = self._current_theme_name if hasattr(self, '_current_theme_name') else 'default'
            is_light = is_light_theme(theme_name)
            
            # Don't use A_DIM for instructions - it makes text too faint on all themes
            # Use bold attribute instead for better visibility
            attr = curses.color_pair(5) | curses.A_BOLD

            for i, line in enumerate(lines):
                if i >= available_lines:
                    break
                y_pos = max_y - available_lines + i
                padded_line = line.ljust(available_width)
                stdscr.addstr(y_pos, 0, padded_line, attr)

        except curses.error:
            pass

    def _redraw_instructions(self, stdscr: curses.window, max_y: int, max_x: int) -> None:
        """Redraw only the instructions at bottom (for partial redraw)."""
        self._display_instructions(stdscr, max_y, max_x)

    def _handle_volume_display(self, stdscr: curses.window) -> None:
        """Handle volume indicator display"""
        # Always draw volume indicator if it was recently updated
        if self.volume_display is not None:
            elapsed = time.time() - self.volume_display_time
            if elapsed < VOLUME_DISPLAY_TIMEOUT:
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
        # Use named constants for color pairs
        vol_bar_color = VOLUME_BAR_COLOR_PAIR
        vol_icon_color = VOLUME_ICON_COLOR_PAIR

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
        """Show notification with automatic screen refresh after closing."""
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
            
            # Перерисовываем основной экран после закрытия уведомления
            stdscr.refresh()
        except curses.error:
            pass

    def display_sleep_overlay(
        self,
        stdscr: curses.window,
        sleep_input: str,
    ) -> None:
        """Display sleep timer input overlay - drawn on main screen for proper cleanup."""
        max_y, max_x = stdscr.getmaxyx()

        # Overlay dimensions
        overlay_width = 30
        overlay_height = 7
        start_y = (max_y - overlay_height) // 2
        start_x = (max_x - overlay_width) // 2

        try:
            # Draw overlay box manually (curses.window.box doesn't accept coordinates)
            stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
            
            # Draw border
            for x in range(overlay_width):
                stdscr.addstr(start_y, start_x + x, "─", curses.color_pair(3) | curses.A_BOLD)
                stdscr.addstr(start_y + overlay_height - 1, start_x + x, "─", curses.color_pair(3) | curses.A_BOLD)
            for y in range(1, overlay_height - 1):
                stdscr.addstr(start_y + y, start_x, "│", curses.color_pair(3) | curses.A_BOLD)
                stdscr.addstr(start_y + y, start_x + overlay_width - 1, "│", curses.color_pair(3) | curses.A_BOLD)
            
            # Corners
            stdscr.addstr(start_y, start_x, "┌", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y, start_x + overlay_width - 1, "┐", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + overlay_height - 1, start_x, "└", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + overlay_height - 1, start_x + overlay_width - 1, "┘", curses.color_pair(3) | curses.A_BOLD)
            
            stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)

            # Title
            title = "Sleep Timer"
            stdscr.addstr(start_y + 1, start_x + (overlay_width - len(title)) // 2,
                         title, curses.color_pair(1) | curses.A_BOLD)

            # Input field
            input_label = "Minutes: "
            input_value = sleep_input or ""
            input_display = input_label + input_value + "_"
            stdscr.addstr(start_y + 3, start_x + 2, input_display[:overlay_width - 4],
                         curses.color_pair(2))

            # Hints
            stdscr.addstr(start_y + 5, start_x + 2, "Esc: cancel",
                         curses.color_pair(5) | curses.A_DIM)

            # Position cursor at input
            curses.curs_set(1)
            stdscr.move(start_y + 3, start_x + 2 + len(input_label) + len(input_value))
            stdscr.refresh()

        except curses.error:
            curses.curs_set(0)

    def display_sleep_timer(
        self,
        stdscr: curses.window,
        remaining: str,
    ) -> None:
        """Display sleep timer countdown in bottom right corner"""
        if not remaining:
            return

        max_y, max_x = stdscr.getmaxyx()

        # Timer format: " ⏱ MM:SS "
        timer_text = f" ⏱ {remaining} "
        timer_width = len(timer_text)
        start_y = max_y - 3  # Above instructions
        start_x = max_x - timer_width - 1

        try:
            # Clear area using clrtoeol to prevent artifacts
            stdscr.move(start_y, start_x)
            stdscr.clrtoeol()
            # Draw timer box
            stdscr.addstr(start_y, start_x, timer_text, curses.color_pair(3) | curses.A_BOLD)
        except curses.error:
            pass

    def _display_help(self, stdscr: curses.window, max_y: int, max_x: int) -> None:
        """Display help screen - drawn on main screen for proper cleanup."""
        # Get version from package
        from . import __version__
        
        help_text = [
            (f"SomaFM TUI v{__version__} - Keyboard Shortcuts", "header"),
            ("", ""),
            ("Navigation", "section"),
            ("  ↑/k  - Move up", "normal"),
            ("  ↓/j  - Move down", "normal"),
            ("  Enter/l - Play selected channel", "normal"),
            ("  ?     - Toggle this help", "normal"),
            ("", ""),
            ("Playback", "section"),
            ("  Space - Pause/Resume", "normal"),
            ("  h     - Stop playback", "normal"),
            ("  r     - Cycle bitrate", "normal"),
            ("  v/b   - Decrease/Increase volume", "normal"),
            ("  PgUp  - Increase volume", "normal"),
            ("  PgDn  - Decrease volume", "normal"),
            ("", ""),
            ("Channels", "section"),
            ("  /     - Search channels", "normal"),
            ("  f     - Toggle track favorite", "normal"),
            ("  Ctrl+F - Toggle channel favorite", "normal"),
            ("  z     - Show only favorites", "normal"),
            ("  x     - Toggle footer", "normal"),
            ("", ""),
            ("Timer", "section"),
            ("  s     - Set sleep timer", "normal"),
            ("", ""),
            ("Appearance", "section"),
            ("  t/y   - Cycle theme (forward/back)", "normal"),
            ("", ""),
            ("Other", "section"),
            ("  q     - Quit", "normal"),
            ("  ESC   - Close search/help/timer", "normal"),
        ]

        # Calculate box size
        box_height = len(help_text) + 2
        box_width = min(HELP_OVERLAY_WIDTH, max_x - 10)  # Limit width to HELP_OVERLAY_WIDTH chars
        box_y = (max_y - box_height) // 2
        box_x = (max_x - box_width) // 2  # Center horizontally

        try:
            # Draw overlay box manually on main screen (not separate window)
            stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
            
            # Draw border
            for x in range(box_width):
                stdscr.addstr(box_y, box_x + x, "─", curses.color_pair(3) | curses.A_BOLD)
                stdscr.addstr(box_y + box_height - 1, box_x + x, "─", curses.color_pair(3) | curses.A_BOLD)
            for y in range(1, box_height - 1):
                stdscr.addstr(box_y + y, box_x, "│", curses.color_pair(3) | curses.A_BOLD)
                stdscr.addstr(box_y + y, box_x + box_width - 1, "│", curses.color_pair(3) | curses.A_BOLD)
            
            # Corners
            stdscr.addstr(box_y, box_x, "┌", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(box_y, box_x + box_width - 1, "┐", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(box_y + box_height - 1, box_x, "└", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(box_y + box_height - 1, box_x + box_width - 1, "┘", curses.color_pair(3) | curses.A_BOLD)
            
            stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)

            # Draw help content
            for i, (text, style) in enumerate(help_text):
                y = box_y + 1 + i

                if style == "header":
                    attr = curses.color_pair(1) | curses.A_BOLD
                elif style == "section":
                    attr = curses.color_pair(2) | curses.A_BOLD
                else:
                    attr = curses.color_pair(1)

                stdscr.addstr(y, box_x + 2, text.ljust(box_width - 4)[:box_width - 4], attr)

            # Draw footer
            footer = "Press ? or ESC to close"
            stdscr.addstr(box_y + box_height - 2, box_x + 2, footer.ljust(box_width - 4), curses.color_pair(5) | curses.A_DIM)

        except curses.error:
            pass
