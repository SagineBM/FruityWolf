# Active Context

## Current Focus
**FruityWolf Documentation & Workflow System** — Complete documentation ecosystem and agent workflow system established.

## Active Work
- **Documentation System**: ✅ Complete! Comprehensive documentation created.
- **Workflow System**: ✅ Complete! Command-based agent workflow established.
- **Codebase Analysis**: ✅ Complete! Full codebase report generated.

## Recent Changes (2026-01-28)
- **Documentation System Created**: 
  - Complete codebase report (`codebaseReport.md`)
  - Feature checklist with market-ready assessment (`featureChecklist.md`)
  - Workflow system with `/command` structure (`workflowSystem.md`)
  - Daily sync command documentation (`dailySyncCommand.md`)
  - Optimization opportunities roadmap (`optimizationOpportunities.md`)
  - Complete ecosystem documentation (`ecosystemDocumentation.md`)
  - Quick reference guide (`QUICK_REFERENCE.md`)
- **FLP Parser MAJOR Enhancement** (2026-01-28):
  - **Fixed Mixer Effect Detection**: Mixer slots now properly iterate using `iter(track)` instead of non-existent `.slots` attribute (pyflp 2.x API)
  - **VST Plugin Detection**: Direct access to VSTPlugin attributes (`name`, `plugin_path`, `vendor`, `fourcc`, `guid`) per pyflp documentation
  - **Native FL Plugin Database**: Comprehensive list of ~100+ native FL Studio plugins (generators + effects)
  - **Smart Sample Filtering**: Detects audio clip names vs real plugins using patterns (dates, #numbers, common sample names)
  - **Third-Party Vendor Detection**: Recognizes 40+ vendors (FabFilter, Waves, Valhalla, SoundToys, etc.) to avoid false native classification
  - **Format Detection**: Properly identifies VST2 (.dll), VST3 (.vst3), CLAP, AAX formats
  - **Test Result**: Successfully detects 17 instances of FabFilter Pro-Q 3 in single project (was 0 before!)
- **Code Changes**: 
  - Multiple UI modules updated (projects_view, panels, delegates)
  - Scanner improvements (library_scanner.py)
  - Database migrations updated
  - New modules: flp_parser, services, core/stats_service
- **Architecture**: ProjectsView uses Model/View pattern (performance optimized)

## Key Decisions
- **Documentation Structure**: Centralized in `memory-bank/` with standardized format
- **Workflow System**: Command-based (`/command <action>`) for agent tasks
- **Daily Sync**: Automated documentation sync command established
- **Performance**: Model/View pattern implemented for ProjectsView (lag issue resolved)

## Open Issues
- **Bug**: "Empty path" warning in playback needs proper handling (low priority)
- **TODO**: Async cover loading (high priority optimization)
- **TODO**: Light theme implementation
- **TODO**: Increase test coverage (currently ~20%)

## Next Steps
1. Implement high-priority optimizations (async cover loading, database queries)
2. Increase test coverage to >80%
3. Complete market-ready features (first-run wizard, error reporting)
4. Set up CI/CD pipeline
5. Create installer and distribution pipeline

## Files to Watch
- `memory-bank/` — All documentation files (keep in sync)
- `FruityWolf/ui/projects_view.py` — Model/View implementation (working well)
- `FruityWolf/scanner/library_scanner.py` — Scanner optimizations
- `FruityWolf/database/migrations.py` — Schema version 17 (renders table)
