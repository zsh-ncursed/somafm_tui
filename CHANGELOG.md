# Changelog

All notable changes to SomaFM TUI Player will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.2] - 2026-03-16

### Added
- **Reverse theme cycling** — New keyboard shortcut for theme navigation:
  - Press `y` to cycle themes in reverse order
  - Press `t` to cycle themes forward (existing)
  - Updated help screen to show `t/y - Cycle theme (forward/back)`

- **Dynamic theme reloading** — Themes now reload from `themes.json` without restart:
  - Modified `themes.py` with `reload_themes()` function
  - Colors update dynamically when switching themes
  - Added `_update_color()` for runtime color updates
  - Added `reset_theme_cache()` for debugging

- **Enhanced visibility for light themes** — Improved text visibility:
  - Removed `A_DIM` attribute from instructions on light themes
  - Instructions now use `A_BOLD` for better visibility
  - Statistics (listeners/bitrate) use `color_pair(3)` without `A_DIM`
  - "Select a channel" message uses `color_pair(5)` without `A_DIM`

- **Version display in help** — Help screen now shows application version:
  - Header displays "SomaFM TUI v{version} - Keyboard Shortcuts"
  - Version is pulled from `__init__.py`

### Changed
- **Theme color updates** — Improved default theme colors:
  - Default Dark: `instructions` changed from `#0000ff` to `#8888ff` (lighter blue)
  - One Light: `info` changed to match `instructions` color (`#cb2431`)

- **Help screen improvements** — Better theme navigation documentation:
  - Updated to show both `t` and `y` shortcuts
  - Added version number to header

### Fixed
- **Theme caching issue** — Themes now properly reload from JSON file
- **Visibility issues** — Text no longer uses `A_DIM` on light themes
- **Version mismatch** — Synchronized version numbers across all files

### Technical Changes
- **Module updates**:
  - `themes.py`: Added `reload_themes()`, `_update_color()`, `reset_theme_cache()`
  - `state.py`: Added `cycle_theme_reverse()` method
  - `input.py`: Added handling for `y` key
  - `ui.py`: Updated `_display_instructions()`, `_display_help()`, `_display_playback_panel()`
  - `player.py`: Simplified `init_colors()`, added `theme_name` to display call

## [0.6.1] - 2026-03-15

### Fixed
- **Version bump** — Updated version from 0.6.0 to 0.6.1
- **MPRIS memory leak** — Fixed daemon thread accumulation in artwork caching
- **HTTP client shutdown** — Added proper `shutdown_http()` call in cleanup
- **Error handling** — Improved exception handling in `fetch_channels_async`
- **URL validation** — Added basic URL validation in `get_stream_url_for_bitrate`
- **Magic numbers** — Replaced with named constants in `ui.py`
- **Search input validation** — Added length limit and character filtering
- **Type hints** — Added `get_executor()` method to `HttpClient`

### Changed
- **Dependencies** — Updated pyproject.toml version to 0.6.1
- **Code quality** — Improved error logging with exception types

## [0.6.0] - 2026-03-12

### Added
- **Dependency checking at startup** — Comprehensive dependency validation with helpful installation instructions:
  - Checks for `mpv`, `requests`, and `dbus_next` before importing
  - Provides distribution-specific installation commands (Arch, Ubuntu, Fedora, macOS)
  - Distinguishes between required and optional dependencies
  - Graceful degradation when optional dependencies are missing

- **Enhanced configuration validation** — Secure configuration handling:
  - Strict type checking with explicit conversion (no dynamic eval)
  - Range validation for numeric values (volume: 0-100)
  - Whitelist validation for theme names
  - String sanitization and length limits (prevents DoS)
  - Unknown configuration keys are ignored for security

- **Improved error handling** — Specific exception handling throughout the codebase:
  - Replaced bare `except Exception` with specific exception types
  - Better error messages for network, file I/O, and configuration errors
  - Proper logging of error context for debugging
  - Graceful fallback to defaults on configuration errors

- **Thread-safe HTTP client** — Singleton pattern with proper resource management:
  - Double-checked locking for thread-safe initialization
  - Module-level singleton with explicit lifecycle management
  - Thread-safe session and executor management
  - Proper cleanup on application shutdown

- **Bitrate utilities module** — Centralized bitrate handling:
  - New `bitrate_utils.py` with constants and helper functions
  - Eliminated code duplication in bitrate mapping
  - Consistent bitrate extraction from URLs and playlist filenames
  - Reusable utilities for future development

### Changed
- **Removed vertical separator line** — Clean UI without divider between channel list and playback panel:
  - Removed vertical line from `_full_redraw()` in `ui.py`
  - Updated instructions separator from `" | "` to `"  "` (double space)
  - Improved instruction area clearing to prevent artifacts

- **Signal handler memory leak fix** — Using `weakref` for signal handlers:
  - Signal handlers now use weak references to prevent reference cycles
  - Proper garbage collection of player instances
  - Safe handling when player is already garbage collected

- **Async channel fetching** — Using shared HTTP client executor:
  - `fetch_channels_async()` now uses singleton executor from `HttpClient`
  - Eliminates resource leak from creating executors without cleanup
  - Consistent resource management across the application

- **Dead code removal** — Removed unused functions and methods:
  - Removed `_supports_emoji()` (always returned False, never called)
  - Removed `_display_volume()` and `_clear_volume()` (replaced by `_draw_volume_indicator()`)
  - Removed `check_mpv()` (replaced by comprehensive `check_dependencies()`)

### Fixed
- **MPV dependency check** — Fixed false positive in dependency detection:
  - Corrected import name from `python-mpv` to `mpv` (package vs module name)
  - Display name shows `python-mpv` for clarity
  - Proper detection of system-installed MPV bindings

- **Configuration validation bypass** — Prevented potential security issues:
  - Explicit type conversion instead of `expected_type(value)`
  - Range validation for all numeric values
  - Whitelist validation prevents arbitrary theme injection

### Technical
- Modified `somafm_tui/player.py`:
  - Added `check_dependencies()` function with detailed error reporting
  - Removed `check_mpv()` function (redundant)
  - Updated signal handler to use `weakref.ref()`
  - Initialize allowed themes whitelist for security
  - Better exception handling in channel fetching

- Modified `somafm_tui/config.py`:
  - Added `CONFIG_VALIDATORS` with explicit constraints
  - Added `ALLOWED_THEMES` whitelist mechanism
  - Rewrote `validate_config()` with strict validation
  - Added `set_allowed_themes()` for runtime whitelist setup

- Modified `somafm_tui/http_client.py`:
  - Module-level singleton with `_http_client_lock`
  - Thread-safe `get_instance()` with double-checked locking
  - Thread-safe `reset_instance()` for testing
  - Per-instance lock for session initialization
  - Updated `shutdown_http()` to use `reset_instance()`

- Modified `somafm_tui/channels.py`:
  - `fetch_channels_async()` uses `HttpClient.get_instance()._executor`
  - Removed local `ThreadPoolExecutor` creation
  - Better exception handling with specific types

- Modified `somafm_tui/models.py`:
  - Import bitrate utilities from `bitrate_utils`
  - Use `extract_bitrate_from_url()` in `from_api_response()`
  - Use `extract_bitrate_from_playlist_filename()` in `get_available_bitrates()`
  - Use `map_label_to_bitrate_numbers()` in `get_stream_url_for_bitrate()`
  - Use `get_bitrate_sort_key()` for sorting

- New file `somafm_tui/bitrate_utils.py`:
  - Constants: `BITRATE_LABELS`, `BITRATE_NUM_TO_LABEL`, `LABEL_TO_BITRATE_NUM`, etc.
  - Functions: `extract_bitrate_from_url()`, `extract_bitrate_from_playlist_filename()`, `map_bitrate_number_to_label()`, etc.

- Modified `somafm_tui/ui.py`:
  - Removed vertical separator line from `_full_redraw()`
  - Changed instructions separator from `" | "` to `"  "`
  - Improved instruction area clearing with explicit spaces
  - Removed unused `_supports_emoji()`, `_display_volume()`, `_clear_volume()`

---

## [0.5.12] - 2026-03-11

### Fixed
- **Screen corruption on terminal resize** — Fixed text artifacts and corruption when resizing terminal window:
  - Replaced `addstr(" " * width)` with `move() + clrtoeol()` in all redraw methods
  - Fixed channel list, playback info, search prompt, instructions, and sleep timer display
  - Prevents text remnants when terminal width decreases

- **Ghost sleep timer overlay** — Sleep timer input overlay now properly disappears when pressing Esc:
  - Changed from `curses.newwin()` to drawing on main screen
  - Added automatic cleanup of overlay area when hidden
  - Cursor properly hidden after closing overlay

- **Ghost help overlay** — Help screen (?) now fully clears when pressing Esc or ?:
  - Changed from `curses.newwin()` to drawing on main screen
  - Added automatic cleanup of help area when hidden

### Performance
- **Improved UI responsiveness** — Reduced input lag from 100ms to 50ms (20 FPS):
  - Changed main loop sleep from `time.sleep(0.1)` to `time.sleep(0.05)`
  - More responsive keyboard input and navigation

- **Optimized sleep timer checks** — Reduced CPU usage:
  - Timer expiration check reduced from every cycle to every 10 seconds
  - Single `time.time()` call per main loop iteration (cached for all checks)

- **Removed forced full redraw** — Eliminated unnecessary 2-second full screen redraw:
  - Partial redraw with `clrtoeol()` is sufficient to prevent artifacts
  - ~2.5% reduction in CPU usage for redraw operations
  - Full redraw only on: channel changes, search mode, help overlay, cache invalidation

### Technical
- Modified `somafm_tui/ui.py`:
  - `_redraw_channel_list()` — Use `clrtoeol()` for line clearing
  - `_redraw_playback_info()` — Use `clrtoeol()` for area clearing
  - `_redraw_search_prompt()` — Use `clrtoeol()` for line clearing
  - `_display_channels_panel()` — Use `clrtoeol()` for all lines
  - `_display_playback_panel()` — Use `clrtoeol()` for all lines
  - `_display_instructions()` — Use `clrtoeol()` for instruction lines
  - `display_sleep_timer()` — Use `clrtoeol()` for timer area
  - `display_sleep_overlay()` — Draw on main screen instead of `newwin()`
  - `_display_help()` — Draw on main screen instead of `newwin()`
  - Removed `_full_redraw_interval` and forced redraw logic
  - Added `cache_invalidated` check for proper full redraw on resize/theme change

- Modified `somafm_tui/player.py`:
  - Reduced main loop sleep from 100ms to 50ms
  - Sleep timer check every 10 seconds instead of every cycle
  - Cache `time.time()` once per loop iteration
  - Added cleanup for sleep overlay area when hidden
  - Added cleanup for help overlay area when hidden
  - Proper cursor hide/show for sleep overlay

- Modified `somafm_tui/core/state.py`:
  - Simplified `hide_sleep_overlay()` (cleanup moved to `_display_interface()`)

---

### Added
- **New keyboard shortcuts** for favorites management:
  - `f` — Add current track to favorites (requires track metadata)
  - `Ctrl+F` — Toggle channel favorite status (heart icon in channel list)
- **3 new color themes**:
  - Everforest Dark — Nature-inspired dark theme
  - Kanagawa Dragon — Japanese-inspired dark theme
  - Snazzy — Popular Hyper terminal theme
- **Theme notification timeout** — Increased from 0.5s to 1.0s for better readability

### Changed
- **Color themes updated with official palettes** — All 24 themes now use authentic colors from original sources:
  - Dracula, Nord, One Dark/Light, Solarized Dark/Light
  - Gruvbox, Tokyo Night, Monokai Pro, GitHub Dark/Light
  - Ayu Dark/Mirage/Light, Catppuccin Mocha, Night Owl
  - Material Light, Cobalt, Zenburn, Everforest, Kanagawa, Snazzy
- **README.md** — Updated theme descriptions and keyboard shortcuts documentation

### Fixed
- **UI refresh for favorites** — Channel list now properly updates when toggling channel favorite status
- **Wrong channel favorite bug** — Fixed issue where favorite status was applied to wrong channel when scrolled
- **Channel panel redraw** — Fixed y-coordinate calculation in `_redraw_channel_list()`

### Technical
- Modified `somafm_tui/core/playback.py`:
  - Added `toggle_channel_favorite()` method for channel favorites
  - Refactored `toggle_favorite_track()` to only handle track favorites
  - Added `StateManager` dependency for correct channel index tracking
- Modified `somafm_tui/core/input.py`:
  - Separated `f` and `Ctrl+F` key handlers
  - Increased theme notification timeout to 1.0s
- Modified `somafm_tui/player.py`:
  - Updated component initialization order (StateManager before PlaybackController)
  - Added playback change callback for UI refresh
- Modified `somafm_tui/ui.py`:
  - Fixed `_redraw_channel_list()` y-coordinate calculation
- Modified `somafm_tui/themes.json`:
  - Updated all theme colors with official palettes
  - Added 3 new themes (24 total: 19 dark + 5 light)

---

## [0.5.10] - 2026-03-09

### Fixed
- **Curses rendering bugs** — Fixed text duplication/corruption issues during runtime:
  - Added line clearing before writing in `_display_channels_panel()` to prevent text remnants
  - Added line clearing in `_display_volume()` before rendering volume indicator
  - Added line clearing in `display_sleep_timer()` before rendering countdown timer
  - Fixed header line clearing in channels panel

- **Terminal resize handling** — Added proper `curses.KEY_RESIZE` handling:
  - Screen now clears and fully redraws when terminal is resized
  - Prevents display corruption when window size changes

### Technical
- Modified `somafm_tui/ui.py`: Added `stdscr.addstr()` with space-clearing before all text output
- Modified `somafm_tui/player.py`: Added KEY_RESIZE handling with `stdscr.clear()` in main loop
- Modified `somafm_tui/core/input.py`: Added KEY_RESIZE handler in `_handle_special_key()`

---

## [0.5.4] - 2026-03-07

### Fixed
- **GitHub Release workflow** — Fixed duplicate file upload issue in sigstore action

### Technical
- Finalized release process with proper versioning

---

## [0.5.3] - 2026-03-07

### Fixed
- **PyPI workflow trigger** — Changed to only publish on release (not on tag push) to prevent duplicate uploads

### Technical
- Updated .github/workflows/publish.yml to remove push: tags trigger
- AUR package still triggers on both push: tags and release

---

## [0.5.2] - 2026-03-07

### Fixed
- **Version bump** — Updated pyproject.toml version to 0.5.2 for PyPI release

---

## [0.5.1] - 2026-03-07

### Fixed
- **AUR package resource paths** — Fixed `themes.json` installation path in PKGBUILD:
  - Changed from `/usr/lib/somafm_tui/themes.json` to `/usr/lib/somafm_tui/somafm_tui/themes.json`
  - Themes now work correctly in system-installed package
- **PyPI package data** — Added `themes.json` to `pyproject.toml` package-data for proper inclusion in wheel

### Technical
- Updated `PKGBUILD` to install resource files to correct directory
- Updated `pyproject.toml` with `[tool.setuptools.package-data]`
- Added documentation: `docs/solutions/packaging/resource-paths.md`
- Added critical patterns documentation: `docs/solutions/patterns/critical-patterns.md`

---

## [0.5.0] - 2026-03-06

### Added
- **CLI arguments** — Full command-line interface with 10+ options:
  - `--play`, `--volume`, `--theme` for quick launch
  - `--list-channels`, `--search`, `--favorites` for information
  - `--sleep` timer (1-480 minutes)
  - `--list-themes`, `--no-dbus`, `--verbose`
- **Async HTTP requests** — Non-blocking channel loading with ThreadPoolExecutor
- **Smart UI redraw** — Hash-based change detection for 6-20x performance improvement
- **Help key (?)** — Toggle help window in interactive mode
- **Theme sorting** — Dark themes first, light themes last

### Changed
- **Architecture refactoring** — Split monolithic `player.py` (739 lines) into modular components:
  - `PlaybackController` — Audio playback management (289 lines)
  - `StateManager` — Application state management (396 lines)
  - `InputHandler` — User input handling (230 lines)
  - `SomaFMPlayer` — Orchestration only (566 lines, -23%)
- **Removed global variables** — HttpClient singleton and closure-based signal handlers
- **Enhanced documentation** — README.md expanded by 50% with installation, configuration, and troubleshooting

### Fixed
- **somafm.fish path** — Corrected path to `__main__.py`
- **Theme switching** — Force full redraw when theme changes
- **Sleep timer validation** — Maximum 480 minutes (8 hours)

### Technical
- New files: `somafm_tui/cli.py`, `somafm_tui/core/__init__.py`, `somafm_tui/core/playback.py`, `somafm_tui/core/state.py`, `somafm_tui/core/input.py`
- Updated: `somafm_tui/http_client.py` (async support), `somafm_tui/ui.py` (smart redraw), `somafm_tui/player.py` (orchestration)
- PKGBUILD updated to include new core module files

---

## [0.4.5] - 2026-03-04

### Fixed
- Sync .SRCINFO version with PKGBUILD (v0.4.5)
- GitHub Actions workflow consistency

---

## [0.4.4] - 2026-03-03

### Added
- Comprehensive documentation for GitHub release
- README.md with full feature list and installation guide
- CHANGELOG.md following Keep a Changelog format
- Updated CONTRIBUTING.md with development guidelines

### Changed
- Updated email contact to zsh.ncursed@gmail.com
- Improved AUR installation instructions

### Fixed
- Documentation consistency and formatting
- Remove unused StreamBuffer module (SomaFM supports live streams only)
- Clean up buffer-related code from mpris_service.py and models.py

---

## [0.4.0] - 2024-03-01

### Added
- Sleep timer with overlay input
- Bitrate cycling for channels with multiple stream qualities
- Channel sorting by usage history (most recently listened first)
- Search functionality for channels by name and description
- Multiple color themes (10+ dark and light themes)
- MPRIS/D-Bus integration for Linux media keys control
- Volume display overlay when adjusting volume
- Help overlay with keyboard shortcuts

### Changed
- Improved channel navigation with adaptive panel width
- Enhanced metadata display with artist/title parsing
- Better error handling for network failures
- Optimized HTTP client with connection pooling and retry logic

### Fixed
- MPRIS metadata property updates
- Signal handling for graceful shutdown (SIGINT/SIGTERM)
- UI rendering issues in small terminals
- Volume control persistence across sessions

---

## [0.3.0] - 2024-01-15

### Added
- Favorite channels feature with local persistence
- Track metadata display (artist and title)
- Volume control with mute toggle
- Play/pause functionality
- Channel caching for offline resilience

### Changed
- Refactored UI rendering for better performance
- Improved MPV integration
- Enhanced configuration management

### Fixed
- Memory leaks in channel fetching
- Race conditions in metadata updates
- Terminal compatibility issues

---

## [0.2.0] - 2023-11-20

### Added
- Basic channel list display
- Stream playback via MPV
- Simple navigation (up/down/enter)
- Configuration file support

### Changed
- Improved error messages
- Initial AUR package release

---

## [0.1.0] - 2023-10-01

### Added
- Initial release
- Basic TUI interface
- SomaFM API integration
- Channel streaming

---

## Version History Summary

| Version | Release Date | Key Features |
|---------|-------------|--------------|
| 0.5.4 | 2026-03-07 | GitHub Release workflow fix |
| 0.5.3 | 2026-03-07 | PyPI workflow trigger fix |
| 0.5.2 | 2026-03-07 | Version bump for PyPI |
| 0.5.1 | 2026-03-07 | Resource paths fix (AUR & PyPI) |
| 0.5.0 | 2026-03-06 | CLI arguments, async HTTP, smart UI redraw |
| 0.4.4 | 2026-03-03 | Documentation update, AUR instructions |
| 0.4.0 | 2024-03-01 | Sleep timer, bitrate cycling, MPRIS, themes |
| 0.3.0 | 2024-01-15 | Favorites, metadata, volume control |
| 0.2.0 | 2023-11-20 | Basic playback, AUR package |
| 0.1.0 | 2023-10-01 | Initial release |

---

## Contributing

When contributing to this project, please:
1. Update this changelog with your changes
2. Follow the established format
3. Include the date of release
4. Categorize changes (Added, Changed, Deprecated, Removed, Fixed, Security)

## Contact

- **GitHub**: [zsh-ncursed/somafm_tui](https://github.com/zsh-ncursed/somafm_tui)
- **AUR**: [somafm_tui](https://aur.archlinux.org/packages/somafm_tui)
- **Email**: zsh.ncursed@gmail.com
