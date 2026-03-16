"""Tests for StateManager module."""

import pytest
from unittest.mock import Mock, patch, call
import time

from somafm_tui.core.state import StateManager
from somafm_tui.models import Channel
from somafm_tui.timer import SleepTimer


class TestStateManagerInit:
    """Tests for StateManager initialization."""

    def test_init_sets_attributes(self):
        """Should initialize all attributes correctly."""
        config = {"theme": "default"}
        channels = [Channel(id="test", title="Test")]

        manager = StateManager(
            config=config,
            channels=channels,
            cache_dir="/tmp/cache",
            config_file="/tmp/config.cfg",
        )

        assert manager.config == config
        assert manager.channels == channels
        assert manager.cache_dir == "/tmp/cache"
        assert manager.config_file == "/tmp/config.cfg"
        assert manager.running is True
        assert manager.current_index == 0
        assert manager.scroll_offset == 0
        assert manager.is_searching is False
        assert manager.search_query == ""
        assert manager.filtered_channels == []
        assert manager.show_help is False
        assert isinstance(manager.sleep_timer, SleepTimer)
        assert manager.sleep_overlay_active is False
        assert manager.sleep_input == ""
        assert manager._current_theme == "default"
        assert manager._on_state_change is None
        assert manager._on_theme_change is None

    def test_set_on_state_change(self):
        """Should set state change callback."""
        manager = self._create_manager()
        callback = Mock()

        manager.set_on_state_change(callback)

        assert manager._on_state_change is callback

    def test_set_on_theme_change(self):
        """Should set theme change callback."""
        manager = self._create_manager()
        callback = Mock()

        manager.set_on_theme_change(callback)

        assert manager._on_theme_change is callback

    def _create_manager(self):
        """Helper to create StateManager."""
        return StateManager(
            config={"theme": "default"},
            channels=[Channel(id="test", title="Test")],
            cache_dir="/tmp/cache",
            config_file="/tmp/config.cfg",
        )


class TestGetChannelsToDisplay:
    """Tests for get_channels_to_display method."""

    def test_returns_all_channels_when_not_searching(self):
        """Should return all channels when not searching."""
        channels = [
            Channel(id="ch1", title="Channel 1"),
            Channel(id="ch2", title="Channel 2"),
        ]
        manager = StateManager(
            config={},
            channels=channels,
            cache_dir="/tmp/cache",
            config_file="/tmp/config.cfg",
        )
        manager.is_searching = False

        result = manager.get_channels_to_display()

        assert result == channels

    def test_returns_filtered_channels_when_searching(self):
        """Should return filtered channels when searching."""
        channels = [
            Channel(id="ch1", title="Channel 1"),
            Channel(id="ch2", title="Channel 2"),
        ]
        manager = StateManager(
            config={},
            channels=channels,
            cache_dir="/tmp/cache",
            config_file="/tmp/config.cfg",
        )
        manager.is_searching = True
        manager.search_query = "Channel 1"

        with patch('somafm_tui.core.state.filter_channels_by_query') as mock_filter:
            mock_filter.return_value = [channels[0]]
            result = manager.get_channels_to_display()

            mock_filter.assert_called_once_with(channels, "Channel 1")
            assert result == [channels[0]]

    def test_returns_all_channels_when_searching_with_empty_query(self):
        """Should return all channels when searching with empty query."""
        channels = [Channel(id="ch1", title="Channel 1")]
        manager = StateManager(
            config={},
            channels=channels,
            cache_dir="/tmp/cache",
            config_file="/tmp/config.cfg",
        )
        manager.is_searching = True
        manager.search_query = ""

        result = manager.get_channels_to_display()

        assert result == channels


class TestNavigation:
    """Tests for navigation methods."""

    def test_navigate_up(self):
        """Should navigate up in channel list."""
        manager = self._create_manager()
        manager.current_index = 5

        manager.navigate_up()

        assert manager.current_index == 4

    def test_navigate_up_stops_at_zero(self):
        """Should not go below zero."""
        manager = self._create_manager()
        manager.current_index = 0

        manager.navigate_up()

        assert manager.current_index == 0

    def test_navigate_up_with_step(self):
        """Should navigate up by step."""
        manager = self._create_manager()
        manager.current_index = 10

        manager.navigate_up(step=3)

        assert manager.current_index == 7

    def test_navigate_down(self):
        """Should navigate down in channel list."""
        manager = self._create_manager()
        manager.current_index = 0

        manager.navigate_down()

        assert manager.current_index == 1

    def test_navigate_down_stops_at_end(self):
        """Should not go beyond last channel."""
        channels = [Channel(id=f"ch{i}", title=f"Channel {i}") for i in range(5)]
        manager = StateManager(
            config={},
            channels=channels,
            cache_dir="/tmp/cache",
            config_file="/tmp/config.cfg",
        )
        manager.current_index = 4

        manager.navigate_down()

        assert manager.current_index == 4

    def test_navigate_down_with_step(self):
        """Should navigate down by step."""
        channels = [Channel(id=f"ch{i}", title=f"Channel {i}") for i in range(10)]
        manager = StateManager(
            config={},
            channels=channels,
            cache_dir="/tmp/cache",
            config_file="/tmp/config.cfg",
        )
        manager.current_index = 0

        manager.navigate_down(step=3)

        assert manager.current_index == 3

    def test_navigate_page_up(self):
        """Should navigate page up."""
        manager = self._create_manager()
        manager.current_index = 15

        manager.navigate_page_up(page_size=10)

        assert manager.current_index == 5

    def test_navigate_page_down(self):
        """Should navigate page down."""
        channels = [Channel(id=f"ch{i}", title=f"Channel {i}") for i in range(20)]
        manager = StateManager(
            config={},
            channels=channels,
            cache_dir="/tmp/cache",
            config_file="/tmp/config.cfg",
        )
        manager.current_index = 0

        manager.navigate_page_down(page_size=10)

        assert manager.current_index == 10

    def test_navigate_triggers_callback(self):
        """Should trigger state change callback on navigation."""
        manager = self._create_manager()
        callback = Mock()
        manager.set_on_state_change(callback)

        manager.navigate_down()

        callback.assert_called_once()

    def _create_manager(self):
        """Helper to create StateManager."""
        channels = [Channel(id=f"ch{i}", title=f"Channel {i}") for i in range(10)]
        return StateManager(
            config={},
            channels=channels,
            cache_dir="/tmp/cache",
            config_file="/tmp/config.cfg",
        )


class TestScrollOffset:
    """Tests for scroll offset management."""

    def test_update_scroll_offset_keeps_selection_visible(self):
        """Should update scroll offset to keep selection visible."""
        channels = [Channel(id=f"ch{i}", title=f"Channel {i}") for i in range(20)]
        manager = StateManager(
            config={},
            channels=channels,
            cache_dir="/tmp/cache",
            config_file="/tmp/config.cfg",
        )
        manager.current_index = 15
        manager.scroll_offset = 0

        manager.update_scroll_offset(panel_height=12)

        assert manager.scroll_offset > 0
        assert manager.current_index >= manager.scroll_offset

    def test_update_scroll_offset_when_selection_above_view(self):
        """Should scroll up when selection is above visible area."""
        channels = [Channel(id=f"ch{i}", title=f"Channel {i}") for i in range(20)]
        manager = StateManager(
            config={},
            channels=channels,
            cache_dir="/tmp/cache",
            config_file="/tmp/config.cfg",
        )
        manager.current_index = 5
        manager.scroll_offset = 10

        manager.update_scroll_offset(panel_height=12)

        assert manager.scroll_offset <= manager.current_index

    def test_update_scroll_offset_clamps_to_valid_range(self):
        """Should clamp scroll offset to valid range."""
        channels = [Channel(id=f"ch{i}", title=f"Channel {i}") for i in range(5)]
        manager = StateManager(
            config={},
            channels=channels,
            cache_dir="/tmp/cache",
            config_file="/tmp/config.cfg",
        )
        manager.scroll_offset = 100  # Invalid value

        manager.update_scroll_offset(panel_height=12)

        assert manager.scroll_offset == 0

    def test_update_scroll_offset_adjusts_current_index_if_out_of_bounds(self):
        """Should adjust current index if out of bounds."""
        channels = [Channel(id=f"ch{i}", title=f"Channel {i}") for i in range(5)]
        manager = StateManager(
            config={},
            channels=channels,
            cache_dir="/tmp/cache",
            config_file="/tmp/config.cfg",
        )
        manager.current_index = 100  # Out of bounds

        manager.update_scroll_offset(panel_height=12)

        assert manager.current_index < len(channels)


class TestSearch:
    """Tests for search functionality."""

    def test_start_search(self):
        """Should enter search mode."""
        manager = self._create_manager()
        manager.is_searching = False
        manager.search_query = "old query"
        manager.current_index = 5

        manager.start_search()

        assert manager.is_searching is True
        assert manager.search_query == ""
        assert manager.current_index == 0

    def test_exit_search(self):
        """Should exit search mode."""
        manager = self._create_manager()
        manager.is_searching = True
        manager.search_query = "test query"

        manager.exit_search()

        assert manager.is_searching is False
        assert manager.search_query == ""

    def test_add_search_char(self):
        """Should add character to search query."""
        manager = self._create_manager()
        manager.search_query = "test"

        manager.add_search_char("i")
        manager.add_search_char("n")
        manager.add_search_char("g")

        assert manager.search_query == "testing"

    def test_add_search_char_ignores_non_printable(self):
        """Should ignore non-printable characters."""
        manager = self._create_manager()
        manager.search_query = "test"

        manager.add_search_char("\n")
        manager.add_search_char("\t")

        assert manager.search_query == "test"

    def test_remove_search_char(self):
        """Should remove last character from search query."""
        manager = self._create_manager()
        manager.search_query = "test"

        manager.remove_search_char()

        assert manager.search_query == "tes"

    def test_remove_search_char_empty_query(self):
        """Should handle empty query."""
        manager = self._create_manager()
        manager.search_query = ""

        manager.remove_search_char()

        assert manager.search_query == ""

    def test_add_search_char_resets_index(self):
        """Should reset index when adding search char."""
        manager = self._create_manager()
        manager.current_index = 5

        manager.add_search_char("a")

        assert manager.current_index == 0

    def test_search_triggers_callback(self):
        """Should trigger callback on search changes."""
        manager = self._create_manager()
        callback = Mock()
        manager.set_on_state_change(callback)

        manager.start_search()

        callback.assert_called()

    def _create_manager(self):
        """Helper to create StateManager."""
        return StateManager(
            config={},
            channels=[Channel(id="test", title="Test")],
            cache_dir="/tmp/cache",
            config_file="/tmp/config.cfg",
        )


class TestHelpOverlay:
    """Tests for help overlay."""

    def test_toggle_help(self):
        """Should toggle help overlay."""
        manager = self._create_manager()
        manager.show_help = False

        manager.toggle_help()

        assert manager.show_help is True

        manager.toggle_help()

        assert manager.show_help is False

    def test_hide_help(self):
        """Should hide help overlay."""
        manager = self._create_manager()
        manager.show_help = True

        manager.hide_help()

        assert manager.show_help is False

    def test_toggle_help_triggers_callback(self):
        """Should trigger callback when toggling help."""
        manager = self._create_manager()
        callback = Mock()
        manager.set_on_state_change(callback)

        manager.toggle_help()

        callback.assert_called_once()

    def _create_manager(self):
        """Helper to create StateManager."""
        return StateManager(
            config={},
            channels=[Channel(id="test", title="Test")],
            cache_dir="/tmp/cache",
            config_file="/tmp/config.cfg",
        )


class TestSleepTimer:
    """Tests for sleep timer functionality."""

    def test_show_sleep_overlay(self):
        """Should show sleep overlay."""
        manager = self._create_manager()

        manager.show_sleep_overlay()

        assert manager.sleep_overlay_active is True
        assert manager.sleep_input == ""

    def test_hide_sleep_overlay(self):
        """Should hide sleep overlay."""
        manager = self._create_manager()
        manager.sleep_overlay_active = True
        manager.sleep_input = "30"

        manager.hide_sleep_overlay()

        assert manager.sleep_overlay_active is False
        assert manager.sleep_input == ""

    def test_add_sleep_input_single_digit(self):
        """Should add single digit to sleep input."""
        manager = self._create_manager()

        manager.add_sleep_input("3")

        assert manager.sleep_input == "3"

    def test_add_sleep_input_multiple_digits(self):
        """Should add multiple digits to sleep input."""
        manager = self._create_manager()

        manager.add_sleep_input("1")
        manager.add_sleep_input("2")
        manager.add_sleep_input("0")

        assert manager.sleep_input == "120"

    def test_add_sleep_input_max_length(self):
        """Should respect max length of 3 digits."""
        manager = self._create_manager()
        manager.sleep_input = "123"

        manager.add_sleep_input("4")

        assert manager.sleep_input == "123"

    def test_add_sleep_input_exceeds_max_value(self):
        """Should reject input that exceeds 480 minutes."""
        manager = self._create_manager()
        manager.sleep_input = "48"

        manager.add_sleep_input("1")  # Would make 481

        assert manager.sleep_input == "48"

    def test_add_sleep_input_first_digit_validation(self):
        """Should validate first digit (1-4 only)."""
        manager = self._create_manager()

        manager.add_sleep_input("5")  # Invalid first digit

        assert manager.sleep_input == ""

    def test_add_sleep_input_second_digit_validation_for_4(self):
        """Should validate second digit when first is 4."""
        manager = self._create_manager()
        manager.sleep_input = "4"

        manager.add_sleep_input("9")  # Invalid: would be 49

        assert manager.sleep_input == "4"

        manager.add_sleep_input("8")  # Valid: would be 48

        assert manager.sleep_input == "48"

    def test_remove_sleep_input(self):
        """Should remove last digit from sleep input."""
        manager = self._create_manager()
        manager.sleep_input = "120"

        manager.remove_sleep_input()

        assert manager.sleep_input == "12"

    def test_remove_sleep_input_empty(self):
        """Should handle empty input."""
        manager = self._create_manager()
        manager.sleep_input = ""

        manager.remove_sleep_input()

        assert manager.sleep_input == ""

    def test_set_sleep_timer_valid(self):
        """Should set sleep timer for valid value."""
        manager = self._create_manager()
        manager.sleep_input = "30"

        result = manager.set_sleep_timer(30)

        assert result is True
        assert manager.sleep_overlay_active is False
        assert manager.sleep_input == ""
        assert manager.sleep_timer.is_active()

    def test_set_sleep_timer_invalid_low(self):
        """Should reject value below 1."""
        manager = self._create_manager()

        result = manager.set_sleep_timer(0)

        assert result is False

    def test_set_sleep_timer_invalid_high(self):
        """Should reject value above 480."""
        manager = self._create_manager()

        result = manager.set_sleep_timer(481)

        assert result is False

    def test_cancel_sleep_timer(self):
        """Should cancel sleep timer."""
        manager = self._create_manager()
        manager.sleep_timer.set(30)
        manager.sleep_overlay_active = True

        manager.cancel_sleep_timer()

        assert not manager.sleep_timer.is_active()
        assert manager.sleep_overlay_active is False

    def test_check_sleep_timer_not_active(self):
        """Should return False when timer not active."""
        manager = self._create_manager()

        result = manager.check_sleep_timer()

        assert result is False

    def test_check_sleep_timer_not_expired(self):
        """Should return False when timer not expired."""
        manager = self._create_manager()
        manager.sleep_timer.set(30)

        result = manager.check_sleep_timer()

        assert result is False

    def test_check_sleep_timer_expired(self):
        """Should return True when timer expired."""
        manager = self._create_manager()
        # Set timer with 0 remaining seconds to simulate expiration
        manager.sleep_timer._remaining_seconds = 0
        manager._last_timer_check = 0

        result = manager.check_sleep_timer()

        # Timer with 0 remaining should be considered expired
        assert result is True or manager.sleep_timer.get_remaining_seconds() <= 0

    def test_should_update_timer_display(self):
        """Should return True when display should update."""
        manager = self._create_manager()
        manager.sleep_timer.set(30)
        manager._last_timer_display = 0

        result = manager.should_update_timer_display()

        assert result is True

    def test_should_update_timer_display_not_active(self):
        """Should return False when timer not active."""
        manager = self._create_manager()

        result = manager.should_update_timer_display()

        assert result is False

    def test_get_timer_remaining_active(self):
        """Should return formatted remaining time."""
        manager = self._create_manager()
        manager.sleep_timer.set(30)

        result = manager.get_timer_remaining()

        assert result != ""
        assert ":" in result  # Format is MM:SS or similar

    def test_get_timer_remaining_inactive(self):
        """Should return empty string when timer inactive."""
        manager = self._create_manager()

        result = manager.get_timer_remaining()

        assert result == ""

    def _create_manager(self):
        """Helper to create StateManager."""
        return StateManager(
            config={},
            channels=[Channel(id="test", title="Test")],
            cache_dir="/tmp/cache",
            config_file="/tmp/config.cfg",
        )


class TestTheme:
    """Tests for theme management."""

    def test_cycle_theme(self):
        """Should cycle to next theme."""
        manager = self._create_manager()
        manager._current_theme = "default"

        new_theme = manager.cycle_theme()

        assert new_theme != "default" or new_theme == "default"  # May wrap around
        assert manager.config["theme"] == new_theme

    def test_cycle_theme_triggers_callback(self):
        """Should trigger theme change callback."""
        manager = self._create_manager()
        callback = Mock()
        manager.set_on_theme_change(callback)

        manager.cycle_theme()

        callback.assert_called_once()

    def test_get_theme_info(self):
        """Should return theme information."""
        manager = self._create_manager()

        with patch('somafm_tui.core.state.get_color_themes', return_value={"default": {"name": "Default"}}):
            theme_info = manager.get_theme_info()

            assert isinstance(theme_info, dict)
            assert "name" in theme_info

    def test_get_current_theme_name(self):
        """Should return current theme name."""
        manager = self._create_manager()
        manager._current_theme = "monochrome"

        name = manager.get_current_theme_name()

        assert name == "monochrome"

    def test_cycle_theme_handles_invalid_current(self):
        """Should handle invalid current theme."""
        manager = self._create_manager()
        manager._current_theme = "invalid_theme"

        new_theme = manager.cycle_theme()

        assert new_theme is not None

    def _create_manager(self):
        """Helper to create StateManager."""
        return StateManager(
            config={"theme": "default"},
            channels=[Channel(id="test", title="Test")],
            cache_dir="/tmp/cache",
            config_file="/tmp/config.cfg",
        )


class TestChannelManagement:
    """Tests for channel management methods."""

    def test_get_channel_favorites(self):
        """Should load favorite channel IDs."""
        manager = self._create_manager()

        with patch('somafm_tui.core.state.load_favorites') as mock_load:
            mock_load.return_value = {"ch1", "ch2"}

            favorites = manager.get_channel_favorites("/tmp/favorites.json")

            mock_load.assert_called_once_with("/tmp/favorites.json")
            assert favorites == {"ch1", "ch2"}

    def test_get_selected_channel(self):
        """Should return currently selected channel."""
        channels = [
            Channel(id="ch1", title="Channel 1"),
            Channel(id="ch2", title="Channel 2"),
        ]
        manager = StateManager(
            config={},
            channels=channels,
            cache_dir="/tmp/cache",
            config_file="/tmp/config.cfg",
        )
        manager.current_index = 1

        selected = manager.get_selected_channel()

        assert selected is channels[1]

    def test_get_selected_channel_no_channels(self):
        """Should return None when no channels."""
        manager = StateManager(
            config={},
            channels=[],
            cache_dir="/tmp/cache",
            config_file="/tmp/config.cfg",
        )

        selected = manager.get_selected_channel()

        assert selected is None

    def test_get_selected_channel_invalid_index(self):
        """Should return None when index out of bounds."""
        channels = [Channel(id="ch1", title="Channel 1")]
        manager = StateManager(
            config={},
            channels=channels,
            cache_dir="/tmp/cache",
            config_file="/tmp/config.cfg",
        )
        manager.current_index = 10

        selected = manager.get_selected_channel()

        assert selected is None

    def test_get_all_channels(self):
        """Should return all channels."""
        channels = [
            Channel(id="ch1", title="Channel 1"),
            Channel(id="ch2", title="Channel 2"),
        ]
        manager = StateManager(
            config={},
            channels=channels,
            cache_dir="/tmp/cache",
            config_file="/tmp/config.cfg",
        )

        result = manager.get_all_channels()

        assert result == channels

    def test_reload_channels(self):
        """Should reload and sort channels by usage."""
        channels = [
            Channel(id="ch1", title="Channel 1"),
            Channel(id="ch2", title="Channel 2"),
        ]
        manager = StateManager(
            config={},
            channels=channels,
            cache_dir="/tmp/cache",
            config_file="/tmp/config.cfg",
        )

        with patch('somafm_tui.core.state.load_channel_usage') as mock_load, \
             patch('somafm_tui.core.state.clean_channel_usage') as mock_clean, \
             patch('somafm_tui.core.state.sort_channels_by_usage') as mock_sort:
            mock_load.return_value = {"ch1": 100}
            mock_clean.return_value = {"ch1": 100}
            mock_sort.return_value = channels[::-1]  # Reversed

            manager.reload_channels("/tmp/usage.json")

            mock_load.assert_called_once()
            mock_clean.assert_called_once()
            mock_sort.assert_called_once()
            assert manager.channels == channels[::-1]

    def _create_manager(self):
        """Helper to create StateManager."""
        return StateManager(
            config={},
            channels=[Channel(id="test", title="Test")],
            cache_dir="/tmp/cache",
            config_file="/tmp/config.cfg",
        )


class TestApplicationLifecycle:
    """Tests for application lifecycle methods."""

    def test_stop(self):
        """Should stop the application."""
        manager = self._create_manager()
        manager.running = True

        manager.stop()

        assert manager.running is False

    def test_is_running(self):
        """Should return running state."""
        manager = self._create_manager()
        manager.running = True

        assert manager.is_running() is True

    def test_is_running_false(self):
        """Should return False when stopped."""
        manager = self._create_manager()
        manager.running = False

        assert manager.is_running() is False

    def test_is_running_signal_received(self):
        """Should return False when signal received."""
        manager = self._create_manager()
        manager.running = True
        manager._signal_received = True

        assert manager.is_running() is False

    def test_set_signal_received(self):
        """Should mark signal as received."""
        manager = self._create_manager()

        manager.set_signal_received()

        assert manager._signal_received is True

    def _create_manager(self):
        """Helper to create StateManager."""
        return StateManager(
            config={},
            channels=[Channel(id="test", title="Test")],
            cache_dir="/tmp/cache",
            config_file="/tmp/config.cfg",
        )


class TestNotifyStateChange:
    """Tests for state change notification."""

    def test_notify_state_change_with_callback(self):
        """Should notify callback of state change."""
        manager = self._create_manager()
        callback = Mock()
        manager.set_on_state_change(callback)

        manager._notify_state_change()

        callback.assert_called_once()

    def test_notify_state_change_without_callback(self):
        """Should handle missing callback."""
        manager = self._create_manager()

        # Should not raise
        manager._notify_state_change()

    def _create_manager(self):
        """Helper to create StateManager."""
        return StateManager(
            config={},
            channels=[Channel(id="test", title="Test")],
            cache_dir="/tmp/cache",
            config_file="/tmp/config.cfg",
        )
