# FruityWolf Workflow System & Agent Commands

**Purpose:** Standardized workflow for agent-assisted development  
**Last Updated:** 2026-01-28

---

## 🎯 Workflow Philosophy

FruityWolf uses a **command-based workflow** where agents can be invoked with specific tasks using `/command` syntax. This ensures:
- **Consistency** - Same approach for all tasks
- **Traceability** - Commands are logged and tracked
- **Efficiency** - Agents know exactly what to do
- **Documentation** - Commands update relevant docs

---

## 📋 Command Structure

### Format
```
/command <action> [target] [options]
```

### Examples
```
/command scan library
/command fix bug empty_path_playback
/command add feature pagination
/command optimize performance projects_view
/command update docs codebase_report
/command sync daily
```

---

## 🔧 Available Commands

### 1. Library Management

#### `/command scan library`
**Purpose:** Trigger full library scan  
**Agent:** Scanner Agent  
**Actions:**
1. Check library roots
2. Start background scan
3. Show progress
4. Update database
5. Refresh UI

**Usage:**
```
/command scan library
/command scan library --root "F:\Music"
/command scan library --incremental
```

---

#### `/command scan project <path>`
**Purpose:** Scan single project  
**Agent:** Scanner Agent  
**Actions:**
1. Validate path
2. Detect FL Studio project
3. Extract metadata
4. Parse FLP (if available)
5. Update database
6. Return results

**Usage:**
```
/command scan project "F:\Music\MyProject"
```

---

### 2. Classification

#### `/command classify project <id>`
**Purpose:** Reclassify a project  
**Agent:** Classifier Agent  
**Actions:**
1. Load project signals
2. Run classifier
3. Update state/score/action
4. Update database
5. Refresh UI

**Usage:**
```
/command classify project 123
/command classify project --all
/command classify project --bulk 1,2,3,4,5
```

---

#### `/command update rules`
**Purpose:** Reload classification rules  
**Agent:** Classifier Agent  
**Actions:**
1. Load JSON rules
2. Compute hash
3. Update classifier
4. Log changes

**Usage:**
```
/command update rules
```

---

### 3. Bug Fixes

#### `/command fix bug <bug_id>`
**Purpose:** Fix a specific bug  
**Agent:** Bug Fix Agent  
**Actions:**
1. Identify bug location
2. Analyze root cause
3. Implement fix
4. Test fix
5. Update documentation
6. Update progress.md

**Usage:**
```
/command fix bug empty_path_playback
/command fix bug projects_view_lag
/command fix bug render_classification
```

**Known Bugs:**
- `empty_path_playback` - Empty path warning in playback
- `projects_view_lag` - Lag when loading projects (mostly fixed)
- `render_classification` - Incorrect render detection

---

### 4. Feature Development

#### `/command add feature <feature_name>`
**Purpose:** Add a new feature  
**Agent:** Feature Agent  
**Actions:**
1. Read requirements
2. Design implementation
3. Create/modify files
4. Update database (if needed)
5. Update UI (if needed)
6. Test feature
7. Update documentation

**Usage:**
```
/command add feature pagination
/command add feature async_cover_loading
/command add feature light_theme
/command add feature export_library
```

**Feature Templates:**
- UI Feature: Creates view/panel/model
- Database Feature: Creates migration + queries
- Service Feature: Creates service module
- Integration Feature: Creates parser/adapter

---

### 5. Performance Optimization

#### `/command optimize performance <target>`
**Purpose:** Optimize performance of a component  
**Agent:** Performance Agent  
**Actions:**
1. Profile target component
2. Identify bottlenecks
3. Implement optimizations
4. Benchmark before/after
5. Update systemHealth.md

**Usage:**
```
/command optimize performance projects_view
/command optimize performance scanner
/command optimize performance database
/command optimize performance player
```

**Optimization Targets:**
- `projects_view` - Table rendering
- `scanner` - Scanning speed
- `database` - Query performance
- `player` - Playback latency
- `waveform` - Generation speed

---

### 6. Documentation

#### `/command update docs <doc_type>`
**Purpose:** Update documentation  
**Agent:** Documentation Agent  
**Actions:**
1. Read current state
2. Update relevant docs
3. Ensure consistency
4. Update timestamps

**Usage:**
```
/command update docs codebase_report
/command update docs feature_checklist
/command update docs workflow_system
/command update docs all
```

**Document Types:**
- `codebase_report` - Full codebase analysis
- `feature_checklist` - Feature status
- `workflow_system` - This file
- `progress` - Progress tracking
- `activeContext` - Current focus
- `systemPatterns` - Architecture patterns
- `techContext` - Technology stack
- `all` - Update all docs

---

### 7. Daily Sync

#### `/command sync daily`
**Purpose:** Sync current state with documentation  
**Agent:** Sync Agent  
**Actions:**
1. Read git status
2. Read recent changes
3. Update activeContext.md
4. Update progress.md
5. Update systemHealth.md (if needed)
6. Generate daily report

**Usage:**
```
/command sync daily
/command sync daily --verbose
```

**Output:**
- Current focus
- Recent changes
- Blockers
- Next steps
- Updated documentation

---

### 8. Testing

#### `/command test <target>`
**Purpose:** Run tests  
**Agent:** Test Agent  
**Actions:**
1. Run unit tests
2. Run integration tests
3. Generate coverage report
4. Update test status

**Usage:**
```
/command test all
/command test database
/command test scanner
/command test classifier
```

---

### 9. Database

#### `/command db migrate`
**Purpose:** Run database migrations  
**Agent:** Database Agent  
**Actions:**
1. Check current version
2. Run pending migrations
3. Verify schema
4. Log changes

**Usage:**
```
/command db migrate
/command db migrate --version 17
/command db migrate --rollback 16
```

---

#### `/command db backup`
**Purpose:** Backup database  
**Agent:** Database Agent  
**Actions:**
1. Create backup file
2. Verify backup
3. Store in safe location

**Usage:**
```
/command db backup
/command db backup --path "backups/"
```

---

### 10. Code Quality

#### `/command lint`
**Purpose:** Run linters  
**Agent:** Lint Agent  
**Actions:**
1. Run ruff/black
2. Check formatting
3. Report issues
4. Auto-fix (if possible)

**Usage:**
```
/command lint
/command lint --fix
/command lint --strict
```

---

#### `/command format`
**Purpose:** Format code  
**Agent:** Format Agent  
**Actions:**
1. Run black
2. Run isort
3. Verify formatting

**Usage:**
```
/command format
/command format --check
```

---

## 🔄 Workflow Patterns

### Pattern 1: Feature Development
```
1. /command sync daily          # Get current state
2. /command add feature <name>  # Implement feature
3. /command test all            # Run tests
4. /command update docs all     # Update docs
5. /command sync daily          # Final sync
```

### Pattern 2: Bug Fix
```
1. /command sync daily          # Get current state
2. /command fix bug <id>        # Fix bug
3. /command test all            # Verify fix
4. /command update docs progress # Update progress
5. /command sync daily          # Final sync
```

### Pattern 3: Performance Optimization
```
1. /command optimize performance <target>  # Optimize
2. /command test all                      # Verify
3. /command update docs systemHealth      # Update health
4. /command sync daily                    # Sync
```

### Pattern 4: Daily Work
```
1. /command sync daily          # Morning sync
2. [Work on tasks]
3. /command sync daily          # End of day sync
```

---

## 📊 Command Logging

All commands are logged to:
- `memory-bank/commandLog.md` - Command history
- `memory-bank/activeContext.md` - Current state
- Git commits - Code changes

---

## 🎨 Agent Roles

### Scanner Agent
- Handles library scanning
- Manages file watching
- Updates database

### Classifier Agent
- Manages classification rules
- Runs classification
- Updates project states

### Bug Fix Agent
- Identifies bugs
- Implements fixes
- Tests solutions

### Feature Agent
- Designs features
- Implements code
- Updates UI

### Performance Agent
- Profiles code
- Optimizes performance
- Benchmarks results

### Documentation Agent
- Updates docs
- Ensures consistency
- Maintains accuracy

### Sync Agent
- Syncs state
- Updates context
- Generates reports

---

## 🚀 Quick Reference

### Most Common Commands
```
/command sync daily              # Daily sync
/command scan library            # Scan library
/command classify project --all  # Reclassify all
/command fix bug <id>            # Fix bug
/command add feature <name>     # Add feature
/command update docs all         # Update all docs
```

### Development Workflow
```
Morning:
  /command sync daily

During work:
  /command add feature <name>
  /command fix bug <id>
  /command optimize performance <target>

End of day:
  /command sync daily
  /command test all
```

---

## 📝 Notes

- Commands are **case-insensitive**
- Use `--help` for command-specific help
- Commands update **relevant documentation automatically**
- All commands are **logged** for traceability
- Commands can be **chained** (future enhancement)

---

## 🔮 Future Enhancements

- [ ] Command aliases (`/scan` → `/command scan library`)
- [ ] Command history
- [ ] Command completion
- [ ] Command scheduling
- [ ] Command chaining
- [ ] Command templates
- [ ] Command validation
- [ ] Command rollback
