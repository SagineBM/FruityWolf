# System Health & Performance Report

## Current Status: ⚠️ Performance Issues Detected

### 1. Critical Lag in Projects View
**Symptom**: Application freezes or lags severely when switching to "Projects" tab or refreshing.
**Root Cause**: `FruityWolf/ui/projects_view.py`
- **Issue**: Usage of `QTableWidget` with `setCellWidget` inside a loop of 2000 items (`get_all_projects(limit=2000)`).
- **Impact**: The loop creates ~2000 rows. For each row, it creates a `QWidget` container and 2 `QPushButton` instances. That is **~4000 widgets created instantly on the main UI thread**.
- **Explanation**: Qt widgets are heavy objects. Creating thousands of them in a loop blocks the event loop. `setCellWidget` breaks UI virtualization because the widgets must exist in memory even if not visible.
- **Recommendation**:
  - Switch to `QTableView` with a `QAbstractTableModel`.
  - Use `QStyledItemDelegate` to render the buttons/icons and handle clicks, instead of creating actual `QPushButton` widgets for every cell.
  - Implement pagination or "Load More" instead of fetching 2000 items at once.

### 2. Potential Signal Flooding during Scan
**Symptom**: UI stays responsive physically but stutters during scanning.
**Root Cause**: `FruityWolf/scanner/library_scanner.py`
- **Issue**: `self.progress.emit(idx + 1, total_projects, ...)` occurs for *every single project*.
- **Impact**: If scanning 5000 projects, 5000 signals are sent to the main thread. Qt's event loop gets flooded with update events.
- **Recommendation**: Throttle progress updates (e.g., emit only every 1% or every 10 items, or every 100ms).

### 3. Database Concurency
**Symptom**: Potential locks if scanning and usage happen simultaneously.
**Observation**: Uses raw SQLite without a connection pool or explicit WAL mode configuration visible in snippets.
**Recommendation**: Ensure `PRAGMA journal_mode=WAL;` is set to allow concurrent reads/writes (rendering UI while scanning).

## Refactoring Roadmap for Performance
1.  **[HIGH] Refactor `ProjectsView` to Model/View Pattern**.
    - Cost: Medium (Requires rewriting `ProjectsView`).
    - Benefit: Massive performance gain (Zero lag scrolling).
2.  **[MEDIUM] Throttle Scanner Signals**.
    - Cost: Low.
    - Benefit: Smoother UI during background ops.
3.  **[LOW] Optimize Loop Logic**.
    - Pre-compile regex or optimize string operations in `_populate_table` (though widget creation is the 99% bottleneck).
