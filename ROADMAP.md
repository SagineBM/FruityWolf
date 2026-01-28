# FruityWolf Roadmap 🐺

> **Mission**: Make FruityWolf the tool every FL Studio producer thanks 10 times a day.

---

## 🎯 Vision

FruityWolf will become the **definitive open-source library manager** for FL Studio producers by offering features no other tool provides — particularly **deep FLP file intelligence** powered by PyFLP.

---

## 📋 Current Status

| Component                  | Status                       | Notes                           |
| -------------------------- | ---------------------------- | ------------------------------- |
| Core Player                | ✅ Complete                  | VLC-based, waveforms, shortcuts |
| Library Scanner            | ✅ Complete                  | Throttled signals, WAL mode     |
| Project Classification     | ✅ Complete                  | Lifecycle stages, scoring       |
| Sample Intelligence        | ✅ Basic                     | Overused/underused detection    |
| **Deep FLP Parsing** | ✅ Basic - Not very accurate | The game-changer feature        |
| **Scalability**      | 🟡 Partial                   | Pagination TODO                 |

---

## 🚀 Phases

### Phase 1: Bug Fixes & Stability

**Target**: Immediate

- [ ] Fix "empty path" playback bug
- [ ] Validate file paths before operations
- [ ] Graceful handling of missing files

---

### Phase 2: PyFLP Integration ⭐ (Game-Changer)

**Target**: Week 1-2

**What it unlocks:**

- See which **plugins** are used in each project
- Discover **samples** referenced in FLP files
- Get **BPM/time signature** directly from project
- Detect **missing plugins/samples**

**Implementation:**

- [ ] Add `pyflp` dependency
- [ ] Create `FruityWolf/flp_parser/` module
- [ ] Parse plugins, samples, tempo from FLP
- [ ] New DB tables: `project_plugins`, `project_flp_samples`
- [ ] Integrate parsing into scanner
- [ ] UI: Plugins panel in project details

**Why this matters:**

> "You use Serum in 73% of projects"
> "This kick sample appears in 42 projects"
> "Warning: 3 projects need plugins you don't have"

---

### Phase 3: Scalability

**Target**: Week 2-3

- [ ] Pagination for ProjectsView (>2000 items)
- [ ] Database indexes on search columns
- [ ] Async cover/artwork loading
- [ ] Virtual scrolling for large lists

---

### Phase 4: Producer Analytics

**Target**: Week 3-4

- [ ] **Plugin Usage Dashboard**: Most used plugins across library
- [ ] **Sample Hotspots**: Find reused samples
- [ ] **Missing Dependencies**: Warn about unavailable plugins
- [ ] **Project Templates**: Detect starting point templates
- [ ] **Export Reports**: PDF/HTML project summaries

---

### Phase 5: Open Source Polish

**Target**: Week 4+

- [ ] Theme system (light/dark/custom)
- [ ] Comprehensive test coverage
- [ ] Contributor documentation
- [ ] GitHub Actions CI/CD
- [ ] Release automation
- [ ] README with screenshots/GIFs

---

## 🔧 Technical Details

### New Module: `flp_parser/`

```
FruityWolf/flp_parser/
├── __init__.py      # Exports FLPParser
├── parser.py        # PyFLP wrapper
└── models.py        # FLPData dataclass
```

### Database Schema Additions

```sql
-- Plugins used in projects
CREATE TABLE project_plugins (
    id INTEGER PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    plugin_name TEXT NOT NULL,
    plugin_type TEXT,  -- 'generator', 'effect'
    channel_index INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Samples referenced in FLP
CREATE TABLE project_flp_samples (
    id INTEGER PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    sample_path TEXT NOT NULL,
    sample_name TEXT,
    is_missing BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes
CREATE INDEX idx_tracks_title ON tracks(title);
CREATE INDEX idx_tracks_bpm ON tracks(bpm_user);
CREATE INDEX idx_projects_state ON projects(state);
```

---

## 📦 Dependencies

```txt
# New additions to requirements.txt
pyflp>=2.0.0  # FLP file parsing (FL 20+ support)
```

---

## ✅ Progress Tracking

Use this section to track implementation:

```
[x] = Completed
[/] = In Progress  
[ ] = Not Started
```

### Phase 1

- [ ] Bug fix: empty path playback

### Phase 2

- [ ] PyFLP dependency added
- [ ] flp_parser module created
- [ ] Database schema updated
- [ ] Scanner integration
- [ ] UI plugins panel

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

MIT License — Free for all producers!
