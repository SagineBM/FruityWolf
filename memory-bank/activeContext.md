# Active Context

**Last Updated:** 2026-02-05

## Current Focus

**Rendering Engine** — Core implementation complete. Safe FL Studio CLI integration, single-project and batch folder rendering with backup exclusions, timeout protection, and progress tracking. **Plugin Matching** and **Activity Heat** are implemented in-tree (some new files still untracked). **Plugin page freeze** fixed (detail load in background + cache).

## Recent Changes (2026-02-05)

**Sync:** Working tree — 4 modified, line-ending only (LF→CRLF): `database/migrations.py`, `ui/panels/plugin_details.py`, `ui/panels/plugins_panel.py`, `utils/plugin_scanner.py`. No substantive code changes since last sync.

### Rendering Engine Implementation ✅ (Major Feature)
- **Core Logic (`rendering/`)**:
  - `backup_exclusion.py` - Mandatory exclusion of Backup/Autosave folders and filenames.
  - `fl_cli.py` - Safe FL Studio CLI argument builder and executable resolution.
  - `engine.py` - `RenderJob` and `RenderQueue` for sequential, monitored execution with timeouts (10m default).
- **User Interface**:
  - **Project Details**: Added "Render Preview..." button with safety confirmation.
  - **Tools Menu**: Added "Render folder..." batch action.
  - **Progress UI**: `RenderProgressDialog` with Pause/Stop controls and real-time logging.
  - **Settings**: Added FL Studio Path configuration in Library/Paths tab.
- **Database**:
  - **Migration 25**: Added `render_status` column (`unheard`, `rendering`, `preview_ready`, `render_failed`) to `projects` table.
- **Safety & Determinism**:
  - Output naming locked to `{project_name}__fw_preview.{ext}`.
  - Strict overwrite policy (only touches own preview files).
  - Background processing to keep UI responsive.

### Plugin Matching System
- **Native FL plugins:** No longer shown as "Missing"; marked Safe/Risky with format "Native" via `_is_native_fl_plugin` (flp_parser) and plugin_scanner truth-state logic.
- **New modules:** `utils/plugin_matcher.py`, `utils/plugin_aliases_data.py`; doc `docs/plugin-matching-system.md`. Plugin Intelligence and panels updated.

### Activity Heat
- **Core:** `core/activity_heat.py` — `calculate_activity_heat()` (recency + engagement → score 0–100, label Cold/Warm/Hot) and `get_heat_color()`. Used in projects model, project/plugin details, and delegates.

### Bug Fixes
- **Volume Setting Crash**: Fixed `ValueError` when loading float volume settings (e.g., "0.8") from database. Now correctly converts to integer percentage (80).

### Identity-First Scanning Layer (2026-01-30)
- **Migration 23**: Identity system schema (PID, confidence, user_locked).
- **Conflict Prevention**: Greedy bipartite matching for flat folders.
- **Test Coverage**: 45 identity system tests passing.

## Blockers

None.

## Next Steps

1. **Verify Rendering in Production**: Test with various FL Studio versions and project complexities.
2. **Expand Render Formats**: Enable UI for WAV/MIDI/ZIP options (backend structure ready).
3. **Increase Test Coverage**: Add tests for rendering and plugin matching modules.
4. **Stage/commit new modules**: rendering/, activity_heat.py, render_dialogs.py, plugin_matcher.py, plugin_aliases_data.py, plugin-matching-system.md when ready.
5. **CI/CD Pipeline**: Set up automated builds.

## Files to Watch

- `FruityWolf/rendering/engine.py` — Render queue logic
- `FruityWolf/rendering/backup_exclusion.py` — Safety rules
- `FruityWolf/ui/render_dialogs.py` — Batch progress UI
- `FruityWolf/ui/panels/project_details.py` — Single render trigger
- `FruityWolf/app.py` — Batch render trigger & settings fix
- `FruityWolf/core/activity_heat.py` — Activity heat score/color
- `FruityWolf/utils/plugin_matcher.py` — Plugin matching logic
