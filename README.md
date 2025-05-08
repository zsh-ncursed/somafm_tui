# SomaFM TUI Player

A console-based player for SomaFM internet radio with stream buffering support.

## System Requirements

- Python 3.7 or higher
- MPV media player
- pip (Python package manager)
- Terminal with UTF-8 support

## Features

- Automatic channel list retrieval from SomaFM
- Console interface with intuitive navigation
- Stream buffering for stable playback
- Track history display
- Real-time track metadata
- Automatic configuration management
- Error logging and recovery

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

Default values:
```
buffer_minutes: 5
buffer_size_mb: 50
```

## Usage

### Basic Controls
- ↑/↓: Navigate through channels
- Enter: Play selected channel
- Space: Pause/Resume playback
- q/ESC: Return to channel list or exit

### Files and Directories

- Configuration: `~/.somafm_tui/somafm.cfg`
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
Current version: 0.2.0

--- 
