"""State manager module.

Manages application state including navigation, search, sleep timer, and UI state.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Set, Callable

from ..models import Channel
from ..timer import SleepTimer
from ..themes import get_theme_names, get_color_themes
from ..config import save_config
from ..channels import (
    filter_channels_by_query,
    load_favorites,
    sort_channels_by_usage,
    clean_channel_usage,
    load_channel_usage,
)


class StateManager:
    """Manager for application state.
    
    Responsibilities:
    - Application lifecycle (running flag)
    - Navigation state (current_index, scroll_offset)
    - Search state (is_searching, search_query, filtered_channels)
    - Sleep timer state
    - Help overlay state
    - Theme management
    - Channel list management
    """

    def __init__(
        self,
        config: Dict[str, Any],
        channels: List[Channel],
        cache_dir: str,
        config_file: str,
    ):
        self.config = config
        self.channels = channels
        self.cache_dir = cache_dir
        self.config_file = config_file

        # Application state
        self.running = True
        self.current_index = 0
        self.scroll_offset = 0

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
        self._last_timer_display = 0.0
        self._last_timer_check = 0.0

        # Theme state
        self._current_theme = config.get("theme", "default")

        # Callbacks
        self._on_state_change: Optional[Callable] = None
        self._on_theme_change: Optional[Callable] = None

    def set_on_state_change(self, callback: Callable) -> None:
        """Set callback for state changes."""
        self._on_state_change = callback

    def set_on_theme_change(self, callback: Callable) -> None:
        """Set callback for theme changes."""
        self._on_theme_change = callback

    def get_channels_to_display(self) -> List[Channel]:
        """Get list of channels to display based on current state.
        
        Returns filtered channels if searching, otherwise all channels.
        """
        if self.is_searching:
            if self.search_query:
                return filter_channels_by_query(self.channels, self.search_query)
            return self.channels
        return self.channels

    def navigate_up(self, step: int = 1) -> None:
        """Navigate up in channel list."""
        channels = self.get_channels_to_display()
        if channels:
            self.current_index = max(0, self.current_index - step)
            self._notify_state_change()

    def navigate_down(self, step: int = 1) -> None:
        """Navigate down in channel list."""
        channels = self.get_channels_to_display()
        if channels:
            self.current_index = min(len(channels) - 1, self.current_index + step)
            self._notify_state_change()

    def navigate_page_up(self, page_size: int = 10) -> None:
        """Navigate page up."""
        self.navigate_up(page_size)

    def navigate_page_down(self, page_size: int = 10) -> None:
        """Navigate page down."""
        self.navigate_down(page_size)

    def update_scroll_offset(self, panel_height: int) -> None:
        """Update scroll offset to keep current selection visible.
        
        Args:
            panel_height: Height of the channel panel in rows
        """
        channels = self.get_channels_to_display()
        visible_channels = panel_height - 3
        max_scroll = max(0, len(channels) - visible_channels)

        if self.current_index < self.scroll_offset:
            self.scroll_offset = self.current_index
        elif self.current_index >= self.scroll_offset + visible_channels:
            self.scroll_offset = min(max_scroll, self.current_index - visible_channels + 1)

        self.scroll_offset = max(0, min(max_scroll, self.scroll_offset))

        # Ensure current selection is visible
        if self.current_index >= len(channels):
            self.current_index = max(0, len(channels) - 1)

    def start_search(self) -> None:
        """Enter search mode."""
        self.is_searching = True
        self.search_query = ""
        self.current_index = 0
        self._notify_state_change()

    def exit_search(self) -> None:
        """Exit search mode."""
        self.is_searching = False
        self.search_query = ""
        self._notify_state_change()

    def add_search_char(self, char: str) -> None:
        """Add character to search query."""
        if isinstance(char, str) and len(char) == 1 and char.isprintable():
            self.search_query += char
            self.current_index = 0
            self._notify_state_change()

    def remove_search_char(self) -> None:
        """Remove last character from search query."""
        if self.search_query:
            self.search_query = self.search_query[:-1]
            self.current_index = 0
            self._notify_state_change()

    def toggle_help(self) -> None:
        """Toggle help overlay."""
        self.show_help = not self.show_help
        self._notify_state_change()

    def hide_help(self) -> None:
        """Hide help overlay."""
        self.show_help = False
        self._notify_state_change()

    def show_sleep_overlay(self) -> None:
        """Show sleep timer input overlay."""
        self.sleep_overlay_active = True
        self.sleep_input = ""

    def hide_sleep_overlay(self) -> None:
        """Hide sleep timer input overlay."""
        self.sleep_overlay_active = False
        self.sleep_input = ""

    def add_sleep_input(self, digit: str) -> None:
        """Add digit to sleep timer input.
        
        Args:
            digit: Digit character (0-9)
            
        Note:
            Maximum sleep timer is 480 minutes (8 hours).
            Input validation prevents entering values > 480.
        """
        if isinstance(digit, str) and digit.isdigit():
            if len(self.sleep_input) >= 3:
                return  # Max length reached
            
            # Calculate potential new value
            potential_value = int(self.sleep_input + digit) if self.sleep_input else int(digit)
            
            # Reject if exceeds maximum
            if potential_value > 480:
                return
            
            # Additional validation: prevent entering invalid intermediate values
            # that could lead to confusion (e.g., 47 is OK, but user can't reach 480 from there)
            if len(self.sleep_input) == 0:
                # First digit: 1-4 only
                if digit in '1234':
                    self.sleep_input += digit
            elif len(self.sleep_input) == 1:
                # Second digit: depends on first
                first_digit = int(self.sleep_input)
                if first_digit < 4:
                    # 1-3: any digit OK (10-399 range)
                    self.sleep_input += digit
                else:
                    # 4: only 0-8 OK (40-48 range)
                    if int(digit) <= 8:
                        self.sleep_input += digit
            else:
                # Third digit: already validated by potential_value <= 480
                self.sleep_input += digit

    def remove_sleep_input(self) -> None:
        """Remove last digit from sleep timer input."""
        if self.sleep_input:
            self.sleep_input = self.sleep_input[:-1]

    def set_sleep_timer(self, minutes: int) -> bool:
        """Set sleep timer.

        Args:
            minutes: Minutes until shutdown (1-480)

        Returns:
            True if timer was set successfully, False if invalid
            
        Note:
            Maximum sleep timer is 480 minutes (8 hours).
        """
        if 1 <= minutes <= 480:
            self.sleep_timer.set(minutes)
            self.sleep_overlay_active = False
            self.sleep_input = ""
            return True
        return False

    def cancel_sleep_timer(self) -> None:
        """Cancel sleep timer."""
        self.sleep_timer.cancel()
        self.sleep_overlay_active = False
        self.sleep_input = ""

    def check_sleep_timer(self) -> bool:
        """Check if sleep timer has expired.
        
        Returns:
            True if timer has expired and app should shut down
        """
        current_time = time.time()

        # Check timer expiration every minute
        if self.sleep_timer.is_active():
            if current_time - self._last_timer_check >= 60:
                self._last_timer_check = current_time

            if self.sleep_timer.get_remaining_seconds() <= 0:
                logging.info("Sleep timer expired, shutting down")
                return True

        return False

    def should_update_timer_display(self) -> bool:
        """Check if timer display should be updated.
        
        Returns:
            True if display should be updated (every second)
        """
        current_time = time.time()
        if self.sleep_timer.is_active():
            if current_time - self._last_timer_display >= 1:
                self._last_timer_display = current_time
                return True
        return False

    def get_timer_remaining(self) -> str:
        """Get formatted remaining time.
        
        Returns:
            Formatted time string (MM:SS) or empty string if timer not active
        """
        if self.sleep_timer.is_active():
            return self.sleep_timer.format_remaining()
        return ""

    def cycle_theme(self) -> str:
        """Cycle to next theme.
        
        Returns:
            Name of the new theme
        """
        themes = get_theme_names()
        try:
            current_index = themes.index(self._current_theme)
            next_index = (current_index + 1) % len(themes)
        except ValueError:
            next_index = 0

        self._current_theme = themes[next_index]
        self.config["theme"] = self._current_theme
        save_config(self.config)

        if self._on_theme_change:
            self._on_theme_change(self._current_theme)

        return self._current_theme

    def get_theme_info(self) -> Dict[str, Any]:
        """Get current theme information.
        
        Returns:
            Theme dictionary with colors and settings
        """
        themes = get_color_themes()
        return themes.get(self._current_theme, themes.get("default", {}))

    def get_current_theme_name(self) -> str:
        """Get current theme name."""
        return self._current_theme

    def get_channel_favorites(self, favorites_file: str) -> Set[str]:
        """Load favorite channel IDs.
        
        Args:
            favorites_file: Path to favorites file
            
        Returns:
            Set of favorite channel IDs
        """
        return load_favorites(favorites_file)

    def get_selected_channel(self) -> Optional[Channel]:
        """Get currently selected channel.
        
        Returns:
            Selected channel or None if no channels
        """
        channels = self.get_channels_to_display()
        if channels and 0 <= self.current_index < len(channels):
            return channels[self.current_index]
        return None

    def get_all_channels(self) -> List[Channel]:
        """Get all channels.
        
        Returns:
            List of all channels
        """
        return self.channels

    def stop(self) -> None:
        """Stop the application."""
        self.running = False

    def is_running(self) -> bool:
        """Check if application is running.
        
        Returns:
            True if application should continue running
        """
        return self.running and not getattr(self, '_signal_received', False)

    def set_signal_received(self) -> None:
        """Mark that a termination signal was received."""
        self._signal_received = True

    def _notify_state_change(self) -> None:
        """Notify callbacks of state change."""
        if self._on_state_change:
            self._on_state_change()

    def reload_channels(self, usage_file: str) -> None:
        """Reload and sort channels by usage.
        
        Args:
            usage_file: Path to channel usage file
        """
        usage = load_channel_usage(usage_file)
        valid_ids = {ch.id for ch in self.channels}
        usage = clean_channel_usage(usage, valid_ids)
        self.channels = sort_channels_by_usage(self.channels, usage)
