# Installation

## From release (recommended)

1. Download `FruityWolf-Setup.exe` from [Releases](https://github.com/FruityWolf/FruityWolf/releases).
2. Run the installer.
3. Launch FruityWolf from the Start Menu or Desktop shortcut.

No Python or VLC installation is required; the installer guides you through setup.

## From source

### Prerequisites

- **Python 3.11+** — [python.org](https://www.python.org/downloads/)
- **VLC** — Required for audio playback. [Download VLC](https://www.videolan.org/vlc/) and install it; FruityWolf uses it for playback.
- **Git** — To clone the repository.

### Steps

```bash
git clone https://github.com/FruityWolf/FruityWolf.git
cd FruityWolf

# Create virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m FruityWolf
```

### Optional: BPM/Key analysis

For automatic BPM and key detection (heavier dependencies):

```bash
pip install "fruitywolf[analysis]"
```

This adds `scipy` and `librosa`. Startup may be slower when analysis is enabled.

### Optional: Development tools

For formatting, linting, and tests:

```bash
pip install "fruitywolf[dev]"
```

See [Development](development.md) for details.

## First run

On first launch, FruityWolf will:

1. Create its app data directory (e.g. `%APPDATA%\FruityWolf` on Windows).
2. Create a default `config.json` if none exists.
3. Show the first-run wizard so you can set your library folder(s).

You can change library roots and other settings later in **Settings**.

## System requirements

- **OS:** Windows 10/11 (primary); macOS and Linux are partially supported.
- **RAM:** 4 GB minimum, 8 GB recommended for large libraries.
- **Storage:** 500 MB for the app plus space for cache (waveforms, thumbnails).

## Troubleshooting

### "VLC not found" or playback fails

Install [VLC](https://www.videolan.org/vlc/) and ensure it is on your PATH or in the default install location. On Windows, the default is typically `C:\Program Files\VideoLAN\VLC`.

### Python version

FruityWolf requires Python 3.11 or newer. Check with:

```bash
python --version
```

### Missing modules

If you see `ModuleNotFoundError`, ensure the virtual environment is activated and dependencies are installed:

```bash
pip install -r requirements.txt
```
