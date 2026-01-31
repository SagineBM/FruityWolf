# Building FruityWolf

This page summarizes how to build FruityWolf for distribution. For the full guide, see [BUILD.md](../BUILD.md) in the project root.

## Prerequisites

- Python 3.11+
- Dependencies installed: `pip install -r requirements.txt`
- PyInstaller and icon tools: `pip install pyinstaller Pillow cairosvg`
- **NSIS** (optional, for installer): [nsis.sourceforge.io](https://nsis.sourceforge.io/)

## Quick build

### 1. Create icon (if needed)

If `assets/icon.ico` does not exist:

```bash
python scripts/create_icon.py
```

### 2. Build executable

```bash
python build.py
```

Output: `dist/FruityWolf/` with `FruityWolf.exe` and bundled dependencies.

### 3. Create installer (optional)

```bash
python build.py --installer
```

Output: `dist/FruityWolf-Setup.exe`.

## Build options

| Option | Description |
|--------|-------------|
| `python build.py` | Build executable only |
| `python build.py --installer` | Build executable and NSIS installer |
| `python build.py --clean` | Clean build directories |
| `python build.py --assets` | Create placeholder assets |

## What gets bundled

- Python code (`FruityWolf/`)
- QML files (`qml/`)
- Assets (`assets/`)
- Resources/icons (`FruityWolf/resources/`)
- PySide6, VLC (if available), NumPy, SoundFile, Mutagen, Watchdog
- Application icon

## Testing the build

1. Go to `dist/FruityWolf/`.
2. Run `FruityWolf.exe`.
3. Confirm the app starts, scans a library, and plays audio.

## Troubleshooting

- **Icon not showing:** Ensure `assets/icon.ico` exists; run `python scripts/create_icon.py`.
- **Missing DLLs:** Check that PyInstaller collects all required modules (e.g. `--collect-all PySide6`).
- **Large size:** The folder is typically 150–300 MB; use `--exclude-module` for unused modules and UPX if desired.

For more detail, see [BUILD.md](../BUILD.md).
