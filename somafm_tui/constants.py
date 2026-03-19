"""Application constants for SomaFM TUI Player.

Centralized constants to avoid magic numbers throughout the codebase.
"""

# =============================================================================
# Application Limits
# =============================================================================

# Sleep timer limits (in minutes)
MAX_SLEEP_TIMER_MINUTES = 480  # 8 hours maximum
MIN_SLEEP_TIMER_MINUTES = 1

# Search query limits
MAX_SEARCH_QUERY_LENGTH = 50

# Input validation
MAX_THEME_NAME_LENGTH = 100
MAX_CONFIG_VALUE_LENGTH = 100

# =============================================================================
# UI Constants
# =============================================================================

# Screen layout
CHANNEL_PANEL_MIN_WIDTH = 25
CHANNEL_PANEL_MAX_WIDTH = 40
CHANNEL_PANEL_WIDTH_FRACTION = 3  # max 1/3 of screen

# Panel dimensions
CHANNEL_PANEL_HEADER_HEIGHT = 3
INSTRUCTION_LINES = 2

# Volume indicator
VOLUME_BAR_WIDTH = 20
VOLUME_DISPLAY_TIMEOUT = 3  # seconds

# Color configuration
VOLUME_BAR_COLOR_PAIR = 60
VOLUME_ICON_COLOR_PAIR = 61
MIN_CURSES_COLOR_ID = 10
MAX_CURSES_COLOR_ID = 254

# =============================================================================
# Timing Constants
# =============================================================================

# Timer check intervals (in seconds)
TIMER_CHECK_INTERVAL = 10  # Check sleep timer every 10 seconds
TIMER_DISPLAY_UPDATE_INTERVAL = 1  # Update display every second

# Cache configuration
CHANNEL_CACHE_MAX_AGE = 3600  # 1 hour in seconds

# HTTP timeouts
HTTP_DEFAULT_TIMEOUT = 10  # seconds
HTTP_MAX_RETRIES = 3
HTTP_BACKOFF_FACTOR = 0.5
HTTP_MAX_WORKERS = 4

# Artwork caching
ARTWORKS_TIMEOUT = 10  # seconds
ARTWORK_MAX_WORKERS = 2  # Limited thread pool for artwork caching

# =============================================================================
# File Paths
# =============================================================================

# Temporary directories
TEMP_DIR = "/tmp/.somafmtmp"
CACHE_DIR = f"{TEMP_DIR}/cache"
ARTWORKS_DIR = f"{CACHE_DIR}/artworks"

# =============================================================================
# API Configuration
# =============================================================================

# SomaFM API
SOMAFM_API_URL = "https://api.somafm.com/channels.json"

# =============================================================================
# Sleep Timer Input Validation
# =============================================================================

# Maximum digits in sleep timer input
MAX_SLEEP_INPUT_DIGITS = 3

# First digit validation (1-4 only for values <= 480)
SLEEP_FIRST_DIGIT_MAX = 4

# Second digit validation (depends on first digit)
SLEEP_SECOND_DIGIT_AFTER_4_MAX = 8  # If first digit is 4, second can be 0-8

# =============================================================================
# Track History
# =============================================================================

# Maximum track history entries to display
MAX_TRACK_HISTORY_ENTRIES = 10

# =============================================================================
# Channel Configuration
# =============================================================================

# Default bitrate when not specified
DEFAULT_BITRATE = "128k"

# Bitrate format
BITRATE_FORMAT_MP3 = "mp3"
BITRATE_FORMAT_AAC = "aac"
BITRATE_FORMAT_AACP = "aacp"

# =============================================================================
# Configuration Defaults
# =============================================================================

# Default configuration values
DEFAULT_THEME = "default"
DEFAULT_VOLUME = 100
DEFAULT_DBUS_ALLOWED = False
DEFAULT_DBUS_SEND_METADATA = False
DEFAULT_DBUS_SEND_METADATA_ARTWORKS = False
DEFAULT_DBUS_CACHE_METADATA_ARTWORKS = True

# =============================================================================
# Error Messages
# =============================================================================

ERROR_MISSING_DEPENDENCIES = "Missing required dependencies"
ERROR_NETWORK_FETCH = "Cannot connect to SomaFM API. Check your internet connection."
ERROR_PROCESSING_DATA = "Failed to process channel data."
ERROR_INVALID_CHANNEL_DATA = "Invalid channel data."
ERROR_NO_CHANNEL_PLAYING = "No channel playing"
ERROR_NO_METADATA_AVAILABLE = "No track metadata available"

# =============================================================================
# Success Messages
# =============================================================================

SUCCESS_ADDED_TO_FAVORITES = "Added to favorites"
SUCCESS_REMOVED_FROM_FAVORITES = "Removed from favorites"
SUCCESS_TIMER_SET = "Sleep timer: {} min"

# =============================================================================
# Help and Instructions
# =============================================================================

# Help overlay dimensions
HELP_OVERLAY_WIDTH = 50
HELP_OVERLAY_HEIGHT = 32

# Instruction items
INSTRUCTION_ITEMS = [
    "↑↓/jk - select",
    "Enter/l - play",
    "/ - search",
    "Space - pause",
    "h - stop",
    "f - favorite",
    "r - bitrate",
    "s - sleep",
    "t/y - theme",
    "PgUp/Dn - volume",
    "q - quit",
]

# =============================================================================
# Version
# =============================================================================

# Version is now dynamic, retrieved from package metadata
# See somafm_tui/__init__.py for version retrieval logic
