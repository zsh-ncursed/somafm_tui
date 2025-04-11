#!/usr/bin/env python3
import curses
import mpv
import requests
import json
import sys
import time
import logging
from typing import List, Dict
from datetime import datetime

# Logging setup
logging.basicConfig(
    filename='/tmp/somafm.log',
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
        max_y, max_x = stdscr.getmaxyx()
        
        # Clear screen
        stdscr.clear()
        
        # Display channel name
        try:
            stdscr.addstr(0, 0, f"Channel: {self.channel['title']}", 
                         curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
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
            if len(current_track) > max_x:
                current_track = current_track[:max_x-3] + "..."
            stdscr.addstr(2, 0, current_track, curses.color_pair(4) | curses.A_BOLD)
        except curses.error:
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
        if metadata != self.current_metadata:
            # Move current track to history
            self.add_to_history(self.current_metadata)
            # Update current track
            self.current_metadata = metadata
            # Clear next track
            self.next_metadata = {
                'artist': 'Next track',
                'title': 'Loading...',
                'duration': '--:--',
                'timestamp': None
            }

class SomaFMPlayer:
    def __init__(self):
        # Check if MPV is installed
        if not self._check_mpv():
            print("Error: MPV player is not installed or not in PATH")
            print("Please install MPV using your package manager:")
            print("  - Arch Linux: sudo pacman -S mpv")
            print("  - Ubuntu/Debian: sudo apt-get install mpv")
            print("  - Fedora: sudo dnf install mpv")
            sys.exit(1)

        self.channels = self._fetch_channels()
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
        
        # Subscribe to property changes
        @self.player.property_observer('metadata')
        def metadata_handler(name, value):
            if value:
                # Log all metadata
                logging.debug("=== Received metadata ===")
                for key, val in value.items():
                    logging.debug(f"Key: {key}, Value: {val}")
                logging.debug("==========================")
                
                # Get metadata from stream
                icy_title = value.get('icy-title', '')
                
                # If icy-title exists, split into artist and title
                if icy_title and ' - ' in icy_title:
                    artist, title = icy_title.split(' - ', 1)
                    logging.debug(f"Split icy-title: artist={artist}, title={title}")
                    metadata = {
                        'artist': artist,
                        'title': title,
                        'duration': '--:--',  # TODO: Add duration retrieval
                        'timestamp': datetime.now().strftime("%H:%M:%S")  # Add playback start time
                    }
                    self.current_metadata = metadata
                    if self.playback_screen:
                        self.playback_screen.update_metadata(metadata)
                else:  # If no metadata, use channel name
                    artist = 'No data'
                    title = self.current_channel['title'] if self.current_channel else 'No data'
                    logging.debug(f"Using channel name as title: {title}")
                    metadata = {
                        'artist': artist,
                        'title': title,
                        'duration': '--:--',
                        'timestamp': datetime.now().strftime("%H:%M:%S")  # Add playback start time
                    }
                    self.current_metadata = metadata
                    if self.playback_screen:
                        self.playback_screen.update_metadata(metadata)

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
            
            # Stop current playback if any
            if self.player:
                self.player.stop()
            
            # Start new playback
            self.player.play(stream_url)
            self.current_channel = channel
            self.is_playing = True
            self.is_paused = False
            
            # Create playback screen
            self.playback_screen = PlaybackScreen(self.player, channel)
            
            # Log channel change
            logging.info(f"Playing channel: {channel['title']}")
            logging.debug(f"Stream URL: {stream_url}")
            
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
        if self.player:
            self.player.terminate()

    def run(self):
        """Main application loop"""
        def main(stdscr):
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
                        # Проверяем нажатие клавиши 'q' в любой раскладке
                        if key in ['q', 'й', 'Q', 'Й'] or key == curses.KEY_ESCAPE:
                            logging.debug(f"Detected 'q' key press during playback (key: {key})")
                            self.playback_screen = None
                            self.player.stop()
                            self.is_playing = False
                            self.is_paused = False
                            self.current_metadata = {
                                'artist': 'Loading...',
                                'title': 'Loading...',
                                'duration': '--:--'
                            }
                            continue  # Возвращаемся к списку каналов
                        elif key == ' ':
                            self._toggle_playback()
                    else:
                        if key == curses.KEY_UP:
                            self.current_index = max(0, self.current_index - 1)
                        elif key == curses.KEY_DOWN:
                            self.current_index = min(len(self.channels) - 1, self.current_index + 1)
                        elif key in [curses.KEY_ENTER, '\n', '\r']:
                            self._play_channel(self.channels[self.current_index])
                        elif key in ['q', 'й', 'Q', 'Й'] or key == curses.KEY_ESCAPE:
                            logging.debug(f"Detected 'q' key press in channel list (key: {key})")
                            self.running = False
                except curses.error:
                    continue
            
            # Clean up
            self._cleanup()

        # Run curses application
        curses.wrapper(main)

if __name__ == "__main__":
    player = SomaFMPlayer()
    player.run() 