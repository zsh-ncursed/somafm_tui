# SomaFM TUI Player

A console-based player for SomaFM internet radio with stream buffering support.
<img width="1646" height="1028" alt="somafm_tui" src="https://github.com/user-attachments/assets/f4c6fe1e-0db1-45e4-a4cb-2b408e800aec" />

## System Requirements

- Python 3.7 or higher
- MPV media player
- pip (Python package manager)
- Terminal with UTF-8 support

## Features

- **Unified Interface**: Combined channel list and playback in split-screen layout
- **Multiple Color Themes**: 21 built-in themes (5 light, 16 dark) with alternative background mode
- **Automatic Channel Retrieval**: Fetches latest SomaFM channel list
- **Intuitive Navigation**: Vim-style keys (hjkl) and arrow key support
- **Stream Buffering**: Stable playback with configurable buffering
- **Volume Control**: Adjustable volume with visual indicator (PageUp/PageDown keys)
- **Track History**: Real-time metadata and playback history
- **Favorites System**: Save favorite tracks and channels
- **Responsive Design**: Adaptive interface that works on various screen sizes
- **Configuration Management**: Persistent settings and theme preferences
- **Error Logging**: Comprehensive logging for troubleshooting

## Installation

### For Arch Linux Users

You can install SomaFM TUI directly from the AUR (Arch User Repository):

```bash
# Using yay
yay -S somafm_tui

# Using paru
paru -S somafm_tui

# Manual installation from Github
git clone https://aur.archlinux.org/somafm_tui.git
cd somafm_tui
makepkg -si
```

### Manual Installation

#### 1. Install System Dependencies

#### For Arch Linux:
```bash
sudo pacman -S mpv python python-pip
```

#### For Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install mpv libmpv-dev python3 python3-pip
```

#### For Fedora:
```bash
sudo dnf install mpv python3 python3-pip
```

### 2. Clone the Repository
```bash
git clone https://github.com/zsh-ncursed/somafm_tui.git
cd somafm_tui
```

### 3. Create and Activate Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the Application
```bash
python somafm.py
```

## Configuration

The application uses a configuration file located at `~/.somafm_tui/somafm.cfg` with the following settings:

- `buffer_minutes`: Duration of audio buffering in minutes
- `buffer_size_mb`: Maximum size of buffer in megabytes
- `theme`: Color theme for the interface
- `alternative_bg_mode`: Use pure black background instead of dark gray (true/false)
- `dbus_allowed`: Allow D-Bus communication (true/false)
- `dbus_send_metadata`: Send metadata over D-Bus (true/false)
- `dbus_send_metadata_artworks`: Send metadata artworks over D-Bus (true/false)
- `dbus_cache_metadata_artworks`: Cache metadata artworks locally (true/false)

Default values:
```
buffer_minutes: 5
buffer_size_mb: 50
theme: default
alternative_bg_mode: false
dbus_allowed: false
dbus_send_metadata: false
dbus_send_metadata_artworks: false
dbus_cache_metadata_artworks: true
```

### Available Themes

The application supports 21 color themes that can be switched using the `t` key:

**Light Themes (5):**
- `one-light`, `github-light`, `solarized-light`, `ayu-light`, `material-light`

**Dark Themes (16):**
- `one-dark`, `dracula`, `tokyo-night`, `monokai`, `gruvbox`, `ayu-dark`, `solarized-dark`, `github-dark`, `monochrome-dark`, `nord`, `night-owl`, `catppuccin`, `cobalt`, `zenburn`, `ayu-mirage`, `default`

### Alternative Background Mode

All themes support an alternative background mode that can be toggled with the `a` key:
- **Normal mode**: Dark themes use dark gray background (color 10)
- **Alternative mode**: All themes use pure black background (color 0)

This allows you to customize the background intensity of any theme to match your terminal preferences.

Themes are designed to work well across different terminal emulators and their color interpretations.

## Usage

### Basic Controls
- **↑/↓ or j/k**: Navigate through channels
- **/**: Search field channel
- **Enter or l**: Play selected channel
- **Space**: Pause/Resume playback
- **h**: Stop playback
- **f**: Add current track to favorites (or toggle channel favorite)
- **t**: Cycle through color themes
- **a**: Toggle alternative background mode (pure black vs dark gray)
- **PageUp**: Increase volume
- **PageDown**: Decrease volume
- **q**: Quit application

### Files and Directories

- Configuration: `~/.somafm_tui/somafm.cfg`
- Favorites: `~/.somafm_tui/favorites.list`
- Temporary files: `/tmp/.somafmtmp/`
- Logs: `/tmp/.somafmtmp/somafm.log`
- Cached images: `/tmp/.somafmtmp/cache/artworks`

### Volume Control

Volume can be adjusted using **PageUp** (increase) and **PageDown** (decrease) keys. A visual volume indicator appears at the top-right corner showing the current volume level and automatically disappears after 3 seconds of inactivity.

### Error Handling

- In case of errors, logs are preserved at `/tmp/.somafmtmp/somafm.log`
- Temporary files are automatically cleaned up on normal exit
- Logs are retained if application crashes for debugging

## Troubleshooting

### Common Issues

1. **MPV not found**
   - Install MPV using your package manager
   - Verify MPV is in system PATH

2. **Playback Issues**
   - Check internet connection
   - Verify audio system is working
   - Check logs for detailed error messages

3. **Buffer Issues**
   - Ensure sufficient disk space in /tmp
   - Adjust buffer settings in configuration file

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Version
Current version: 0.3.2

### Changelog

#### Version 0.3.2
- **Fixed Volume Indicator**: Volume indicator now properly hides after 3 seconds of inactivity
- **Improved Screen Refresh Logic**: Optimized display refresh to avoid flickering while maintaining responsiveness
- **Initial Display Fix**: Interface now displays immediately on startup without requiring key press
- **Volume Control Documentation**: Updated documentation to reflect volume control functionality

#### Version 0.3.1
- **Updated Color Themes**: Expanded from 20 to 21 built-in color schemes (5 light, 16 dark)
- **New Light Themes**: Added material-light theme
- **New Dark Themes**: Added nord, night-owl, catppuccin, cobalt, zenburn, ayu-mirage themes
- **Theme Restructuring**: Refined theme selection to meet specific requirements (5 light + 16 dark themes)
- **Documentation Update**: Updated README with accurate theme list and counts

#### Version 0.3.0
- **Resolve problem with playback**: When channel start to play pause = false
- **Search chanel**: Press '/' to open channel search field

#### Version 0.2.4
- **Alternative Background Mode**: Press 'a' to toggle between normal (dark gray) and alternative (pure black) background
- **Universal Background Control**: All themes now support both background modes instead of separate alternative theme
- **Persistent Settings**: Alternative background mode preference is now saved in configuration file
- **Improved UX**: Better theme switching experience with background mode indicators
- **Enhanced Notifications**: Theme notifications now show current background mode status

#### Version 0.2.3
- **Color Themes**: Expanded from 6 to 20 built-in color schemes (5 light, 15 dark).
- **Theme Switching**: Press 't' key to cycle through available themes
- **Theme Persistence**: Selected theme is saved in configuration file
- **Terminal Compatibility**: Themes designed to work well across different terminal emulators

#### Version 0.2.2
- **New Combined Interface**: Unified channel list and playback into a single screen
- **Split Layout**: Channels on the left (fixed 30 chars width), playback info on the right
- **Improved Controls**: Added 'h' key to stop playback while staying in the interface
- **Color Themes**: 6 built-in themes (default, light, matrix, ocean, sunset, monochrome)
- **Theme Switching**: Press 't' to cycle through themes during runtime
- **Adaptive Footer**: Instructions automatically stack when screen width is reduced
- **Better Responsiveness**: Fixed width left panel, responsive right panel
- **Visual Improvements**: Eliminated screen gaps and improved fullscreen display

## Favorites Feature

On the playback screen, press `f` to add the current track to favorites. The first entry creates the file `~/.somafm_tui/favorites.list`. Format: Artist - Title (date-time).

---
