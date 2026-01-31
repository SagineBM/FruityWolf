# System Patterns

**Last Updated:** 2026-01-30

## Architecture Overview

FruityWolf follows a **layered modular architecture** using PySide6 (Qt) for the frontend and Python/SQLite for the backend.

```
┌─────────────────────────────────────┐
│   Presentation Layer (UI)            │
│   PySide6/QML Hybrid                 │
│   Views • Panels • Delegates         │
└─────────────────────────────────────┘
           ↕ Qt Signals
┌─────────────────────────────────────┐
│   Domain Logic Layer                 │
│   Scanner • Classifier • Player     │
│   FLP Parser • Analysis • Waveform  │
└─────────────────────────────────────┘
           ↕ SQL
┌─────────────────────────────────────┐
│   Data Layer                         │
│   SQLite (WAL mode)                  │
│   Migrations • Cache                 │
└─────────────────────────────────────┘
```

---

## Scanner Architecture & Algorithms

### Three-Pass Scanning Strategy

The scanner uses a **three-pass approach** for optimal performance:

#### Pass 1: Project Detection
- Scans library roots for FL Studio project folders
- Uses scoring-based detection (`fl_project_detector.py`)
- Scoring rules:
  - +5 if root contains `.flp`
  - +3 if `Backup/` contains `.flp`
  - +1 for each directory: `Audio/`, `Samples/`, `Backup/`
  - Score >= 5 = FL Studio project

#### Pass 2: Batch Project Scanning
- Processes projects in **batches of 50** per transaction
- **Incremental scanning**: Only scans projects modified since last scan
- **Parallel scanning**: Optional ThreadPoolExecutor (default 1, recommended 4-8 workers)
- Each project:
  1. Detects renders (root-level audio only)
  2. Parses FLP (if changed since last parse)
  3. Classifies project state
  4. Updates database

#### Pass 3: Orphan FLP Scanning
- Scans for FLPs directly in library roots (flat folder structures)
- Uses smart name matching to associate audio files with FLPs
- Handles old FL Studio workflows where FLPs and audio are in same folder

### Performance Optimizations

#### Schema Caching
```python
# Cache schema info once at scan start (eliminates thousands of PRAGMA queries)
self._cache_schema_info()  # Checks: renders_table, primary_render_id, file_created_at columns
```

**Impact**: Eliminates repeated `PRAGMA table_info()` queries during scanning.

#### Incremental Scanning
```python
def _project_needs_scan(self, proj_path: Path) -> bool:
    """Check if project modified since last scan."""
    last_scan = self._project_last_scans.get(str(proj_path))
    if last_scan is None:
        return True  # New project
    
    # Check folder mtime + most recent file mtime
    folder_mtime = proj_path.stat().st_mtime
    latest_mtime = max(item.stat().st_mtime for item in proj_path.iterdir() if item.is_file())
    return latest_mtime > last_scan
```

**Impact**: Skips unchanged projects, dramatically faster rescans.

#### FLP Parse Caching
```python
# Only parse if FLP modified since last parse
needs_flp_parse = (
    is_new or 
    existing_flp_parsed_at is None or 
    flp_mtime > existing_flp_parsed_at
)
```

**Impact**: Skips re-parsing unchanged FLP files (saves 100-200ms per project).

#### Smart Duration Caching
```python
def get_duration_smart(path: Path, current_mtime: int) -> float:
    """Reuse cached duration if file mtime unchanged."""
    if cached_mtime == current_mtime and cached_duration:
        return cached_duration  # Skip Mutagen call
    
    # Only compute duration for new/changed files
    return mutagen_duration(path)
```

**Impact**: Skips expensive Mutagen calls for unchanged renders.

#### Batch Transactions
```python
BATCH_SIZE = 50  # Projects per transaction
with batch_transaction():
    for project in batch:
        save_project(project)  # No auto-commit
    # Single commit for entire batch
```

**Impact**: Reduces database overhead by 50x (1 commit per 50 projects vs 1 per project).

#### Parallel Scanning
```python
# Parallel file I/O (database writes still serialized)
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(self._scan_project, path): path for path in batch}
    for future in as_completed(futures):
        result = future.result()
```

**Impact**: 2-4x faster scanning on multi-core systems (I/O parallelized, DB serialized).

### File Creation Date Tracking

**Purpose**: Sort projects/tracks by **original file creation date** (Windows "Date created"), not scan time.

**Implementation**:
```python
def get_file_created_at(path: Path) -> int:
    """Get original file creation timestamp."""
    stat = path.stat()
    if hasattr(stat, 'st_birthtime'):  # Windows Python 3.12+
        return int(stat.st_birthtime)  # True creation time
    return int(stat.st_ctime)  # Fallback (creation on Windows, inode change on Unix)
```

**Usage in Queries**:
```sql
-- Projects sorted by original file creation date
ORDER BY COALESCE(file_created_at, created_at) DESC

-- Tracks sorted by original file creation date  
ORDER BY COALESCE(t.file_created_at, t.created_at) DESC
```

**Priority**:
1. FLP file creation date (if exists)
2. Primary render creation date (if no FLP)
3. Project folder creation date (fallback)

**Database Columns**:
- `projects.file_created_at` (Migration 19)
- `tracks.file_created_at` (Migration 20)
- `renders.file_created_at` (Migration 21)

**Update Strategy**:
- Uses `COALESCE(NULLIF(file_created_at, 0), ?)` to preserve existing values
- Only updates if NULL or 0 (preserves user-set values)

---

## Presentation Layer

### UI Framework
- **PySide6** (Qt for Python) — Primary framework
- **QML** — Modern components (hybrid approach)
- **QSS** — Styling (Qt Style Sheets)

### Structure
- `app.py` — MainWindow, global state, navigation
- `ui/views/` — High-level screens (ProjectsView, etc.)
- `ui/panels/` — Detail panels (ProjectDetails, etc.)
- `ui/view_models/` — Qt data models
- `ui/delegates/` — Custom rendering
- `ui/widgets.py` — Reusable components

### Key Pattern: Model/View/Delegate

For large lists (projects, plugins, samples):

```python
# Model: Provides data
class ProjectsModel(QAbstractTableModel):
    def data(self, index, role):
        # Return data for role
        pass

# View: Displays data
table_view = QTableView()
table_view.setModel(projects_model)

# Delegate: Custom rendering
class ProjectsDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        # Custom painting without creating widgets
        pass
```

**Why**: Prevents lag with 10k+ items by avoiding widget creation per row.

---

## Domain Logic Layer

### Scanner Module
- **LibraryScanner**: Background scanning with QThread
- **Three-pass scanning**: Detection → Batch scan → Orphan FLPs
- **Incremental scanning**: Skips unchanged projects
- **Parallel scanning**: ThreadPoolExecutor for file I/O
- **Schema caching**: Eliminates repeated PRAGMA queries
- **FLP parse caching**: Skips unchanged FLPs
- **Smart duration caching**: Reuses cached durations
- **Identity layer**: Write-through layer populating `project_files` and `file_signals`
- **Signal-based matching**: Token overlap + mtime + fingerprint for flat folders
- **Conflict prevention**: Greedy bipartite matching prevents duplicate assignments

### FL Project Detector
- **Scoring-based detection**: +5 for root FLP, +3 for Backup FLP, +1 per directory
- **Multiple FLP support**: Tracks all FLPs, selects primary (newest in root)

### Render Classifier
- **Root-level audio** = RENDER
- **Audio/** = INTERNAL_AUDIO
- **Samples/** = SOURCE_SAMPLE
- **Optional render subfolders**: Render/, Renders/, Exports/, etc. (configurable)
- **Smart name matching**: Associates audio with FLPs in flat folders

### Classifier Module
- **ProjectClassifier**: Rule-based engine
- JSON-configurable rules
- States: MICRO_IDEA → IDEA → WIP → PREVIEW_READY → ADVANCED

### Player Module
- VLC backend (primary)
- Qt Multimedia fallback
- State machine: PLAYING, PAUSED, STOPPED

### Analysis Module
- BPM detection (librosa)
- Key detection (librosa)
- Background workers

---

## Data Layer

### Database
- **SQLite** with WAL mode enabled
- **23 migrations** for schema versioning (current: 23)
- **FTS5** for full-text search
- **Indexes** on frequently queried columns

### Key Pattern: Batch Transactions
```python
# Batch 50 items per transaction
with batch_transaction():
    for project in batch:
        save_project(project)  # No auto-commit
    # Auto-commit happens here
```

### Key Tables
| Table | Purpose |
|-------|---------|
| projects | FL Studio project folders |
| renders | Audio renders with primary (legacy, maintained for compatibility) |
| project_files | **Source of truth** for all files (FLP, renders, backups, stems) |
| file_signals | Evidence signals for file matching (name tokens, mtime, etc.) |
| metadata_review_queue | Uncertain metadata changes requiring user review |
| project_plugins | Plugins from FLP |
| project_samples | Samples from FLP |
| tracks | Legacy audio files (linked to renders) |
| tags, playlists | Organization |

### File Creation Date Columns
- `projects.file_created_at` — Original FLP/render creation date
- `tracks.file_created_at` — Original render creation date
- `renders.file_created_at` — Original render creation date

### Identity System (Migration 23+)
- **Project Identity (PID)**: Stable UUID per project, never derived from file hash
- **Confidence Scoring**: 0-100 score for file matching and project quality
- **User Locks**: Prevents metadata drift (`user_locked=1` blocks auto-updates)
- **DAW Type**: Foundation for multi-DAW support (`daw_type` column)
- **Signal-Based Matching**: Token overlap, mtime proximity, previously seen fingerprint
- **Conflict Prevention**: Greedy bipartite matching ensures one audio → one FLP
- **Metadata Drift Prevention**: Confidence thresholds (85% for auto-update), review queue

---

## Design Patterns Used

### 1. Model/View/Delegate (Qt)
- All large tables use this pattern
- Enables virtualization
- Custom rendering without widgets

### 2. Worker Threads (QThread)
- All heavy operations run in background
- Communication via signals only
- Never touch UI from worker

### 3. Signal Throttling
- Progress updates limited to 20fps (50ms minimum)
- Prevents UI flooding during scans

### 4. Schema Caching
- Cache schema info once at scan start
- Eliminates repeated PRAGMA queries
- Module-level cache for UI helpers

### 5. Incremental Scanning
- Track last scan time per project
- Skip unchanged projects (mtime check)
- Dramatically faster rescans

### 6. Batch Processing
- Database writes batched (50 per transaction)
- Reduces overhead significantly

### 7. Caching Strategies
- **Waveform cache**: File-based, signature-keyed
- **FLP parse cache**: Mtime-based, skips unchanged
- **Duration cache**: Mtime-based, skips Mutagen for unchanged files
- **Schema cache**: Module-level, eliminates PRAGMA queries

### 8. Parallel Processing
- ThreadPoolExecutor for file I/O
- Database writes serialized (SQLite WAL)
- Configurable worker count (default 1, recommended 4-8)

### 9. Factory Pattern
- `get_player()` — Player instance
- `get_db()` — Database connection

---

## Anti-Patterns (Forbidden)

### Widget-per-Cell
```python
# ❌ FORBIDDEN - Creates thousands of widgets
for row in data:
    btn = QPushButton("Play")
    table.setCellWidget(row, col, btn)

# ✅ CORRECT - Use delegate
delegate.paint()  # Paint button appearance
```

### UI Thread Blocking
```python
# ❌ FORBIDDEN - Blocks UI
def on_scan_click(self):
    scan_all_projects()  # Heavy operation

# ✅ CORRECT - Background thread
def on_scan_click(self):
    self.scanner_thread.start()
```

### N+1 Queries
```python
# ❌ FORBIDDEN - N+1 queries
for project in projects:
    plugins = get_plugins(project.id)  # N queries

# ✅ CORRECT - Batch query
plugins_map = get_plugins_batch(project_ids)  # 1 query
```

### Unthrottled Signals
```python
# ❌ FORBIDDEN - Floods UI
for item in 10000_items:
    self.progress.emit(i, total)  # 10000 signals

# ✅ CORRECT - Throttled (50ms minimum)
if time.time() - last_emit > 0.05:
    self.progress.emit(i, total)
```

### Repeated Schema Queries
```python
# ❌ FORBIDDEN - Repeated PRAGMA queries
for project in projects:
    has_renders = query("PRAGMA table_info(renders)")  # N queries

# ✅ CORRECT - Cache once
self._cache_schema_info()  # Once at start
has_renders = self._has_renders_table  # Cached value
```

---

## Performance Invariants

1. **UI thread < 16ms** — Never block longer
2. **20fps signal limit** — Throttle progress updates (50ms minimum)
3. **50 items per batch** — Database transactions
4. **WAL mode always on** — Concurrent access
5. **Virtualization** — No widget-per-row
6. **Schema cache** — No repeated PRAGMA queries
7. **Incremental scan** — Skip unchanged projects
8. **FLP cache** — Skip unchanged FLP parsing
9. **Duration cache** — Skip Mutagen for unchanged files
10. **Fast fingerprinting** — 64KB chunk only during scan (full hash lazy)
11. **Signal-based matching** — Token overlap + mtime + fingerprint (no full file reads)

---

## Module Dependencies

```
app.py
├── ui/ (all views, panels, models, delegates)
├── scanner/ (library_scanner, detectors)
│   ├── identity/ (fingerprint, signals, identity_store)
│   ├── adapters/ (base, fl_studio)
│   └── flp_parser/
├── player/ (audio_player)
├── classifier/ (engine)
├── database/ (models, migrations, project_metadata)
├── analysis/ (detector)
├── waveform/ (extractor)
├── services/ (cover_manager)
└── utils/ (helpers, icons, path_utils)
```

---

## Future Architecture Improvements

1. **Split app.py** — Extract into smaller modules
2. **Repository Pattern** — Centralize all database access
3. **Service Layer** — Extract business logic from UI
4. **Event Bus** — Decouple components further
5. **Plugin System** — Allow extensions
