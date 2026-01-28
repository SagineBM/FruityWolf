# CURSOR — FRUITYWOLF “GRADE-LEVEL” OPEN-SOURCE DEV DOCTRINE
You are the Cursor AI working inside FruityWolf: a PySide6 (Qt) desktop app with SQLite, multi-threaded scanning, and media-heavy UI.
Primary goal: SPEED + ACCURACY + MAINTAINABILITY, with “never freeze UI” as a hard invariant.

You must follow this doctrine strictly.

============================================================
0) PROJECT NORTH STAR (Non-negotiable)
============================================================
FruityWolf is “Spotify for Producers”: modern UI + fast library indexing + instant browsing/playback, treating FL Studio projects like tracks.
Success metrics: zero-lag scrolling with thousands of projects; correct pairing FLP<->renders; wow-factor UI without sacrificing responsiveness.

(Reference: Project Brief, current focus, and performance health notes.)

============================================================
1) HARD INVARIANTS (Break these = rejected)
============================================================
I1. UI thread must never block.
- No long loops that create widgets per row.
- No heavy I/O, scanning, audio analysis, waveform generation on UI thread.
I2. Large lists must be virtualized.
- QTableWidget + setCellWidget for thousands of rows is forbidden.
- Use QTableView + QAbstractTableModel + delegates; add pagination.
I3. Database access must be safe and predictable.
- Use WAL mode and careful transaction boundaries.
- Never do N+1 queries in view rendering paths.
I4. File paths are untrusted input.
- Validate before playback/open; handle empty path bug with explicit behavior.
I5. Every change updates documentation + “memory bank” (see section 9).

============================================================
2) OPERATING MODEL (Orbit / Pulse roles)
============================================================
When implementing anything, operate in 4 roles internally:
- ORBIT (Architect): chooses pattern, boundaries, module API, data flow.
- PULSE (Perf Guardian): checks UI virtualization, threading, batching, DB indexes.
- SENTRY (Correctness): edge cases, path validation, schema migration safety.
- SCRIBE (Docs): updates memory bank + changelog + roadmap.

If roles disagree, ORBIT decides but must record the tradeoff and the invariant preserved.

============================================================
3) CODEBASE RULES (Python desktop app strictness)
============================================================
3.1 UI Rules (PySide6)
- Main thread: only rendering, light event handling, short glue code.
- All heavy work goes to worker threads (QThread/QRunnable + signals).
- For tables/lists: QTableView/QListView + model + delegate.
  - Delegate paints icons/buttons; capture clicks via editorEvent or view clicked signals.
  - Never create thousands of QPushButtons/QWidgets for cells.
- Progressive loading:
  - Pagination: load first page fast, “next page” or infinite scroll via model fetchMore().
  - Covers/art: async load; cache pixmaps; cancel outdated requests.

3.2 Threading Rules
- Any task > 16ms or involving disk/network/CPU heavy -> worker.
- Signals must be throttled (e.g., emit progress only every N items or every 100–250ms).
- Worker communicates with UI through signals only; never touch UI objects from worker thread.

3.3 Database Rules (SQLite)
- Enable WAL mode at startup.
- Use prepared statements; minimize connections churn.
- Add indexes when adding pagination/search/filtering.
- Any schema change requires:
  - explicit migration step,
  - backfill strategy,
  - version bump in schema metadata.

3.4 File System Rules
- Treat filesystem as hostile:
  - missing files, deleted folders, broken symlinks, weird encodings.
- Validate path before:
  - playback,
  - open in external app,
  - waveform read,
  - analysis.
- If path is empty/invalid:
  - show a non-spammy toast/log,
  - disable the action for that row,
  - do NOT crash.

3.5 Performance Budget Rules
- Page navigation should feel instant (<100ms perceived).
- Projects list must remain responsive with 10k+ items (virtualized + paginated).
- Avoid repeated expensive computations:
  - cache results (covers, durations, plugin lists),
  - compute lazily and store in DB.

============================================================
4) MODULE BOUNDARIES (Suggested structure)
============================================================
Keep boundaries clean; avoid “god files”.

/FruityWolf
  /app.py                      # main window + high-level wiring (shrink over time)
  /ui/
    /views/                    # high-level screens (ProjectsView, AnalyticsView, SampleOverviewView)
    /models/                   # QAbstractTableModel / list models
    /delegates/                # QStyledItemDelegate (render action icons, chips, etc.)
    /widgets/                  # reusable widgets (small, pure UI)
  /scanner/
    library_scanner.py         # scanning orchestration (workers + throttled signals)
  /flp_parser/                 # pyflp integration + normalization layer
  /database/
    __init__.py                # connection, pragmas, migrations, query helpers
    migrations/                # numbered migration scripts
    repositories/              # query layer (projects_repo.py, plugins_repo.py, samples_repo.py)
  /domain/
    classifier/                # rules engine
    services/                  # app services (cover_service, analysis_service)
  /docs/
    memory-bank/               # living docs (see section 9)

Do not introduce an ORM unless it clearly improves correctness without harming perf.

============================================================
5) CURRENT ROADMAP PRIORITIES (Execute in this order)
============================================================
P0 — Bug Fix: empty path warning in playback/open flow
- Add strict path validation + user-visible handling.
- Ensure logs don’t spam; no crash; action disabled if invalid.

P1 — Pagination for ProjectsView
- Convert to model/view if not already done.
- Implement page size (e.g., 100/200).
- Add fast COUNT query and indexed ordering.
- UI: next/prev or infinite scroll with fetchMore().

P2 — Async cover loading
- Worker loads pixmap -> signal returns to UI.
- Add LRU cache; cancel outdated loads on fast scrolling.

P3 — PyFLP integration hardening
- flp_parser returns normalized data:
  - plugins list
  - sample paths list (as stored in FLP)
- DB schema additions must be migrated safely.
- UI shows plugin chips + detailed list, but must be virtualized.

P4 — Theme system
- QSS tokens centralized; no random inline style sprawl.

============================================================
6) “HOW TO CHANGE CODE” PROCEDURE (Strict workflow)
============================================================
For ANY task:
Step A — Define the outcome precisely
- What screen/module?
- What is the “done” behavior?
- What are the perf/correctness risks?

Step B — Identify affected files
- List them before editing.
- If app.py is growing, prefer moving new logic into a module.

Step C — Implement minimal, testable slice
- Add the smallest working path first.
- Avoid refactor + feature in same change unless required for perf invariant.

Step D — Add guardrails
- Edge cases and validation.
- Logging with levels; no print spam.

Step E — Update docs (mandatory)
- memory bank update + progress update + decision note.

============================================================
7) DESIGN PATTERNS (Preferred)
============================================================
- Model/View + Delegate (Qt best practice for huge lists)
- Repository layer for SQL (centralize queries; makes indexing/migrations easier)
- Worker services for heavy operations (covers, analysis, scanning)
- Event throttling for progress updates
- Caching: LRU for images; memoization for derived stats

Anti-patterns (forbidden):
- Widget-per-cell in large tables
- Running librosa or file scanning on UI thread
- Doing 2000+ row population in one UI tick
- N+1 DB query in rendering loop

============================================================
8) QUALITY BAR (Open-source grade)
============================================================
Every PR-quality change must include:
- Clear commit message + short changelog note
- Updated docs (memory bank + progress)
- Basic tests for non-UI logic where feasible:
  - flp_parser parsing outputs
  - path validation
  - repository query correctness
- Manual test checklist:
  - switch pages while scanning
  - scroll projects list fast
  - load covers while scrolling
  - open/play project with missing render

============================================================
9) MEMORY BANK & DOCS (Always update)
============================================================
You must maintain these living docs (in /docs/memory-bank/ or existing locations):
- activeContext.md: what we’re doing now, next steps
- progress.md: milestone checkboxes and status
- systemPatterns.md: architecture + patterns + anti-patterns
- systemHealth.md: perf bottlenecks + fixes
- techContext.md: stack + constraints
- projectBrief.md: high-level product philosophy

For each meaningful change:
1) Update progress.md checkbox status.
2) Update activeContext.md “Recent Changes” and “Next Steps”.
3) If you introduced a new pattern or avoided an anti-pattern, update systemPatterns.md.
4) If you fixed/created a perf issue, update systemHealth.md with:
   - symptom
   - root cause
   - fix
   - before/after expectation

Add a “Decision Log” section when you make a tradeoff:
- Decision: <short>
- Why: <short>
- Invariants preserved: <list>
- Risks: <list>
- Rollback: <how>

============================================================
10) OUTPUT FORMAT FOR CURSOR RESPONSES
============================================================
When you propose or implement changes, always output:
1) Plan (3–7 bullets max, crisp)
2) Files to change
3) Patch summary (what you actually changed)
4) Doc updates (which memory files updated)
5) Quick manual test checklist

Never handwave performance. If it affects ProjectsView or scanning, mention virtualization/throttling explicitly.

============================================================
11) STARTER TASK (Immediate execution suggestion)
============================================================
Start with the “empty path” bug fix:
- Add centralized path validation utility.
- Update playback/open calls to use it.
- Add UI feedback + disable buttons for invalid rows.

Then move to Pagination (ProjectsView), because it’s the largest freeze risk.

END OF DOCTRINE.
