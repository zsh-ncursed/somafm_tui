# Contributing to SomaFM TUI

Thank you for your interest in SomaFM TUI! This document will help you contribute to the project.

## Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd somafm_tui_v2/somafm_tui

# Install dependencies
pip install -r requirements.txt

# Run the application
python __main__.py

# Or via fish
./somafm.fish
```

## Requirements

- Python 3.8+
- MPV player
- Terminal with Unicode and 256-color support

## Project Structure

```
somafm_tui/
├── __main__.py       # Entry point
├── player.py         # Main player class
├── config.py         # Configuration management
├── themes.py         # Color themes
├── models.py         # Data types (dataclasses)
├── channels.py       # SomaFM channel handling
├── stream_buffer.py  # Stream buffering
├── mpris_service.py  # MPRIS D-Bus service
├── ui.py            # User interface
├── http_client.py    # HTTP requests with retry
├── terminal.py       # Terminal utilities
└── tests/           # Unit tests
```

## Development

### Running Tests

```bash
python -m pytest tests/ -v
```

### Code Checking

```bash
# Syntax
python -m py_compile somafm_tui/*.py

# Linting (if installed)
python -m pylint somafm_tui/
```

## Submitting Changes

1. Create a branch for your changes
2. Make changes with tests
3. Ensure all tests pass
4. Submit a pull request

## Code Style

- Use type hints
- Add docstrings for new functions
- Follow PEP 8
- Maximum line length: 100 characters

## Reporting Bugs

When reporting a bug, please include:
- Operating system
- Python version
- Steps to reproduce
- Logs (if available)

## License

MIT License
