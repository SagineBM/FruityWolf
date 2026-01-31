# Active Context

**Last Updated:** 2026-01-30

## Current Focus

**Identity-First Scanning Layer** — Core implementation complete. Added Project Identity (PID) system with confidence scoring, signal-based matching, conflict prevention, and metadata drift prevention. Fixed duplicate render path handling. All 45 identity system tests passing.

## Recent Changes (2026-01-30)

### Reliability & Performance Enhancements (2026-01-30)
- **Error Handling & Logging**:
  - Implemented proper file-based logging (`fruity.log` with rotation) in `utils/helpers.py`.
  - Replaced silent `except Exception: pass` blocks with `logger.error(..., exc_info=True)` in `app.py` and `library_scanner.py`.
  - Added `log_exception` context manager for standardized error handling.
- **Path Normalization**:
  - Added `normalize_path()` in `utils/path_utils.py` (handles `os.path.normcase` for Windows).
  - Applied normalization to all database queries and inserts in `library_scanner.py` to prevent duplicate projects due to case sensitivity.
- **Async Startup**:
  - Implemented `StartupWorker` in `app.py` to run database migrations in a background thread.
  - Added `QSplashScreen` to show status during initialization.
  - Moved `get_db()` call out of the main thread to prevent UI freezing on startup.
- **Database Optimization**:
  - **Migration 24**: Added missing performance indexes (`idx_projects_updated_at`, `idx_renders_project_mtime`, etc.).
  - Updated `models.py` schema definition with new indexes for fresh installs.
- **Safety Fixes**:
  - Added `safe_json_loads` helper.
  - Fixed empty path handling in `AudioPlayer.load_track` (prevents playing invalid files).
  - Added critical error logging to database migration failures.

### Identity-First Scanning Layer ✅ (Major Feature)
- **Migration 23**: Identity system schema
  - `projects.pid` (UUID) - Stable project identity
  - `projects.confidence_score` (0-100) - Match confidence
  - `projects.user_locked` - Prevents metadata drift
  - `projects.daw_type` - Foundation for multi-DAW support
  - `project_files` table - Source of truth for all files
  - `file_signals` table - Evidence signals for matching
  - `metadata_review_queue` table - Uncertain metadata changes
- **Identity Layer Modules**:
  - `scanner/identity/fingerprint.py` - Fast fingerprinting (64KB chunk)
  - `scanner/identity/signals.py` - Signal extraction (name tokens, mtime, etc.)
  - `scanner/identity/identity_store.py` - Database operations for identity system
- **Adapter Pattern**:
  - `scanner/adapters/base.py` - DAWAdapter interface
  - `scanner/adapters/fl_studio.py` - FL Studio-specific logic
  - Signal-based matching with conflict prevention
  - Greedy bipartite matching for flat folders
- **Scanner Integration**:
  - Write-through layer in existing 3-pass scanner
  - Populates identity tables during scan
  - Signal-based matching for flat folders
  - Primary render selection via identity system
  - Backward compatibility maintained
- **Metadata Drift Prevention**:
  - `database/project_metadata.py` - MetadataManager
  - Respects user locks
  - Confidence thresholds (85% for auto-update)
  - Review queue for uncertain changes
- **UI Updates**:
  - Confidence indicators (✅ high, ⚠️ medium, ❓ low)
  - Lock indicator (📌)
  - Tooltips show match reasons (signals)
- **Bug Fixes**:
  - Fixed duplicate render path UNIQUE constraint errors
  - Global path checking before insert
  - Graceful handling of race conditions
- **Test Coverage**:
  - 45 identity system tests (100% passing)
  - Unit tests: fingerprinting, signals, identity store, adapter
  - Integration tests: flat folder matching, end-to-end workflow
  - Duplicate path handling tests

### Async Cover Loading & Custom Covers ✅ (Previous)
- **Enhanced ImageManager**: 
  - Proper async loading with QThreadPool
  - LRU cache (500 items default)
  - Request cancellation for fast scrolling
  - Request deduplication
  - Thread-safe signal handling
- **Cover Management Service**:
  - `cover_manager.py` for managing user-uploaded covers
  - Stores covers in dedicated `covers/` directory
  - Supports projects, tracks, and playlists
  - Automatic cleanup on deletion
- **Database Migration 22**:
  - Added `custom_cover_path` column to projects table
  - Tracks and playlists already had `cover_path` columns
- **UI Updates**:
  - Project details panel: Async loading + cover upload UI
  - Track details panel: Async loading + cover upload UI
  - Context menu for cover management
  - "Change Cover" button
- **Cover Retrieval Logic**:
  - Checks custom covers first, then auto-detected covers
  - Fallback to placeholder if none found

### Code Improvements
- **Scanner enhancements**: Continued optimization of `library_scanner.py` (1440+ lines changed)
  - Improved render classification logic
  - Enhanced project detection
  - Better error handling
- **Database improvements**: Updates to models and migrations
  - Query optimizations
  - Schema refinements
- **UI improvements**: Updates to backend, panels, and projects view
  - Better data handling
  - Improved refresh logic
- **Debug tools**: New scripts for troubleshooting
  - `scripts/debug_renders.py` — Debug render data for projects
  - `scripts/check_project_files.py` — Verify project file structure
  - `scripts/check_renders.py` — Check render data
  - `scripts/check_dates.py` — Check date consistency
  - `scripts/check_library_tracks.py` — Verify library tracks
  - `scripts/fix_project_dates.py` — Fix project dates from renders
  - `scripts/fix_track_dates.py` — Fix track dates
  - `scripts/fix_schema.py` — Schema repair utilities
  - `scripts/run_migrations.py` — Migration runner

### Documentation Cleanup
- **Deleted old documentation files**:
  - BUILD_ALL.md, BUILD_TROUBLESHOOTING.md, BUILD_WARNINGS.md
  - DISTRIBUTION.md, FIXES.md, QUICK_BUILD.md
  - SHARING_COMPARISON.md
  - memory-bank/FruityWolf_Doctrine.md
  - memory-bank/dailySyncCommand.md
  - .cursor/commands/command.md (replaced with individual command files)
- **New documentation**:
  - SCANNER_ALGORITHMS.md — Detailed scanner algorithm documentation
  - Individual Cursor command files (6 files)

### Previous Changes (2026-01-29)

### Documentation Sync
- **Updated `systemPatterns.md`**: Added comprehensive scanner architecture details
  - Three-pass scanning strategy
  - Schema caching
  - Incremental scanning
  - FLP parse caching
  - Smart duration caching
  - Parallel scanning
  - File creation date tracking
- **Updated `codebaseReport.md`**: Added scanner deep dive section
  - Performance optimizations documented
  - File creation date implementation details
  - Render classification rules
- **Updated `systemHealth.md`**: Added scanner performance metrics
  - Full scan: 2-5 min for 1000 projects
  - Incremental scan: 10-30s for 1000 projects (10% changed)
  - Parallel scanning: 2-4x faster

### Previous Changes (2026-01-29)
- Created `.cursorrules` file
- Created `AGENTS.md` for agent instructions
- Created Cursor commands (6 commands)
- Cleaned up redundant documentation
- Updated ROADMAP.md
- Fixed version/naming inconsistencies

### Previous Changes (2026-01-28)
- FLP Parser MAJOR Enhancement (mixer effects, VST detection, native plugin DB)
- Complete documentation system established
- Model/View pattern for ProjectsView

## Key Decisions

| Decision | Reason | Date |
|----------|--------|------|
| Use .cursorrules | Standard Cursor AI rules file | 2026-01-29 |
| Schema caching | Eliminates thousands of PRAGMA queries | 2026-01-29 |
| Incremental scanning | 90%+ faster rescans | 2026-01-29 |
| File creation date tracking | Sort by original date, not scan time | Migration 19-21 |
| Parallel scanning | 2-4x faster on multi-core | 2026-01-29 |
| Batch size 50 | Optimal balance of performance and memory | 2026-01-29 |

## Open Issues

### High Priority
- **Bug**: Empty path playback needs proper handling
- **Test**: Coverage at ~25% (identity system adds 45 tests), needs >80%

### Medium Priority
- **Tech Debt**: app.py too large (3300+ lines)
- **Feature**: Light theme not implemented
- **CI/CD**: Not set up yet
- **Feature**: Studio One / Logic adapters (scaffolding ready)

## Next Steps

1. **Monitor identity system in production** (verify accuracy, performance)
2. **Fix empty path playback bug** (user experience)
3. **Set up CI/CD pipeline** (automation)
4. **Increase test coverage** (stability, target >80%)
5. **Create installer with auto-updater** (distribution)
6. **Implement Studio One / Logic adapters** (multi-DAW support)

## Files to Watch

- `.cursorrules` — Project rules (new)
- `AGENTS.md` — Agent instructions (new)
- `.cursor/commands/` — Cursor commands (new)
- `FruityWolf/scanner/library_scanner.py` — Scanner with optimizations
- `FruityWolf/ui/projects_view.py` — Model/View implementation
- `FruityWolf/database/migrations.py` — Schema version 23 (identity system)

## Architecture Notes

### Completed Patterns
- Model/View/Delegate for tables ✅
- Signal throttling (50ms/20fps) ✅
- WAL mode for database ✅
- Pagination with infinite scroll ✅
- Batch transactions (50 per commit) ✅
- **Schema caching** (eliminates PRAGMA queries) ✅
- **Incremental scanning** (skips unchanged projects) ✅
- **FLP parse caching** (skips unchanged FLPs) ✅
- **Smart duration caching** (skips Mutagen for unchanged) ✅
- **Parallel scanning** (ThreadPoolExecutor) ✅
- **File creation date tracking** (Windows st_birthtime) ✅

### Needed Patterns
- Async cover loading (worker pool + LRU cache)
- Repository pattern for database queries
- Service layer extraction from UI

## Scanner Performance Summary

### Full Scan
- **1000 projects**: ~2-5 minutes
- **5000 projects**: ~10-20 minutes
- Uses parallel scanning (4-8 workers recommended)

### Incremental Scan
- **1000 projects (10% changed)**: ~10-30 seconds
- **5000 projects (10% changed)**: ~1-2 minutes
- Only scans projects modified since last scan

### Optimizations Active
- Schema caching (eliminates PRAGMA queries)
- Incremental scanning (skips unchanged projects)
- FLP parse caching (skips unchanged FLPs)
- Smart duration caching (skips Mutagen for unchanged)
- Batch transactions (50 per commit)
- Parallel file I/O (ThreadPoolExecutor)
