# SomaFM TUI Player - Potential Improvements

## Critical Issues

### 1. Unused StreamBuffer
**File:** `stream_buffer.py`, `player.py:279-289`

StreamBuffer writes audio data to file, but MPV plays directly from URL. The buffer is not used for timeshift.

**Solution:** Either remove the buffer or implement timeshift functionality.

---

## Architecture Improvements

### 2. Signal Handling
**File:** `player.py`

Application doesn't handle SIGTERM/SIGINT, which may lead to buffer data loss.

```python
import signal

def _setup_signal_handlers(self):
    signal.signal(signal.SIGTERM, self._signal_handler)
    signal.signal(signal.SIGINT, self._signal_handler)
```

### 3. Use ConfigParser
**File:** `config.py`

Manual config parsing. Better to use built-in `configparser`:

```python
import configparser
config = configparser.ConfigParser()
config.read(CONFIG_FILE)
```

### 4. Connection Pooling
**File:** `http_client.py`

New session is created for each request. Better to reuse session:

```python
_session = None

def get_session():
    global _session
    if _session is None:
        _session = create_session()
    return _session
```

### 5. Unified HTTP Function
**File:** `http_client.py`

`fetch_json` and `fetch_bytes` duplicate code:

```python
def fetch_data(url: str, parse_json: bool = False, ...) -> Optional[Any]:
    # Unified function
```

---

## UI/UX Improvements

### 6. Extended Channel Search
**File:** `channels.py:115-121`

Search only by name. Can add search by description and genres:

```python
def filter_channels_by_query(channels: List[Channel], query: str) -> List[Channel]:
    query_lower = query.lower()
    return [
        ch for ch in channels
        if query_lower in ch.title.lower()
        or query_lower in ch.description.lower()
    ]
```

### 7. Adaptive Panel Width
**File:** `ui.py:49`

Channel panel width (30 characters) is hardcoded:

```python
split_x = min(30, max_x // 3)  # Adaptive width
```

### 8. UTF-8 Emoji Support
**File:** `ui.py`

Emojis (`👤`, `🎵`, `🔊`) may not display in some terminals. Add fallback:

```python
USE_EMOJI = os.environ.get("TERM", "").lower() not in ("linux", "vt100")

def get_listener_icon():
    return "👤" if USE_EMOJI else "L"

def get_bitrate_icon():
    return "🎵" if USE_EMOJI else "B"
```

### 9. Improved Error Handling in UI
**File:** `ui.py`

Many `try/except` hide errors. Better to add logging:

```python
except curses.error as e:
    logging.warning(f"UI render error: {e}")
    continue
```

---

## MPRIS/D-Bus Improvements

### 10. Typo in MPRIS
**File:** `mpris_service.py:223-227`

Uses `current_channel` as dict, but it's a `Channel` object:

```python
# Was
mpris_metadata["xesam:album"] = Variant("s", self.player.current_channel["title"])

# Fixed to
mpris_metadata["xesam:album"] = Variant("s", self.player.current_channel.title)
```

### 11. Proper D-Bus Disconnect Handling
**File:** `mpris_service.py`

No handling for when D-Bus is unavailable.

### 12. Use async/await
**File:** `mpris_service.py:349-357`

MPRIS loop runs in daemon thread but uses synchronous approach. Better to use full async.

---

## Themes Improvements

### 13. Move Themes to JSON
**File:** `themes.py`

Hardcoded colors. Better to move to file:

```python
# themes.json
{
  "default": {
    "name": "Default Dark",
    "colors": {...}
  }
}
```

### 14. Color Support Detection
**File:** `themes.py`

No terminal capabilities check:

```python
def check_terminal_colors():
    if not curses.has_colors():
        return "monochrome"
    if curses.COLORS >= 256:
        return "256color"
    return "16color"
```

---

## Configuration Improvements

### 15. Reset Command
**File:** `config.py`

No way to reset settings. Add function:

```python
def reset_config():
    """Reset configuration to defaults"""
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
    save_config(get_default_config())
```

### 16. Startup Validation
**File:** `player.py:92`

No dependency check after start. Add re-validation.

---

## Code Improvements

### 17. Remove Duplicate Imports
**File:** `player.py:257`

```python
# Duplicate import inside method
import time  # Already imported at file start
```

### 18. Typing
**File:** `player.py:8`

```python
from typing import Optional, List, Set  # Set is not used
```

### 19. Hardcoded Paths
**File:** `player.py:39-43`

```python
TEMP_DIR = "/tmp/.somafmtup"  # Better to move to config
```

### 20. Remove Non-existent Method
**File:** `mpris_service.py:81, 89`

Calls non-existent method `_display_combined_interface` instead of `_display_interface`.

---

## Testing

### 21. Test Coverage
- Add tests for `channels.py`
- Add tests for `config.py`
- Add integration tests for UI

---

## Documentation

### 22. Missing README
- Add installation documentation
- Add keyboard shortcuts description
- Add Troubleshooting section

---

## Implementation Priorities

| Priority | Task |
|----------|------|
| High | Fix/remove StreamBuffer |
| High | Fix MPRIS typing error |
| Medium | Signal handling |
| Medium | Extended search |
| Medium | Connection pooling |
| Low | Move themes to JSON |
| Low | Improved documentation |
