# HMS-Commander Documentation Index

Complete guide to all documentation in the hms-commander repository.

## Quick Start (New Users)

1. **README.md** (root) - Project overview and installation
2. **GETTING_STARTED.md** (root) - First steps and basic usage
3. **QUICK_REFERENCE.md** (root) - API quick reference with examples

## Developer Documentation

### Core Development Guide
- **CLAUDE.md** (root) - Comprehensive development guidelines for Claude Code and human developers
  - Project overview and architecture
  - Complete API reference for all 14 core classes
  - HMS file format specifications
  - Development patterns and naming conventions
  - HMS version support (3.x vs 4.x differences)
  - Common pitfalls to avoid

### Current Plans
- **REORGANIZATION_PLAN.md** (root) - Active reorganization plan
  - Phase 1: Code Consolidation
  - Phase 2: Agent Infrastructure
  - Phase 3: Testing & Documentation
  - Implementation timeline and acceptance criteria

## Agent Workflows

### Agent System
- **agents/README.md** - Agent framework guide (formerly AGENTS.md)
  - GIS data extraction patterns
  - Agent workflow structure
  - Quality verdict system

- **.agent/** - Agent memory and coordination system
  - **STATE.md** - Current project state (READ FIRST)
  - **CONSTITUTION.md** - Project principles and constraints
  - **BACKLOG.md** - Task queue with dependencies
  - **PROGRESS.md** - Session-by-session log
  - **LEARNINGS.md** - Patterns and anti-patterns
  - **README.md** - Memory system guide

### Existing Agent Workflows
- **agents/Update_3_to_4/** - HMS 3.x → 4.x version upgrade workflow
  - Complete workflow with 0.00% result deviation
  - Decompilation-based problem solving
  - Comprehensive change tracking

## Archived Documentation

Located in `.old/` directory (not tracked by git):

### Planning Documents (.old/planning/)
- **PLAN_HmsPrj_Enhancement.md** - HmsPrj enhancement planning (superseded)
- **PLAN_HMS_Version_Fix.md** - HMS version fix planning (superseded)
- **DEVELOPMENT_PLAN.md** - Original development roadmap (superseded by REORGANIZATION_PLAN.md)

### Research Documents (.old/research/)
- **decompile_findings.md** - HMS JAR decompilation results
  - Index Parameter Type discovery
  - Zero-depth bug analysis
- **HMS_LOG_ANALYSIS_INDEX.md** - HMS log message analysis

### Old API Documentation (.old/docs_old/)
- **API_Reference.md** - Generated API reference (67 KB)
- **API_Gap_Analysis.md** - API gap analysis (44 KB)
- **Feature_Implementation_Specs.md** - Feature specs (60 KB)

*Note: These were comprehensive but became outdated. CLAUDE.md now serves as the canonical API reference.*

## Documentation Structure

```
hms-commander/
├── README.md                    # Project overview
├── GETTING_STARTED.md           # Quick start guide
├── QUICK_REFERENCE.md           # API quick reference
├── CLAUDE.md                    # Complete dev guide
├── REORGANIZATION_PLAN.md       # Current active plan
├── docs/
│   └── DOCUMENTATION_INDEX.md   # This file
├── agents/
│   ├── README.md                # Agent framework
│   ├── Update_3_to_4/           # Version upgrade workflow
│   └── (future agents)
├── .agent/                      # Memory system (multi-session work)
│   ├── STATE.md
│   ├── CONSTITUTION.md
│   ├── BACKLOG.md
│   ├── PROGRESS.md
│   ├── LEARNINGS.md
│   └── README.md
└── .old/                        # Archived/deprecated docs
    ├── planning/
    ├── research/
    └── docs_old/
```

## Documentation Maintenance

### When to Update

| Document | Update Frequency | Trigger |
|----------|-----------------|---------|
| README.md | Rarely | Major feature additions, installation changes |
| GETTING_STARTED.md | Occasionally | API changes affecting basic usage |
| QUICK_REFERENCE.md | Frequently | New methods added, signature changes |
| CLAUDE.md | Frequently | New patterns, architecture changes |
| .agent/STATE.md | Every session | Session end (current state) |
| .agent/PROGRESS.md | Every session | Session end (append log) |
| .agent/BACKLOG.md | Every session | Task completion, new tasks discovered |
| .agent/LEARNINGS.md | After tasks | New patterns discovered |

### Documentation Principles

1. **Single Source of Truth**: CLAUDE.md is canonical for development patterns
2. **User-Facing vs Internal**: Root docs are user-facing, .agent/ is for multi-session development
3. **Archive Don't Delete**: Move superseded docs to .old/ rather than deleting
4. **Git-Friendly**: Use markdown, avoid binary formats
5. **Examples Required**: Every major feature needs usage examples

## Finding What You Need

### I want to...

**...get started with hms-commander**
→ README.md → GETTING_STARTED.md

**...find a specific API method**
→ QUICK_REFERENCE.md (quick lookup) or CLAUDE.md (complete details)

**...understand the architecture**
→ CLAUDE.md "Architecture Overview" section

**...create an agent workflow**
→ agents/README.md → .agent/README.md

**...continue multi-session work**
→ .agent/STATE.md (read first every session)

**...understand HMS file formats**
→ CLAUDE.md "HEC-HMS File Formats" section

**...see version differences (HMS 3.x vs 4.x)**
→ CLAUDE.md "HMS Version Support" section

**...find decompilation results**
→ .old/research/decompile_findings.md

**...understand project principles**
→ .agent/CONSTITUTION.md

## Contributing to Documentation

When adding new features:

1. **Update QUICK_REFERENCE.md** with method signature and example
2. **Update CLAUDE.md** with detailed explanation and patterns
3. **Add docstring** to the code itself (Google style)
4. **Update .agent/LEARNINGS.md** if new pattern discovered
5. **Consider**: Does README.md or GETTING_STARTED.md need updating?

When changing architecture:

1. **Update .agent/CONSTITUTION.md** if principles change
2. **Update CLAUDE.md** with new patterns
3. **Update REORGANIZATION_PLAN.md** if affects planned work
4. **Document in .agent/PROGRESS.md** with rationale

## Version

**Index Version**: 1.0
**Created**: 2025-12-10
**Last Updated**: 2025-12-10
