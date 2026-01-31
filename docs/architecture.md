# Architecture

FruityWolf uses a **layered modular architecture** with PySide6 (Qt) for the frontend and Python/SQLite for the backend.

## High-level layers

```
┌─────────────────────────────────────┐
│   Presentation Layer (UI)           │
│   PySide6 / QML Hybrid              │
│   Views • Panels • Delegates        │
└─────────────────────────────────────┘
           ↕ Qt Signals
┌─────────────────────────────────────┐
│   Domain Logic Layer                │
│   Scanner • Classifier • Player      │
│   FLP Parser • Analysis • Waveform  │
└─────────────────────────────────────┘
           ↕ SQL
┌─────────────────────────────────────┐
│   Data Layer                         │
│   SQLite (WAL mode)                  │
│   Migrations • Cache                 │
└─────────────────────────────────────┘
```

## Main modules

| Layer | Module | Purpose |
|-------|--------|---------|
| **UI** | `app.py` | Main window, navigation, global state |
| **UI** | `ui/views/` | High-level screens (e.g. ProjectsView) |
| **UI** | `ui/panels/` | Detail panels (project, track, plugins) |
| **UI** | `ui/view_models/` | Qt data models for tables/lists |
| **UI** | `ui/delegates/` | Custom cell/widget rendering |
| **Domain** | `scanner/` | Library scanning, project detection, render classification |
| **Domain** | `flp_parser/` | FL Studio project file parsing (PyFLP) |
| **Domain** | `classifier/` | Project lifecycle classification |
| **Domain** | `player/` | Audio playback (VLC + Qt fallback) |
| **Domain** | `analysis/` | BPM/Key detection (optional) |
| **Domain** | `waveform/` | Waveform extraction and cache |
| **Data** | `database/` | SQLite schema, migrations, queries |

## Key patterns

### Model/View/Delegate

Large lists (projects, plugins, samples) use Qt’s Model/View pattern:

- **Model** — Subclass of `QAbstractTableModel` (or similar) providing data.
- **View** — `QTableView` (or list view) displaying the model.
- **Delegate** — Custom painting/editing for cells (e.g. icons, progress).

This keeps UI responsive and avoids creating a widget per row.

### Background work

Heavy work (scanning, analysis, waveform generation) runs off the UI thread via:

- `QThread` / `QRunnable` and thread pools
- Qt signals to update the UI when work completes

The UI thread is never blocked by I/O or long-running loops.

### Database

- **SQLite** with WAL mode for concurrency.
- **Migrations** — Schema changes are versioned in `database/migrations.py`.
- **Parameterized queries** — All user input is passed as parameters.
- **Batch transactions** — Bulk updates use batches (e.g. 50 items per commit) to reduce overhead.

## Scanner overview

The scanner uses a **three-pass** strategy:

1. **Pass 1 — Project detection:** Find FL Studio project folders under library roots (scoring: .flp presence, Audio/Samples/Backup folders).
2. **Pass 2 — Batch project scan:** For each project, detect renders, parse FLP if changed, classify state, update DB. Uses incremental and parallel scanning where applicable.
3. **Pass 3 — Orphan FLP scan:** Handle flat folders where FLPs and audio live in the same directory (name-based matching).

Performance is improved by schema caching, incremental scanning (skip unchanged projects), FLP parse caching, duration caching, and batched DB writes.

## Technology stack

| Area | Technologies |
|------|---------------|
| **Runtime** | Python 3.11+ |
| **UI** | PySide6 (Qt for Python), QML, QSS |
| **Database** | SQLite 3 |
| **Audio** | python-vlc (primary), Qt Multimedia (fallback), soundfile, numpy |
| **FLP** | pyflp ≥ 2.0 |
| **Analysis** | librosa, scipy (optional) |
| **Build** | PyInstaller, Pillow (icons) |

For more detail on dependencies and versions, see [Development](development.md) and the root [pyproject.toml](../pyproject.toml).
