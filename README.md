# SomaFM TUI

A terminal user interface (TUI) for SomaFM internet radio.

## Features

- Browse and play SomaFM radio channels
- Volume control with mute toggle
- Favorite channels (persisted locally)
- Multiple color themes (dark and light)
- Search channels by name
- MPRIS support (Linux media controls)
- System tray support
- Now playing track metadata display

## Requirements

- Python 3.8+
- MPV player
- Terminal with Unicode and 256-color support

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd somafm_tui

# Install dependencies
pip install mpv requests dbus-python

# Run the application
python -m somafm_tui
```

Or use the provided shell scripts:

```bash
# Fish shell
./somafm.fish

# Bash/Zsh
./somafm.sh
```

## Usage

### Keyboard Controls

| Key | Action |
|-----|--------|
| `Up/Down` or `j/k` | Navigate channels |
| `Enter` | Play selected channel |
| `Space` or `p` | Toggle play/pause |
| `+` / `-` | Adjust volume |
| `m` | Mute/unmute |
| `/` | Search channels |
| `Esc` | Clear search / exit |
| `f` | Toggle favorite |
| `t` | Cycle through themes |
| `q` | Quit |

## Configuration

Configuration is stored in `~/.config/somafm-tui/config`:

- Theme selection
- Volume level
- Favorite channels

## License

MIT License
