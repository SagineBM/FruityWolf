# System Health & Performance

**Last Updated:** 2026-02-03

## Current Status: ✅ Excellent (Production-Ready)

**Recent Major Addition:** Rendering Engine (Single/Batch) with safe exclusion rules and timeout protection. **Plugin page freeze** on click fixed (detail load moved to background + cache).

---

## Resolved Issues

### Plugin Page Freeze on Click ✅
**Status:** RESOLVED (2026-02-03)

**Problem:** Clicking a plugin in Plugin Intelligence triggered a multi-second UI freeze. Root cause: `PluginDetailsPanel.set_plugin()` ran on the main thread and called `get_plugin_state_for_name()`, which in turn called `get_plugin_truth_states(limit=10000)` — i.e. full recompute of all plugin truth states just to show one row. Plus `get_safe_to_open_project_ids()` and triage query on the UI thread.

**Solution:** (1) When the main plugin list loads, cache result by plugin name in `_plugin_state_cache`. (2) Detail panel now loads in a background thread: state from cache (instant when list was already loaded) or `get_plugin_state_for_name()` only when cache miss; triage and safe-to-open also in worker. (3) UI shows "Loading…" then applies result in `_on_detail_loaded`; stale responses ignored by comparing `loaded_name` to current `plugin_name`.

**Files:** `ui/panels/plugins_panel.py` (cache + `get_cached_plugin_state`), `ui/panels/plugin_details.py` (`_PluginDetailLoadThread`, async `set_plugin`). See `docs/plugin-page-performance-diagnosis.md` for full analysis and further optimization ideas.

**Result:** Plugin page stays responsive; clicking a plugin shows "Loading…" briefly then detail without blocking the app.

### Plugin Matching (Native FL Showing as Missing) ✅
**Status:** RESOLVED (2026-02-02)

**Problem:** Plugin Intelligence showed many installed plugins as "Missing" with "?" format. FL Studio native plugins (Fruity Limiter, Edison, 808 Kick, Fruity Soft Clipper, etc.) were incorrectly marked Missing because they are built-in and never appear in `installed_plugins` (we only scan VST/CLAP/AAX folders).

**Solution:** In `FruityWolf/utils/plugin_scanner.py`: (1) When computing truth state, if a referenced plugin has no match in `installed_plugins`, check if it is a native FL plugin via `_is_native_fl_plugin` from the FLP parser; if so, set state = Safe (or Risky if in an unstable project) and format = "Native". (2) Exclude native FL plugin names from `get_referenced_missing_plugins()` so they do not appear in the "missing" list.

**Result:** Native FL plugins now show as Safe/Risky with format "Native" instead of Missing. Third-party plugins still require a successful plugin scan (Scan button) and correct scan paths to show as present.

### Volume Setting Crash ✅
**Status:** RESOLVED (2026-02-02)

**Problem:** App crashed on startup/settings change if volume was stored as a float (e.g., "0.8") in DB.
**Solution:** Added try-except block in `app.py` to safely handle float strings and convert them to integer percentages.
**Result:** Startup is robust against legacy/varied data types.

### Cover Loading (Sync) ✅
**Status:** RESOLVED (2026-01-30)

**Problem:** Cover art loaded synchronously, blocking UI.
**Solution:** Enhanced `ImageManager` with async loading, LRU cache, and request cancellation.
**Result:** Non-blocking cover loading, smooth scrolling.

### Projects View Lag ✅
**Status:** RESOLVED (2026-01-28)

**Problem:** Severe lag when loading 2000+ projects.
**Solution:** Refactored to `QTableView` + `QAbstractTableModel` + Custom Delegates.
**Result:** 10x faster load, smooth scrolling.

### Signal Flooding ✅
**Status:** RESOLVED (2026-01-28)

**Problem:** UI stuttering during library scan.
**Solution:** Throttled signals to max 20fps.
**Result:** Smooth UI during scanning.

---

## Open Issues

### Empty Path Playback ⚠️
**Status:** OPEN  
**Priority:** MEDIUM  
**Impact:** User experience

**Problem:** Empty path warning without proper handling.
**Current State:** Logs warning, no UI feedback.
**Planned Fix:** Validate path before load, disable play button, show message.

---

## Performance Metrics

### Current Performance
| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Projects View Load | ~100ms (1000) | <100ms | ✅ |
| Library Scan (Full) | ~2-5min (1000) | ~1-2min | ✅ |
| Library Scan (Incremental) | ~10-30s (1000) | <1min | ✅ |
| Render Job Overhead | ~1s (start/end) | <2s | ✅ |
| Memory Usage | ~200-400MB | <400MB | ✅ |
| Startup Time | ~3-5s | <3s | 🟡 |

---

## Performance Budget

| Operation | Budget | Current |
|-----------|--------|---------|
| Page navigation | <100ms | ~50ms ✅ |
| Projects list scroll | 60fps | 60fps ✅ |
| Scanner progress | 20fps | 20fps ✅ |
| Cover load | <50ms | Async ✅ |
| Render Count Query | <50ms | <10ms ✅ |

---

## Bottleneck Analysis

### High Impact (Fix Soon)
1. **Startup time** — Could use lazy loading.

### Medium Impact (addressed)
2. **Query result caching** — `get_safe_to_open_project_ids()` cached 60s; invalidated on plugin scan.
3. **Plugin list apply** — Plugin Analytics and Plugin Details use QTableView + model; PluginsPanel uses QListView + model (virtualization, no widget-per-row).

### Low Impact
4. **Database queries** — Indexed; migration 28 adds `idx_installed_plugins_is_active`.

---

## Monitoring Recommendations

### Key Metrics to Track
- Render job success rate (timeouts/failures)
- Page load times
- Memory usage
- Scanner performance

---

## Technical Debt

| Item | Impact | Effort | Priority |
|------|--------|--------|----------|
| app.py size (3300+ lines) | Maintainability | High | Medium |
| Limited test coverage | Stability | High | High |
| Hardcoded constants | Flexibility | Low | Low |

---

## Next Performance Tasks

1. **Monitor Rendering Stability** (HIGH)
   - Ensure timeouts are effective
   - Monitor FL Studio process cleanup

2. **Increase Test Coverage** (HIGH)
   - Target rendering module
   - Add unit tests for `engine.py`

3. **Query Caching** (MEDIUM)
   - Cache frequent queries (e.g. `get_safe_to_open_project_ids()` for plugin page)

4. **Plugin page** — Done: Model/View for all plugin tables; installed index cache; safe-to-open cache (see docs/plugin-page-performance-diagnosis.md).
