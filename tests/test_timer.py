"""Tests for timer module."""

import pytest
import time
from unittest.mock import patch

from somafm_tui.timer import SleepTimer


class TestSleepTimerInit:
    """Tests for SleepTimer initialization."""

    def test_default_end_time_is_none(self):
        """Should initialize with end_time as None."""
        timer = SleepTimer()
        assert timer.end_time is None

    def test_custom_end_time(self):
        """Should accept custom end_time."""
        custom_time = time.time() + 60
        timer = SleepTimer(end_time=custom_time)
        assert timer.end_time == custom_time


class TestSleepTimerSet:
    """Tests for SleepTimer.set method."""

    def test_sets_end_time(self):
        """Should set end_time to current time + minutes."""
        timer = SleepTimer()
        
        with patch('somafm_tui.timer.time.time', return_value=1000):
            timer.set(30)  # 30 minutes
            
            # 30 minutes = 1800 seconds
            expected_end = 1000 + 1800
            assert timer.end_time == expected_end

    def test_set_overwrites_previous(self):
        """Should overwrite previous end_time."""
        timer = SleepTimer()
        
        with patch('somafm_tui.timer.time.time', return_value=1000):
            timer.set(10)  # First set
            timer.set(20)  # Overwrite
            
            # 20 minutes = 1200 seconds
            expected_end = 1000 + 1200
            assert timer.end_time == expected_end


class TestSleepTimerCancel:
    """Tests for SleepTimer.cancel method."""

    def test_cancels_timer(self):
        """Should set end_time to None."""
        timer = SleepTimer(end_time=1000)
        timer.cancel()
        
        assert timer.end_time is None

    def test_cancel_when_already_cancelled(self):
        """Should not error when already cancelled."""
        timer = SleepTimer()
        timer.cancel()  # Already None
        
        assert timer.end_time is None


class TestSleepTimerGetRemainingSeconds:
    """Tests for SleepTimer.get_remaining_seconds method."""

    def test_returns_zero_when_inactive(self):
        """Should return 0 when timer is not set."""
        timer = SleepTimer()
        assert timer.get_remaining_seconds() == 0

    def test_returns_remaining_time(self):
        """Should return remaining seconds."""
        timer = SleepTimer(end_time=1100)
        
        with patch('somafm_tui.timer.time.time', return_value=1050):
            remaining = timer.get_remaining_seconds()
            assert remaining == 50

    def test_returns_zero_when_expired(self):
        """Should return 0 when timer has expired."""
        timer = SleepTimer(end_time=1000)
        
        with patch('somafm_tui.timer.time.time', return_value=1100):
            remaining = timer.get_remaining_seconds()
            assert remaining == 0

    def test_never_returns_negative(self):
        """Should never return negative values."""
        timer = SleepTimer(end_time=1000)
        
        # Time is 200 seconds after end
        with patch('somafm_tui.timer.time.time', return_value=1200):
            remaining = timer.get_remaining_seconds()
            assert remaining >= 0


class TestSleepTimerIsActive:
    """Tests for SleepTimer.is_active method."""

    def test_inactive_when_end_time_none(self):
        """Should be inactive when end_time is None."""
        timer = SleepTimer()
        assert timer.is_active() is False

    def test_active_when_end_time_in_future(self):
        """Should be active when end_time is in future."""
        timer = SleepTimer(end_time=1100)
        
        with patch('somafm_tui.timer.time.time', return_value=1000):
            assert timer.is_active() is True

    def test_inactive_when_end_time_in_past(self):
        """Should be inactive when end_time is in past."""
        timer = SleepTimer(end_time=1000)
        
        with patch('somafm_tui.timer.time.time', return_value=1100):
            assert timer.is_active() is False

    def test_inactive_when_end_time_equals_current(self):
        """Should be inactive when end_time equals current time."""
        timer = SleepTimer(end_time=1000)
        
        with patch('somafm_tui.timer.time.time', return_value=1000):
            assert timer.is_active() is False


class TestSleepTimerFormatRemaining:
    """Tests for SleepTimer.format_remaining method."""

    def test_formats_as_mmss(self):
        """Should format as MM:SS."""
        timer = SleepTimer(end_time=1125)
        
        with patch('somafm_tui.timer.time.time', return_value=1000):
            # 125 seconds = 2 minutes 5 seconds
            formatted = timer.format_remaining()
            assert formatted == "02:05"

    def test_formats_zero_when_inactive(self):
        """Should format as 00:00 when inactive."""
        timer = SleepTimer()
        assert timer.format_remaining() == "00:00"

    def test_formats_zero_when_expired(self):
        """Should format as 00:00 when expired."""
        timer = SleepTimer(end_time=1000)
        
        with patch('somafm_tui.timer.time.time', return_value=1100):
            assert timer.format_remaining() == "00:00"

    def test_formats_single_digit_seconds(self):
        """Should pad single digit seconds."""
        timer = SleepTimer(end_time=1065)
        
        with patch('somafm_tui.timer.time.time', return_value=1000):
            # 65 seconds = 1 minute 5 seconds
            formatted = timer.format_remaining()
            assert formatted == "01:05"

    def test_formats_large_values(self):
        """Should handle large time values."""
        # 2 hours = 7200 seconds
        timer = SleepTimer(end_time=8200)
        
        with patch('somafm_tui.timer.time.time', return_value=1000):
            formatted = timer.format_remaining()
            assert formatted == "120:00"


class TestSleepTimerIntegration:
    """Integration tests for SleepTimer."""

    def test_full_lifecycle(self):
        """Test complete timer lifecycle."""
        timer = SleepTimer()
        
        # Initially inactive
        assert timer.is_active() is False
        assert timer.get_remaining_seconds() == 0
        assert timer.format_remaining() == "00:00"
        
        # Set timer with mocked time
        with patch('somafm_tui.timer.time.time', return_value=1000):
            timer.set(5)  # 5 minutes = 300 seconds
            # Check immediately after setting while still in mock
            assert timer.is_active() is True
            assert timer.get_remaining_seconds() == 300
            assert timer.format_remaining() == "05:00"
        
        # Time passes (3 minutes) - 180 seconds later
        with patch('somafm_tui.timer.time.time', return_value=1180):
            assert timer.is_active() is True
            assert timer.get_remaining_seconds() == 120
            assert timer.format_remaining() == "02:00"
        
        # Timer expires - 350 seconds after start
        with patch('somafm_tui.timer.time.time', return_value=1350):
            assert timer.is_active() is False
            assert timer.get_remaining_seconds() == 0
            assert timer.format_remaining() == "00:00"
        
        # Cancel
        timer.cancel()
        assert timer.end_time is None
        assert timer.is_active() is False
