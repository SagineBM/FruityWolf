# Project Brief: FruityWolf

**Last Updated:** 2026-01-29  
**Version:** 2.0.0

---

## Core Philosophy

**"Spotify for Producers"** — A beautiful, modern library manager and player for FL Studio project folders.

FruityWolf replaces basic file explorer interaction with a rich, media-centric interface that treats FL Studio projects (`.flp`) and their renders as "tracks" in a library.

---

## Vision

FruityWolf is the **definitive open-source library manager** for FL Studio producers, offering features no other tool provides — particularly **deep FLP file intelligence** powered by PyFLP.

---

## Key Features

### Core
- **Modern UI** — Dark theme, glassmorphism, smooth animations
- **Intelligent Indexing** — Auto-scan FL Studio folders
- **Instant Playback** — VLC-based player with waveforms
- **Smart Metadata** — BPM/Key detection, tagging, organization
- **Non-Destructive** — Reads files without modification

### FLP Intelligence
- **Plugin Tracking** — See which plugins are used in each project
- **Sample Usage** — Track overused/underused samples
- **Project Classification** — Lifecycle states (Idea → WIP → Advanced)
- **Completion Scoring** — 0-100 score based on project signals

---

## User Workflow

1. **Immerse** — Point FruityWolf to music production folder
2. **Discover** — App indexes projects, creating searchable library
3. **Organize** — Tag ideas, filter by key/BPM, create playlists
4. **Act** — One-click to open FLP in FL Studio

---

## Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| Zero-lag scrolling | 10k+ projects | ✅ Achieved |
| FLP ↔ Render pairing | Accurate | ✅ Achieved |
| UI "wow" factor | Modern creative tools | ✅ Achieved |
| Crash rate | <1% | 🟡 Needs testing |
| Test coverage | >80% | ❌ Currently ~20% |

---

## Target Users

- FL Studio producers with large project libraries
- Beat makers who need to organize ideas
- Artists managing hundreds of project folders
- Anyone who wants Spotify-like browsing for their beats

---

## Non-Goals

- Not a DAW replacement
- Not for editing FLP files
- Not for audio production
- Not a cloud service (local only)

---

## Technical Constraints

1. **Windows primary** — Mac/Linux secondary
2. **Python 3.11+** — Required for pyflp
3. **VLC required** — For audio playback
4. **Local only** — No cloud/network features

---

## Business Impact

- **Time Saved** — Quick access to any project
- **Organization** — No more lost ideas
- **Insights** — Plugin/sample usage analytics
- **Workflow** — Seamless FL Studio integration

---

## Stakeholders

- **Primary** — FL Studio producers
- **Secondary** — Music production community
- **Tertiary** — Open-source contributors

---

## Documentation

| File | Purpose |
|------|---------|
| `.cursorrules` | AI agent rules |
| `AGENTS.md` | Agent instructions |
| `ROADMAP.md` | Feature roadmap |
| `memory-bank/` | Living documentation |

---

## Current Focus

**Production Polish Phase** — Preparing for production-grade quality:
1. Async cover loading
2. Error reporting
3. Test coverage
4. CI/CD pipeline

See `memory-bank/activeContext.md` for current details.
