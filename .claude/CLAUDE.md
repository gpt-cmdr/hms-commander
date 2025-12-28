# HMS-Commander Project Memory

**Hierarchical Loading**: This file uses @imports for modular knowledge organization.

---

## Python Development Patterns

@.claude/rules/python/static-classes.md
@.claude/rules/python/file-parsing.md
@.claude/rules/python/constants.md

Additional patterns in `.claude/rules/python/`:
- decorators.md - @log_call usage
- path-handling.md - pathlib.Path patterns
- error-handling.md - LoggingConfig, log levels
- naming-conventions.md - Code style

---

## HEC-HMS Domain Knowledge

@.claude/rules/hec-hms/execution.md
@.claude/rules/hec-hms/basin-files.md
@.claude/rules/hec-hms/clone-workflows.md

Additional HMS knowledge in `.claude/rules/hec-hms/`:
- met-files.md - Meteorologic models
- control-files.md - Control specifications
- dss-operations.md - DSS file operations (including paired data)
- version-support.md - HMS 3.x vs 4.x differences
- file-formats.md - .hms, .basin, .met, .control structures
- aorc-integration.md - AORC precipitation and HUC watersheds
- atlas14-storms.md - Atlas 14 hyetograph generation (✓ PRODUCTION-READY)
- frequency-storms.md - TP-40/Hydro-35 HCFCD M3 compatibility (in validation)

---

## Testing & Documentation

@.claude/rules/testing/example-projects.md

Additional in `.claude/rules/testing/` and `.claude/rules/documentation/`:
- testing/tdd-approach.md - No mocks, use real projects
- documentation/mkdocs-config.md - ReadTheDocs patterns
- documentation/notebook-standards.md - Jupyter integration

---

## Project Setup & Organization

@.claude/rules/project/development-environment.md
@.claude/rules/project/repository-organization.md

**Development Environment**:
- Use `uv` and `python` for agent scripts and tools
- Jupyter testing: `hmscmdr_local` (local dev) or `hmscmdr_pip` (published package)
- Create/activate environments before testing code changes

**Keep root clean**:
- Only 5 essential .md files: CLAUDE.md, README.md, GETTING_STARTED.md, QUICK_REFERENCE.md, STYLE_GUIDE.md
- Move completion reports → `feature_dev_notes/`
- Move old/backup files → `.old/`
- Run cleanup after each major feature or session

---

## Agent Naming Conventions

**Two-Tier Architecture**: Specialist subagents vs production agents

### Specialist Agents (`.claude/agents/*.md`)
**Purpose**: Domain experts that use hms-commander library APIs
**Format**: Single `.md` file (YAML frontmatter + markdown)
**Naming**: `kebab-case.md` (e.g., `basin-model-specialist.md`, `met-model-specialist.md`)
**Rationale**: Follows YAML/skills convention, lightweight definitions

### Production Agents (`hms_agents/*/`)
**Purpose**: Complete automation workflows with tools and reference data
**Format**: Folder with multiple files (AGENT.md, scripts, knowledge/, tools/, etc.)
**Naming**: `python_case/` (e.g., `update_3_to_4/`, `hms_doc_query/`, `hms_atlas14/`)
**Rationale**: Python importable, PEP 8 compliant, matches library style

### Key Differences

| Aspect | Specialist Agents | Production Agents |
|--------|---------------------|-------------------|
| Location | `.claude/agents/` | `hms_agents/` |
| Structure | Single `.md` file | Folder with multiple files |
| Naming | `kebab-case.md` | `python_case/` |
| Purpose | Domain expertise | Automation workflows |
| Dependencies | hms-commander library | Self-contained with tools |
| Shareable | Framework-specific | Production-ready |

**Examples**:
- ✅ Specialist: `basin-model-specialist.md` (domain expert using HmsBasin API)
- ✅ Production: `hms_atlas14/` (automated Atlas 14 updates with downloader, converter, knowledge files)

See: `feature_dev_notes/SPECIALIST_VS_PRODUCTION_AGENTS.md` for complete architectural guide

---

## Cross-Repository Integration

@.claude/rules/integration/hms-ras-linking.md
@.claude/rules/integration/m3-model-integration.md

**HMS→RAS Workflows** (watershed to river modeling):
- HMS generates runoff hydrographs in DSS format
- RAS imports as upstream boundary conditions
- Shared RasDss infrastructure (no format conversion)
- Spatial matching required (HMS outlets → RAS cross sections)

**HCFCD M3 Model Workflows** (testing and upgrades):
- `feature_dev_notes/HCFCD_M3_HMS411_UPGRADE_WORKFLOW.md` - Manual upgrade guide
- `examples/m3_upgrade_helpers/` - Validation helper scripts
- `feature_dev_notes/HCFCD_M3_Clear_Creek_*` - Clear Creek pilot (reference)

**Skills & Agents**:
- `.claude/skills/linking-hms-to-hecras/` - HMS side workflow
- `.claude/agents/hms-ras-workflow-coordinator.md` - Coordinates both tools
- `ras-commander/.claude/skills/importing-hms-boundaries/` - RAS side (cross-reference)

---

## Quick Links

### Memory System
@.agent/README.md - Multi-session task coordination

### Task Agents
@hms_agents/README.md - Production workflows (update_3_to_4, hms_doc_query, hms_atlas14, hms_decompiler)

### Development Roadmap
@feature_dev_notes/DEVELOPMENT_ROADMAP.md - Strategic planning

### Primary Sources

**Code**: `hms_commander/*.py` - Authoritative API with docstrings
**Examples**: `examples/*.ipynb` - Working demonstrations
**File Formats**: `tests/projects/2014.08_HMS/File Parsing Guide/` - HMS file structure
**API Docs**: `docs/api/*.md` - Generated reference

---

## Navigation

Claude should READ primary sources (code, notebooks, docs), not duplicate them.

The `.claude/rules/` files document:
- **Patterns** (architectural decisions)
- **Workflows** (how to accomplish tasks)
- **Decisions** (why we chose approach X)
- **Navigation** (where to find information)

They do NOT duplicate:
- API signatures (read docstrings)
- Method parameters (read code)
- Examples (read notebooks)
- File formats (read parsing guides)
