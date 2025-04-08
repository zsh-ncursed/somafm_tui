SomaFM Console Player A simple, lightweight console-based application for streaming SomaFM internet radio channels. Browse available stations using arrow keys, select your favorite channel, and enjoy real-time track information display. Perfect for users who prefer minimalistic tools without graphical interfaces.

---
# SomaFM TUI Player

A console-based player for SomaFM internet radio.

## System Requirements

- Python 3.7 or higher
- MPV media player
- pip (Python package manager)
- Terminal with UTF-8 support

## Installation

### 1. Install System Dependencies

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
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

### 4. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 5. Install the Application
```bash
pip install .
```

### 6. Run the Application
```bash
somafm
```

## Usage

### Basic Controls
- ↑/↓: Navigate through the channel list
- Enter: Select a channel to play
- Space: Pause/Resume playback
- q: Exit the application or return to channel list

### Features
- Automatic retrieval of the channel list from SomaFM
- Console interface with navigation support
- Playback of the selected channel
- Track history display
- Graceful shutdown when exiting

## Troubleshooting

### Common Issues

1. **MPV not found**
   - Make sure MPV is installed on your system
   - Check if MPV is in your system's PATH

2. **Python dependencies not found**
   - Ensure virtual environment is activated
   - Run `pip install -r requirements.txt` again

3. **Character encoding issues**
   - Ensure your terminal supports UTF-8
   - Set terminal encoding to UTF-8 if needed

4. **Audio playback issues**
   - Check if MPV can play audio files
   - Verify system audio settings
   - Check if required audio codecs are installed

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

--- 
