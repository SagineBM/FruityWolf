# FruityWolf Workflow System

**Last Updated:** 2026-01-29

## Overview

FruityWolf uses a command-based workflow for AI agent collaboration. Commands are defined in `.cursor/commands/` and rules in `.cursorrules`.

## Quick Start

1. **Read Rules**: `.cursorrules` (project-specific)
2. **Read Context**: `memory-bank/activeContext.md`
3. **Use Commands**: See below

## Available Cursor Commands

| Command | Purpose |
|---------|---------|
| `/sync-daily` | Sync codebase state with documentation |
| `/fix-bug <id>` | Fix a specific bug |
| `/add-feature <name>` | Add a new feature |
| `/optimize-performance <target>` | Optimize performance |
| `/update-docs [target]` | Update documentation |
| `/scan-library [action]` | Work on scanner |

## Workflow Patterns

### Daily Development
```
Morning:  /sync-daily
Work:     Make changes
Evening:  /sync-daily
```

### Feature Development
```
1. /sync-daily
2. /add-feature <name>
3. Test
4. /update-docs
5. /sync-daily
```

### Bug Fix
```
1. /sync-daily
2. /fix-bug <id>
3. Test
4. /update-docs progress
5. /sync-daily
```

### Performance Work
```
1. /optimize-performance <target>
2. Benchmark
3. /update-docs health
4. /sync-daily
```

## Documentation Files

### Required Reading (Before Any Task)
- `.cursorrules` — Project rules
- `activeContext.md` — Current focus

### Update Frequency
- **Daily**: activeContext.md, progress.md
- **On Change**: systemPatterns.md, systemHealth.md
- **Weekly**: Full review

## Agent Roles

See `AGENTS.md` in project root for detailed agent instructions.

| Role | Focus |
|------|-------|
| Feature Agent | New features |
| Bug Fix Agent | Bug fixes |
| Performance Agent | Optimizations |
| Documentation Agent | Documentation |
| Scanner Agent | Library scanning |
| Database Agent | Database layer |
| UI Agent | User interface |

## Key Invariants

1. **UI thread never blocks**
2. **Large lists virtualized**
3. **Database safety (WAL mode)**
4. **Path validation required**
5. **Documentation always updated**

## Command Files Location

All command definitions are in:
```
.cursor/commands/
├── sync-daily.md
├── fix-bug.md
├── add-feature.md
├── optimize-performance.md
├── update-docs.md
└── scan-library.md
```
