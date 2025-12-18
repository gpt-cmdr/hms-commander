# .claude Framework Index

**Purpose**: Navigation index for the hms-commander cognitive infrastructure including subagents, skills, commands, and architectural patterns.

---

## Framework Overview

The `.claude/` directory contains the hierarchical knowledge framework for hms-commander:

```
.claude/
├── INDEX.md                 # This file - Navigation index
├── CLAUDE.md                # Framework aggregation (@imports)
│
├── agents/                  # Specialist domain experts + development agents
├── skills/                  # Task-specific workflows
├── commands/                # Slash commands
└── rules/                   # Architectural patterns
    ├── python/              # Python development patterns
    ├── hec-hms/             # HMS domain knowledge
    ├── testing/             # Testing approaches
    ├── documentation/       # Documentation patterns
    ├── integration/         # Cross-repository workflows
    └── project/             # Repository organization
```

---

## HMS Domain Specialists

**Purpose**: Specialist domain experts that use hms-commander library APIs

**Format**: Single `.md` file with YAML frontmatter + markdown
**Naming**: `kebab-case.md`
**Location**: `.claude/agents/`

### Active HMS Domain Specialists

| Agent | Domain | When to Use |
|-------|--------|-------------|
| **hms-orchestrator.md** | Traffic controller and task classifier | Route tasks to specialists, coordinate multi-domain workflows, handle simple queries |
| **basin-model-specialist.md** | Basin files (.basin) | Subbasins, junctions, reaches, loss methods, transform methods, baseflow, routing |
| **met-model-specialist.md** | Meteorologic models (.met) | Precipitation, gage assignments, Atlas 14 updates, ET, snowmelt |
| **run-manager-specialist.md** | Run configuration and execution | Run setup, validation, execution, Jython script generation |
| **dss-integration-specialist.md** | DSS files and results | Results extraction, peak flows, hydrographs, volumes, time series |
| **hms-ras-workflow-coordinator.md** | HMS-RAS integration | Hydrograph extraction for RAS, spatial matching, cross-tool validation |
| **hierarchical-knowledge-curator.md** | Knowledge architecture | CLAUDE.md maintenance, skills organization, memory system |

### Agent Architecture

**Specialist Agents** (`.claude/agents/`):
- Single `.md` file (lightweight)
- Uses hms-commander library APIs
- Domain expertise focus
- Framework-integrated

**Production Agents** (`hms_agents/`):
- Folder with multiple files (self-contained)
- Complete automation workflows
- Production-ready, shareable

**See**: `.claude/CLAUDE.md` "Agent Naming Conventions" for complete architecture

---

## Development Agents

**Purpose**: Development infrastructure agents for documentation, environments, and knowledge management

**Format**: Main `.md` file with optional `reference/` folder
**Location**: `.claude/agents/`

### Active Development Agents

| Agent | Domain | When to Use |
|-------|--------|-------------|
| **documentation-generator/** | MkDocs, notebooks, API docs | Creating tutorials, updating docs, notebook issues, mkdocs deployment |
| **python-environment-manager.md** | Python environments | Environment setup, import errors, Jupyter kernels, hmscmdr_local/hmscmdr_pip |
| **claude-code-guide/** | Claude Code configuration | Skills creation, memory hierarchy, CLAUDE.md organization, official docs |
| **hierarchical-knowledge-curator/** | Knowledge architecture | Memory consolidation, .claude/outputs curation, governance rules |
| **example-notebook-librarian.md** | Example notebooks | Notebook navigation, QA/QC, authoring assistance, which notebook shows X |
| **notebook-runner.md** | Notebook execution | Run notebooks as tests, pytest/nbmake, output capture, troubleshooting |
| **notebook-output-auditor.md** (Haiku) | Error detection | Exception/traceback detection in notebook outputs |
| **notebook-anomaly-spotter.md** (Haiku) | Anomaly detection | Empty results, missing artifacts, unexpected behavior |
| **conversation-insights-orchestrator.md** | Conversation analysis | Pattern detection, slash command candidates, project activity |
| **conversation-deep-researcher.md** (Opus) | Strategic analysis | Cross-conversation synthesis, trend identification, recommendations |
| **best-practice-extractor.md** | Best practices | Successful patterns, lessons learned, HMS-specific practices |

### Agent Types

| Type | Location | Format | Purpose |
|------|----------|--------|---------|
| **Specialist Agents** | `.claude/agents/` | Single .md | Domain expertise using hms-commander |
| **Development Agents** | `.claude/agents/` | .md + optional reference/ | Development infrastructure |
| **Production Agents** | `hms_agents/` | Full folder | HMS automation workflows |

---

## Skills

**Purpose**: Task-specific workflows and guidance for using hms-commander APIs

**Format**: Folder with `SKILL.md`, optional `examples/`, `reference/`, `scripts/`
**Naming**: `kebab-case/`
**Location**: `.claude/skills/`

### Active Skills

| Skill | Purpose | Trigger Keywords |
|-------|---------|------------------|
| **executing-hms-runs/** | Run HMS simulations and batch processing | run simulation, compute, execute HMS, batch runs, parallel execution |
| **parsing-basin-models/** | Extract and modify basin model data | basin file, subbasin, junction, reach, loss method, transform, routing |
| **updating-met-models/** | Update precipitation and meteorologic data | met model, precipitation, gage assignment, Atlas 14, TP40, frequency storm |
| **extracting-dss-results/** | Extract results from DSS files | DSS results, peak flow, hydrograph, time series, volume |
| **cloning-hms-components/** | Non-destructive component duplication | clone basin, clone met, clone run, QAQC, scenario comparison |
| **linking-hms-to-hecras/** | HMS hydrograph extraction for RAS | HMS to RAS, boundary condition, watershed to river, integrated model |
| **investigating-hms-internals/** | HMS source code analysis and decompilation | HMS internals, decompilation, class files, HEC-HMS source |
| **querying-hms-documentation/** | Query official HMS documentation | HMS documentation, User's Manual, Technical Reference, release notes |
| **managing-hms-versions/** | Multi-version HMS support (3.x vs 4.x) | HMS version, HMS 3.x, HMS 4.x, Python 2 compatibility |

### How to Use Skills

**From Subagents**: Reference skill in YAML frontmatter `skills:` list
**From Code**: Skills document patterns and workflows, not executable code
**Navigation**: Skills point to primary sources (code, examples, rules)

---

## Commands

**Purpose**: Slash commands for common tasks and workflows

**Format**: Single `.md` file with command documentation
**Naming**: `{prefix}-{command}.md` (e.g., `hms-run.md`, `agent-cleanfiles.md`)
**Location**: `.claude/commands/`

### Agent Management Commands

| Command | Purpose | Usage |
|---------|---------|-------|
| **agent-cleanfiles.md** | Clean up root directory | Move completion reports, session notes, backups |
| **agent-crossrepo.md** | Cross-repository coordination | Coordinate HMS + RAS workflows |
| **agent-engagesubagents.md** | Engage specialist subagents | Delegate to domain experts |
| **agent-taskclose.md** | Close tasks in memory system | Update .agent/ when tasks complete |
| **agent-taskupdate.md** | Update task progress | Log progress in .agent/ memory |

### HMS Operation Commands

| Command | Purpose | Usage |
|---------|---------|-------|
| **hms-run.md** | Execute HMS simulation | Run single or multiple simulations |
| **hms-calibrate.md** | Calibration workflow | Parameter adjustment, goodness-of-fit |
| **hms-plot-dss.md** | Plot DSS time series | Visualize hydrographs, compare results |
| **hms-orient.md** | Orient to project structure | Understand HMS project organization |

### Framework Management Commands

| Command | Purpose | Usage |
|---------|---------|-------|
| **hms-docs.md** | Documentation operations | Build docs, serve locally, deploy |
| **hms-new-agent.md** | Create new subagent | Scaffold specialist subagent |
| **hms-new-skill.md** | Create new skill | Scaffold task-specific skill |

### How to Add New Commands

1. Create `.md` file in `.claude/commands/`
2. Use prefix: `hms-` for HMS operations, `agent-` for agent management
3. Document command purpose, usage, examples
4. Update this INDEX.md with new command

---

## Rules

**Purpose**: Architectural patterns, domain knowledge, and development guidelines

**Format**: Markdown files organized by category
**Location**: `.claude/rules/{category}/`

### Python Development Patterns (`.claude/rules/python/`)

| Rule | Purpose |
|------|---------|
| **static-classes.md** | Core HMS pattern - static methods, no instantiation |
| **file-parsing.md** | HmsFileParser utilities for HMS file operations |
| **constants.md** | Centralized magic numbers and configuration |
| **decorators.md** | @log_call and other decorators |
| **path-handling.md** | pathlib.Path patterns |
| **error-handling.md** | LoggingConfig and error patterns |
| **naming-conventions.md** | Code style and naming |

### HEC-HMS Domain Knowledge (`.claude/rules/hec-hms/`)

| Rule | Purpose |
|------|---------|
| **execution.md** | HmsCmdr, HmsJython, version detection |
| **basin-files.md** | HmsBasin operations and file format |
| **met-files.md** | HmsMet operations and precipitation methods |
| **control-files.md** | HmsControl operations and time specifications |
| **dss-operations.md** | HmsDss and HmsResults patterns |
| **clone-workflows.md** | CLB Engineering non-destructive workflows |
| **version-support.md** | HMS 3.x vs 4.x differences |
| **file-formats.md** | HMS file structure documentation |

### Testing (`.claude/rules/testing/`)

| Rule | Purpose |
|------|---------|
| **example-projects.md** | HmsExamples usage for testing |
| **tdd-approach.md** | No mocks, use real HMS projects |

### Documentation (`.claude/rules/documentation/`)

| Rule | Purpose |
|------|---------|
| **mkdocs-config.md** | ReadTheDocs and MkDocs patterns |
| **notebook-standards.md** | Jupyter notebook integration |

### Integration (`.claude/rules/integration/`)

| Rule | Purpose |
|------|---------|
| **hms-ras-linking.md** | HMS→RAS cross-repository workflows |

### Project Organization (`.claude/rules/project/`)

| Rule | Purpose |
|------|---------|
| **development-environment.md** | Package management, conda environments |
| **repository-organization.md** | Keep root clean, file organization |

---

## Primary Sources Philosophy

**Critical Principle**: The `.claude/` framework documents PATTERNS, WORKFLOWS, and NAVIGATION. It does NOT duplicate primary sources.

### Primary Sources (Authoritative)

**Code**: `hms_commander/*.py` - Complete API with docstrings
**Examples**: `examples/*.ipynb` - Working demonstrations
**Tests**: `tests/` - Test suite with real HMS projects
**Docs**: `docs/api/*.md` - Generated API reference
**File Formats**: `tests/projects/.../File Parsing Guide/` - HMS file structures

### What .claude/ Documents

**Patterns**: Architectural decisions (static classes, file parsing)
**Workflows**: How to accomplish tasks (clone workflows, execution patterns)
**Decisions**: Why we chose approach X (HMS version support, DSS integration)
**Navigation**: Where to find information (primary sources, skills, rules)

### What .claude/ Does NOT Duplicate

**API Signatures**: Read from code docstrings
**Method Parameters**: Read from code
**Examples**: Read from Jupyter notebooks
**File Formats**: Read from parsing guides

**Rationale**: Single source of truth prevents documentation drift

---

## How to Add New Components

### Add New Specialist Agent

**Use command**: `/hms-new-agent` or read `.claude/commands/hms-new-agent.md`

1. Create `.claude/agents/{agent-name}.md`
2. Use YAML frontmatter + markdown structure
3. Document domain expertise and integration points
4. Update this INDEX.md with new agent

### Add New Skill

**Use command**: `/hms-new-skill` or read `.claude/commands/hms-new-skill.md`

1. Create `.claude/skills/{skill-name}/` folder
2. Create `SKILL.md` with workflow guidance
3. Add `examples/`, `reference/`, `scripts/` folders as needed
4. Update this INDEX.md with new skill

### Add New Command

1. Create `.claude/commands/{prefix}-{command}.md`
2. Document command purpose, usage, examples
3. Update this INDEX.md in appropriate category

### Add New Rule

1. Create `.claude/rules/{category}/{rule-name}.md`
2. Document pattern, workflow, or decision
3. Update `.claude/CLAUDE.md` with @import if core pattern
4. Update this INDEX.md in appropriate category

---

## Framework Maintenance

### Regular Updates

**When adding features**:
- Create or update relevant skill
- Add examples to skill folder
- Update this INDEX.md

**When changing patterns**:
- Update rule in `.claude/rules/`
- Update affected subagents
- Update `.claude/CLAUDE.md` if core pattern

**When adding integrations**:
- Update integration rule
- Update affected skills and subagents
- Document in appropriate sections

### Cleanup Protocol

**Root cleanup**: Use `agent-cleanfiles` command
**Framework cleanup**: Review and consolidate when framework grows large
**Deprecation**: Move deprecated components to `.old/` folder

---

## Quick Reference

### Most Used Specialist Agents
- **hms-orchestrator** - Start here for task routing
- **basin-model-specialist** - Basin operations
- **met-model-specialist** - Precipitation updates

### Most Used Skills
- **executing-hms-runs** - Run simulations
- **parsing-basin-models** - Basin operations
- **extracting-dss-results** - Results analysis

### Most Used Commands
- `/hms-run` - Execute HMS simulation
- `/hms-orient` - Understand project structure
- `/hms-docs` - Documentation operations

### Most Used Rules
- **static-classes.md** - Core HMS pattern
- **clone-workflows.md** - Non-destructive workflows
- **execution.md** - HMS execution patterns

---

## Cross-References

### Memory System
**Location**: `.agent/`
**Purpose**: Multi-session task coordination
**See**: `.agent/README.md` for memory system overview

### Production Agents
**Location**: `hms_agents/`
**Purpose**: Complete automation workflows
**See**: `hms_agents/README.md` for production agents overview

### Development Notes
**Location**: `feature_dev_notes/`
**Purpose**: Session notes, planning, research (gitignored)
**See**: `feature_dev_notes/INDEX.md` for development notes organization

**IMPORTANT**: Production agents MUST NOT reference `feature_dev_notes/` (gitignored)

---

## Framework Version

**Version**: 1.1 (2025-12-17)
**Status**: Active framework with consolidated agents folder
**Recent Changes**:
- Consolidated subagents into `.claude/agents/` folder
- HMS domain specialists now alongside development agents
- Orchestrator agent (hms-orchestrator.md)
- Slash commands for common tasks

**See**: `feature_dev_notes/DEVELOPMENT_ROADMAP.md` for cognitive infrastructure roadmap

---

**Last Updated**: 2025-12-17
