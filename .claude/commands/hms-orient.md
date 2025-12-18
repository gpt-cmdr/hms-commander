# HMS Commander Orientation

You are providing orientation for a new user or agent starting work in hms-commander.

## Do This First Checklist

**Before ANY work**, read these files in order:

1. **README.md** (root) - Project overview, installation, quick start
2. **CLAUDE.md** (root) - Primary AI guidance and key patterns
3. **QUICK_REFERENCE.md** (root) - API quick reference

## Repo Layout Overview

```
hms-commander/
├── hms_commander/        # Core library (static classes)
│   ├── HmsBasin.py       # Basin file operations
│   ├── HmsMet.py         # Met model operations
│   ├── HmsControl.py     # Control spec operations
│   ├── HmsCmdr.py        # Execution engine
│   ├── HmsDss.py         # DSS operations
│   └── HmsPrj.py         # Project initialization
├── examples/             # Jupyter notebooks (living tests)
├── tests/                # Test suite
│   └── projects/         # Example HMS projects
├── docs/                 # MkDocs documentation
├── .claude/              # Claude knowledge framework
│   ├── skills/           # Task-specific workflows
│   ├── subagents/        # Domain specialists
│   └── commands/         # Slash commands (you're here!)
├── hms_agents/           # Production workflow agents
└── agent_tasks/          # Multi-session memory
```

## Environment Setup

```bash
# Install for development
pip install -e ".[all]"

# Or use uv for fast installation
uv pip install -e ".[all]"

# Two Conda environments for testing:
# hmscmdr_local - Local development (editable install)
# hmscmdr_pip   - Published package testing
```

## Core Architecture Patterns

### Static Classes (No Instantiation)

```python
# Correct
from hms_commander import HmsBasin
subbasins = HmsBasin.get_subbasins("project.basin")

# Wrong
basin = HmsBasin()  # Don't instantiate
```

### Project Initialization

```python
from hms_commander import init_hms_project, hms

# Initialize a project
init_hms_project(r"C:\Projects\watershed")

# Access project data via hms object
print(hms.basin_df)   # All subbasins
print(hms.met_df)     # All met models
print(hms.run_df)     # All runs
```

## Safety Boundaries

**DO:**
- Use clone workflows for non-destructive changes
- Test with example projects from HmsExamples
- Use `hms_object=hms` parameter for multi-project work

**DON'T:**
- Overwrite golden/reference example data
- Instantiate static classes
- Run batch computations without explicit user request
- Create new files in root directory (keep it clean)

## Common Workflows

| Task | Command/Skill |
|------|---------------|
| Run HMS simulation | `/hms-run` or `executing-hms-runs` skill |
| Calibrate model | `/hms-calibrate` |
| Plot DSS results | `/hms-plot-dss` |
| Cross-repo work | `/agent-crossrepo` |

## Getting Help

- **Skills**: `.claude/skills/` - Task-specific workflows
- **Subagents**: `.claude/agents/` - Domain specialists
- **Examples**: `examples/` - Jupyter notebooks
- **Rules**: `.claude/rules/` - Patterns and decisions

## Specialist Subagents

When you need domain expertise, engage these specialists:

| Subagent | Domain |
|----------|--------|
| `basin-model-specialist` | Basin files, subbasins, loss methods |
| `met-model-specialist` | Meteorologic models, gage data |
| `run-manager-specialist` | Execution, compute settings |
| `dss-integration-specialist` | DSS file operations |
| `hms-ras-workflow-coordinator` | HMS→RAS integration |

## Your Response

After reading this orientation, provide a brief summary of:
1. What task the user wants to accomplish
2. Which skills/subagents might help
3. Any files you need to read first to understand the codebase

Remember: Read primary sources (code, notebooks), don't duplicate them.
