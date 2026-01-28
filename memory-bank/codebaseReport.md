# FruityWolf Codebase Report
**Generated:** 2026-01-28  
**Status:** Complete Analysis

## Executive Summary

FruityWolf is a PySide6-based desktop application for managing FL Studio project libraries. The codebase is **moderately sized** (~15,000+ lines) with a **well-structured modular architecture**. Current state: **Beta/Production-ready** with some scalability improvements needed.

### Key Metrics
- **Total Modules:** 25+ Python modules
- **UI Components:** 36+ QML/Python files
- **Database Tables:** 12+ tables with migrations
- **Lines of Code:** ~15,000+ (estimated)
- **Architecture:** MVC-like with Model/View/Delegate pattern

---

## Architecture Overview

### Layer Structure

```
┌─────────────────────────────────────┐
│   Presentation Layer (UI)            │
│   - PySide6/QML Hybrid               │
│   - Views, Panels, Delegates         │
└─────────────────────────────────────┘
           ↕ Signals
┌─────────────────────────────────────┐
│   Domain Logic Layer               │
│   - Scanner, Classifier, Player     │
│   - FLP Parser, Analysis            │
└─────────────────────────────────────┘
           ↕ SQL
┌─────────────────────────────────────┐
│   Data Layer                        │
│   - SQLite Database                 │
│   - Migrations System               │
└─────────────────────────────────────┘
```

---

## Module Breakdown

### 1. Core Application (`FruityWolf/app.py`)
**Status:** ✅ Complete but large (2800+ lines)  
**Purpose:** Main window, navigation, global state management

**Key Features:**
- MainWindow class with QStackedWidget navigation
- Player integration (VLC-based)
- Queue panel (Now Playing / Next Up)
- Command palette (Ctrl+/)
- Settings integration
- Keyboard shortcuts

**Issues:**
- ⚠️ File is very large (should be split)
- ⚠️ Contains too much UI layout logic

**Dependencies:**
- All UI modules
- Scanner, Player, Database

---

### 2. Database Layer (`FruityWolf/database/`)

#### `models.py`
**Status:** ✅ Complete  
**Purpose:** SQLite schema, connection management, query helpers

**Schema:**
- `projects` - FL Studio project folders (main entity)
- `tracks` - Individual audio files (renders)
- `renders` - New render system (Migration 17)
- `project_plugins` - Plugins used in projects (PyFLP)
- `project_samples` - Samples referenced in FLP
- `tags` - User tags (mood/genre/custom)
- `track_tags` - Many-to-many tags
- `playlists` - User playlists
- `playlist_tracks` - Playlist membership
- `library_roots` - Multiple folder support
- `settings` - App settings
- `installed_plugins` - System-wide VST tracking
- `play_history` - Play tracking
- `schema_version` - Migration tracking

**Features:**
- WAL mode enabled (concurrency)
- Full-text search (FTS5)
- Indexes on key columns
- Migration system (17 migrations)

#### `migrations.py`
**Status:** ✅ Complete  
**Purpose:** Schema versioning and upgrades

**Migrations:**
1. Initial schema
2. Schema version table + indexes
3. Extended tags
4. Play history + rating
5. Track state classification
6. User dead column
7. Lyrics column
8. Project signals
9. Phase 1 classification columns
10. Sample usage indexing
11. PyFLP integration (plugins/metadata)
12. Installed plugins table
13. Plugin path tracking
14. Plugin scan roots
15. Plugin metadata expansion
16. Production plugin detection
17. Renders table + primary render

---

### 3. Scanner Module (`FruityWolf/scanner/`)

#### `library_scanner.py`
**Status:** ✅ Complete  
**Purpose:** Background scanning of FL Studio folders

**Features:**
- Multi-threaded scanning (QThread)
- Progress signals (throttled to 20fps)
- FL Studio project detection
- Render classification
- FLP parsing integration
- Sample indexing
- Classification integration

**Performance:**
- ✅ Throttled signals (50ms minimum)
- ✅ WAL mode for concurrency
- ⚠️ Could benefit from batch inserts

#### `fl_project_detector.py`
**Status:** ✅ Complete  
**Purpose:** Detect FL Studio project roots with scoring

**Features:**
- Scoring-based detection
- Multiple FLP file support
- Subfolder analysis

#### `fl_render_classifier.py`
**Status:** ✅ Complete  
**Purpose:** Classify audio files as renders vs samples

**Features:**
- Root-level render detection
- Excludes Audio/Samples/Backup folders
- Duration-based classification

#### `file_watcher.py`
**Status:** ✅ Complete  
**Purpose:** Watch for file system changes

#### `playlist_manager.py`
**Status:** ✅ Complete  
**Purpose:** Playlist CRUD operations

---

### 4. FLP Parser (`FruityWolf/flp_parser/`)

#### `parser.py`
**Status:** ✅ Complete  
**Purpose:** Extract data from FL Studio project files

**Features:**
- Plugin extraction (generators + effects)
- Sample path extraction
- Metadata extraction (tempo, version, title, artist, genre)
- Pattern count
- Plugin name normalization
- Installed plugin matching

**Dependencies:**
- `pyflp>=2.0.0`
- Compatibility patch for Python 3.11+

#### `compatibility.py`
**Status:** ✅ Complete  
**Purpose:** Fix pyflp Enum issues on Python 3.11+

---

### 5. Classifier (`FruityWolf/classifier/`)

#### `engine.py`
**Status:** ✅ Complete  
**Purpose:** Rule-based project classification

**Features:**
- State classification (5 stages + broken)
- Completion scoring (0-100)
- Next action recommendation
- JSON-based rules (data-driven)
- Ruleset versioning (hash)

**States:**
- MICRO_IDEA
- IDEA
- WIP
- PREVIEW_READY
- ADVANCED
- BROKEN_OR_EMPTY

**Rules Files:**
- `signals.json` - Signal definitions
- `project_states.json` - State conditions
- `scoring_rules.json` - Score calculation
- `next_actions.json` - Action mapping

---

### 6. Player Module (`FruityWolf/player/`)

#### `audio_player.py`
**Status:** ✅ Complete  
**Purpose:** Audio playback with VLC backend

**Features:**
- VLC backend (primary)
- Qt Multimedia fallback
- Playlist management
- Shuffle/repeat modes
- Position tracking
- Volume control
- Error handling

**Signals:**
- state_changed
- position_changed
- duration_changed
- track_changed
- volume_changed
- error_occurred

---

### 7. Analysis Module (`FruityWolf/analysis/`)

#### `detector.py`
**Status:** ✅ Complete  
**Purpose:** BPM/Key detection

**Features:**
- BPM detection (librosa)
- Key detection (librosa)
- Confidence scoring
- Background processing

#### `worker_process.py`
**Status:** ✅ Complete  
**Purpose:** Separate process for heavy analysis

---

### 8. Waveform Module (`FruityWolf/waveform/`)

#### `extractor.py`
**Status:** ✅ Complete  
**Purpose:** Generate waveform visualizations

**Features:**
- Peak extraction
- Caching system
- Background generation

---

### 9. UI Layer (`FruityWolf/ui/`)

#### Views
- `projects_view.py` - ✅ Main projects table (Model/View)
- `playlists_view.py` - ✅ Playlist management
- `plugin_intelligence_view.py` - ✅ Plugin analytics
- `sample_overview_view.py` - ✅ Sample usage overview
- `sample_detail_view.py` - ✅ Sample detail view
- `settings_view.py` - ✅ Settings UI

#### Panels
- `project_details.py` - ✅ Project drill-down
- `track_details.py` - ✅ Track metadata
- `plugins_panel.py` - ✅ Plugin list per project
- `plugin_details.py` - ✅ Plugin detail view
- `renders_panel.py` - ✅ Render management
- `sample_projects_panel.py` - ✅ Projects using sample
- `sample_usage_panel.py` - ✅ Sample usage stats

#### Models
- `projects_model.py` - ✅ QAbstractTableModel for projects
- `playlists_model.py` - ✅ Playlist list model
- `playlist_tracks_model.py` - ✅ Playlist tracks model

#### Delegates
- `projects_delegate.py` - ✅ Custom rendering for projects table

#### Other
- `dialogs.py` - ✅ Various dialogs
- `widgets.py` - ✅ Reusable widgets
- `style.py` - ✅ Stylesheet management
- `style_tokens.py` - ✅ Design tokens
- `design_system.py` - ✅ Design system
- `jobs.py` - ✅ Background job manager
- `command_palette.py` - ✅ Command palette
- `shortcuts.py` - ✅ Keyboard shortcuts

---

### 10. Utils (`FruityWolf/utils/`)

- `helpers.py` - ✅ Common utilities
- `icons.py` - ✅ Icon management
- `image_manager.py` - ✅ Image caching
- `path_utils.py` - ✅ Path validation
- `plugin_scanner.py` - ✅ VST scanner
- `plugin_scanner_cli.py` - ✅ CLI plugin scanner
- `shortcuts.py` - ✅ Shortcut definitions

---

### 11. Services (`FruityWolf/services/`)

- `folder_watcher.py` - ✅ File system watching
- `batch_analyzer.py` - ✅ Batch analysis jobs

---

### 12. Core (`FruityWolf/core/`)

- `config.py` - ✅ Configuration management
- `stats_service.py` - ✅ Statistics service

---

## QML Components (`qml/`)

**Status:** ✅ Hybrid UI (QWidgets + QML)

**Files:**
- `Main.qml` - Main QML entry (if used)
- `Theme.qml` - Theme definitions
- `components/` - Reusable QML components
  - `PlayerBar.qml`
  - `WaveformView.qml`
  - `TrackItem.qml`
  - `SearchBar.qml`
  - etc.

**Note:** App primarily uses QWidgets, QML used for specific modern components.

---

## Database Schema Details

### Projects Table
**Columns:**
- Basic: id, name, path, flp_path, audio_dir, samples_dir, stems_dir, backup_dir
- Classification: state_id, state_confidence, state_reason, score, score_breakdown
- Actions: next_action_id, next_action_meta, next_action_reason
- Signals: signals (JSON), user_meta (JSON)
- FLP Metadata: flp_tempo, flp_time_sig, flp_version, flp_title, flp_artist, flp_genre, flp_pattern_count
- Timestamps: last_scan, last_played_ts, classified_at_ts, created_at, updated_at

### Tracks Table
**Columns:**
- Basic: id, project_id, title, path, ext, duration, file_size, mtime
- Analysis: bpm_detected, bpm_user, bpm_confidence, key_detected, key_user, key_confidence
- Metadata: notes, favorite, play_count, last_played, rating, lyrics
- Cache: waveform_cache_path, cover_path

### Renders Table (New)
**Columns:**
- id, project_id, path, filename, ext, file_size, mtime
- duration_s, fingerprint_fast, override_key, override_bpm, label
- is_primary, created_at, updated_at

**Purpose:** Separate renders from general tracks for better FL Studio workflow.

---

## Dependencies

### Core
- `PySide6>=6.6.0,<6.8.0` - UI framework
- `python-vlc>=3.0.20` - Audio playback
- `numpy>=1.26.0,<2.0.0` - Numerical operations

### Analysis
- `soundfile>=0.12.1` - Audio I/O
- `scipy>=1.11.0` - Scientific computing
- `librosa>=0.10.1` - Audio analysis

### FLP Parsing
- `pyflp>=2.0.0` - FL Studio project parsing

### Utilities
- `mutagen>=1.47.0` - Audio metadata
- `watchdog>=3.0.0` - File watching
- `Pillow>=10.1.0` - Image processing

### Build
- `pyinstaller>=6.3.0` - Executable building

---

## Performance Characteristics

### ✅ Optimizations Implemented
1. **Model/View Pattern** - ProjectsView uses QAbstractTableModel
2. **Throttled Signals** - Scanner emits max 20fps
3. **WAL Mode** - Database concurrency enabled
4. **Virtualization** - Table view only renders visible rows
5. **Pagination** - Infinite scroll with page_size=100
6. **Caching** - Waveform cache, image cache

### ⚠️ Known Issues
1. **app.py Size** - Too large, should be split
2. **Batch Operations** - Could use bulk inserts
3. **Cover Loading** - Not fully async yet

---

## Testing Status

**Test Files:**
- `tests/test_analysis.py`
- `tests/test_database.py`
- `tests/test_scanner.py`
- `tests/test_utils.py`

**Coverage:** Partial (core logic tested, UI not tested)

---

## Build System

- `build.py` - Custom build script
- `pyproject.toml` - Package configuration
- `requirements.txt` - Dependencies
- `run.bat` / `run.ps1` - Windows launchers

---

## Configuration

**Config File:** `config.json` (in app data directory)

**Settings:**
- Library roots
- Theme
- Volume
- Auto-scan
- File watching

---

## Code Quality

### Strengths
- ✅ Modular architecture
- ✅ Clear separation of concerns
- ✅ Type hints (partial)
- ✅ Documentation strings
- ✅ Error handling
- ✅ Migration system

### Areas for Improvement
- ⚠️ Some large files (app.py)
- ⚠️ Inconsistent error handling patterns
- ⚠️ Limited test coverage
- ⚠️ Some hardcoded values

---

## Security Considerations

- ✅ Path validation (`path_utils.py`)
- ✅ SQL injection protection (parameterized queries)
- ✅ File existence checks before operations
- ⚠️ No input sanitization for user tags/notes (low risk)

---

## Future Architecture Recommendations

1. **Split app.py** - Extract panels/views into separate files
2. **Repository Pattern** - Centralize database queries
3. **Service Layer** - Extract business logic from UI
4. **Event Bus** - Decouple components further
5. **Plugin System** - Allow extensions

---

## Conclusion

FruityWolf has a **solid foundation** with a **well-structured codebase**. The architecture is **scalable** and follows **Qt best practices**. Main areas for improvement are **code organization** (splitting large files) and **test coverage**.

**Overall Grade:** B+ (Production-ready with minor improvements needed)
