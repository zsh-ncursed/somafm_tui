"""Application configuration module"""

import configparser
import logging
import os
from typing import Any, Dict, Optional, Set

HOME = os.path.expanduser("~")
# Use XDG Base Directory specification for Linux compliance
XDG_CONFIG_HOME = os.environ.get("XDG_CONFIG_HOME", os.path.join(HOME, ".config"))
CONFIG_DIR = os.path.join(XDG_CONFIG_HOME, "somafm_tui")
CONFIG_FILE = os.path.join(CONFIG_DIR, "somafm.cfg")

# Default configuration
DEFAULT_CONFIG: Dict[str, Any] = {
    "theme": "default",
    "dbus_allowed": False,
    "dbus_send_metadata": False,
    "dbus_send_metadata_artworks": False,
    "dbus_cache_metadata_artworks": True,
    "volume": 100,
    "show_only_favorites": False,
    "show_footer": True,
}

# Type mapping for config values
CONFIG_TYPES = {
    "theme": str,
    "dbus_allowed": bool,
    "dbus_send_metadata": bool,
    "dbus_send_metadata_artworks": bool,
    "dbus_cache_metadata_artworks": bool,
    "volume": int,
    "show_only_favorites": bool,
    "show_footer": bool,
}

# Comments for each config option
CONFIG_COMMENTS = {
    "theme": "Color theme",
    "dbus_allowed": "Enable MPRIS/D-Bus support for media keys (true/false)",
    "dbus_send_metadata": "Send channel metadata over D-Bus (true/false)",
    "dbus_send_metadata_artworks": "Send channel picture with metadata over D-Bus (true/false)",
    "dbus_cache_metadata_artworks": "Cache channel picture locally for D-Bus (true/false)",
    "volume": "Default volume (0-100)",
    "show_only_favorites": "Show only favorite channels (true/false)",
    "show_footer": "Show footer instructions (true/false)",
}

# Validation constraints for configuration values
CONFIG_VALIDATORS = {
    "volume": {
        "type": int,
        "min": 0,
        "max": 100,
        "default": 100,
    },
    "theme": {
        "type": str,
        "default": "default",
    },
    "dbus_allowed": {
        "type": bool,
        "default": False,
    },
    "dbus_send_metadata": {
        "type": bool,
        "default": False,
    },
    "dbus_send_metadata_artworks": {
        "type": bool,
        "default": False,
    },
    "dbus_cache_metadata_artworks": {
        "type": bool,
        "default": True,
    },
    "show_only_favorites": {
        "type": bool,
        "default": False,
    },
    "show_footer": {
        "type": bool,
        "default": True,
    },
}

# Allowed themes whitelist (loaded dynamically from themes.json)
# This is set at runtime to prevent arbitrary theme names
ALLOWED_THEMES: Optional[Set[str]] = None


def set_allowed_themes(themes: Set[str]) -> None:
    """Set allowed themes whitelist.

    Call this after loading themes to restrict theme configuration values.

    Args:
        themes: Set of allowed theme names
    """
    global ALLOWED_THEMES
    ALLOWED_THEMES = themes


def get_default_config() -> Dict[str, Any]:
    """Returns a copy of the default configuration."""
    return DEFAULT_CONFIG.copy()


def ensure_config_dir() -> None:
    """Create the configuration directory if it doesn't exist."""
    os.makedirs(CONFIG_DIR, exist_ok=True)


def load_config() -> Dict[str, Any]:
    """Load configuration from file using configparser."""
    ensure_config_dir()

    # If config file doesn't exist, create with defaults
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return get_default_config()

    config = get_default_config()

    try:
        parser = configparser.ConfigParser()
        parser.read(CONFIG_FILE)

        if parser.has_section("somafm"):
            for key in CONFIG_TYPES:
                if parser.has_option("somafm", key):
                    raw_value = parser.get("somafm", key)
                    try:
                        # Handle boolean conversion
                        if CONFIG_TYPES[key] == bool:
                            config[key] = raw_value.lower() in ("true", "1", "yes", "on")
                        else:
                            config[key] = CONFIG_TYPES[key](raw_value)
                    except (ValueError, TypeError):
                        pass  # Keep default value

    except (configparser.Error, IOError, OSError) as e:
        logging.warning(f"Error reading config file: {e}")
        config = get_default_config()

    return config


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file using configparser."""
    ensure_config_dir()

    parser = configparser.ConfigParser()

    # Add comments as inline comments (configparser doesn't support comments well)
    parser.add_section("somafm")

    for key, value in config.items():
        if isinstance(value, bool):
            value = str(value).lower()
        parser.set("somafm", key, str(value))

    with open(CONFIG_FILE, "w") as f:
        f.write("# Configuration file for SomaFM TUI Player\n")
        f.write("#\n")
        for key, comment in CONFIG_COMMENTS.items():
            f.write(f"# {key}: {comment}\n")
        f.write("#\n")
        parser.write(f)


def update_config(key: str, value: Any, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Update a single configuration value and save."""
    if config is None:
        config = load_config()

    config[key] = value
    save_config(config)
    return config


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate configuration values with strict type checking and range validation.

    Security: Uses explicit type conversion instead of dynamic eval-like patterns.
    Validates ranges for numeric values and whitelists for string values.

    Args:
        config: Configuration dictionary to validate

    Returns:
        Validated configuration dictionary with safe values
    """
    validated = get_default_config()

    for key, default_value in DEFAULT_CONFIG.items():
        if key not in config:
            continue

        value = config[key]
        validator = CONFIG_VALIDATORS.get(key)

        if validator is None:
            # Unknown config key - skip for security
            continue

        try:
            # Safe boolean conversion
            if validator["type"] == bool:
                if isinstance(value, bool):
                    validated[key] = value
                elif isinstance(value, str):
                    validated[key] = value.lower() in ("true", "1", "yes", "on")
                elif isinstance(value, int):
                    validated[key] = value != 0
                else:
                    validated[key] = validator.get("default", default_value)

            # Safe integer conversion with range validation
            elif validator["type"] == int:
                if isinstance(value, int) and not isinstance(value, bool):
                    int_value = value
                elif isinstance(value, str):
                    int_value = int(value)
                else:
                    int_value = validator.get("default", default_value)

                # Range validation
                min_val = validator.get("min")
                max_val = validator.get("max")

                if min_val is not None and int_value < min_val:
                    int_value = min_val
                if max_val is not None and int_value > max_val:
                    int_value = max_val

                validated[key] = int_value

            # Safe string validation with optional whitelist
            elif validator["type"] == str:
                if isinstance(value, str):
                    # Sanitize string value (prevent injection attacks)
                    sanitized = value.strip()

                    # Check against whitelist if available
                    if key == "theme" and ALLOWED_THEMES is not None:
                        if sanitized not in ALLOWED_THEMES:
                            # Invalid theme - use default
                            validated[key] = validator.get("default", default_value)
                        else:
                            validated[key] = sanitized
                    else:
                        # Limit string length to prevent DoS
                        validated[key] = sanitized[:100]
                else:
                    validated[key] = str(value)

        except (ValueError, TypeError, AttributeError):
            # Invalid value - use default
            validated[key] = validator.get("default", default_value)

    return validated
