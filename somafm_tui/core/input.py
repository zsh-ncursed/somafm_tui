"""Input handler module.

Handles all user input including keyboard navigation, search, and sleep timer.
"""

import curses
from typing import Any, Optional, Tuple

from .playback import PlaybackController
from .state import StateManager
from ..ui import UIScreen


class InputHandler:
    """Handler for user input.
    
    Responsibilities:
    - Dispatch input to appropriate handler based on mode
    - Handle normal mode input (navigation, playback controls)
    - Handle search mode input
    - Handle sleep timer input
    """

    def __init__(
        self,
        playback_controller: PlaybackController,
        state_manager: StateManager,
        ui_screen: UIScreen,
    ):
        self.playback = playback_controller
        self.state = state_manager
        self.ui = ui_screen

        self._stdscr: Optional[curses.window] = None

    def set_stdscr(self, stdscr: curses.window) -> None:
        """Set curses window reference."""
        self._stdscr = stdscr

    def handle_input(self, key: Any) -> None:
        """Handle user input.
        
        Dispatches to appropriate handler based on current mode.
        
        Args:
            key: Key event from curses
        """
        if self.state.sleep_overlay_active:
            self._handle_sleep_input(key)
        elif self.state.is_searching:
            self._handle_search_input(key)
        else:
            self._handle_normal_input(key)

    def _handle_sleep_input(self, key: Any) -> None:
        """Handle input in sleep overlay mode.
        
        Args:
            key: Key event from curses
        """
        if key == chr(27):  # ESC
            self.state.hide_sleep_overlay()
        elif key in (curses.KEY_BACKSPACE, "\b", "\x7f"):
            self.state.remove_sleep_input()
        elif isinstance(key, str) and key.isdigit():
            self.state.add_sleep_input(key)
        elif key in (curses.KEY_ENTER, "\n", "\r"):
            # Set timer
            if self.state.sleep_input:
                try:
                    minutes = int(self.state.sleep_input)
                    if self.state.set_sleep_timer(minutes):
                        if self._stdscr:
                            self.ui.show_notification(
                                self._stdscr, f"Sleep timer: {minutes} min"
                            )
                except ValueError:
                    pass
            self.state.hide_sleep_overlay()

    def _handle_search_input(self, key: Any) -> None:
        """Handle input in search mode.
        
        Args:
            key: Key event from curses
        """
        if key == chr(27):  # ESC
            self.state.exit_search()
        elif key == "?":
            self.state.exit_search()
            self.state.toggle_help()
        elif key in (curses.KEY_BACKSPACE, "\b", "\x7f"):
            self.state.remove_search_char()
        elif isinstance(key, str) and len(key) == 1 and key.isprintable():
            self.state.add_search_char(key)
        elif key == curses.KEY_UP or (isinstance(key, str) and key == "k"):
            self.state.navigate_up()
        elif key == curses.KEY_DOWN or (isinstance(key, str) and key == "j"):
            self.state.navigate_down()
        elif key == curses.KEY_PPAGE:
            if self.playback.is_playing:
                self.playback.increase_volume()
                self._show_volume_overlay()
        elif key == curses.KEY_NPAGE:
            if self.playback.is_playing:
                self.playback.decrease_volume()
                self._show_volume_overlay()
        elif key in (curses.KEY_ENTER, "\n", "\r") or (isinstance(key, str) and key == "l"):
            selected = self.state.get_selected_channel()
            if selected:
                channels = self.state.get_all_channels()
                # Find original index
                for i, ch in enumerate(channels):
                    if ch.id == selected.id:
                        self.state.current_index = i
                        break
                self.playback.play_channel(selected, self.state.current_index)
                self.state.exit_search()

    def _handle_normal_input(self, key: Any) -> None:
        """Handle input in normal mode.
        
        Args:
            key: Key event from curses
        """
        if isinstance(key, str):
            self._handle_string_input(key)
        else:
            self._handle_special_key(key)

    def _handle_string_input(self, key: str) -> None:
        """Handle string input in normal mode.
        
        Args:
            key: Key character
        """
        # Search and help
        if key == "/":
            self.state.start_search()
        elif key == "?":
            self.state.toggle_help()
        elif key == chr(27):  # ESC - close help
            if self.state.show_help:
                self.state.hide_help()

        # Application control
        elif key in ("q", "Q"):
            self.state.stop()

        # Playback control
        elif key in ("h", "H"):
            self.playback.stop_playback()
        elif key in ("\n", "\r", "l"):
            selected = self.state.get_selected_channel()
            if selected:
                self.playback.play_channel(selected, self.state.current_index)
        elif key == " ":
            if self.playback.is_playing:
                self.playback.toggle_playback()

        # Favorites
        elif key == "f":
            # 'f' adds current track to favorites
            success, message = self.playback.toggle_favorite_track()
            if self._stdscr and message:
                self.ui.show_notification(self._stdscr, message)
        elif key == "\x06":  # Ctrl+F
            # Ctrl+F toggles channel favorite
            success, message = self.playback.toggle_channel_favorite()
            if self._stdscr and message:
                self.ui.show_notification(self._stdscr, message)

        # Navigation
        elif key == "k":
            self.state.navigate_up()
        elif key == "j":
            self.state.navigate_down()

        # Appearance
        elif key in ("t", "T"):
            new_theme = self.state.cycle_theme()
            if self._stdscr:
                theme_info = self.state.get_theme_info()
                # Показываем уведомление без блокировки
                self.ui.show_notification(
                    self._stdscr, f"Theme: {theme_info.get('name', new_theme)}", timeout=1.0
                )

        # Volume
        elif key in ("v", "V"):
            self.playback.decrease_volume()
            self._show_volume_overlay()
        elif key in ("b", "B"):
            self.playback.increase_volume()
            self._show_volume_overlay()

        # Sleep timer
        elif key in ("s", "S"):
            self.state.show_sleep_overlay()

        # Bitrate
        elif key in ("r", "R"):
            self.playback.cycle_bitrate()

    def _handle_special_key(self, key: Any) -> None:
        """Handle special keys (arrows, page keys, etc.).

        Args:
            key: Special key code
        """
        if key == curses.KEY_RESIZE:
            # Handle terminal resize - invalidate UI cache to trigger full redraw
            if hasattr(self.ui, 'invalidate_cache'):
                self.ui.invalidate_cache()
            return  # Let main loop handle redraw
        elif key == curses.KEY_UP:
            self.state.navigate_up()
        elif key == curses.KEY_DOWN:
            self.state.navigate_down()
        elif key == curses.KEY_ENTER:
            selected = self.state.get_selected_channel()
            if selected:
                self.playback.play_channel(selected, self.state.current_index)
        elif key == curses.KEY_PPAGE:
            self.playback.increase_volume()
            self._show_volume_overlay()
        elif key == curses.KEY_NPAGE:
            self.playback.decrease_volume()
            self._show_volume_overlay()

    def _show_volume_overlay(self) -> None:
        """Show volume overlay if stdscr is available."""
        if self._stdscr:
            self.ui.show_volume(self._stdscr, self.playback.get_volume())
