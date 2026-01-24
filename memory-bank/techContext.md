# Tech Context

## Technology Stack
- **Language**: Python 3.11+
- **GUI Framework**: PySide6 (Qt for Python). Uses a mix of QWidgets for complex desktop logic and QML for custom visual components (components in `qml/`).
- **Audio Engine**: `python-vlc` (libVLC bindings) for playback.
- **Analysis**: `librosa` for BPM/Key detection (computationally heavy).
- **Database**: SQLite (via standard `sqlite3` library).
- **Waveforms**: `numpy` for data processing.

## library/Dependencies
- `PySide6`: Core UI.
- `python-vlc`: Audio playback.
- `librosa`: Audio analysis.
- `numpy`: Numerical operations.
- `mutagen` (likely): Metadata reading (implied by typical audio apps, to be confirmed).
- `watchdog` (likely): File system watching (implied by "Auto-scanning", to be confirmed).

## Development Environment
- **OS**: Windows (primary target), compatible with macOS/Linux (mostly).
- **Build System**: `build.py` (custom script) + `pyinstaller` (likely for exe).
- **Assets**: `assets/` folder for images/fonts.

## Key Constraints
- **Performance**: Python's GIL is a bottleneck for audio analysis. Heavy tasks (scanning, waveforms, analysis) must be offloaded to threads (`QThread`).
- **UI Responsiveness**: The main thread (GUI) must never block.
- **File System**: Must handle large directories with thousands of files efficiently.
