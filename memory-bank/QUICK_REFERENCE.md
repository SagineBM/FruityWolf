# FruityWolf Quick Reference

**Last Updated:** 2026-01-29

---

## Quick Start for AI Agents

1. **Read Rules**: `.cursorrules`
2. **Read Context**: `memory-bank/activeContext.md`
3. **Use Commands**: `.cursor/commands/`

---

## Cursor Commands

| Command | Purpose |
|---------|---------|
| `/sync-daily` | Sync codebase with docs |
| `/fix-bug <id>` | Fix a bug |
| `/add-feature <name>` | Add a feature |
| `/optimize-performance <target>` | Optimize |
| `/update-docs [target]` | Update docs |
| `/scan-library` | Scanner work |

---

## Project Status

**Version:** 2.0.0  
**Completion:** ~80%

| Area | Status |
|------|--------|
| Core Features | ✅ 95% |
| UI/UX | ✅ 80% |
| Performance | ✅ 85% |
| Documentation | ✅ 95% |
| Testing | ❌ 20% |
| Distribution | 🟡 30% |

---

## Key Files

### Must Read
- `.cursorrules` — Project rules
- `AGENTS.md` — Agent instructions
- `memory-bank/activeContext.md` — Current focus

### Documentation
- `memory-bank/projectBrief.md` — Goals
- `memory-bank/systemPatterns.md` — Architecture
- `memory-bank/techContext.md` — Tech stack
- `memory-bank/progress.md` — Task status

---

## Module Map

| Module | Purpose | Key File |
|--------|---------|----------|
| core | Config | config.py |
| database | SQLite | models.py |
| scanner | Indexing | library_scanner.py |
| flp_parser | FLP | parser.py |
| classifier | States | engine.py |
| player | Audio | audio_player.py |
| ui | Interface | projects_view.py |

---

## Database

**Schema Version:** 17

| Table | Purpose |
|-------|---------|
| projects | FL projects |
| renders | Audio renders |
| project_plugins | FLP plugins |
| project_samples | FLP samples |
| tags, playlists | Organization |

---

## Key Patterns

1. **Model/View/Delegate** — Tables
2. **QThread Workers** — Background ops
3. **Signal Throttling** — 20fps max
4. **Batch Transactions** — 50 per commit
5. **WAL Mode** — Concurrency

---

## Forbidden

- Widget-per-cell in tables
- UI thread blocking
- N+1 database queries
- Unthrottled signals

---

## Open Issues

| Issue | Priority |
|-------|----------|
| Empty path playback | Medium |
| Async cover loading | High |
| Test coverage (~20%) | High |

---

## Quick Commands

```bash
python -m FruityWolf      # Run
python -m pytest tests/   # Test
python build.py           # Build
```

---

## Workflows

### Daily
```
/sync-daily (morning)
[work]
/sync-daily (evening)
```

### Feature
```
/sync-daily
/add-feature <name>
Test
/update-docs
/sync-daily
```

### Bug Fix
```
/sync-daily
/fix-bug <id>
Test
/update-docs progress
/sync-daily
```

---

## Success Metrics

- ✅ Zero-lag scrolling (10k+ projects)
- ✅ Model/View pattern
- ✅ Signal throttling
- ✅ WAL mode
- ✅ Documentation complete
- ⚠️ Test coverage needs work
