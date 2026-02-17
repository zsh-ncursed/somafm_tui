"""Application configuration module"""

import configparser
import os
from typing import Any, Dict, Optional

HOME = os.path.expanduser("~")
CONFIG_DIR = os.path.join(HOME, ".somafm_tui")
CONFIG_FILE = os.path.join(CONFIG_DIR, "somafm.cfg")

# Default configuration
DEFAULT_CONFIG: Dict[str, Any] = {
    "theme": "default",
    "dbus_allowed": False,
    "dbus_send_metadata": False,
    "dbus_send_metadata_artworks": False,
    "dbus_cache_metadata_artworks": True,
    "volume": 100,
}

# Type mapping for config values
CONFIG_TYPES = {
    "theme": str,
    "dbus_allowed": bool,
    "dbus_send_metadata": bool,
    "dbus_send_metadata_artworks": bool,
    "dbus_cache_metadata_artworks": bool,
    "volume": int,
}

# Comments for each config option
CONFIG_COMMENTS = {
    "theme": "Color theme",
    "dbus_allowed": "Enable MPRIS/D-Bus support for media keys (true/false)",
    "dbus_send_metadata": "Send channel metadata over D-Bus (true/false)",
    "dbus_send_metadata_artworks": "Send channel picture with metadata over D-Bus (true/false)",
    "dbus_cache_metadata_artworks": "Cache channel picture locally for D-Bus (true/false)",
    "volume": "Default volume (0-100)",
}


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

    except Exception:
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
    """Validate configuration values."""
    validated = get_default_config()

    for key, default_value in DEFAULT_CONFIG.items():
        if key in config:
            value = config[key]
            expected_type = CONFIG_TYPES.get(key, type(default_value))

            try:
                # Validate type
                if expected_type == bool and isinstance(value, str):
                    value = value.lower() in ("true", "1", "yes", "on")

                validated[key] = expected_type(value)
            except (ValueError, TypeError):
                validated[key] = default_value

    # Additional validation
    validated["volume"] = max(0, min(100, validated["volume"]))

    return validated
