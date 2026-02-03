# Plugin Matching System — Current State & Algorithm

**Last updated:** 2026-02-02

This document describes how FruityWolf discovers plugins from FL Studio projects (FLP), how it scans the system for installed plugins, and how it matches the two to show **Safe**, **Risky**, **Missing**, **Native**, or **Unused**. It also summarizes the current issue (plugins still showing as Missing) and how to verify/fix it.

---

## 1. High-Level Pipeline

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  FLP files      │     │  project_plugins  │     │  get_plugin_truth_  │
│  (on disk)      │────▶│  (DB table)       │────▶│  states()            │
│                 │     │  plugin_name      │     │  Match ref vs inst  │
└─────────────────┘     └──────────────────┘     └──────────┬──────────┘
        │                            │                       │
        │ FLP parser                 │ Library scanner       │
        │ (flp_parser/parser.py)      │ (scanner/)            │
        ▼                            ▼                       ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Parse result   │     │  projects (DB)     │     │  Plugin Intelligence │
│  plugins[].name │     │  + FLP parse       │     │  UI (status badges)  │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
                                │
                                │ Plugin scan (optional)
                                ▼
                        ┌──────────────────┐
                        │ installed_plugins │
                        │ (DB table)        │
                        │ name, format, path│
                        └──────────────────┘
                                │
                        plugin_scanner.py
                        scan_system_plugins()
```

- **Referenced plugins** = what FL Studio projects use → come from **FLP parsing** → stored in **project_plugins**.
- **Installed plugins** = what the OS has on disk (VST2/VST3/CLAP/AAX) → come from **system scan** → stored in **installed_plugins**.
- **Matching** = for each referenced name we decide: found in installed (Safe/Risky), not found but FL native (Safe/Risky + format "Native"), or not found (Missing). Unreferenced installed = Unused.

---

## 2. Where Referenced Names Come From (FLP → project_plugins)

### 2.1 FLP parsing

- **File:** `FruityWolf/flp_parser/parser.py`
- **Entry:** `parse(flp_path, match_installed_plugins=True)` builds a result dict with a `plugins` list.
- Each plugin entry has at least: `name`, `type` (generator/effect), `channel_index` or `slot`/`mixer_track`, and optionally `path`, `preset`, `is_native`.

**How `name` is set:**

- **Generators:** From channel plugin (pyflp). Strategies: `plugin_info['name']`, channel name, internal name for natives.
- **Effects:** From mixer slot plugin. Strategies: `plugin_info['name']`, slot name, patterns like "Plugin - Preset" or "Plugin (Preset)", internal name for natives.
- **VST plugins:** From `_extract_vst_info()` → `plugin_obj.name` (factory name), or vendor + name, or path-based name.
- All names are normalized with **`_normalize_plugin_name(name)`** before being added to the result:
  - Strips suffixes: ` (VST3)`, ` (x64)`, ` VST2`, `.dll`, etc.
  - Normalizes whitespace with `' '.join(name.split())`.
- **No DB or installed_plugins** are written here; the parser only returns a dict. Optional step: `_match_plugins_to_installed()` can rewrite `plugin['name']` to an installed name for display, but the **library scanner** persists the parser result as-is (see below).

### 2.2 Persisting into project_plugins

- **File:** `FruityWolf/scanner/library_scanner.py`
- When a project folder is scanned, the scanner calls the FLP parser and then writes to the DB:
  - **Plugins:** `plugin_name = p.get('name', 'Unknown')` — i.e. the **exact** `name` from the parser result (already normalized by the parser).
  - Rows inserted: `(project_id, plugin_name, plugin_type, channel_index, mixer_slot, preset_name, plugin_path, created_at)`.

So **project_plugins.plugin_name** = parser’s normalized display name (e.g. `"Fruity Limiter"`, `"Native Instruments Kontakt 7"`, `"Edison"`). There is no separate “internal name” or “path” used for matching at this stage; matching uses this single `plugin_name` string.

---

## 3. Where Installed Names Come From (System scan → installed_plugins)

### 3.1 System plugin scan

- **File:** `FruityWolf/utils/plugin_scanner.py`
- **Entry:** `scan_system_plugins(use_cache=True, max_workers=4)`.

**Search paths:**

- Defaults: `DEFAULT_VST_PATHS` (ProgramFiles VSTPlugins, Common Files VST2/VST3/CLAP, Avid, Image-Line FL Studio Plugins).
- Plus registry and **plugin_scan_roots** (user-added paths in DB).
- Combined via `get_vst_search_paths()`.

**What gets a row:**

- **VST3:** Folder with `.vst3` → valid bundle → **name = folder stem** (e.g. `Kontakt 7.vst3` → name `"Kontakt 7"`).
- **VST2 / Waves:** `.dll` with PE export check (VSTPluginMain / main) → **name = file stem** (e.g. `Serum_x64.dll` → name `"Serum_x64"`).
- **CLAP:** `.clap` with `CLAP_PLUGIN_ENTRY` → **name = file stem**.
- **AAX:** `.aaxplugin` bundle → **name = bundle stem**.
- **Content:** e.g. `.nki`, `.ufs` → **name = file stem**.

So **installed_plugins.name** = filesystem-derived (folder or file stem). No FL Studio “display name” here; we only have what the scan path and file/folder names give.

**Written columns (relevant):** `name`, `path`, `format` (VST2, VST3, CLAP, AAX, etc.), `is_active = 1`. Matching uses `name` and `format` only.

---

## 4. How Matching Works (get_plugin_truth_states) — Hardened flow

- **File:** `FruityWolf/utils/plugin_scanner.py` → `get_plugin_truth_states()`; matching logic in `FruityWolf/utils/plugin_matcher.py`.

### 4.1 Data loaded

1. **Referenced:** SQL returns per `plugin_name`: `project_count`, `last_seen`, `plugin_type`, and **most frequent non-null `plugin_path`** (subquery `ORDER BY COUNT(*) DESC LIMIT 1`), not `MAX(plugin_path)`.

2. **Installed:** `SELECT * FROM installed_plugins WHERE is_active = 1`. Then **`build_installed_index(inst_rows)`** builds a multi-key index (canon, product_key, tokens_no_vendor, etc.) using **`canonicalize()`** from `plugin_matcher`.

3. **Installed guard:** If `installed_count < 50`, **Missing is not computed**; third-party refs are set to **Unknown** ("Scan Required"). Logs: `ref_count`, `inst_count`, `inst_index_keys`, sample refs and installed (name → canon).

4. **Overrides:** `plugin_alias_overrides` keyed by `ref_key = lower(ref_raw)|ref_type`. If present, that installed row wins and scoring is skipped.

5. **Unstable projects:** Plugins in projects with `last_render_failed_at IS NOT NULL` → `unstable_set` (used for Risky).

### 4.2 Canonicalization (plugin_matcher.canonicalize)

- **Rule A:** Strip prefixes `vst3:`, `vst2:`, `fruity wrapper`, `wrapper`, etc.
- **Rule B:** Strip decoration parens `(x64)`, `(bridged)`, `(demo)`, etc.
- **Rule C:** Extensions, arch suffixes, junk words (mono, stereo, vst, …).
- **Rule D:** `_`, `-`, `.` → space; collapse whitespace; lowercase.
- **Rule E:** Version extraction (trailing numbers, v10, etc.); exclude note-like (C4, M1).
- **Token rewrites** before alias lookup: e.g. `nativeinstruments` → `native instruments`, `serum_x64` → `serum`, `xferrecords` → `xfer`.
- **Output:** `canon`, `tokens`, `tokens_no_vendor`, `vendor_tokens`, `version`, `arch`, `product_key`. Scoring uses **`tokens_no_vendor`** (vendor stripped on both sides).

### 4.3 Matching strategy (no global substring)

1. **Exact canon** → `installed_index[ref.canon]`.
2. **Exact product_key** → `installed_index[ref.product_key]`.
3. **Token narrowing** → only installed that share ≥1 **non-generic** token with ref (`tokens_no_vendor`; exclude e.g. compressor, limiter, eq).

Candidates are **scored** (Lane 1: product_key +0.50; Lane 2: Jaccard on `tokens_no_vendor` +0.40; Lane 3: path stem +0.30, vendor folder +0.10; version ±0.08/0.05). **Sanity:** empty token intersection and no path stem → score 0; generic-only overlap → cap 0.65.

**Thresholds:** **MATCHED** if best_score ≥ 0.78 and (best − second_best) ≥ 0.08. **UNKNOWN** if 0.60 ≤ best < 0.78 or separation < 0.08. **MISSING** if best < 0.60 (and not native, no override, scan ready).

### 4.4 Unknown vs Missing

**Missing** only when: installed scan is populated (≥50), resolver returns best < 0.60, not native, and no override. Otherwise **Unknown**.

### 4.5 Native FL check (no parser import)

**`_is_native_fl_plugin_name(name)`** (in `plugin_scanner.py`):

- **Blacklist:** If any `_FL_THIRD_PARTY` substring (e.g. `"native instruments"`, `"kontakt"`, `"soundtoys"`) is in `name.lower()`, return False.
- **Fruity prefix:** If `name.strip().lower().startswith("fruity ")` → True.
- **Whitelist:** If `name.strip().lower()` is in `_FL_NATIVE_NAMES` (large set of known FL native names: limiter, edison, fruity limiter, soft clipper, etc.) → True.
- **Word-boundary partial:** For each token in `_FL_NATIVE_NAMES`, if token appears in name with word boundaries (start/end/whole) → True.

So FL natives (Fruity Limiter, Edison, Limiter, Fruity Soft Clipper, etc.) are marked Safe/Risky + "Native" even though they never appear in `installed_plugins` (we only scan VST/CLAP/AAX).

---

## 5. Where the UI Gets Its Data

- **Plugin Intelligence** list: `FruityWolf/ui/panels/plugins_panel.py` calls `get_plugin_truth_states(studio_filter, search_term, limit)` (from a **worker thread** so the UI does not freeze).
- Result rows: `plugin_name`, `state`, `format`, `project_count`, `last_seen`, `plugin_type`.
- Table columns: Status (state), Name, Format, Projects, Last seen. Filters: Studio, Missing, Risky, Hot, Last 30 days, All.

---

## 6. Current Issue: “Still All Plugins Missing”

**Observed:** Plugin Intelligence still shows (almost) all plugins as **Missing** with format **?**, even after native detection and matching fixes.

**Possible causes:**

1. **Names in DB differ from what we expect**
   - Parser or scanner might store a different string (e.g. with prefix/suffix, or internal name). Then:
     - Normalized base might not match any `inst_by_base` (e.g. typo or extra token).
     - Native check might fail (e.g. name contains an unexpected character or third-party substring).
   - **Check:** Run `SELECT DISTINCT plugin_name FROM project_plugins LIMIT 100` and compare to:
     - `_normalize_plugin_name_for_match(plugin_name)` (should match some `inst_by_base` key for third-party, or pass `_is_native_fl_plugin_name` for natives).

2. **installed_plugins empty or not visible when UI loads**
   - If the plugin scan runs in a background thread and the UI loads truth states before the scan commits (or from another connection), `inst_by_base` could be empty → every ref would be “no match” → Missing unless native.
   - **Check:** Right after opening Plugin Intelligence, run `SELECT COUNT(*), name FROM installed_plugins WHERE is_active = 1 GROUP BY name LIMIT 20`. If count is 0 or very low, scan may not have completed or DB path may differ.

3. **Filter “Missing” selected**
   - If the user has the **Missing** filter on, the list shows only plugins in state Missing. So even if natives are correctly Safe/Native, they would not appear in that tab. **Check:** Switch to **All** or **Studio** and see if Fruity Limiter / Edison etc. appear as Safe with format Native.

4. **Native check too strict**
   - If stored names have a prefix/suffix that we don’t strip before the native check (e.g. `"VST3: Fruity Limiter"`), we do strip and lowercase for substring/word-boundary; but if the only match would be `startswith("fruity ")` and the stored name is `"Fruity Limiter"` with no prefix, it should still pass. If you see names like `"Limiter (Fruity)"` or with extra tokens, we may need to extend normalization or native token list.

**Recommended next steps:**

- Log or inspect **ref_by_name** keys and **inst_by_base** keys (size and a few examples) inside `get_plugin_truth_states` to confirm referenced vs installed names and normalization.
- Confirm in DB: `SELECT DISTINCT plugin_name FROM project_plugins` and `SELECT name FROM installed_plugins WHERE is_active = 1 LIMIT 50`.
- Ensure plugin scan has finished and the same DB file is used when opening Plugin Intelligence (no second process or stale connection).

---

## 7. “QThread: Destroyed while thread is still running”

This appears when the **plugin scan** is run (Plugin Intelligence “Scan” or Settings “Scan Plugins Now”) and the window is closed (or the app exits) before the scan thread finishes. The QThread object is destroyed while `run()` is still executing.

**Mitigation:** Before app exit (e.g. in `closeEvent`), if `_plugin_scan_thread` is not None and `isRunning()`, call `_plugin_scan_thread.quit()` and `wait(3000)` (or similar) so the thread is not destroyed while still running. Alternatively, keep the thread object alive until `finished()` (e.g. don’t clear the reference until then) so Qt does not destroy it mid-run.

---

## 10. Debugging “All Missing”

1. **Inspect DB contents**
   - Referenced: `SELECT DISTINCT plugin_name FROM project_plugins ORDER BY plugin_name LIMIT 50;`
   - Installed: `SELECT name, format FROM installed_plugins WHERE is_active = 1 LIMIT 50;`
   - Compare: do referenced names (after normalization) appear in installed names (after normalization)? Do FL native names (Fruity Limiter, Edison, etc.) appear in referenced?

2. **Temporary logging in get_plugin_truth_states**
   - After building `ref_by_name` and `inst_by_base`, log: `logger.info("ref_count=%s inst_base_count=%s sample_refs=%s sample_inst_bases=%s", len(ref_by_name), len(inst_by_base), list(ref_by_name.keys())[:5], list(inst_by_base.keys())[:10])`.
   - Inside the loop for each ref, for the first few names log: `base`, `match is not None`, `_is_native_fl_plugin_name(name)`. That confirms whether match fails and whether native is True/False.

3. **Filter**
   - Ensure you are not on the **Missing** filter only; use **All** or **Studio** to see Safe/Native plugins.

---

## 8. Summary Table

| Step | Location | Input | Output |
|------|----------|--------|--------|
| FLP parse | flp_parser/parser.py | FLP path | `plugins[].name` (normalized) |
| Save refs | scanner/library_scanner.py | Parse result | project_plugins.plugin_name |
| System scan | utils/plugin_scanner.py | Search paths | installed_plugins (name, format, path) |
| Truth state | utils/plugin_scanner.py | project_plugins + installed_plugins | state (safe/risky/missing/unknown/unused), format |
| Native check | utils/plugin_scanner.py | plugin_name | True → Safe/Risky + "Native" |
| UI list | ui/panels/plugins_panel.py | get_plugin_truth_states() | Table: Status, Name, Format, Projects, Last seen |

---

## 9. Definitions (from plugin-page-analysis.md)

- **Missing:** Referenced in ≥1 FLP and not found in installed_plugins (by normalized name) and not FL native.
- **Safe:** Present on disk (or FL native) and not in an unstable project.
- **Risky:** Present on disk (or FL native) and referenced by ≥1 project with `last_render_failed_at` set.
- **Unknown:** Multiple formats or ambiguous match.
- **Unused:** In installed_plugins but not referenced by any project.
- **Native:** FL Studio built-in plugin; not in installed_plugins scan; treated as “present” with format "Native".
