#!/usr/bin/env python3
import os
import curses
import select
import mpv
import requests
import json
import sys
import time
import logging
import shutil
import subprocess
import tempfile
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
    def __init__(self, player, channel, cava_stdout=None):
        self.player = player
        self.channel = channel
        self.cava_stdout = cava_stdout
        self.last_bar_heights = []
        self.cava_num_bars = 15  # Updated to match CAVA config
        self.cava_max_value = 1000 # As per CAVA config (ascii_max_range)
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
        
        # Clear screen - done selectively now
        stdscr.bkgd(' ', curses.color_pair(1)) # Set background for the whole window
        stdscr.clear() # Clear entire screen with background

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

        # --- CAVA Visualization ---
        viz_start_y = max_y // 2
        viz_end_y = max_y - 3  # Inclusive last line for visualization
        viz_drawable_height = viz_end_y - viz_start_y + 1

        if self.cava_stdout:
            if viz_drawable_height <= 0:
                # Try to read and discard any pending CAVA data to prevent pipe blockage
                try:
                    readable, _, _ = select.select([self.cava_stdout], [], [], 0)
                    if readable:
                        _ = self.cava_stdout.readline() # Read and discard
                except Exception:
                    pass # Ignore errors here, as we are just trying to clear
                self.last_bar_heights = [] # Clear any previous heights
            else:
                # Non-blocking read from CAVA
                try:
                    readable, _, _ = select.select([self.cava_stdout], [], [], 0)
                    if readable:
                        line = self.cava_stdout.readline().strip()
                        logging.debug(f"CAVA raw line: '{line}'") # Added logging
                        if line:
                            try:
                                parts = line.split(';')
                                if len(parts) >= self.cava_num_bars:
                                    bar_heights = [int(p) for p in parts[:self.cava_num_bars] if p]
                                    if len(bar_heights) == self.cava_num_bars:
                                        self.last_bar_heights = bar_heights
                                        logging.debug(f"CAVA parsed heights: {bar_heights}") # Added logging
                            except ValueError:
                                logging.warning(f"Could not parse CAVA data: '{line}'")
                            # No need for a generic Exception here as it's mainly parsing
                        elif not line and self.cava_process and self.cava_process.poll() is not None:
                            # CAVA process might have exited
                            logging.warning("CAVA stdout returned empty line and process has exited. Disabling CAVA for this session.")
                            if self.cava_stdout: self.cava_stdout.close()
                            self.cava_stdout = None # Stop further processing
                except BrokenPipeError:
                    logging.warning("Broken pipe when reading from CAVA. CAVA might have crashed. Disabling CAVA for this session.")
                    if self.cava_stdout: self.cava_stdout.close()
                    self.cava_stdout = None
                except IOError as e:
                    logging.warning(f"IOError reading from CAVA: {e}. Disabling CAVA for this session.")
                    if self.cava_stdout: self.cava_stdout.close()
                    self.cava_stdout = None
                except Exception as e: # Catch any other unexpected errors during CAVA read/parse
                    logging.error(f"Unexpected error reading or parsing CAVA data: {e}. Disabling CAVA for this session.")
                    if self.cava_stdout: self.cava_stdout.close()
                    self.cava_stdout = None # Stop further processing
                
                # Clear visualization area (from viz_start_y to viz_end_y inclusive)
                if viz_drawable_height > 0 : # Ensure we only clear if there's an area to clear
                    for y_clear in range(viz_start_y, viz_end_y + 1):
                        try:
                            stdscr.addstr(y_clear, 0, " " * (max_x -1), curses.color_pair(1))
                        except curses.error: # Ignore errors if writing outside bounds
                            pass

                # Draw bars using self.last_bar_heights
                current_heights_to_draw = self.last_bar_heights

                if hasattr(self, 'last_bar_heights') and current_heights_to_draw and viz_drawable_height > 0:
                    terminal_width = max_x -1 
                    actual_bar_char_width = 1 

                    if self.cava_num_bars > 0:
                        spacing_total_width = terminal_width - (self.cava_num_bars * actual_bar_char_width)
                        spacing_per_gap = spacing_total_width / (self.cava_num_bars + 1)
                        spacing_per_gap = max(0, spacing_per_gap) 
                    else:
                        spacing_per_gap = 0

                    current_x_float = spacing_per_gap 

                    for bar_idx, height_val in enumerate(current_heights_to_draw): # Added bar_idx
                        scaled_bar_screen_height = int((height_val / self.cava_max_value) * viz_drawable_height)
                        scaled_bar_screen_height = max(0, min(scaled_bar_screen_height, viz_drawable_height))

                        # Added logging for the first bar's details (and now for all bars if DEBUG level is very verbose, but primarily for the first)
                        if bar_idx == 0: # Log details for the first bar of every frame
                            logging.debug(f"Bar {bar_idx}: raw={height_val}, max_raw={self.cava_max_value}, viz_draw_h={viz_drawable_height}, scaled_h={scaled_bar_screen_height}")
                        # Example of more verbose logging for all bars:
                        # logging.debug(f"Bar {bar_idx}: raw={height_val}, max_raw={self.cava_max_value}, viz_draw_h={viz_drawable_height}, scaled_h={scaled_bar_screen_height}")

                        x_pos = int(current_x_float)

                        for char_offset in range(scaled_bar_screen_height):
                            draw_y = viz_end_y - char_offset
                            if 0 <= x_pos < (max_x -1) and viz_start_y <= draw_y <= viz_end_y : 
                                try:
                                    stdscr.addstr(draw_y, x_pos, "█", curses.color_pair(4))
                                except curses.error:
                                    pass 
                        
                        current_x_float += actual_bar_char_width + spacing_per_gap
        elif viz_drawable_height > 0 : # Ensure area is cleared if CAVA is not available / becomes unavailable
            for y_clear in range(viz_start_y, viz_end_y + 1):
                try:
                    stdscr.addstr(y_clear, 0, " " * (max_x -1), curses.color_pair(1))
                except curses.error:
                    pass
        # --- End CAVA Visualization ---

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
        self.fifo_path = "/tmp/somafm_audio.fifo"
        
        # CAVA related attributes
        self.cava_executable_path = shutil.which("cava")
        self.cava_available = self.cava_executable_path is not None
        self.cava_process = None
        self.cava_stdout = None
        self.cava_config_path = None
        if not self.cava_available:
            logging.warning("CAVA executable not found in PATH. Visualization will be disabled.")

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

    def _create_cava_config(self):
        """Create CAVA configuration file"""
        config_content = f"""
[general]
framerate = 20
bars = 15
autosens = 1
sensitivity = 100

[input]
method = fifo
source = {self.fifo_path}
sample_rate = 44100
sample_bits = 16

[output]
method = raw
raw_target = /dev/stdout
data_format = ascii
bar_delimiter = ;
frame_delimiter = 10
channels = mono

[smoothing]
noise_reduction = 85
"""
        try:
            # Create a temporary file for CAVA config
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.cfg', prefix='cava_config_') as tmp_file:
                tmp_file.write(config_content)
                self.cava_config_path = tmp_file.name
            logging.debug(f"CAVA config created at {self.cava_config_path}")
        except Exception as e:
            logging.error(f"Error creating CAVA config: {e}")
            self.cava_config_path = None

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
        # Ещё более тёмный фон
        if curses.can_change_color():
            # Ещё более тёмный фон
            curses.init_color(10, 80, 80, 80)  # Очень тёмно-серый, 8% от максимума
            bg_color = 10
        else:
            bg_color = curses.COLOR_BLACK
        # Main colors
        curses.init_pair(1, curses.COLOR_CYAN, bg_color)    # Header
        curses.init_pair(2, curses.COLOR_GREEN, bg_color)   # Selected channel
        curses.init_pair(3, curses.COLOR_YELLOW, bg_color)  # Channel info
        curses.init_pair(4, curses.COLOR_MAGENTA, bg_color) # Track metadata
        curses.init_pair(5, curses.COLOR_BLUE, bg_color)    # Instructions

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
        for y in range(max_y):
            stdscr.addstr(y, 0, " " * (max_x - 1), curses.color_pair(1))
        
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
                    stdscr.addstr(display_y, 0, f"  {title}", curses.color_pair(1))
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
            
            # Terminate existing CAVA process if any
            if self.cava_process:
                self.cava_process.terminate()
                try:
                    self.cava_process.wait(timeout=0.5) # Wait for a short period
                except subprocess.TimeoutExpired:
                    self.cava_process.kill() # Force kill if terminate fails
                if self.cava_stdout:
                    self.cava_stdout.close()
                self.cava_process = None
                self.cava_stdout = None
            if self.cava_config_path and os.path.exists(self.cava_config_path):
                try:
                    os.remove(self.cava_config_path)
                except OSError as e:
                    logging.error(f"Error removing old CAVA config {self.cava_config_path}: {e}")
                self.cava_config_path = None

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
            # Create FIFO for CAVA
            if os.path.exists(self.fifo_path):
                os.remove(self.fifo_path)
            os.mkfifo(self.fifo_path)
            
            self.player.loadfile(stream_url, audio_file=self.fifo_path, audio_file_auto="no")
            
            # Create and launch CAVA
            if self.cava_available:
                self._create_cava_config() # Should set self.cava_config_path
                if self.cava_config_path:
                    # Corrected try-except block for CAVA launch:
                    try:
                        self.cava_process = subprocess.Popen(
                            [self.cava_executable_path, "-p", self.cava_config_path],
                            stdout=subprocess.PIPE,
                            stdin=subprocess.DEVNULL,
                            text=True
                        )
                        self.cava_stdout = self.cava_process.stdout
                        
                        # Logging for successful launch attempt, inside the try block:
                        logging.info("CAVA subprocess initiated.") 
                        logging.info(f"CAVA process PID: {self.cava_process.pid}")
                        logging.info(f"CAVA stdout pipe: {self.cava_stdout}")

                    except FileNotFoundError:
                        logging.error(f"CAVA executable not found at '{self.cava_executable_path}' during Popen. Visualization disabled.")
                        self.cava_available = False # Prevent further attempts if it failed here
                        self.cava_process = None
                        self.cava_stdout = None
                    except OSError as e:
                        logging.error(f"OSError launching CAVA with '{self.cava_executable_path}': {e}. Visualization disabled.")
                        self.cava_process = None
                        self.cava_stdout = None
                    except Exception as e:
                        logging.error(f"Unexpected Exception launching CAVA: {e}. Visualization disabled.")
                        self.cava_process = None
                        self.cava_stdout = None
                else:
                    logging.warning("CAVA config path not set (e.g., temp file creation failed), CAVA not launched.")
                    self.cava_stdout = None # Ensure cava_stdout is None
            else:
                # This log is from __init__ if shutil.which fails,
                # but good to have a state check here too or rely on self.cava_stdout being None.
                logging.warning("CAVA not available (pre-check failed or failed previous launch). Visualization will be disabled.")
                self.cava_stdout = None # Ensure cava_stdout is None
            
            self.current_channel = channel
            self.is_playing = True
            self.is_paused = False
            
            # Create playback screen
            self.playback_screen = PlaybackScreen(self.player, channel, cava_stdout=self.cava_stdout)
            
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
        # Terminate CAVA process
        if self.cava_process:
            logging.debug(f"Terminating CAVA process {self.cava_process.pid}")
            self.cava_process.terminate()
            try:
                self.cava_process.wait(timeout=1) # Wait for CAVA to terminate
            except subprocess.TimeoutExpired:
                logging.warning(f"CAVA process {self.cava_process.pid} did not terminate in time, killing.")
                self.cava_process.kill() # Force kill if it doesn't terminate
            if self.cava_stdout:
                self.cava_stdout.close()
            self.cava_process = None
            self.cava_stdout = None
        
        # Remove CAVA config file
        if self.cava_config_path and os.path.exists(self.cava_config_path):
            try:
                os.remove(self.cava_config_path)
                logging.debug(f"Removed CAVA config file {self.cava_config_path}")
            except OSError as e:
                logging.error(f"Error removing CAVA config file {self.cava_config_path}: {e}")
            self.cava_config_path = None

        # Remove FIFO on cleanup
        if os.path.exists(self.fifo_path):
            try:
                os.remove(self.fifo_path)
            except OSError as e:
                logging.error(f"Error removing FIFO {self.fifo_path}: {e}")
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
                                # Terminate CAVA process
                                if self.cava_process:
                                    self.cava_process.terminate()
                                    try:
                                        self.cava_process.wait(timeout=0.5)
                                    except subprocess.TimeoutExpired:
                                        self.cava_process.kill()
                                    if self.cava_stdout:
                                        self.cava_stdout.close()
                                    self.cava_process = None
                                    self.cava_stdout = None
                                if self.cava_config_path and os.path.exists(self.cava_config_path):
                                    try:
                                        os.remove(self.cava_config_path)
                                    except OSError as e:
                                        logging.error(f"Error removing CAVA config {self.cava_config_path}: {e}")
                                    self.cava_config_path = None
                                
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