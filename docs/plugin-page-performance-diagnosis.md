# Plugin Page Performance — Deep Diagnosis

**Date:** 2026-02-03  
**Scope:** Plugin Intelligence view, Plugin Analytics panel, Plugin Details panel, plugin_scanner truth-state pipeline.

---

## Executive Summary

The plugin page slows the app primarily because **clicking a plugin** triggers a **full recompute of all plugin truth states on the UI thread**, plus heavy DB queries. A secondary cost is the **size and shape of the main plugin list load** (full table scans, N× matching, then 2500+ table items applied on the main thread). This document gives root causes and concrete fixes that keep behavior correct while making the app feel “blazing fast.”

---

## 1. Root Cause #1 — Plugin Detail Panel Blocks UI (CRITICAL)

**What happens:** When the user clicks a plugin in the Plugin Intelligence table, the app shows the right-hand “Plugin Details” panel. That panel’s `set_plugin(plugin_name)` runs **entirely on the main (UI) thread** and does:

1. **`get_plugin_state_for_name(plugin_name)`**  
   Implemented as: load **all** plugin truth states with `get_plugin_truth_states(studio_filter=None, search_term=None, limit=10000)`, then loop to find the one row whose name matches. So **one click = full truth-state computation** (all refs, all installed, all resolution) just to get a single plugin’s state.

2. **`get_projects_using_plugin_for_triage(plugin_name, limit=100)`**  
   A bounded query; acceptable but still on UI thread.

3. **`get_safe_to_open_project_ids()`**  
   A heavy query: `SELECT id FROM projects WHERE ... AND id NOT IN (SELECT project_id FROM project_plugins WHERE ... NOT IN (SELECT name FROM installed_plugins ...))`. Run on every plugin click with no cache.

**Impact:** With thousands of `project_plugins` and hundreds of unique plugins, a single click can block the UI for **several seconds**. This is the main “app freezes when I use the plugin page” symptom.

**Evidence (code):**

- `FruityWolf/ui/panels/plugin_details.py` — `set_plugin()` calls the three functions above synchronously.
- `FruityWolf/utils/plugin_scanner.py` — `get_plugin_state_for_name()` (lines 1138–1151) calls `get_plugin_truth_states(..., limit=10000)` and scans the result.

---

## 2. Root Cause #2 — get_plugin_truth_states Is Inherently Heavy

Even when run in a **background thread** (as for the main plugin list), this function is expensive:

| Step | Cost |
|------|------|
| Load all refs | `SELECT ... FROM project_plugins pp JOIN projects p` with **no LIMIT** — full table scan. |
| Aggregate in Python | For every ref row: `normalize_reference_name`, `canonicalize`, merge by product key. O(ref_rows) with non-trivial work per row. |
| Load installed | `SELECT * FROM installed_plugins WHERE is_active = 1`. |
| Build index | `build_installed_index(inst_rows)` — `canonicalize()` for every installed plugin and multi-key index. |
| Unstable set | Another query over `project_plugins` + `projects` for `last_render_failed_at`. |
| Per-ref resolution | For **each** unique referenced plugin: `resolve_reference(name, path_hint, installed_index, inst_rows)` — tokenization, scoring, thresholds. |
| Unused loop | For each installed plugin, check if matched. |
| Filter/sort | Studio filter, search term, sort, then `result[:limit]`. |

So the **first load** of the Plugin Intelligence tab (triggered 200 ms after show) does a lot of work in the worker thread. That’s correct. The problem is (1) using the same path for “one plugin” in the detail panel on the UI thread, and (2) what happens when the result comes back (see #3).

---

## 3. Root Cause #3 — Applying the Plugin List on the Main Thread

When the background load of the plugin list finishes, `_on_plugin_list_loaded` runs on the main thread and:

- Sets `table.setRowCount(len(raw))` (e.g. 500).
- For each row, creates **5 `QTableWidgetItem`** and sets them on the table.

So **500 × 5 = 2500** table items are created and attached in one go. With `QTableWidget` there is **no virtualization** — all rows exist in the widget tree. This can cause a **noticeable short freeze** when the list appears, especially on slower machines.

---

## 4. Root Cause #4 — get_safe_to_open_project_ids() Is Heavy and Uncached

The “Safe to open” column in the Plugin Details triage table requires knowing which project IDs are “safe” (no missing plugins, not unstable). The implementation is:

```sql
SELECT id FROM projects p
WHERE p.last_render_failed_at IS NULL
AND p.id NOT IN (
  SELECT project_id FROM project_plugins pp
  WHERE LOWER(pp.plugin_name) NOT IN (
    SELECT LOWER(name) FROM installed_plugins WHERE is_active = 1
  )
)
```

This is a **correlated NOT IN** over `project_plugins` and `installed_plugins`. On large DBs it can be slow. It is run **on every plugin click** and **on the UI thread**, with no caching.

---

## 5. Root Cause #5 — QTableWidget Instead of Model/View

Both:

- The **Plugin Analytics** table (main plugin list), and  
- The **Plugin Details** table (projects using this plugin)

use **`QTableWidget`**. So:

- No virtualization (all rows are real widgets/items).
- No lazy loading or incremental updates.

The **Projects** view was refactored to `QTableView` + `QAbstractTableModel` + delegates and got a large improvement. The plugin page still uses the older pattern.

---

## 6. Minor — Widget-per-Row in Project Plugins Panel

The **PluginsPanel** (project detail: “Plugins Used”) builds one **`PluginChip`** widget per plugin. For a project with 30 plugins that’s 30 widgets. This is the “widget-per-row” pattern that the project avoids for large lists. Impact is lower than the detail panel but worth fixing if we refactor the plugin UI further.

---

## Recommended Fixes (Priority Order)

### P0 — Fix Plugin Detail Panel Freeze (Must Do)

1. **Single-plugin state API**  
   Add a **lightweight** API that returns truth state for **one** plugin without calling `get_plugin_truth_states(limit=10000)`:
   - Query `project_plugins` / `projects` only for refs matching this plugin name (or canonical name).
   - Use a **cached** (or once-per-detail-open) `installed_plugins` list and `build_installed_index`.
   - Call `resolve_reference` once for that name.
   - Apply unstable check for this plugin only.
   Return the same dict shape as `get_plugin_state_for_name` so the detail panel can drop in the new API.

2. **Run detail panel work in a background thread**  
   In `PluginDetailsPanel.set_plugin(plugin_name)`:
   - Do **not** call the heavy functions on the UI thread.
   - Start a worker that: computes single-plugin state (new API), `get_projects_using_plugin_for_triage(plugin_name)`, and `get_safe_to_open_project_ids()`.
   - Emit a signal with the combined result; in the slot (main thread) update the header, danger text, and table.
   - Show “Loading…” or a spinner until the result arrives.

3. **Optional: cache `get_safe_to_open_project_ids()`**  
   Cache the set for the current “session” of the plugin page (e.g. 60 s or until the user runs “Scan” or switches library). Reduces repeated heavy queries when clicking many plugins.

**Expected result:** Clicking a plugin no longer freezes the UI; detail panel fills in after a short delay (e.g. &lt; 200–500 ms) without blocking.

---

### P1 — Reduce Main-List Apply Cost

4. **Throttle or batch table updates**  
   When applying the main plugin list in `_on_plugin_list_loaded`, consider:
   - Setting row count and filling in batches (e.g. 100 rows at a time) with `QTimer.singleShot(0, ...)` between batches so the event loop can breathe, or  
   - Switching to `QTableView` + `QAbstractTableModel` so only visible rows are painted (virtualization).  
   The model approach is the “right” long-term fix and matches the Projects view.

5. **Limit initial load**  
   The list already uses `limit=500`. Keeping a hard cap and “Load more” or pagination avoids accidentally creating 2000+ rows at once.

**Expected result:** Tab switch to Plugin Intelligence and first paint of the list feels smooth; no multi-hundred-ms freeze when the list appears.

---

### P2 — Optimize get_plugin_truth_states (Background Path)

6. **DB-side aggregation where possible**  
   E.g. “referenced plugins” with project count and last_seen could be computed in SQL (GROUP BY canonical name or plugin_name) to reduce Python-side aggregation and memory.

7. **Cache installed index**  
   `build_installed_index(inst_rows)` depends only on `installed_plugins`. Cache it (invalidate when user runs “Scan” or when `installed_plugins` is updated) so that repeated calls to `get_plugin_truth_states` (or the new single-plugin API) don’t rebuild it every time.

8. **Indexes**  
   Ensure `project_plugins(plugin_name)`, `project_plugins(project_id)`, `installed_plugins(is_active)`, and any columns used in the “unstable” and “safe to open” queries are indexed so the heavy queries stay fast as data grows.

**Expected result:** Full plugin list load (in background) finishes sooner; less CPU and memory.

---

### P3 — Align with System Patterns

9. **Migrate plugin tables to Model/View**  
   Replace `QTableWidget` with `QTableView` + `QAbstractTableModel` (+ delegate if needed) for both the main plugin list and the detail panel’s project table. Matches `systemPatterns.md` and improves scalability.

10. **PluginsPanel**  
    For “Plugins Used” in project detail, consider a list model + delegate instead of N `PluginChip` widgets if we later support very large plugin counts per project.

---

## Summary Table

| Issue | Severity | Fix | Impact |
|-------|----------|-----|--------|
| Detail panel calls full get_plugin_truth_states on UI thread | **Critical** | Single-plugin API + detail load in worker | Removes multi-second freeze on click |
| get_safe_to_open_project_ids on every click, no cache | High | Move to worker; optional cache | Less repeated heavy query |
| 2500 table items applied at once on main thread | Medium | Batch apply or Model/View | Smoother list appearance |
| QTableWidget (no virtualization) | Medium | QTableView + model | Better scalability and smoothness |
| get_plugin_truth_states full scans + N× resolve | Medium | DB aggregation, index cache | Faster background load |
| Widget-per-row in PluginsPanel | Low | Model + delegate (later) | Minor |

Implementing **P0** gives the largest perceived improvement (“app no longer freezes when I click a plugin”) without changing behavior. **Implemented (2026-02-03):** P0–P3 done: detail worker + cache; Plugin Analytics and Plugin Details use QTableView + model; PluginsPanel uses QListView + model; installed index cache and safe-to-open 60s cache; migration 28 for idx_installed_plugins_is_active.
