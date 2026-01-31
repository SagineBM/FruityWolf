# Configuration

FruityWolf stores user settings and data in an **app data directory**, not in the project folder. The config file is created automatically on first run.

## Config file location

| OS | Path |
|----|------|
| **Windows** | `%APPDATA%\FruityWolf\config.json` |
| **macOS** | `~/Library/Application Support/FruityWolf/config.json` |
| **Linux** | `~/.local/share/FruityWolf/config.json` (or `$XDG_DATA_HOME/FruityWolf/config.json`) |

When you run the app (from source or from the built executable), it reads and writes this file. The repo contains **config.sample.json** as a reference only; the app does not use it at runtime.

## Sample config structure

The following mirrors [config.sample.json](../config.sample.json). Your actual `config.json` may contain extra keys or defaults added by the app.

| Field | Description |
|-------|-------------|
| `name` | Application name (informational) |
| `version` | Config / app version (informational) |
| `default_library_root` | Default folder to scan for FL Studio projects. Can be empty; user sets library roots in Settings or first-run wizard. |
| `audio_extensions` | List of audio file extensions (e.g. `.wav`, `.mp3`, `.flac`) |
| `project_file_extension` | Project file extension (`.flp`) |
| `subfolders` | Names of standard subfolders: `audio`, `samples`, `stems`, `backup` |
| `settings.theme` | UI theme (e.g. `"dark"`) |
| `settings.default_volume` | Default volume 0.0–1.0 |
| `settings.waveform_cache_size_mb` | Max size in MB for waveform cache |
| `settings.auto_scan_on_startup` | Whether to scan library on startup |
| `settings.watch_for_changes` | Whether to watch the library folder for changes |

## App data directory contents

```
%APPDATA%\FruityWolf\
├── config.json    # User settings (created on first run)
├── library.db     # SQLite database (tracks, projects, etc.)
├── cache/         # Waveforms, thumbnails
│   └── waveforms/
└── fruity.log     # Log file (if logging to file)
```

## Using the sample config

To start from a known-good config (e.g. after a clean install):

1. Copy `config.sample.json` from the repo (or from the docs) into your app data folder.
2. Rename the copy to `config.json`.
3. Set `default_library_root` to your FL Studio project root if desired, or leave it empty and set library roots in the app (Settings or first-run wizard).

Do not commit your real `config.json` if it contains local paths; it is listed in `.gitignore`.
