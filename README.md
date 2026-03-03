# SomaFM TUI Player

[![AUR Version](https://img.shields.io/aur/version/somafm_tui)](https://aur.archlinux.org/packages/somafm_tui)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

**SomaFM TUI Player** is a modern terminal application for listening to [SomaFM](https://somafm.com/) — the legendary internet radio with over 30 unique channels.

The app combines a minimalist interface, rich features, and low resource consumption, making it ideal for terminal-based workflows.

---

## 🌟 Features

### Core Features

- **📻 30+ Radio Channels** — Access all SomaFM channels directly from your terminal
- **🎵 Track Metadata** — Real-time display of artist and track title
- **❤️ Favorites** — Save favorite channels with local persistence
- **🎨 Color Themes** — 10+ built-in themes (dark and light)
- **🔊 Volume Control** — Adjust volume and mute toggle
- **⏱ Sleep Timer** — Auto-shutdown with configurable timer
- **🔍 Search** — Quick channel search by name and description
- **📊 Usage-Based Sorting** — Channels sorted by listening history

### System Integration

- **🎧 MPRIS/D-Bus** — Linux media keys integration (play/pause/next/previous)
- **🖥 System Tray** — System tray support (via compatible environments)
- **⌨️ Vim Navigation** — `j/k` key navigation for Vim users
- **📦 AUR Package** — Easy installation on Arch Linux via AUR

---

## 📦 Installation

### Arch Linux (Recommended)

Install from **AUR** (Arch User Repository):

```bash
paru -S somafm_tui
# or
yay -S somafm_tui
```

Manual installation from AUR:

```bash
git clone https://aur.archlinux.org/somafm_tui.git
cd somafm_tui
makepkg -si
```

After installation, run the app with:
```bash
somafm-tui
```

### Installation from Source

```bash
# Clone the repository
git clone https://github.com/zsh-ncursed/somafm_tui.git
cd somafm_tui

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m somafm_tui
```

### Shell Scripts

Quick launch using provided scripts:

```bash
# Fish shell
./somafm.fish

# Bash/Zsh
./somafm.sh
```

### Dependencies

- **Python 3.8+**
- **MPV** — Media player for stream playback
- **python-requests** — HTTP client for API requests
- **python-mpv** — MPV Python bindings
- **python-dbus-next** — D-Bus integration for MPRIS (optional)

#### Installing Dependencies on Different Distributions

**Arch Linux:**
```bash
sudo pacman -S python mpv python-requests python-mpv python-dbus-next
```

**Ubuntu/Debian:**
```bash
sudo apt-get install python3 python3-pip mpv libmpv-dev
pip install requests mpv dbus-next
```

**Fedora:**
```bash
sudo dnf install python3 python3-pip mpv mpv-libs
pip install requests mpv dbus-next
```

---

## ⌨️ Controls

### Navigation

| Key | Action |
|-----|--------|
| `↑` / `↓` or `j` / `k` | Navigate channel list |
| `Enter` or `l` | Play selected channel |
| `PgUp` / `PgDn` or `v` / `b` | Increase/decrease volume |
| `/` | Search channels |
| `Esc` | Exit search / close help |
| `f` | Toggle favorite status |
| `t` | Cycle through color themes |
| `q` | Quit application |

### Playback

| Key | Action |
|-----|--------|
| `Space` or `p` | Toggle play/pause |
| `m` | Mute/unmute audio |
| `h` | Stop playback |
| `r` | Cycle bitrate (if available) |
| `s` | Set sleep timer |

### MPRIS (Media Keys)

When D-Bus support is enabled (`dbus_allowed: true` in config), the app responds to system media keys:

- **Play/Pause** — Toggle playback
- **Next** — Next channel
- **Previous** — Previous channel
- **Stop** — Stop playback

---

## ⚙️ Configuration

### Config File

Configuration is stored in `~/.somafm_tui/somafm.cfg`

```ini
# Configuration file for SomaFM TUI Player
#
# theme: Color theme
# dbus_allowed: Enable MPRIS/D-Bus support for media keys (true/false)
# dbus_send_metadata: Send channel metadata over D-Bus (true/false)
# dbus_send_metadata_artworks: Send channel picture with metadata over D-Bus (true/false)
# dbus_cache_metadata_artworks: Cache channel picture locally for D-Bus (true/false)
# volume: Default volume (0-100)
#
[somafm]
theme = default
dbus_allowed = false
dbus_send_metadata = false
dbus_send_metadata_artworks = false
dbus_cache_metadata_artworks = true
volume = 100
```

### Available Themes

| Theme | Description |
|-------|-------------|
| `default` | Default Dark — Classic dark theme |
| `monochrome` | Monochrome — Black and white theme |
| `monochrome-dark` | Monochrome Dark — Alternative monochrome |
| *and more* | See `themes.json` for full list |

### Enabling MPRIS

For Linux media keys integration, set:

```ini
dbus_allowed = true
dbus_send_metadata = true
```

The app will then appear in media control systems (GNOME, KDE, etc.)

---

## 📁 Data Structure

### Directories

| Path | Purpose |
|------|---------|
| `~/.somafm_tui/somafm.cfg` | Configuration file |
| `~/.somafm_tui/channel_favorites.json` | Favorite channels |
| `~/.somafm_tui/channel_usage.json` | Listening history |
| `/tmp/.somafmtmp/` | Temporary files and cache |
| `/tmp/.somafmtmp/cache/` | Channel cache |

### Data Formats

**Favorites** (`channel_favorites.json`):
```json
["dronezone", "beatblender", "groovesalad"]
```

**History** (`channel_usage.json`):
```json
{
  "dronezone": 1709481600,
  "beatblender": 1709395200
}
```

---

## 🔧 Troubleshooting

### Error: "MPV player is not installed"

Ensure MPV is installed on your system:

```bash
# Check installation
mpv --version

# Install (Arch Linux)
sudo pacman -S mpv

# Install (Ubuntu/Debian)
sudo apt-get install mpv
```

### Error: "Failed to fetch channels"

Check your internet connection and SomaFM API availability:

```bash
curl https://api.somafm.com/channels.json
```

### Emojis Display Incorrectly

The app automatically uses ASCII symbols in terminals without Unicode support. To force ASCII, ensure `TERM` is set correctly:

```bash
export TERM=xterm-256color
```

### MPRIS Not Working

1. Ensure `dbus_allowed = true` in config
2. Verify `python-dbus-next` is installed:
   ```bash
   pip show dbus-next
   ```
3. Restart the application

---

## 📊 Screenshots

*(Add screenshots to the `docs/` folder)*

---

## 🤝 Contributing

We welcome contributions! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting pull requests.

### Reporting Bugs

- Check existing issues first
- Include app version (`somafm-tui --version` or from PKGBUILD)
- Attach logs from `/tmp/.somafmtmp/somafm.log`

### Feature Requests

- Describe the desired functionality
- Explain how it improves user experience

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- **[SomaFM](https://somafm.com/)** — For amazing radio and open API
- **python-mpv** — For excellent MPV Python bindings
- **dbus-next** — For modern D-Bus library for Python

---

## 📬 Contact

- **GitHub**: [zsh-ncursed/somafm_tui](https://github.com/zsh-ncursed/somafm_tui)
- **AUR**: [somafm_tui](https://aur.archlinux.org/packages/somafm_tui)
- **Email**: zsh.ncursed@gmail.com

---

## 🗺 Roadmap

- [ ] Listening history export
- [ ] Last.fm integration (scrobbling)
- [ ] Support for other streaming services
- [ ] GUI settings via ncurses dialogs

---

*Made with ❤️ for quality internet radio lovers*
