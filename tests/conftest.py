"""Pytest fixtures for SomaFM TUI tests."""

import pytest
from unittest.mock import Mock, patch
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_channel_data():
    """Sample channel data from SomaFM API."""
    return {
        "id": "dronezone",
        "title": "Drone Zone",
        "description": "Served best chilled, a space music experience",
        "playlists": [
            {
                "format": "mp3",
                "url": "https://somafm.com/dronezone130.pls",
            },
            {
                "format": "aac",
                "url": "https://somafm.com/dronezone64.pls",
            },
            {
                "format": "mp3",
                "url": "https://somafm.com/dronezone320.pls",
            },
        ],
        "listeners": "1234",
        "lastPlaying": "Last track",
        "image": "https://somafm.com/i/dronezone.jpg",
        "largeimage": "https://somafm.com/i/dronezone-large.jpg",
    }


@pytest.fixture
def sample_config_dict():
    """Sample configuration dictionary."""
    return {
        "theme": "default",
        "dbus_allowed": False,
        "dbus_send_metadata": False,
        "dbus_send_metadata_artworks": False,
        "dbus_cache_metadata_artworks": True,
        "volume": 75,
    }


@pytest.fixture
def sample_track_metadata():
    """Sample track metadata."""
    return {
        "artist": "Artist Name",
        "title": "Track Title",
        "duration": "3:45",
        "timestamp": "2024-01-01T12:00:00Z",
    }


@pytest.fixture
def mock_curses():
    """Mock curses module for testing without terminal."""
    with patch.dict('sys.modules', {
        'curses': Mock(),
    }) as mock:
        # Setup common curses constants
        mock_curses = mock['curses']
        mock_curses.COLOR_BLACK = 0
        mock_curses.COLOR_WHITE = 1
        mock_curses.COLOR_RED = 2
        mock_curses.COLOR_GREEN = 3
        mock_curses.COLOR_YELLOW = 4
        mock_curses.COLOR_BLUE = 5
        mock_curses.COLOR_MAGENTA = 6
        mock_curses.COLOR_CYAN = 7
        mock_curses.init_pair = Mock()
        mock_curses.init_color = Mock()
        mock_curses.error = Exception
        yield mock_curses


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file."""
    config_dir = tmp_path / ".somafm_tui"
    config_dir.mkdir()
    config_file = config_dir / "somafm.cfg"
    
    config_content = """# Configuration file for SomaFM TUI Player
#
# theme: Color theme
# dbus_allowed: Enable MPRIS/D-Bus support for media keys (true/false)
# dbus_send_metadata: Send channel metadata over D-Bus (true/false)
# dbus_send_metadata_artworks: Send channel picture with metadata over D-Bus (true/false)
# dbus_cache_metadata_artworks: Cache channel picture locally for D-Bus (true/false)
# volume: Default volume (0-100)
#
[somafm]
theme = monochrome
volume = 50
dbus_allowed = true
"""
    config_file.write_text(config_content)
    
    return str(config_file)


@pytest.fixture
def mock_requests():
    """Mock requests module to prevent network calls."""
    with patch('requests.get') as mock_get:
        yield mock_get
