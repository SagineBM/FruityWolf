# Changelog

All notable user-facing changes to FruityWolf are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- Async cover loading (worker pool, LRU cache)
- Error reporting and first-run experience improvements
- Light theme option
- CI/CD pipeline and release automation

---

## [2.0.0] — 2026-01-30

### Added

- **Identity-first scanning** — Stable project identity (PID), confidence scoring, and signal-based matching for FLP ↔ render pairing. Support for flat folder layouts where FLPs and audio live in the same directory.
- **Metadata drift prevention** — User lock to prevent automatic metadata changes; confidence thresholds and review queue for uncertain updates.
- **Custom covers** — Upload and manage custom cover art for projects, tracks, and playlists. Covers stored in app data with automatic cleanup on deletion.
- **Async cover loading** — Background loading with LRU cache and request cancellation for smooth scrolling.
- **Adapter pattern for scanners** — DAW adapter interface (FL Studio adapter included) as a base for future multi-DAW support.
- **Debug and maintenance scripts** — `scripts/debug_renders.py`, `scripts/check_project_files.py`, `scripts/check_renders.py`, `scripts/check_dates.py`, `scripts/check_library_tracks.py`, `scripts/fix_project_dates.py`, `scripts/fix_track_dates.py`, `scripts/fix_schema.py`, `scripts/run_migrations.py`.
- **Open source docs** — CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md, CHANGELOG.md, and [docs/](docs/) (installation, building, architecture, development, configuration). Sample config as `config.sample.json`.

### Changed

- Scanner: incremental scanning, FLP parse caching, duration caching, parallel scanning, and batch transactions for faster rescans.
- Projects and tracks sorted by original file creation date (Windows “Date created”) where available.
- UI: confidence indicators and lock indicator in project details; tooltips for match reasons.

### Fixed

- Duplicate render path handling (UNIQUE constraint errors) with global path checking and graceful handling of race conditions.
- Library sort and date display to use file creation date; project date updates from newest render.

---

## [1.x]

Earlier releases before this changelog was introduced. See [ROADMAP.md](ROADMAP.md) for completed phases and feature history.

[Unreleased]: https://github.com/FruityWolf/FruityWolf/compare/master...HEAD
[2.0.0]: https://github.com/FruityWolf/FruityWolf/releases/tag/v2.0.0
