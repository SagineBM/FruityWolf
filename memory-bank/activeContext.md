# Active Context

## Current Focus
Performance engineering and stability hardening.
Completed a major performance overhaul to address UI lag and freezing.

## Recent Changes
- **Refactor**: Replaced laggy `QTableWidget` in Projects View with high-performance `QTableView` + `QStyledItemDelegate`.
- **Optimization**: Throttled scanner progress signals (max 20fps) to prevent UI flooding.
- **Database**: Enabled WAL mode for better concurrency between Scanner (write) and UI (read).
- **Stability**: Pinned dependencies (Python 3.11), created `requirements.txt` and setup scripts.
- **Compute**: Added `analysis/worker_process.py` for off-main-thread analysis.

## Open Issues
- **Optimization**: Scanner signal payload could be further minimized (currently sends strings).
- **Indexes**: Database indexes for search columns (pending Phase 3 item).

## Next Steps
- Verify performance on large datasets.
- Implement pagination for `ProjectsView` if dataset grows > 10,000 items.
