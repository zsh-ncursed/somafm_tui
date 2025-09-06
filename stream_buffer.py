import os
import threading
import time
import logging
from typing import Optional
import requests
from urllib.parse import urlparse

class StreamBuffer:
    def __init__(self, url: str, buffer_minutes: int, buffer_size_mb: int, cache_dir: str):
        self.url = url
        self.buffer_minutes = buffer_minutes
        self.buffer_size = buffer_size_mb * 1024 * 1024  # Convert to bytes
        self.cache_dir = cache_dir
        self.buffer_file = os.path.join(cache_dir, 'stream.cache')
        self.is_buffering = False
        self.buffer_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start_buffering(self):
        """Start buffering in a separate thread"""
        self.is_buffering = True
        self._stop_event.clear()
        self.buffer_thread = threading.Thread(target=self._buffer_stream)
        self.buffer_thread.daemon = True
        self.buffer_thread.start()

    def stop_buffering(self):
        """Stop buffering"""
        self._stop_event.set()
        if self.buffer_thread:
            self.buffer_thread.join()
        self.is_buffering = False

    def _buffer_stream(self):
        """Buffer stream data to file"""
        try:
            with requests.get(self.url, stream=True) as response:
                with open(self.buffer_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if self._stop_event.is_set():
                            break
                        if chunk:
                            f.write(chunk)
                            f.flush()
                            # Check buffer size
                            if os.path.getsize(self.buffer_file) > self.buffer_size:
                                f.seek(0)
                                f.truncate()
        except Exception as e:
            logging.error(f"Error buffering stream: {e}")
            self.is_buffering = False

    def get_buffer_file(self) -> str:
        """Get path to buffer file"""
        return self.buffer_file if os.path.exists(self.buffer_file) else ""

    def clear(self):
        """Clear buffer"""
        if os.path.exists(self.buffer_file):
            os.remove(self.buffer_file) 