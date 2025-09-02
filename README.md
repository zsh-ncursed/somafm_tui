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
- **Multiple Color Themes**: 7 built-in themes optimized for different terminals
- **Automatic Channel Retrieval**: Fetches latest SomaFM channel list
- **Intuitive Navigation**: Vim-style keys (hjkl) and arrow key support
- **Stream Buffering**: Stable playback with configurable buffering
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
sudo apt-get install mpv python3 python3-pip
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

Default values:
```
buffer_minutes: 5
buffer_size_mb: 50
theme: default
```

### Available Themes

The application supports multiple color themes that can be switched using the `t` key:

- **default** - Default Dark theme with cyan/green colors
- **light** - Light theme with dark text on white background
- **matrix** - Matrix-style green-on-black theme
- **ocean** - Ocean blue theme with cyan accents
- **sunset** - Warm orange/red sunset theme
- **monochrome** - Simple black and white theme
- **alternative** - Alternative Dark theme (same colors as default but with pure black background)

Themes are designed to work well across different terminal emulators and their color interpretations.

## Usage

### Basic Controls
- **↑/↓ or j/k**: Navigate through channels
- **Enter or l**: Play selected channel
- **Space**: Pause/Resume playback
- **h**: Stop playback
- **f**: Add current track to favorites (or toggle channel favorite)
- **t**: Cycle through color themes
- **q**: Quit application

### Files and Directories

- Configuration: `~/.somafm_tui/somafm.cfg`
- Favorites: `~/.somafm_tui/favorites.list`
- Temporary files: `/tmp/.somafmtmp/`
- Logs: `/tmp/.somafmtmp/somafm.log`

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
Current version: 0.2.3

### Changelog

#### Version 0.2.3
- **Color Themes**: Added 7 built-in color themes (default, light, matrix, ocean, sunset, monochrome, alternative)
- **Alternative Theme**: New theme identical to Default Dark but with pure black background
- **Theme Switching**: Press 't' key to cycle through available themes
- **Theme Persistence**: Selected theme is saved in configuration file
- **Terminal Compatibility**: Themes designed to work well across different terminal emulators

#### Version 0.2.2
- **New Combined Interface**: Unified channel list and playback into a single screen
- **Split Layout**: Channels on the left (fixed 30 chars width), playback info on the right
- **Improved Controls**: Added 'h' key to stop playback while staying in the interface
- **Color Themes**: 7 built-in themes (default, light, matrix, ocean, sunset, monochrome, alternative)
- **Theme Switching**: Press 't' to cycle through themes during runtime
- **Adaptive Footer**: Instructions automatically stack when screen width is reduced
- **Better Responsiveness**: Fixed width left panel, responsive right panel
- **Visual Improvements**: Eliminated screen gaps and improved fullscreen display

## Favorites Feature

On the playback screen, press `f` to add the current track to favorites. The first entry creates the file `~/.somafm_tui/favorites.list`. Format: Artist - Title (date-time).

--- 
