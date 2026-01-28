# Daily Sync Command Documentation

**Command:** `/command sync daily`
**Purpose:** Synchronize current codebase state with documentation
**Last Updated:** 2026-01-28

---

## Overview

The daily sync command ensures that all documentation reflects the **current state** of the codebase. It reads git status, analyzes recent changes, and updates relevant documentation files.

---

## What It Does

### 1. Reads Current State

- Git status (modified/new/deleted files)
- Recent commits
- Current branch
- Uncommitted changes

### 2. Analyzes Changes

- Identifies modified modules
- Detects new features
- Finds bug fixes
- Notes refactoring

### 3. Updates Documentation

- `activeContext.md` - Current focus, recent changes, next steps
- `progress.md` - Completed tasks, milestones
- `systemHealth.md` - Performance issues, optimizations
- `codebaseReport.md` - Module status (if major changes)

### 4. Generates Report

- Summary of changes
- Current blockers
- Next steps
- Documentation updates

---

## Usage

### Basic Usage

```
/command sync daily
```

### Verbose Mode

```
/command sync daily --verbose
```

### Force Update

```
/command sync daily --force
```

### Specific Sections

```
/command sync daily --section activeContext
/command sync daily --section progress
/command sync daily --section systemHealth
```

---

## Output Format

### Standard Output

```
✅ Daily Sync Complete

📊 Changes Detected:
  - Modified: 12 files
  - New: 3 files
  - Deleted: 1 file

📝 Documentation Updated:
  - activeContext.md ✓
  - progress.md ✓
  - systemHealth.md ✓

🎯 Current Focus:
  [Current focus from activeContext.md]

🚧 Blockers:
  [Any blockers identified]

📋 Next Steps:
  [Next steps from activeContext.md]
```

### Verbose Output

Includes:

- Detailed file changes
- Git diff summary
- Module analysis
- Performance notes
- Test status

---

## What Gets Updated

### activeContext.md

**Sections Updated:**

- `Current Focus` - What we're working on now
- `Recent Changes` - What changed since last sync
- `Next Steps` - What's planned next
- `Blockers` - What's blocking progress
- `Key Decisions` - Important decisions made

**Example:**

```markdown
## Current Focus
**FruityWolf Scalability Upgrade** — Pagination implementation

## Recent Changes
- Added pagination to ProjectsView
- Implemented infinite scroll
- Updated ProjectsModel for pagination

## Next Steps
1. Test pagination with 10k+ projects
2. Add loading indicators
3. Optimize database queries

## Blockers
- None currently

## Key Decisions
- Using infinite scroll instead of page buttons
- Page size set to 100 items
```

---

### progress.md

**Sections Updated:**

- `Completed` - Checkboxes marked complete
- `In Progress` - Current work items
- `Remaining` - Pending items
- `Known Issues` - Current bugs/issues

**Example:**

```markdown
### Scalability Upgrade (Current Sprint)
- [x] Phase 1: Bug Fixes
  - [x] Fix empty path playback bug
- [x] Phase 2: PyFLP Integration
  - [x] Add pyflp dependency
  - [x] Create flp_parser module
- [ ] Phase 3: Scalability
  - [x] Pagination for ProjectsView
  - [ ] Async cover loading
```

---

### systemHealth.md

**Updated When:**

- Performance issues detected
- Optimizations implemented
- New bottlenecks found

**Example:**

```markdown
## Recent Optimizations

### ProjectsView Pagination (2026-01-28)
**Issue:** Lag when loading 2000+ projects
**Fix:** Implemented pagination with infinite scroll
**Result:** 10x faster initial load, smooth scrolling
**Status:** ✅ Resolved
```

---

## Detection Logic

### Feature Detection

The sync command detects new features by:

1. New files in feature directories (`ui/`, `scanner/`, etc.)
2. New functions/classes with feature keywords
3. Database migrations
4. UI changes

### Bug Fix Detection

Detects bug fixes by:

1. Changes to error handling
2. Fix comments in code
3. Test additions
4. Issue references

### Refactoring Detection

Detects refactoring by:

1. File moves/renames
2. Large code reorganization
3. Pattern changes
4. Architecture updates

---

## Manual Override

If automatic detection fails, you can manually specify:

```
/command sync daily --focus "Working on pagination"
/command sync daily --changes "Added pagination, fixed bug"
/command sync daily --blockers "Waiting for review"
/command sync daily --next "Test pagination, write docs"
```

---

## Best Practices

### When to Run

1. **Morning** - Start of work session
2. **After major changes** - After implementing features
3. **End of day** - Before finishing work
4. **Before commits** - Ensure docs are up to date

### What to Check

After running sync, verify:

- [ ] `activeContext.md` reflects current work
- [ ] `progress.md` has correct checkboxes
- [ ] `systemHealth.md` notes any issues
- [ ] No outdated information

### Common Issues

**Issue:** Sync doesn't detect changes

- **Solution:** Use `--verbose` to see what it's detecting
- **Solution:** Manually specify with `--changes`

**Issue:** Wrong focus detected

- **Solution:** Manually set with `--focus`

**Issue:** Missing blockers

- **Solution:** Manually add with `--blockers`

---

## Integration with Workflow

### Daily Workflow

```
Morning:
  /command sync daily          # Get current state

During work:
  [Make changes]
  /command sync daily          # Update after major changes

End of day:
  /command sync daily          # Final sync
```

### Feature Development

```
1. /command sync daily          # Start
2. [Implement feature]
3. /command sync daily          # Update progress
4. [Test feature]
5. /command sync daily          # Final update
```

### Bug Fix Workflow

```
1. /command sync daily          # Identify bug
2. [Fix bug]
3. /command sync daily          # Update status
4. [Test fix]
5. /command sync daily          # Mark resolved
```

---

## Examples

### Example 1: Morning Sync

```
$ /command sync daily

✅ Daily Sync Complete

📊 Changes Detected:
  - Modified: 0 files
  - New: 0 files
  - Deleted: 0 files

📝 Documentation Updated:
  - activeContext.md ✓

🎯 Current Focus:
  FruityWolf Scalability Upgrade — Pagination implementation

🚧 Blockers:
  None currently

📋 Next Steps:
  1. Test pagination with 10k+ projects
  2. Add loading indicators
  3. Optimize database queries
```

### Example 2: After Feature Implementation

```
$ /command sync daily

✅ Daily Sync Complete

📊 Changes Detected:
  - Modified: 5 files
    - FruityWolf/ui/projects_view.py
    - FruityWolf/ui/view_models/projects_model.py
    - FruityWolf/scanner/library_scanner.py
  - New: 1 file
    - tests/test_pagination.py

📝 Documentation Updated:
  - activeContext.md ✓
  - progress.md ✓
  - systemHealth.md ✓

🎯 Current Focus:
  FruityWolf Scalability Upgrade — Pagination testing

🚧 Blockers:
  None currently

📋 Next Steps:
  1. Run performance tests
  2. Fix any issues found
  3. Update user documentation
```

### Example 3: With Blockers

```
$ /command sync daily

✅ Daily Sync Complete

📊 Changes Detected:
  - Modified: 2 files
  - New: 0 files
  - Deleted: 0 files

📝 Documentation Updated:
  - activeContext.md ✓

🎯 Current Focus:
  FruityWolf Scalability Upgrade — Async cover loading

🚧 Blockers:
  - Need to decide on caching strategy
  - Waiting for review of PR #123

📋 Next Steps:
  1. Research caching options
  2. Implement async loading
  3. Test with large library
```

---

## Troubleshooting

### Sync Fails

**Error:** "Could not read git status"

- **Solution:** Ensure you're in a git repository
- **Solution:** Check git is installed

**Error:** "Could not update documentation"

- **Solution:** Check file permissions
- **Solution:** Ensure files exist

### Incorrect Detection

**Issue:** Wrong changes detected

- **Solution:** Use `--verbose` to see detection logic
- **Solution:** Manually specify changes

**Issue:** Missing changes

- **Solution:** Check git status manually
- **Solution:** Use `--force` to force update

---

## Future Enhancements

- [ ] Automatic git commit message generation
- [ ] Integration with issue tracker
- [ ] Slack/email notifications
- [ ] Visual diff of documentation changes
- [ ] Historical sync reports
- [ ] Sync scheduling
- [ ] Multi-repo sync support

---

## Related Commands

- `/command update docs all` - Update all documentation
- `/command update docs activeContext` - Update active context only
- `/command update docs progress` - Update progress only
