#!/usr/bin/env python3
import os
import curses
import mpv
import requests
import json
import sys
import time
import logging
from typing import List, Dict
from datetime import datetime
from stream_buffer import StreamBuffer

# Setup paths
HOME = os.path.expanduser("~")
CONFIG_DIR = os.path.join(HOME, ".somafm_tui")
CONFIG_FILE = os.path.join(CONFIG_DIR, "somafm.cfg")
TEMP_DIR = "/tmp/.somafmtmp"
CACHE_DIR = os.path.join(TEMP_DIR, "cache")

# Create necessary directories
os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# Logging setup
logging.basicConfig(
    filename=os.path.join(TEMP_DIR, 'somafm.log'),
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class PlaybackScreen:
    def __init__(self, player, channel):
        self.player = player
        self.channel = channel
        self.current_metadata = {
            'artist': 'Loading...',
            'title': 'Loading...',
            'duration': '--:--',
            'timestamp': None
        }
        self.next_metadata = {
            'artist': 'Next track',
            'title': 'Loading...',
            'duration': '--:--',
            'timestamp': None
        }
        self.scroll_offset = 0
        self.max_history = 10  # Maximum number of tracks in history
        self.track_history = []

    def display(self, stdscr):
        logging.debug("PlaybackScreen.display() called")
        max_y, max_x = stdscr.getmaxyx()
        
        # Clear screen
        stdscr.clear()
        
        # Display channel name
        try:
            channel_title = f"Channel: {self.channel['title']}"
            logging.debug(f"Displaying channel title: {channel_title}")
            stdscr.addstr(0, 0, channel_title, curses.color_pair(1) | curses.A_BOLD)
        except curses.error as e:
            logging.error(f"Error displaying channel title: {e}")
            pass

        # Display channel description
        try:
            description = self.channel.get('description', 'No description')
            if len(description) > max_x:
                description = description[:max_x-3] + "..."
            stdscr.addstr(1, 0, description, curses.color_pair(3))
        except curses.error:
            pass

        # Display current track
        try:
            # Add playback icon
            play_symbol = "▶" if not self.player.pause else "⏸"
            current_track = f"{play_symbol} {self.current_metadata['artist']} - {self.current_metadata['title']}"
            logging.debug(f"Displaying current track: {current_track}")
            if len(current_track) > max_x:
                current_track = current_track[:max_x-3] + "..."
            stdscr.addstr(2, 0, current_track, curses.color_pair(4) | curses.A_BOLD)
        except curses.error as e:
            logging.error(f"Error displaying current track: {e}")
            pass

        # Display track history
        y = 4  # Start from line 4
        for track in self.track_history:
            if y >= max_y - 2:
                break
            try:
                # Format timestamp
                timestamp = track.get('timestamp', '')
                if timestamp:
                    timestamp = f"[{timestamp}] "
                track_info = f"  {timestamp}{track['artist']} - {track['title']}"
                if len(track_info) > max_x:
                    track_info = track_info[:max_x-3] + "..."
                stdscr.addstr(y, 0, track_info, curses.color_pair(4))
                y += 1
            except curses.error:
                continue

        # Display instructions
        try:
            stdscr.addstr(max_y - 2, 0, "q - back to channel list", 
                         curses.color_pair(5) | curses.A_DIM)
        except curses.error:
            pass

        stdscr.refresh()

    def add_to_history(self, metadata):
        """Add track to history"""
        # Add timestamp to metadata
        metadata['timestamp'] = datetime.now().strftime("%H:%M:%S")
        self.track_history.insert(0, metadata)
        if len(self.track_history) > self.max_history:
            self.track_history.pop()

    def update_metadata(self, metadata):
        """Update current track metadata"""
        logging.debug(f"PlaybackScreen.update_metadata() called with: {metadata}")
        if metadata != self.current_metadata:
            logging.debug("Metadata changed, updating...")
            # Move current track to history
            self.add_to_history(self.current_metadata)
            # Update current track
            self.current_metadata = metadata.copy()  # Make a copy to avoid reference issues
            logging.debug(f"Updated current_metadata: {self.current_metadata}")
            # Clear next track
            self.next_metadata = {
                'artist': 'Next track',
                'title': 'Loading...',
                'duration': '--:--',
                'timestamp': None
            }
            # Force screen refresh
            curses.doupdate()
        else:
            logging.debug("Metadata unchanged, skipping update")

class SomaFMPlayer:
    def __init__(self):
        self.had_error = False
        # Check if MPV is installed
        if not self._check_mpv():
            print("Error: MPV player is not installed or not in PATH")
            print("Please install MPV using your package manager:")
            print("  - Arch Linux: sudo pacman -S mpv")
            print("  - Ubuntu/Debian: sudo apt-get install mpv")
            print("  - Fedora: sudo dnf install mpv")
            sys.exit(1)

        self._init_config()
        self.channels = self._fetch_channels()
        
        self.buffer = None
        self.player = mpv.MPV(
            input_default_bindings=True,
            input_vo_keyboard=True,
            osc=True
        )
        
        self.current_channel = None
        self.current_index = 0
        self.is_playing = False
        self.is_paused = False
        self.scroll_offset = 0
        self.current_metadata = {
            'artist': 'Loading...',
            'title': 'Loading...',
            'duration': '--:--'
        }
        self.running = True
        self.playback_screen = None
        self.stdscr = None  # Store stdscr for updates
        
        # Set up metadata observer
        @self.player.property_observer('metadata')
        def metadata_handler(name, value):
            if value:
                logging.debug(f"Received metadata: {value}")
                # Try to get track info from metadata
                track_info = value.get('icy-title', '')
                
                if track_info:
                    # Try to split by different separators
                    for separator in [' - ', ' – ']:
                        if separator in track_info:
                            parts = track_info.split(separator, 1)
                            if len(parts) == 2:
                                artist, title = parts
                                metadata = {
                                    'artist': artist.strip(),
                                    'title': title.strip(),
                                    'duration': '--:--',
                                    'timestamp': datetime.now().strftime("%H:%M:%S")
                                }
                                logging.debug(f"Updated metadata: {metadata}")
                                self.current_metadata = metadata
                                if self.playback_screen:
                                    self.playback_screen.update_metadata(metadata)
                                    # Force screen refresh after metadata update
                                    if self.stdscr:
                                        self.playback_screen.display(self.stdscr)
                                        self.stdscr.refresh()
                                break

    def _check_mpv(self) -> bool:
        """Check if MPV is installed and accessible"""
        try:
            import subprocess
            result = subprocess.run(['mpv', '--version'], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
            return result.returncode == 0
        except Exception:
            return False

    def _init_colors(self):
        """Initialize colors"""
        curses.start_color()
        # Main colors
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)    # Header
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Selected channel
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Channel info
        curses.init_pair(4, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # Track metadata
        curses.init_pair(5, curses.COLOR_BLUE, curses.COLOR_BLACK)    # Instructions

    def _init_config(self):
        """Initialize configuration file if it doesn't exist"""
        default_config = {
            "# Configuration file for SomaFM TUI Player": "",
            "# buffer_minutes: Duration of audio buffering in minutes": "",
            "# buffer_size_mb: Maximum size of buffer in megabytes": "",
            "buffer_minutes": 5,
            "buffer_size_mb": 50
        }
        
        try:
            if not os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'w') as f:
                    for key, value in default_config.items():
                        if key.startswith('#'):
                            f.write(f"{key}\n")
                        else:
                            f.write(f"{key}: {value}\n")
                    
            # Read actual config values (skip comments)
            with open(CONFIG_FILE) as f:
                config_lines = f.readlines()
                config_dict = {}
                for line in config_lines:
                    if not line.startswith('#') and ':' in line:
                        key, value = line.split(':', 1)
                        config_dict[key.strip()] = int(value.strip())
                self.config = config_dict
        except Exception as e:
            logging.error(f"Error initializing config: {e}")
            # Use only actual config values, not comments
            self.config = {k: v for k, v in default_config.items() if not k.startswith('#')}

    def _fetch_channels(self) -> List[Dict]:
        """Fetch channel list from SomaFM"""
        try:
            response = requests.get('https://api.somafm.com/channels.json')
            channels = response.json()['channels']
            print(f"Channels received: {len(channels)}")  # Debug information
            return channels
        except Exception as e:
            print(f"Error fetching channel list: {e}")
            sys.exit(1)

    def _display_channels(self, stdscr, selected_index: int):
        """Display channel list in console"""
        # Get window dimensions
        max_y, max_x = stdscr.getmaxyx()
        visible_channels = max_y - 5  # Number of visible channels
        
        # Clear screen
        stdscr.clear()
        
        # Display header
        try:
            stdscr.addstr(0, 0, f"Available channels ({len(self.channels)}):", 
                         curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            pass
        
        # Fixed cursor position at the second line
        cursor_y = 2
        
        # Update scroll offset to keep cursor at the top
        if selected_index < self.scroll_offset:
            self.scroll_offset = selected_index
        elif selected_index >= self.scroll_offset + visible_channels:
            self.scroll_offset = selected_index - visible_channels + 1
        
        # Display channels
        for i, channel in enumerate(self.channels[self.scroll_offset:self.scroll_offset + visible_channels]):
            # Calculate display position
            display_y = cursor_y + i
            if display_y >= max_y - 4:  # Leave space for playback info
                break
                
            # Truncate long channel names
            title = channel['title'][:max_x-4]  # Leave space for "> " and padding
            
            try:
                if i + self.scroll_offset == selected_index:
                    stdscr.addstr(display_y, 0, f"> {title}", 
                                 curses.color_pair(2) | curses.A_REVERSE)
                else:
                    stdscr.addstr(display_y, 0, f"  {title}")
            except curses.error:
                continue

        # Display playback info if available
        if self.current_channel and self.is_playing:
            try:
                info_line = f"Now playing: {self.current_channel['title']}"
                if len(info_line) > max_x:
                    info_line = info_line[:max_x-3] + "..."
                stdscr.addstr(max_y - 2, 0, info_line, curses.color_pair(3))
            except curses.error:
                pass

        # Display instructions
        try:
            stdscr.addstr(max_y - 1, 0, "↑↓ - select channel | Enter - play | q - quit", 
                         curses.color_pair(5) | curses.A_DIM)
        except curses.error:
            pass

        stdscr.refresh()

    def _play_channel(self, channel: Dict):
        """Play selected channel"""
        try:
            # Get stream URL from playlists
            stream_url = None
            for playlist in channel.get('playlists', []):
                if playlist.get('format') == 'mp3':
                    stream_url = playlist.get('url')
                    break
            
            if not stream_url:
                raise Exception(f"No MP3 stream found for channel {channel['title']}")
            
            # Stop current playback and buffering if any
            if self.player:
                self.player.stop()
            if self.buffer:
                self.buffer.stop_buffering()
                self.buffer.clear()
            
            # Initialize new buffer
            self.buffer = StreamBuffer(
                url=stream_url,
                buffer_minutes=self.config['buffer_minutes'],
                buffer_size_mb=self.config['buffer_size_mb'],
                cache_dir=CACHE_DIR
            )
            
            # Start buffering
            self.buffer.start_buffering()
            
            # Start playback
            self.player.play(stream_url)
            self.current_channel = channel
            self.is_playing = True
            self.is_paused = False
            
            # Create playback screen
            self.playback_screen = PlaybackScreen(self.player, channel)
            
            # Log channel change
            logging.info(f"Playing channel: {channel['title']}")
            logging.debug(f"Stream URL: {stream_url}")
            
            # Set initial metadata
            initial_metadata = {
                'artist': 'Loading...',
                'title': 'Loading...',
                'duration': '--:--',
                'timestamp': datetime.now().strftime("%H:%M:%S")
            }
            if self.playback_screen:
                self.playback_screen.update_metadata(initial_metadata)
            
        except Exception as e:
            logging.error(f"Error playing channel: {e}")
            print(f"Error playing channel: {e}")
            self.is_playing = False
            self.is_paused = False
            self.current_channel = None

    def _toggle_playback(self):
        """Toggle playback pause/resume"""
        if self.is_playing:
            if self.is_paused:
                self.player.pause = False
                self.is_paused = False
            else:
                self.player.pause = True
                self.is_paused = True

    def _cleanup(self):
        """Clean up resources"""
        if self.buffer:
            self.buffer.stop_buffering()
            self.buffer.clear()
        if self.player:
            self.player.terminate()
        if not self.had_error and os.path.exists(TEMP_DIR):
            try:
                for root, dirs, files in os.walk(TEMP_DIR, topdown=False):
                    for name in files:
                        os.remove(os.path.join(root, name))
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                os.rmdir(TEMP_DIR)
            except Exception as e:
                logging.error(f"Error cleaning up temp directory: {e}")

    def run(self):
        """Main application loop"""
        def main(stdscr):
            try:
                # Store stdscr globally for updates
                self.stdscr = stdscr
                
                # Initialize colors
                self._init_colors()
                
                # Enable keypad mode for special keys
                stdscr.keypad(True)
                # Enable Unicode support
                curses.raw()
                # Enable non-blocking mode
                stdscr.nodelay(False)
                
                # Main loop
                while self.running:
                    if self.playback_screen:
                        self.playback_screen.display(stdscr)
                    else:
                        self._display_channels(stdscr, self.current_index)
                    
                    # Get user input
                    try:
                        key = stdscr.get_wch()
                        logging.debug(f"Pressed key: {key} (type: {type(key)})")
                        
                        if self.playback_screen:
                            if key in ['q', 'й', 'Q', 'Й', chr(27)]:  # 27 is ESC
                                logging.debug(f"Detected quit key in playback")
                                self.playback_screen = None
                                self.player.stop()
                                self.is_playing = False
                                self.is_paused = False
                                self.current_metadata = {
                                    'artist': 'Loading...',
                                    'title': 'Loading...',
                                    'duration': '--:--'
                                }
                            elif key == ' ':
                                self._toggle_playback()
                        else:
                            if isinstance(key, str):
                                if key in ['q', 'й', 'Q', 'Й', chr(27)]:  # 27 is ESC
                                    logging.debug(f"Detected quit key in channel list")
                                    self.running = False
                                elif key in ['\n', '\r']:  # Handle Enter as string
                                    self._play_channel(self.channels[self.current_index])
                            else:  # Handle special keys
                                if key == curses.KEY_UP:
                                    self.current_index = max(0, self.current_index - 1)
                                elif key == curses.KEY_DOWN:
                                    self.current_index = min(len(self.channels) - 1, self.current_index + 1)
                                elif key == curses.KEY_ENTER:  # Handle Enter as special key
                                    self._play_channel(self.channels[self.current_index])
                    except curses.error:
                        continue
            except Exception as e:
                self.had_error = True
                logging.error(f"Application error: {e}")
                raise
            finally:
                self._cleanup()

        try:
            curses.wrapper(main)
        except Exception as e:
            self.had_error = True
            logging.error(f"Fatal error: {e}")
            print(f"An error occurred. Check logs at {os.path.join(TEMP_DIR, 'somafm.log')}")
            sys.exit(1)

if __name__ == "__main__":
    player = SomaFMPlayer()
    player.run() 