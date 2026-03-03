# Contributing to SomaFM TUI

Thank you for your interest in SomaFM TUI! This document will help you contribute to the project.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/zsh-ncursed/somafm_tui.git
cd somafm_tui

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m somafm_tui

# Or via shell scripts
./somafm.fish    # Fish shell
./somafm.sh      # Bash/Zsh
```

## Requirements

- Python 3.8+
- MPV player
- Terminal with Unicode and 256-color support

## Project Structure

```
somafm_tui/
├── __main__.py         # Entry point
├── player.py           # Main player class and application logic
├── config.py           # Configuration management
├── themes.py           # Color themes and palettes
├── themes.json         # Theme definitions (JSON format)
├── models.py           # Data types (dataclasses)
├── channels.py         # SomaFM channel handling
├── mpris_service.py    # MPRIS D-Bus service for media keys
├── ui.py               # User interface rendering
├── http_client.py      # HTTP requests with retry logic
├── terminal.py         # Terminal utilities
├── timer.py            # Sleep timer functionality
├── requirements.txt    # Python dependencies
├── PKGBUILD            # AUR package build file
├── somafm.sh           # Bash/Zsh launcher script
├── somafm.fish         # Fish shell launcher script
└── somafm.bash         # Bash completion script
```

## Development

### Installing AUR Package Locally

To test AUR package changes locally:

```bash
cd somafm_tui
makepkg -si
```

### Running Tests

```bash
python -m pytest tests/ -v
```

### Code Checking

```bash
# Syntax check
python -m py_compile somafm_tui/*.py

# Linting (if installed)
python -m pylint somafm_tui/

# Type checking (if using mypy)
python -m mypy somafm_tui/
```

## Submitting Changes

1. Fork the repository
2. Create a branch for your changes (`git checkout -b feature/your-feature`)
3. Make changes with tests (if applicable)
4. Ensure all tests pass
5. Commit your changes with clear commit messages
6. Push to your fork
7. Submit a pull request

### Pull Request Guidelines

- Describe what your changes do
- Reference any related issues
- Include screenshots for UI changes
- Update CHANGELOG.md if adding features or fixing bugs

## Code Style

- Use type hints for function arguments and return values
- Add docstrings for public functions and classes
- Follow PEP 8 style guide
- Maximum line length: 100 characters
- Use dataclasses for data containers
- Prefer f-strings for string formatting
- Use meaningful variable names

## Reporting Bugs

When reporting a bug, please include:

- Operating system and version
- Python version (`python --version`)
- SomaFM TUI version
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Logs from `/tmp/.somafmtmp/somafm.log`
- Screenshots (if applicable)

### Where to Report

- GitHub Issues: https://github.com/zsh-ncursed/somafm_tui/issues

## License

MIT License
