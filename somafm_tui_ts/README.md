# SomaFM TUI (TypeScript)

Terminal UI player for [SomaFM](https://somafm.com/) internet radio, written in TypeScript + Ink.

## Features

- 📻 **40+ SomaFM channels** with metadata
- 🎵 **MPV-based audio playback** (requires `mpv` installed)
- 🎨 **24 color themes** (Dracula, Nord, Gruvbox, Catppuccin, etc.)
- ♥ **Channel favorites** with JSON persistence
- ⏱️ **Sleep timer** (1-480 minutes)
- 🔍 **Search** by channel name or description
- 🔊 **Volume control** (0-100)
- 🎚️ **Bitrate cycling** (MP3 128k/320k, AAC, etc.)
- 🎹 **Vim-style navigation** (j/k for nav, l for play)
- 💾 **XDG-compliant** config and cache storage

## Requirements

- Node.js 18+
- [MPV](https://mpv.io/) media player (system binary)
- Linux/macOS/Windows

## Installation

```bash
# From source
git clone https://github.com/zsh-ncursed/somafm_tui.git
cd somafm_tui/somafm_tui_ts
npm install

# Build (optional)
npm run build
```

## Usage

### Interactive Mode (Default)

```bash
npm run dev       # Development mode
npm start         # Production mode (after build)
```

### CLI Arguments

```bash
# List all channels
npm start -- --list-channels

# Search channels
npm start -- --search "groove"

# Show favorites
npm start -- --favorites

# List themes
npm start -- --list-themes
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `↑↓` / `j/k` | Navigate channels |
| `Enter` / `l` | Play selected channel |
| `Space` | Toggle pause |
| `h` | Stop playback |
| `f` | Toggle favorite |
| `r` | Cycle bitrate |
| `s` | Set sleep timer |
| `t` | Next theme |
| `y` | Previous theme |
| `PgUp` / `PgDn` | Volume up/down |
| `/` | Search channels |
| `?` | Show help |
| `q` | Quit |

## Architecture

```
src/
├── components/       # React/Ink UI components
│   ├── App.tsx       # Main orchestrator
│   ├── ChannelList.tsx
│   ├── NowPlaying.tsx
│   ├── StatusBar.tsx
│   ├── SearchPrompt.tsx
│   ├── SleepTimerOverlay.tsx
│   └── HelpOverlay.tsx
├── lib/              # Business logic
│   ├── somafm-api.ts # API client with caching
│   ├── audio-player.ts # MPV wrapper
│   ├── favorites.ts  # Favorites persistence
│   ├── config.ts     # Config management
│   ├── themes.ts     # Theme system
│   ├── cache.ts      # File cache
│   └── bitrate-utils.ts
├── types/            # TypeScript interfaces
└── index.tsx         # Entry point + CLI
```

## Project Structure

This is a TypeScript port of the original [Python SomaFM TUI](https://github.com/zsh-ncursed/somafm_tui).

Key differences:
- `curses` → Ink (React for terminal)
- `python-mpv` → `node-mpv`
- `dbus-next` → `mpris-service` (optional)
- File-based config → `lowdb` JSON persistence

## Development

```bash
# Run tests
npm test

# Type check
npm run lint

# Development mode
npm run dev
```

## License

MIT
