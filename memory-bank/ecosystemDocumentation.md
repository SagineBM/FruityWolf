# FruityWolf Complete Ecosystem Documentation

**Last Updated:** 2026-01-28  
**Version:** 2.0.0  
**Status:** Production-Ready Documentation

---

## 📚 Documentation Index

This document provides a **complete overview** of the FruityWolf ecosystem, including all components, workflows, and how they interact.

### Core Documentation Files
1. **[projectBrief.md](projectBrief.md)** - Project purpose, goals, constraints
2. **[activeContext.md](activeContext.md)** - Current focus, recent changes, blockers
3. **[progress.md](progress.md)** - Completed tasks, milestones, status
4. **[systemPatterns.md](systemPatterns.md)** - Architecture patterns, design decisions
5. **[techContext.md](techContext.md)** - Technology stack, dependencies, constraints
6. **[FruityWold_Doctrine.md](FruityWold_Doctrine.md)** - Development doctrine, rules, patterns

### New Documentation Files
7. **[codebaseReport.md](codebaseReport.md)** - Complete codebase analysis
8. **[featureChecklist.md](featureChecklist.md)** - Feature status, market-ready checklist
9. **[workflowSystem.md](workflowSystem.md)** - Agent command system, workflows
10. **[dailySyncCommand.md](dailySyncCommand.md)** - Daily sync command documentation
11. **[optimizationOpportunities.md](optimizationOpportunities.md)** - Performance optimizations
12. **[ecosystemDocumentation.md](ecosystemDocumentation.md)** - This file

---

## 🏗️ Architecture Overview

### System Layers

```
┌─────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Views      │  │   Panels     │  │   Delegates   │  │
│  │ (Projects,   │  │ (Details,    │  │ (Custom       │  │
│  │  Samples)    │  │  Plugins)    │  │  Rendering)   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│           ↕ Signals                                      │
└─────────────────────────────────────────────────────────┘
                        ↕
┌─────────────────────────────────────────────────────────┐
│                    DOMAIN LOGIC LAYER                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Scanner    │  │ Classifier   │  │   Player     │  │
│  │ (Library     │  │ (Project     │  │ (Audio       │  │
│  │  Indexing)   │  │  States)     │  │  Playback)   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ FLP Parser   │  │  Analysis    │  │  Waveform    │  │
│  │ (Metadata    │  │ (BPM/Key     │  │ (Visualization│ │
│  │  Extraction) │  │  Detection)  │  │              │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                        ↕ SQL
┌─────────────────────────────────────────────────────────┐
│                      DATA LAYER                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Database    │  │ Migrations   │  │   Cache      │  │
│  │  (SQLite)    │  │ (Versioning) │  │ (Waveforms,  │  │
│  │              │  │              │  │  Images)     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow

### 1. Library Scanning Flow

```
User Action: "Scan Library"
    ↓
LibraryScanner.scan_all()
    ↓
For each library root:
    ├─> Detect FL Studio projects (fl_project_detector)
    ├─> Classify renders (fl_render_classifier)
    ├─> Parse FLP files (flp_parser)
    ├─> Extract plugins/samples
    ├─> Classify project (classifier)
    └─> Update database
        ↓
Emit progress signals (throttled)
    ↓
Update UI (ProjectsView)
```

### 2. Project Classification Flow

```
Project Signals (raw + derived)
    ↓
ProjectClassifier.classify()
    ↓
Evaluate Rules (JSON-based)
    ├─> Determine State (project_states.json)
    ├─> Calculate Score (scoring_rules.json)
    └─> Suggest Action (next_actions.json)
        ↓
ClassificationResult
    ↓
Save to Database
    ↓
Update UI
```

### 3. Playback Flow

```
User Action: "Play Track"
    ↓
AudioPlayer.load_track(track_dict)
    ↓
Validate Path
    ↓
Load Media (VLC/Qt)
    ├─> Parse metadata
    ├─> Get duration
    └─> Start playback
        ↓
Emit Signals
    ├─> state_changed
    ├─> duration_changed
    ├─> position_changed (100ms interval)
    └─> track_changed
        ↓
Update UI
    ├─> Player controls
    ├─> Waveform view
    └─> Queue panel
```

### 4. UI Update Flow

```
Data Change (Database/Scanner/Player)
    ↓
Emit Signal
    ↓
Qt Signal/Slot Connection
    ↓
View/Model Update
    ├─> ProjectsModel.set_projects()
    ├─> ProjectsView.refresh_data()
    └─> Delegate repaint()
        ↓
UI Refresh (Qt repaint)
```

---

## 📦 Module Dependencies

### Dependency Graph

```
app.py
├─> ui/ (all UI modules)
│   ├─> projects_view.py
│   │   ├─> view_models/projects_model.py
│   │   └─> delegates/projects_delegate.py
│   ├─> panels/ (all panels)
│   └─> widgets.py
├─> scanner/
│   ├─> library_scanner.py
│   │   ├─> fl_project_detector.py
│   │   ├─> fl_render_classifier.py
│   │   └─> flp_parser/parser.py
│   └─> file_watcher.py
├─> player/
│   └─> audio_player.py
├─> classifier/
│   └─> engine.py
├─> database/
│   ├─> models.py
│   └─> migrations.py
├─> analysis/
│   └─> detector.py
├─> waveform/
│   └─> extractor.py
└─> utils/
    ├─> helpers.py
    ├─> icons.py
    └─> path_utils.py
```

---

## 🗄️ Database Schema

### Entity Relationship Diagram

```
projects (1) ──< (many) renders
projects (1) ──< (many) project_plugins
projects (1) ──< (many) project_samples
projects (1) ──< (many) tracks

tracks (many) ──< (many) track_tags ──> (many) tags
tracks (many) ──< (many) playlist_tracks ──> (many) playlists

projects (1) ──> (1) renders [primary_render_id]
```

### Key Tables

**projects**
- Main entity for FL Studio project folders
- Contains classification data (state, score, next_action)
- Links to FLP metadata
- References primary render

**renders**
- Audio files that are project renders/exports
- Separate from general tracks
- Supports multiple renders per project
- One primary render per project

**project_plugins**
- Plugins used in projects (from FLP parsing)
- Links projects to installed plugins
- Tracks plugin usage

**project_samples**
- Samples referenced in FLP files
- Used for sample usage analytics

**tracks**
- Legacy table for audio files
- Still used for compatibility
- Links to projects

---

## 🔌 Integration Points

### 1. FL Studio Integration
- **FLP Parsing:** `flp_parser/parser.py`
- **Project Detection:** `scanner/fl_project_detector.py`
- **Render Classification:** `scanner/fl_render_classifier.py`

### 2. Audio Playback
- **VLC Backend:** `player/audio_player.py`
- **Fallback:** Qt Multimedia
- **Waveform:** `waveform/extractor.py`

### 3. Analysis
- **BPM/Key:** `analysis/detector.py`
- **Background Processing:** `analysis/worker_process.py`
- **Batch Analysis:** `services/batch_analyzer.py`

### 4. File System
- **Watching:** `services/folder_watcher.py`
- **Scanning:** `scanner/library_scanner.py`
- **Validation:** `utils/path_utils.py`

---

## 🎨 UI Component Structure

### Views (Main Screens)
- `ProjectsView` - Projects table with filtering
- `PlaylistsView` - Playlist management
- `PluginIntelligenceView` - Plugin analytics
- `SampleOverviewView` - Sample usage overview
- `SampleDetailView` - Sample detail
- `SettingsView` - Settings UI

### Panels (Detail Views)
- `ProjectDetailsPanel` - Project drill-down
- `TrackDetailsPanel` - Track metadata
- `PluginsPanel` - Project plugins list
- `PluginDetailsPanel` - Plugin detail
- `RendersPanel` - Render management
- `SampleProjectsPanel` - Projects using sample
- `SampleUsagePanel` - Sample usage stats

### Models (Data)
- `ProjectsModel` - Projects table model
- `PlaylistsModel` - Playlist list model
- `PlaylistTracksModel` - Playlist tracks model

### Delegates (Rendering)
- `ProjectsDelegate` - Custom project rendering

---

## 🔄 Workflow Patterns

### Pattern 1: Feature Development
```
1. Read Memory Bank (projectBrief, activeContext, progress)
2. Design feature (systemPatterns)
3. Implement code
4. Update database (if needed)
5. Update UI (if needed)
6. Test feature
7. Update documentation (progress, activeContext)
8. Sync daily
```

### Pattern 2: Bug Fix
```
1. Identify bug (systemHealth, activeContext)
2. Locate code
3. Fix bug
4. Test fix
5. Update documentation (progress, systemHealth)
6. Sync daily
```

### Pattern 3: Performance Optimization
```
1. Profile code (optimizationOpportunities)
2. Identify bottleneck
3. Implement optimization
4. Benchmark before/after
5. Update documentation (systemHealth, optimizationOpportunities)
6. Sync daily
```

---

## 📊 State Management

### Application State
- **Global State:** `app.py` MainWindow
- **Player State:** `player/audio_player.py` AudioPlayer
- **Scanner State:** `scanner/library_scanner.py` LibraryScanner
- **UI State:** Individual views/panels

### Database State
- **Projects:** `projects` table
- **Tracks:** `tracks` table
- **Renders:** `renders` table
- **Settings:** `settings` table

### Classification State
- **Rules:** JSON files in `resources/rules/`
- **State:** `state_id` column in `projects`
- **Score:** `score` column in `projects`
- **Next Action:** `next_action_id` column in `projects`

---

## 🚀 Command System

### Available Commands
See **[workflowSystem.md](workflowSystem.md)** for complete command reference.

**Common Commands:**
- `/command sync daily` - Daily sync
- `/command scan library` - Scan library
- `/command classify project --all` - Reclassify all
- `/command fix bug <id>` - Fix bug
- `/command add feature <name>` - Add feature
- `/command optimize performance <target>` - Optimize
- `/command update docs all` - Update docs

---

## 📈 Performance Characteristics

### Current Performance
- **Projects View:** ~500ms (1000 projects)
- **Library Scan:** ~2-5 minutes (1000 projects)
- **FLP Parsing:** ~100-200ms per project
- **Memory Usage:** ~200-400MB

### Optimization Opportunities
See **[optimizationOpportunities.md](optimizationOpportunities.md)** for details.

**Key Optimizations:**
1. Async cover loading
2. Database query optimization
3. Scanner batch operations
4. Memory optimization
5. Waveform progressive loading

---

## 🧪 Testing Strategy

### Test Structure
```
tests/
├─> test_analysis.py      # Analysis tests
├─> test_database.py      # Database tests
├─> test_scanner.py       # Scanner tests
└─> test_utils.py         # Utility tests
```

### Test Coverage
- **Unit Tests:** Partial (core logic)
- **Integration Tests:** Minimal
- **UI Tests:** None
- **Performance Tests:** None

### Running Tests
```bash
/command test all
/command test database
/command test scanner
```

---

## 📦 Build & Distribution

### Build System
- **Build Script:** `build.py`
- **Package Config:** `pyproject.toml`
- **Dependencies:** `requirements.txt`

### Distribution
- **Windows:** `FruityWolf-Setup.exe` (planned)
- **Build Tool:** PyInstaller
- **Auto-Updater:** Not implemented

### CI/CD
- **Status:** Not implemented
- **Planned:** GitHub Actions

---

## 🔐 Security Considerations

### Current Security
- ✅ Path validation (`path_utils.py`)
- ✅ SQL injection protection (parameterized queries)
- ✅ File existence checks
- ⚠️ No input sanitization for user content (low risk)

### Recommendations
- Add input sanitization for tags/notes
- Add rate limiting for operations
- Add file type validation
- Add permission checks

---

## 📝 Documentation Standards

### File Naming
- `camelCase.md` for documentation files
- Descriptive names
- Consistent structure

### Update Frequency
- **Daily:** `activeContext.md`, `progress.md`
- **On Change:** `systemPatterns.md`, `techContext.md`
- **Weekly:** `codebaseReport.md`
- **As Needed:** Other files

### Documentation Commands
```bash
/command update docs all
/command update docs activeContext
/command update docs progress
/command sync daily
```

---

## 🎯 Development Workflow

### Daily Workflow
```
Morning:
  1. /command sync daily          # Get current state
  2. Read activeContext.md        # Understand focus
  3. Read progress.md             # Check status

During Work:
  1. Implement changes
  2. Test changes
  3. Update documentation
  4. /command sync daily          # After major changes

End of Day:
  1. /command sync daily          # Final sync
  2. Review changes
  3. Commit (if ready)
```

### Feature Development
```
1. Read projectBrief.md          # Understand goals
2. Read systemPatterns.md         # Understand architecture
3. Design feature
4. /command add feature <name>   # Implement
5. Test feature
6. /command update docs all      # Update docs
7. /command sync daily           # Sync
```

### Bug Fix Workflow
```
1. Identify bug
2. /command fix bug <id>         # Fix
3. Test fix
4. /command update docs progress # Update
5. /command sync daily           # Sync
```

---

## 🔮 Future Enhancements

### Planned Features
- Light theme
- Export/import library
- Advanced search UI
- Analytics dashboard
- Cloud sync (future)
- Mobile app (future)

### Technical Improvements
- Split app.py into smaller modules
- Repository pattern for database
- Service layer extraction
- Event bus for decoupling
- Plugin system

---

## 📞 Support & Resources

### Documentation
- All docs in `memory-bank/`
- README.md for users
- ROADMAP.md for planning

### Development
- Doctrine: `FruityWold_Doctrine.md`
- Patterns: `systemPatterns.md`
- Tech: `techContext.md`

### Commands
- Workflow: `workflowSystem.md`
- Sync: `dailySyncCommand.md`

---

## ✅ Conclusion

FruityWolf has a **well-structured ecosystem** with:
- ✅ Clear architecture
- ✅ Comprehensive documentation
- ✅ Standardized workflows
- ✅ Command system for agents
- ✅ Performance optimization roadmap
- ✅ Testing strategy (partial)

**Next Steps:**
1. Implement high-priority optimizations
2. Increase test coverage
3. Complete market-ready features
4. Set up CI/CD
5. Create distribution pipeline

---

**Last Updated:** 2026-01-28  
**Maintained By:** Development Team  
**Version:** 2.0.0
