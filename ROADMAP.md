# FruityWolf Roadmap

> **Mission**: Make FruityWolf the tool every FL Studio producer thanks 10 times a day.

**Last Updated:** 2026-01-29

---

## Vision

FruityWolf is the **definitive open-source library manager** for FL Studio producers, offering features no other tool provides — particularly **deep FLP file intelligence** powered by PyFLP.

---

## Current Status

| Component | Status | Notes |
|-----------|--------|-------|
| Core Player | ✅ Complete | VLC-based, waveforms, shortcuts |
| Library Scanner | ✅ Complete | Throttled signals, WAL mode, batch ops |
| Project Classification | ✅ Complete | Lifecycle stages, scoring, next actions |
| Sample Intelligence | ✅ Complete | Overused/underused detection |
| Deep FLP Parsing | ✅ Complete | Plugins, samples, metadata extraction |
| Plugin Intelligence | ✅ Complete | Usage tracking, vendor detection |
| Scalability | ✅ Complete | Model/View, pagination, caching |
| Documentation | ✅ Complete | Full ecosystem documentation |
| Testing | 🟡 Partial | ~20% coverage, needs improvement |
| Distribution | 🟡 Partial | Build works, needs CI/CD |

---

## Completed Phases

### Phase 1: Bug Fixes & Stability ✅
- [x] Validate file paths (path_utils.py)
- [x] Graceful handling of missing files
- [ ] Fix "empty path" playback bug (low priority, remaining)

### Phase 2: PyFLP Integration ✅
- [x] Add pyflp dependency
- [x] Create `flp_parser/` module
- [x] Parse plugins (generators + effects)
- [x] Parse samples referenced in FLP
- [x] Get BPM/time signature from project
- [x] New DB tables: `project_plugins`, `project_samples`
- [x] Integrate parsing into scanner
- [x] UI: Plugins panel in project details
- [x] Plugin name normalization
- [x] Native FL plugin database (~100+ plugins)
- [x] Third-party vendor detection (40+ vendors)
- [x] Format detection (VST2, VST3, CLAP, AAX)

### Phase 3: Scalability ✅
- [x] Pagination for ProjectsView (infinite scroll)
- [x] Database indexes on search columns
- [x] Model/View pattern (10x faster)
- [x] Signal throttling (20fps max)
- [x] WAL mode for concurrency
- [ ] Async cover loading (high priority)

### Phase 4: Producer Analytics ✅
- [x] Plugin Usage Dashboard (PluginIntelligenceView)
- [x] Sample Hotspots (SampleOverviewView)
- [x] Project state classification
- [x] Completion scoring
- [ ] Missing dependency warnings (planned)
- [ ] Export reports (planned)

### Phase 5: Documentation ✅
- [x] Complete codebase analysis
- [x] Feature checklist
- [x] Workflow system
- [x] Cursor commands
- [x] Agent instructions
- [x] Quick reference guide

---

## Current Focus

### Phase 6: Production Polish
**Priority:** Getting to production-grade quality

#### High Priority
1. **Async Cover Loading**
   - Worker pool for image loading
   - LRU cache with cancellation
   - Expected: 50-70% faster UI

2. **Error Reporting**
   - Crash reporting integration
   - Error logs collection
   - User feedback system

3. **First-Run Experience**
   - Welcome wizard
   - Library setup guide
   - Tutorial/onboarding

#### Medium Priority
4. **Light Theme**
   - QSS theme system
   - User preference

5. **Test Coverage**
   - Increase to >80%
   - Integration tests
   - UI tests

6. **CI/CD Pipeline**
   - GitHub Actions
   - Automated builds
   - Release automation

---

## Future Phases

### Phase 7: Distribution
- [ ] Automated installer creation
- [ ] Auto-updater
- [ ] Release notes system
- [ ] Changelog generation

### Phase 8: Advanced Features
- [ ] Export/import library
- [ ] Saved searches
- [ ] Analytics dashboard
- [ ] Cloud sync (future)

### Phase 9: Accessibility
- [ ] Screen reader support
- [ ] Keyboard navigation
- [ ] High contrast mode
- [ ] Font size scaling

---

## Technical Debt

| Item | Priority | Notes |
|------|----------|-------|
| Split app.py | Medium | 3300+ lines, hard to maintain |
| Repository pattern | Low | Centralize DB queries |
| Service layer | Low | Extract from UI |
| Event bus | Low | Decouple components |

---

## Success Metrics

- **Performance**: Zero-lag scrolling with 10k+ projects
- **Accuracy**: Correct pairing FLP ↔ renders
- **Aesthetics**: Modern, polished UI
- **Stability**: <1% crash rate
- **Test Coverage**: >80%

---

## Contributing

See `AGENTS.md` for AI agent instructions and `.cursorrules` for project rules.

---

## License

MIT License — Free for all producers!
