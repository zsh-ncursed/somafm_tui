"""Tests for player module (SomaFMPlayer)."""

import pytest
from unittest.mock import Mock, patch, call
import signal

from somafm_tui.player import (
    ensure_directories,
    setup_logging,
    _create_signal_handler,
)


class TestEnsureDirectories:
    """Tests for ensure_directories function."""

    def test_ensure_directories(self):
        """Should create required directories."""
        with patch('os.makedirs') as mock_makedirs:
            ensure_directories()

            assert mock_makedirs.call_count >= 2


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging(self):
        """Should configure logging."""
        with patch('os.makedirs'), \
             patch('logging.basicConfig') as mock_config:

            setup_logging()

            mock_config.assert_called_once()


class TestCreateSignalHandler:
    """Tests for _create_signal_handler function."""

    def test_create_signal_handler(self):
        """Should create signal handler."""
        player = Mock()
        player.running = True

        handler = _create_signal_handler(player)

        assert callable(handler)

    def test_signal_handler_sets_flags(self):
        """Should set signal flags on handler call."""
        player = Mock()
        player.running = True
        player._signal_received = False

        handler = _create_signal_handler(player)
        handler(signal.SIGTERM, None)

        assert player._signal_received is True
        assert player.running is False

    def test_signal_handler_with_garbage_collected_player(self):
        """Should handle garbage collected player."""
        player = Mock()
        player.running = True

        handler = _create_signal_handler(player)
        del player  # Simulate garbage collection

        # Should not raise
        handler(signal.SIGTERM, None)


# Note: SomaFMPlayer and main() tests are skipped because they require
# extensive mocking of curses, mpv, and other system dependencies.
# These are tested indirectly through integration tests.
