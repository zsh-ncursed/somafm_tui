# Changelog

All notable changes to SomaFM TUI Player will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
