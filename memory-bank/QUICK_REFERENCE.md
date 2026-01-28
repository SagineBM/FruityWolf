# FruityWolf Quick Reference Guide

**Last Updated:** 2026-01-28  
**Purpose:** Quick access to common commands, workflows, and information

---

## 🚀 Quick Commands

### Most Used
```bash
/command sync daily              # Daily sync (run morning & end of day)
/command scan library            # Scan library
/command classify project --all  # Reclassify all projects
/command fix bug <id>            # Fix a bug
/command add feature <name>      # Add a feature
/command update docs all         # Update all documentation
```

### Development
```bash
/command optimize performance <target>  # Optimize performance
/command test all                       # Run all tests
/command lint                           # Run linters
/command format                         # Format code
/command db migrate                     # Run migrations
```

---

## 📚 Documentation Files

| File | Purpose | Update Frequency |
|------|---------|------------------|
| `projectBrief.md` | Project goals, scope | On change |
| `activeContext.md` | Current focus, blockers | Daily |
| `progress.md` | Completed tasks, status | Daily |
| `systemPatterns.md` | Architecture patterns | On change |
| `techContext.md` | Tech stack, dependencies | On change |
| `codebaseReport.md` | Complete codebase analysis | Weekly |
| `featureChecklist.md` | Feature status | On change |
| `workflowSystem.md` | Command system | On change |
| `dailySyncCommand.md` | Sync command docs | On change |
| `optimizationOpportunities.md` | Performance optimizations | On change |
| `ecosystemDocumentation.md` | Complete ecosystem overview | Weekly |

---

## 🎯 Common Workflows

### Daily Work
```
Morning:
  /command sync daily
  
End of Day:
  /command sync daily
```

### Feature Development
```
1. /command sync daily
2. /command add feature <name>
3. Test feature
4. /command update docs all
5. /command sync daily
```

### Bug Fix
```
1. /command sync daily
2. /command fix bug <id>
3. Test fix
4. /command update docs progress
5. /command sync daily
```

### Performance Optimization
```
1. /command optimize performance <target>
2. Test changes
3. /command update docs systemHealth
4. /command sync daily
```

---

## 📊 Current Status

### Completion: ~75%
- Core Features: **95%** ✅
- UI/UX: **80%** ✅
- Performance: **85%** ✅
- Testing: **20%** ❌
- Documentation: **90%** ✅ (just completed!)
- Distribution: **30%** 🟡

### Current Focus
**FruityWolf Scalability Upgrade** — Pagination & performance optimization

### Recent Changes
- ✅ Complete documentation system created
- ✅ Workflow system established
- ✅ Command structure defined
- ✅ Optimization roadmap created

### Next Steps
1. Implement high-priority optimizations
2. Increase test coverage
3. Complete market-ready features
4. Set up CI/CD

---

## 🔧 Key Modules

### Core
- `app.py` - Main application (2800+ lines, needs splitting)
- `database/models.py` - Database schema
- `database/migrations.py` - Migration system (17 migrations)

### Scanner
- `scanner/library_scanner.py` - Library scanning
- `scanner/fl_project_detector.py` - Project detection
- `scanner/fl_render_classifier.py` - Render classification

### FLP Parser
- `flp_parser/parser.py` - FLP file parsing
- `flp_parser/compatibility.py` - Python 3.11+ compatibility

### Classifier
- `classifier/engine.py` - Project classification
- `classifier/fl_truth_rules.json` - Classification rules

### Player
- `player/audio_player.py` - Audio playback (VLC)

### UI
- `ui/projects_view.py` - Projects table (Model/View)
- `ui/view_models/projects_model.py` - Projects model
- `ui/delegates/projects_delegate.py` - Custom rendering

---

## 🗄️ Database Schema

### Key Tables
- `projects` - FL Studio project folders (main entity)
- `renders` - Audio renders/exports (new system)
- `tracks` - Legacy audio files
- `project_plugins` - Plugins used in projects
- `project_samples` - Samples referenced in FLP
- `tags` - User tags
- `playlists` - User playlists
- `settings` - App settings

### Current Version
**Migration 17** - Renders table + primary render support

---

## 🎨 UI Structure

### Views
- `ProjectsView` - Projects table
- `PlaylistsView` - Playlist management
- `PluginIntelligenceView` - Plugin analytics
- `SampleOverviewView` - Sample usage
- `SettingsView` - Settings

### Panels
- `ProjectDetailsPanel` - Project drill-down
- `TrackDetailsPanel` - Track metadata
- `PluginsPanel` - Project plugins
- `RendersPanel` - Render management

---

## ⚡ Performance

### Current
- Projects View: ~500ms (1000 projects)
- Library Scan: ~2-5 minutes (1000 projects)
- Memory: ~200-400MB

### Target (After Optimizations)
- Projects View: ~100ms ✅ 5x faster
- Library Scan: ~1-2 minutes ✅ 2x faster
- Memory: ~100-200MB ✅ 50% reduction

### High-Priority Optimizations
1. Async cover loading
2. Database query optimization
3. Scanner batch operations
4. Memory optimization

---

## 🐛 Known Issues

### Bugs
- `empty_path_playback` - Empty path warning (needs proper handling)
- `projects_view_lag` - Mostly fixed, minor improvements possible

### Technical Debt
- `app.py` too large (needs splitting)
- Limited test coverage
- Some hardcoded values

---

## 📦 Dependencies

### Core
- PySide6>=6.6.0,<6.8.0
- python-vlc>=3.0.20
- numpy>=1.26.0,<2.0.0

### Analysis
- librosa>=0.10.1
- scipy>=1.11.0
- soundfile>=0.12.1

### FLP Parsing
- pyflp>=2.0.0

### Utilities
- mutagen>=1.47.0
- watchdog>=3.0.0
- Pillow>=10.1.0

---

## 🎯 Priority Roadmap

### Week 1-2: Critical Fixes
- Error reporting
- Comprehensive logging
- First-run wizard
- Basic documentation ✅

### Week 3-4: Polish
- Light theme
- Help system
- Tooltips
- Empty states

### Week 5-6: Distribution
- CI/CD setup
- Installer creation
- Auto-updater
- Release process

### Week 7-8: Testing
- Unit test coverage
- Integration tests
- Performance testing
- Bug fixes

---

## 📝 Documentation Standards

### Update Frequency
- **Daily:** `activeContext.md`, `progress.md`
- **On Change:** `systemPatterns.md`, `techContext.md`
- **Weekly:** `codebaseReport.md`
- **As Needed:** Other files

### Commands
```bash
/command update docs all
/command update docs activeContext
/command update docs progress
/command sync daily
```

---

## 🔍 Quick Troubleshooting

### Sync Issues
- Use `--verbose` to see detection
- Manually specify with `--focus`, `--changes`, etc.

### Performance Issues
- Check `systemHealth.md`
- See `optimizationOpportunities.md`
- Run `/command optimize performance <target>`

### Documentation Issues
- Run `/command update docs all`
- Check file timestamps
- Verify git status

---

## 📞 Resources

### Documentation
- All docs: `memory-bank/`
- User docs: `README.md`
- Planning: `ROADMAP.md`

### Development
- Doctrine: `FruityWold_Doctrine.md`
- Patterns: `systemPatterns.md`
- Tech: `techContext.md`

### Commands
- Workflow: `workflowSystem.md`
- Sync: `dailySyncCommand.md`

---

## ✅ Checklist for New Features

- [ ] Read `projectBrief.md` (understand goals)
- [ ] Read `systemPatterns.md` (understand architecture)
- [ ] Design feature
- [ ] Implement code
- [ ] Update database (if needed)
- [ ] Update UI (if needed)
- [ ] Test feature
- [ ] Update `progress.md`
- [ ] Update `activeContext.md`
- [ ] Run `/command sync daily`

---

## 🎉 Success Metrics

### Code Quality
- ✅ Modular architecture
- ✅ Clear separation of concerns
- ✅ Documentation strings
- ✅ Error handling
- ⚠️ Test coverage (needs improvement)

### Performance
- ✅ Model/View pattern
- ✅ Throttled signals
- ✅ WAL mode
- ✅ Virtualization
- ✅ Pagination

### Documentation
- ✅ Complete codebase report ✅
- ✅ Feature checklist ✅
- ✅ Workflow system ✅
- ✅ Daily sync command ✅
- ✅ Optimization roadmap ✅
- ✅ Ecosystem documentation ✅

---

**Last Updated:** 2026-01-28  
**Version:** 2.0.0
