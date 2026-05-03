# AGENTS.md

## Running

```bash
python -m somafm_tui
```

## Testing

```bash
python -m pytest              # all tests
python -m pytest tests/test_ui.py  # specific file
```

## Committing

Фиксировать результат только после принятия пользователем.

Не фиксировать промежуточные изменения.

## Notes

- Entry point: `somafm_tui/player.py` → `main()` method
- Key modules: `ui.py` (display/rendering), `core/playback.py` (audio control), `player.py` (main loop)
- Uses curses for terminal UI - watch for `clrtoeol()` artifact issues in partial redraws
- Tests mock curses heavily; pass proper Mock objects with `getmaxyx.return_value`
- Volume bar rendering requires calling `_handle_volume_display()` in both full and partial redraws
- `UIScreen.clear_history()` method required for stop playback to work
- PKGBUILD uses git source with `sha256sums=('SKIP')` - workflow handles this correctly

## Release Process

### Release Checklist
1. Bump version in `pyproject.toml` (e.g., `0.6.14` → `0.6.15`)
2. Commit with message: `release: bump version to X.Y.Z`
3. Push to origin: `git push origin main`
4. Create and push tag: `git tag vX.Y.Z && git push origin vX.Y.Z`
5. Wait for CI/CD workflows to complete

### Publishing Platforms
| Platform | Trigger | Status URL |
|----------|---------|------------|
| GitHub | push pyproject.toml | https://github.com/zsh-ncursed/somafm_tui/releases |
| AUR | tag v* | https://aur.archlinux.org/packages/somafm_tui |
| PyPI | push pyproject.toml | https://pypi.org/project/somafm-tui/ |

### After Publishing
- Verify GitHub Release: check release notes and assets
- Verify PyPI: `pip install somafm-tui==X.Y.Z`
- Verify AUR: `pacman -Ss somafm-tui`