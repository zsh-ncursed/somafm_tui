# Changelog

All notable changes to SomaFM TUI Player will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Listening history export feature
- Last.fm integration (scrobbling)
- Support for other streaming services
- GUI settings via ncurses dialogs

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
