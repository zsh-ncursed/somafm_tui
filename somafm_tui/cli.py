"""Command-line interface argument parsing module."""

import argparse
import sys
from typing import Optional, List


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for SomaFM TUI.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="somafm-tui",
        description="Terminal user interface for SomaFM internet radio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  somafm-tui                          # Launch interactive mode
  somafm-tui --play dronezone         # Play Drone Zone channel
  somafm-tui --volume 50              # Set volume to 50%
  somafm-tui --theme monochrome       # Use monochrome theme
  somafm-tui --list-channels          # List all available channels
  somafm-tui --search beat            # Search for channels with 'beat'
  somafm-tui --favorites              # Show favorite channels
  somafm-tui --sleep 30               # Set sleep timer for 30 minutes

Navigation (interactive mode):
  ↑/↓ or j/k    - Navigate channel list
  Enter or l    - Play selected channel
  Space         - Pause/Resume playback
  /             - Search channels
  f             - Toggle favorite
  t             - Cycle themes
  s             - Set sleep timer
  q             - Quit
        """,
    )

    # Playback arguments
    playback_group = parser.add_argument_group("Playback options")
    playback_group.add_argument(
        "--play", "-p",
        metavar="CHANNEL",
        help="Play specified channel by ID or name (e.g., 'dronezone', 'beatblender')",
    )
    playback_group.add_argument(
        "--volume", "-v",
        type=int,
        metavar="LEVEL",
        help="Set volume level (0-100)",
    )

    # Appearance arguments
    appearance_group = parser.add_argument_group("Appearance options")
    appearance_group.add_argument(
        "--theme", "-t",
        metavar="NAME",
        help="Set color theme (use --list-themes to see available)",
    )
    appearance_group.add_argument(
        "--list-themes",
        action="store_true",
        help="List available color themes and exit",
    )

    # Channel information
    info_group = parser.add_argument_group("Channel information")
    info_group.add_argument(
        "--list-channels", "-l",
        action="store_true",
        help="List all available channels and exit",
    )
    info_group.add_argument(
        "--search", "-s",
        metavar="QUERY",
        help="Search channels by name or description",
    )
    info_group.add_argument(
        "--favorites", "-f",
        action="store_true",
        help="Show favorite channels",
    )

    # Timer arguments
    timer_group = parser.add_argument_group("Timer options")
    timer_group.add_argument(
        "--sleep",
        type=int,
        metavar="MINUTES",
        help="Set sleep timer in minutes",
    )

    # Configuration arguments
    config_group = parser.add_argument_group("Configuration options")
    config_group.add_argument(
        "--config",
        metavar="FILE",
        help="Use alternative configuration file",
    )
    config_group.add_argument(
        "--no-dbus",
        action="store_true",
        help="Disable MPRIS/D-Bus integration",
    )

    # Utility arguments
    utility_group = parser.add_argument_group("Utility options")
    utility_group.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.6.0",
    )
    utility_group.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.
    
    Args:
        args: Arguments list (uses sys.argv if None)
        
    Returns:
        Parsed arguments namespace
    """
    parser = create_parser()
    return parser.parse_args(args)


def validate_args(args: argparse.Namespace) -> bool:
    """Validate parsed arguments.
    
    Args:
        args: Parsed arguments namespace
        
    Returns:
        True if arguments are valid, False otherwise
    """
    # Validate volume range
    if args.volume is not None:
        if args.volume < 0 or args.volume > 100:
            print(f"Error: Volume must be between 0 and 100, got {args.volume}", file=sys.stderr)
            return False
    
    # Validate sleep timer
    if args.sleep is not None:
        if args.sleep <= 0 or args.sleep > 480:
            print(f"Error: Sleep timer must be between 1 and 480 minutes (8 hours), got {args.sleep}", file=sys.stderr)
            return False
    
    return True


def print_channels(channels: list) -> None:
    """Print formatted channel list.
    
    Args:
        channels: List of Channel objects
    """
    print(f"\n{'ID':<20} {'Title':<30} {'Listeners':<10} {'Bitrate':<10}")
    print("-" * 70)
    
    for channel in channels:
        listeners = str(channel.listeners) if channel.listeners > 0 else "N/A"
        bitrate = channel.bitrate or "128k"
        print(f"{channel.id:<20} {channel.title:<30} {listeners:<10} {bitrate:<10}")
    
    print(f"\nTotal: {len(channels)} channels")


def print_favorites(channels: list, favorites: set) -> None:
    """Print favorite channels.
    
    Args:
        channels: List of all Channel objects
        favorites: Set of favorite channel IDs
    """
    fav_channels = [ch for ch in channels if ch.id in favorites]
    
    if not fav_channels:
        print("No favorite channels")
        return
    
    print("\nFavorite channels:")
    print("-" * 50)
    for channel in fav_channels:
        print(f"  • {channel.title} ({channel.id})")
    print()


def print_themes(themes: dict) -> None:
    """Print available themes, sorted: dark themes first, light themes last.

    Args:
        themes: Dictionary of theme names to theme info
    """
    from .themes import get_theme_names
    
    # Get sorted theme names (dark first, light last)
    sorted_names = get_theme_names()
    
    print("\nAvailable themes:")
    print("-" * 50)
    
    # Print dark themes first
    dark_themes = [n for n in sorted_names if not themes.get(n, {}).get("is_light", False)]
    if dark_themes:
        print("\nDark themes:")
        for name in dark_themes:
            description = themes.get(name, {}).get("name", name)
            print(f"  🌙 {name:<18} - {description}")
    
    # Print light themes last
    light_themes = [n for n in sorted_names if themes.get(n, {}).get("is_light", False)]
    if light_themes:
        print("\nLight themes:")
        for name in light_themes:
            description = themes.get(name, {}).get("name", name)
            print(f"  ☀️ {name:<18} - {description}")
    
    print()
