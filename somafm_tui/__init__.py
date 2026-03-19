"""SomaFM TUI Player - Internet Radio Player for SomaFM"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("somafm-tui")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"

__author__ = "zsh-ncursed"
__email__ = "zsh.ncursed@gmail.com"
__all__ = ["player", "config", "models", "channels", "ui", "themes", "mpris_service", "timer", "bitrate_utils", "__version__"]
