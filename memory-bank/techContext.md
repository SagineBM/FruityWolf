# Tech Context

**Last Updated:** 2026-01-29

## Technology Stack

### Core
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Runtime |
| PySide6 | 6.6.0-6.7.x | UI framework |
| SQLite | 3.x | Database |
| VLC | 3.0+ | Audio playback |

### UI
- **PySide6** — Qt for Python (QWidgets + QML hybrid)
- **QML** — Modern fluid UI components
- **QSS** — Qt Style Sheets for theming

### Audio
- **python-vlc** — Primary playback (libVLC bindings)
- **Qt Multimedia** — Fallback playback
- **soundfile** — Audio I/O
- **numpy** — Waveform processing

### Analysis
- **librosa** — BPM/Key detection (optional, heavy)
- **scipy** — Signal processing
- **mutagen** — Audio metadata

### FL Studio Integration
- **pyflp>=2.0.0** — FLP file parsing

### File System
- **watchdog** — File system watching

### Build
- **pyinstaller** — Windows executable
- **Pillow** — Image processing (icon creation)

---

## Dependencies

### requirements.txt
```
PySide6>=6.6.0,<6.8.0
python-vlc>=3.0.20
numpy>=1.26.0,<2.0.0
soundfile>=0.12.1
scipy>=1.11.0
librosa>=0.10.1
pyflp>=2.0.0
mutagen>=1.47.0
watchdog>=3.0.0
Pillow>=10.1.0
```

### requirements-minimal.txt
Core dependencies only (no librosa for faster install).

---

## Development Environment

### OS Support
- **Windows 10/11** — Primary target
- **macOS** — Compatible (mostly)
- **Linux** — Compatible (mostly)

### Python Version
- **3.11+** required (for Enum compatibility with pyflp)

### IDE
- **Cursor** — Recommended (AI-assisted)
- **VS Code** — Compatible

### Build Tools
- **pyinstaller>=6.3.0** — Executable creation
- **NSIS** — Installer creation (optional)

---

## Key Constraints

### Performance
- **GIL limitation** — Heavy tasks must use threads
- **UI responsiveness** — Main thread never blocks
- **Memory** — Target <400MB for typical usage

### Compatibility
- **Python 3.11+** — Required for pyflp Enum compatibility
- **PySide6 6.6-6.7** — Avoid 6.8+ (breaking changes)
- **VLC** — User must have VLC installed

### File System
- **Large directories** — Must handle 10k+ files
- **Unicode paths** — Must support international characters
- **Missing files** — Must handle gracefully

---

## Database Configuration

### SQLite Settings
```python
# WAL mode for concurrency
PRAGMA journal_mode=WAL;

# Synchronous for safety
PRAGMA synchronous=NORMAL;

# Foreign keys enabled
PRAGMA foreign_keys=ON;
```

### Schema Version
- **Current:** 17
- **Managed by:** migrations.py

---

## Audio Configuration

### Supported Formats
- `.wav`, `.mp3`, `.flac`, `.ogg`, `.m4a`, `.aiff`, `.aif`

### Waveform Settings
- **Bins:** 4000 peaks
- **Cache:** File-based, signature-keyed

---

## Project Files

### FL Studio
- `.flp` — Project files
- `*.wav`, `*.mp3` — Renders (root level)
- `Audio/`, `Samples/`, `Backup/` — Subfolders

### App Data
```
%APPDATA%/FruityWolf/
├── library.db      # SQLite database
├── config.json     # User settings
├── cache/          # Waveforms, thumbnails
└── fruity.log      # Log file
```

---

## Build Output

```
dist/FruityWolf/
├── FruityWolf.exe  # Main executable
├── _internal/      # Python runtime
├── qml/            # QML files
├── assets/         # App assets
└── FruityWolf/resources/  # Icons
```

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `APPDATA` | Windows app data location |
| `VLC_PLUGIN_PATH` | VLC plugins (if needed) |

---

## Known Limitations

1. **VLC required** — User must install VLC for playback
2. **Windows primary** — Mac/Linux less tested
3. **librosa heavy** — Analysis startup is slow
4. **Large files** — Some FLP files may timeout parsing

---

## Quick Commands

```bash
# Run application
python -m FruityWolf

# Run tests
python -m pytest tests/

# Build executable
python build.py

# Create installer
python build.py --installer

# Format code
python -m black FruityWolf/

# Lint code
python -m ruff FruityWolf/
```
