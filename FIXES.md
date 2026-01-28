# Critical Fixes for Distribution

## Issues Fixed

### 1. VLC DLL Compatibility Error
**Error:** `Le point d'entrée de procédure decode_URI est introuvable dans la bibliothèque de liens dynamiques C:\Program Files\VideoLAN\VLC\plugins\gui\libqt4_plugin.dll`

**Root Cause:** VLC was trying to load incompatible Qt4 plugins that conflict with PySide6/Qt6.

**Fix:**
- Enhanced VLC initialization with better error handling
- Added VLC arguments to prevent loading problematic plugins (`--no-plugins-cache`, `--no-qt-privacy-ask`, `--no-qt-system-tray`)
- Added early detection of DLL errors before they crash the app
- Graceful fallback to Qt Multimedia if VLC fails

**Files Modified:**
- `FruityWolf/player/audio_player.py` - Enhanced `_init_backend()` method

### 2. Database Schema Error
**Error:** `sqlite3.OperationalError: no such column: t.state`

**Root Cause:** Old databases don't have the `state`, `state_reason`, and `labels` columns that were added in Migration 5. The queries were failing because migrations might not have run.

**Fix:**
- Added helper functions `_has_state_columns()` and `_get_state_columns_sql()` to check column existence
- Updated all queries to dynamically handle missing columns (return `NULL` if columns don't exist)
- Enhanced migration system to handle "column already exists" errors gracefully
- Ensured migrations always run on database initialization

**Files Modified:**
- `FruityWolf/scanner/library_scanner.py` - Added column detection and updated all track queries
- `FruityWolf/database/migrations.py` - Enhanced error handling for duplicate columns
- `FruityWolf/database/models.py` - Ensured migrations always run

**Queries Fixed:**
- `get_all_tracks()`
- `get_favorite_tracks()`
- `search_tracks()`
- `get_track_by_id()`
- `get_recently_added_tracks()`
- `get_missing_metadata_tracks()`

## Testing Recommendations

1. **Test on a clean machine** (without VLC installed) - should use Qt Multimedia fallback
2. **Test on a machine with incompatible VLC** - should detect DLL error and fallback gracefully
3. **Test with old database** - should run migrations and handle missing columns
4. **Test with fresh database** - should work normally

## Build Instructions

Rebuild the installer with:
```powershell
python build.py --both
```

This will create:
- `dist/FruityWolf-SingleFile/FruityWolf.exe` - Single executable
- `dist/FruityWolf-Folder/` - Folder distribution
- `dist/FruityWolf-Installer/FruityWolf-Setup.exe` - Windows installer

## Distribution Notes

- **VLC is optional** - The app will work without VLC using Qt Multimedia
- **Database migrations are automatic** - Old databases will be upgraded automatically
- **Backward compatible** - Works with databases missing newer columns
