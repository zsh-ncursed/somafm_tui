"""Stream buffering module"""

import os
import threading
import logging
from typing import Optional

import requests

DEFAULT_TIMEOUT = 10  # seconds


class StreamBuffer:
    """Audio stream buffer"""

    def __init__(
        self,
        url: str,
        buffer_minutes: int,
        buffer_size_mb: int,
        cache_dir: str,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.url = url
        self.buffer_minutes = buffer_minutes
        self.buffer_size = buffer_size_mb * 1024 * 1024  # Convert to bytes
        self.cache_dir = cache_dir
        self.timeout = timeout
        self.buffer_file = os.path.join(cache_dir, "stream.cache")
        self.is_buffering = False
        self.buffer_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start_buffering(self) -> None:
        """Start buffering in a separate thread"""
        self.is_buffering = True
        self._stop_event.clear()
        self.buffer_thread = threading.Thread(target=self._buffer_stream)
        self.buffer_thread.daemon = True
        self.buffer_thread.start()

    def stop_buffering(self) -> None:
        """Stop buffering"""
        self._stop_event.set()
        if self.buffer_thread:
            self.buffer_thread.join(timeout=5)
        self.is_buffering = False

    def _buffer_stream(self) -> None:
        """Buffer stream data to file"""
        try:
            with requests.get(self.url, stream=True, timeout=self.timeout) as response:
                response.raise_for_status()
                with open(self.buffer_file, "wb") as f:
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
        except requests.Timeout:
            logging.error(f"Timeout buffering stream: {self.url}")
        except requests.RequestException as e:
            logging.error(f"Error buffering stream: {e}")
        except IOError as e:
            logging.error(f"IO error buffering stream: {e}")
        except Exception as e:
            logging.error(f"Unexpected error buffering stream: {e}")
        finally:
            self.is_buffering = False

    def get_buffer_file(self) -> str:
        """Get path to buffer file"""
        return self.buffer_file if os.path.exists(self.buffer_file) else ""

    def clear(self) -> None:
        """Clear buffer"""
        if os.path.exists(self.buffer_file):
            try:
                os.remove(self.buffer_file)
            except OSError as e:
                logging.error(f"Error clearing buffer: {e}")

    def is_active(self) -> bool:
        """Check if buffering is active"""
        return self.is_buffering and self._stop_event.is_set() is False
