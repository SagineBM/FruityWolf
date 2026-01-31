# Development

Guide for setting up a development environment and working on FruityWolf.

## Prerequisites

- **Python 3.11+**
- **VLC** installed (for playback)
- **Git**

## Setup

```bash
git clone https://github.com/FruityWolf/FruityWolf.git
cd FruityWolf

python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
pip install "fruitywolf[dev]"   # Black, Ruff, pytest
```

Optional: `pip install "fruitywolf[analysis]"` for BPM/Key analysis.

## Running the app

```bash
python -m FruityWolf
```

The app uses config and data under your user app data directory (e.g. `%APPDATA%\FruityWolf` on Windows), not the repo. See [Configuration](configuration.md).

## Running tests

```bash
pytest tests/
pytest tests/ -v          # Verbose
pytest tests/ -k "name"  # Run tests matching "name"
```

Tests use the project’s `tests/` directory and `pyproject.toml` [tool.pytest.ini_options].

## Code style

- **Black** — Formatting (line length 100, Python 3.11+).
- **Ruff** — Linting (pycodestyle, Pyflakes, isort, bugbear, comprehensions).

Commands:

```bash
black FruityWolf tests scripts
ruff check FruityWolf tests scripts
```

Configuration is in [pyproject.toml](../pyproject.toml) under `[tool.black]` and `[tool.ruff]`.

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/run_migrations.py` | Run database migrations |
| `scripts/verify_env.py` | Check Python and dependencies |
| `scripts/create_icon.py` | Generate icon from SVG |
| `scripts/debug_renders.py` | Inspect render data for projects |
| `scripts/check_project_files.py` | Verify project file structure |
| `scripts/check_renders.py` | Check render data |
| `scripts/check_dates.py` | Check date consistency |
| `scripts/check_library_tracks.py` | Verify library tracks |
| `scripts/fix_project_dates.py` | Fix project dates from renders |
| `scripts/fix_track_dates.py` | Fix track dates |
| `scripts/fix_schema.py` | Schema repair utilities |
| `scripts/setup_dev_windows.ps1` | Windows dev setup (PowerShell) |

Run from the project root, e.g.:

```bash
python scripts/verify_env.py
```

## Dependencies

- **requirements.txt** — Full install (includes analysis: scipy, librosa).
- **requirements-minimal.txt** — Core only (faster install, no librosa).
- **pyproject.toml** — Package metadata and optional extras: `analysis`, `dev`, `full`.

## Config and data location

At runtime the app does **not** use `config.json` in the repo. It uses:

- **Windows:** `%APPDATA%\FruityWolf\`
- **macOS:** `~/Library/Application Support/FruityWolf/`
- **Linux:** `~/.local/share/FruityWolf/` (or `$XDG_DATA_HOME`)

Contents: `config.json`, `library.db`, `cache/`, `fruity.log`. A sample config for reference is [config.sample.json](../config.sample.json) in the repo.

## Build

See [Building](building.md) and [BUILD.md](../BUILD.md).

```bash
python build.py
python build.py --installer
```

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for pull request workflow and code of conduct.
