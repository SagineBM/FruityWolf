# FruityWolf

> **"Spotify for Producers"** — A beautiful, modern library manager and player for FL Studio project folders.

![FruityWolf](assets/banner.png)

## Features

### 🎵 Spotify-grade Experience
- **Modern Dark Theme** with glass morphism and smooth animations
- **Instant In-App Playback** — No external players needed
- **Waveform Visualization** with playhead, zoom, and scrubbing
- **Keyboard Shortcuts** for power users

### 📚 Intelligent Library Management
- **Auto-scanning** of FL Studio project folders
- **BPM & Key Detection** (auto-guess + manual override)
- **Tags & Notes** — Organize with mood, genre, and custom tags
- **Favorites & Playlists** — Multiple playlists with drag/drop

### 🔍 Powerful Search
- Full-text search across track names, projects, tags, notes
- Filter by BPM range, Key, Tags, Favorites

### 📂 Project Drill-down
- Open FLP files directly
- Browse Stems, Samples, Audio, Backup subfolders
- Preview all audio files in-app

### 🛡️ Non-Destructive
- Never moves or modifies your files
- Only indexes and caches thumbnails/waveforms

## Installation

### From Release (Recommended)
1. Download `FruityWolf-Setup.exe` from [Releases](../../releases)
2. Run the installer
3. Launch FruityWolf

### From Source
```bash
# Clone the repository
git clone https://github.com/yourusername/fl-library-pro.git
cd fl-library-pro

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m FruityWolf
```

## Building from Source

```bash
# Build Windows executable
python build.py
```

The executable will be in `dist/FruityWolf/`.

## System Requirements

- **OS:** Windows 10/11
- **Python:** 3.11+ (for development)
- **RAM:** 4GB minimum, 8GB recommended
- **Storage:** 500MB for app + cache space

## Configuration

App data is stored in `%APPDATA%\FruityWolf\`:
- `config.json` — User settings
- `library.db` — Track database
- `cache/` — Waveform and thumbnail cache

## Keyboard Shortcuts

Press `?` or `F1` in the app to see all shortcuts.

### Playback
| Shortcut | Action |
|----------|--------|
| `Space` | Play/Pause |
| `→` | Next track |
| `←` | Previous track |
| `↑` | Volume up |
| `↓` | Volume down |
| `M` | Toggle mute |
| `S` | Toggle shuffle |
| `R` | Cycle repeat mode (None → All → One) |

### Navigation
| Shortcut | Action |
|----------|--------|
| `Ctrl+/` | Focus search |
| `Ctrl+1` | Go to Library |
| `Ctrl+2` | Go to Favorites |
| `Ctrl+3` | Go to Playlists |
| `Ctrl+4` | Go to Settings |
| `J` | Select next track |
| `K` | Select previous track |
| `Enter` | Play selected track |
| `Esc` | Clear search |

### UI Controls
| Shortcut | Action |
|----------|--------|
| `Ctrl+B` | Toggle sidebar |
| `Ctrl+D` | Toggle details panel |
| `F5` | Rescan library |
| `Ctrl+L` | Toggle favorite |
| `?` | Show keyboard shortcuts help |


## File Structure

```
FL Library Pro/
├── FruityWolf/
│   ├── __init__.py
│   ├── __main__.py
│   ├── app.py              # Main application
│   ├── database/           # SQLite models & migrations
│   ├── scanner/            # Library scanning
│   ├── player/             # Audio playback
│   ├── waveform/           # Waveform extraction
│   ├── analysis/           # BPM/Key detection
│   ├── ui/                 # QML UI components
│   └── utils/              # Utilities
├── qml/                    # QML UI files
├── assets/                 # Icons, fonts, images
├── requirements.txt
├── build.py
└── README.md
```

## License

MIT License — See [LICENSE](LICENSE)

## Acknowledgments

- Built with [PySide6](https://doc.qt.io/qtforpython-6/)
- Audio powered by [python-vlc](https://github.com/oaubert/python-vlc)
- Waveform visualization with [NumPy](https://numpy.org/)
- BPM detection with [librosa](https://librosa.org/)
