# FruityWolf Ecosystem Overview

**Last Updated:** 2026-01-29  
**Version:** 2.0.0

## Documentation Index

### Core Files (memory-bank/)
| File | Purpose | Update |
|------|---------|--------|
| `projectBrief.md` | Project goals and scope | On change |
| `activeContext.md` | Current focus, blockers | Daily |
| `progress.md` | Task completion status | Daily |
| `systemPatterns.md` | Architecture patterns | On change |
| `techContext.md` | Technology stack | On change |
| `systemHealth.md` | Performance status | On change |

### Reference Files
| File | Purpose |
|------|---------|
| `codebaseReport.md` | Complete codebase analysis |
| `featureChecklist.md` | Feature status |
| `optimizationOpportunities.md` | Performance roadmap |
| `QUICK_REFERENCE.md` | Quick reference guide |

### Project Root Files
| File | Purpose |
|------|---------|
| `.cursorrules` | AI agent rules |
| `AGENTS.md` | Agent instructions |
| `ROADMAP.md` | Feature roadmap |
| `README.md` | User documentation |
| `BUILD.md` | Build instructions |

## Architecture

```
┌─────────────────────────────────────┐
│   Presentation (UI)                  │
│   PySide6/QML • Views • Panels      │
└─────────────────────────────────────┘
                ↕
┌─────────────────────────────────────┐
│   Domain Logic                       │
│   Scanner • Classifier • Player     │
│   FLP Parser • Analysis • Waveform  │
└─────────────────────────────────────┘
                ↕
┌─────────────────────────────────────┐
│   Data Layer                         │
│   SQLite • Migrations • Cache       │
└─────────────────────────────────────┘
```

## Data Flow

### Scanning
```
LibraryScanner → Detect Projects → Parse FLP → Classify → Database
```

### Playback
```
User → AudioPlayer → VLC → Waveform → UI
```

### Classification
```
Project Signals → Rules Engine → State/Score/Action → Database
```

## Module Summary

| Module | Purpose | Key File |
|--------|---------|----------|
| core | Config, constants | config.py |
| database | SQLite layer | models.py, migrations.py |
| scanner | Library indexing | library_scanner.py |
| flp_parser | FLP parsing | parser.py |
| classifier | Project states | engine.py |
| player | Audio playback | audio_player.py |
| analysis | BPM/Key detection | detector.py |
| waveform | Visualization | extractor.py |
| ui | User interface | projects_view.py |
| utils | Utilities | helpers.py, path_utils.py |

## Database Tables

| Table | Purpose |
|-------|---------|
| projects | FL Studio project folders |
| renders | Audio renders (with primary) |
| project_plugins | Plugins from FLP |
| project_samples | Samples from FLP |
| tracks | Legacy audio files |
| tags | User tags |
| playlists | User playlists |

**Current Schema:** Version 17

## Performance Status

| Component | Status |
|-----------|--------|
| Projects View | ✅ Model/View pattern |
| Signal Throttling | ✅ 50ms minimum |
| Database | ✅ WAL mode |
| Pagination | ✅ Infinite scroll |
| Cover Loading | ⚠️ Needs async |

## Test Coverage

- **Unit Tests**: Partial (~20%)
- **Integration**: Minimal
- **UI Tests**: None

## Build & Distribution

- Build: `python build.py`
- Output: `dist/FruityWolf/`
- Installer: Planned

## Quick Commands

```bash
python -m FruityWolf          # Run app
python -m pytest tests/       # Run tests
python build.py               # Build exe
```

## For AI Agents

1. Read `.cursorrules` first
2. Check `activeContext.md` for focus
3. Use Cursor commands (`.cursor/commands/`)
4. Update docs after changes
