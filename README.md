---

# SomaFM TUI Player

A console-based player for SomaFM internet radio .

## Requirements

- Python 3.7+
- MPV (media player)
- pip (Python package manager)

## Installation

1. Install MPV:
```bash
# For Arch Linux
sudo pacman -S mpv

# For Ubuntu/Debian
sudo apt-get install mpv
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the application:
```bash
python somafm.py
```

2. Controls:
- Up/Down arrows: Navigate through the channel list
- Enter: Select a channel to play
- q: Exit the application

## Features

- Automatic retrieval of the channel list from SomaFM
- Console interface with navigation support
- Playback of the selected channel
- Graceful shutdown when exiting 

--- 
