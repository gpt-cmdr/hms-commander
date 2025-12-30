# HMS Agents

Task-specific agents for automating HEC-HMS workflows. Each agent is a specialized workflow that performs a specific modeling operation with quality validation.

**For non-Claude agents**: See `../AGENTS.md` or root `AGENTS.md` for import instructions.

---

## Available Agents

### update_3_to_4 - HMS Version Upgrade Agent

Upgrades HEC-HMS projects from version 3.x to 4.x with comprehensive validation.

**Features:**
- Automatic parameter conversion (Muskingum Cunge 8-point → standard)
- DSS file comparison (peak flow, volume, timing)
- Quality verdict system (GREEN/YELLOW/RED)
- Comprehensive change logging
- Session persistence (save/resume)

**Location:** `.claude/agents/update_3_to_4/`

**Documentation:** See `update_3_to_4/AGENT.md`

**Example Results:** `update_3_to_4/example_results_tifton.md`

### hms_doc_query - Documentation Query Agent

Query official HEC-HMS documentation to answer technical questions.

**Features:**
- Web-based documentation retrieval (User's Manual, Technical Reference)
- **Image and screenshot processing** - Can view UI diagrams and parameter screenshots
- Method validation and parameter lookup
- Release note searching
- Version-specific information
- Known HMS method enumeration

**Location:** `.claude/agents/hms_doc_query/`

**Documentation:** See `hms_doc_query/AGENT.md`

**Use Cases:**
- "What parameters does SCS Curve Number require?"
- "How are subbasins defined in .basin files?"
- "What new features were added in HMS 4.11?"
- "How do I configure gridded precipitation?"

**Note:** This agent can process screenshots and images from HMS documentation, which is critical since many HMS docs use UI screenshots to explain parameter configurations.

### hms_decompiler - HMS Internals Investigation Agent

Investigates HEC-HMS internals through decompiled Java classes to support development and debugging.

**Features:**
- Complete JythonHms API reference (HMS 3.x and 4.x)
- Version-specific differences (Python 2 vs 3, API changes)
- CLI options and command-line arguments discovery
- On-demand class decompilation tooling
- Undocumented feature discovery via source analysis
- Reference to complete decompilation library (4,686 class files)

**Location:** `.claude/agents/hms_decompiler/`

**Documentation:** See `hms_decompiler/AGENT.md`

**Quick Start:** `hms_decompiler/QUICK_START.md`

**Use Cases:**
- "What parameters does JythonHms.SetLossRateValue accept?"
- "Does HMS 3.3 support Jython scripting?" (✅ YES - discovered via decompilation!)
- "How do I run HMS in headless mode?" (Use `-lite` flag)
- "What's different between HMS 3.x and 4.x APIs?"
- "How can I decompile hms.model.OptimizationManager?"

**Note:** This agent provides HMS internal knowledge from decompiled source. Use hms_doc_query for official documentation queries.

---

## Future Agents (Planned)

### Atlas14 - Precipitation Update Agent
Convert Region 3 precipitation to NOAA Atlas 14 frequency-based estimates.

**Status:** Phase 2 (REORGANIZATION_PLAN.md)

### AORC - Gridded Precipitation Agent
Configure AORC (Analysis of Record for Calibration) gridded precipitation data.

**Status:** Phase 3 (REORGANIZATION_PLAN.md)

---

## Agent Framework

### Two Agent Types

**Production Agents** (folders):
- Full-featured workflows with tools, knowledge, examples
- Located in `.claude/agents/{agent_name}/`
- Each has `AGENT.md` defining capabilities
- Naming: `python_case/` (e.g., `hms_atlas14/`)

**Specialist Agents** (single files):
- Domain experts that use hms-commander APIs
- Located in `.claude/agents/{name}.md`
- Naming: `kebab-case.md` (e.g., `basin-model-specialist.md`)

### Creating a New Agent

**Production Agent**:
1. Create directory: `.claude/agents/your_agent/`
2. Create `AGENT.md` with capabilities and instructions
3. Add knowledge files, tools, examples as needed
4. Update this README

**Specialist Agent**:
1. Create file: `.claude/agents/your-specialist.md`
2. Define domain expertise and hms-commander API usage
3. Update this README

---

## Directory Structure

```
.claude/agents/
├── README.md (this file)
├── AGENTS.md (import instructions for non-Claude agents)
│
├── # Production Agents (folders with tools/knowledge)
├── update_3_to_4/
│   ├── AGENT.md
│   ├── upgrade_workflow.py
│   ├── compare_dss_outputs.py
│   ├── RESULTS_TEMPLATE.md
│   └── example_results_tifton.md
├── hms_doc_query/
│   ├── AGENT.md
│   ├── QUICK_START.md
│   └── doc_query.py
├── hms_atlas14/
│   ├── AGENT.md
│   ├── atlas14_converter.py
│   └── atlas14_downloader.py
├── hms_decompiler/
│   ├── AGENT.md
│   ├── QUICK_START.md
│   ├── knowledge/
│   │   ├── JYTHON_HMS_API.md
│   │   ├── HMS_3x_SUPPORT.md
│   │   └── HMS_CLI_OPTIONS.md
│   ├── reference/
│   │   ├── HMS_3.3/ (decompiled sources)
│   │   └── HMS_4.13/ (decompiled sources)
│   ├── tools/
│   │   └── cfr.jar
│   └── examples/
│       ├── query_jython_api.md
│       ├── version_compatibility.md
│       └── decompile_new_class.md
│
├── # Specialist Agents (single .md files)
├── basin-model-specialist.md
├── met-model-specialist.md
├── run-manager-specialist.md
├── dss-integration-specialist.md
├── hms-orchestrator.md
└── (additional specialists)
```

---

## Usage Pattern

Production agents follow a consistent pattern. For Claude Code, invoke via skills or direct reference:

```python
# Example: Using update_3_to_4 agent
# See update_3_to_4/AGENT.md for complete instructions

# Initialize workflow
from pathlib import Path
project_path = Path("path/to/hms/project")

# Execute upgrade workflow (via agent or skill)
# Results exported to MODELING_LOG.md
```

**Claude Code invocation**: Use the corresponding skill in `.claude/skills/` or reference the agent's `AGENT.md` directly.

---

## Quality Verdicts

All agents use the same verdict system:

- **🟢 GREEN** - All acceptance criteria passed, safe to proceed
- **🟡 YELLOW** - Minor issues detected, manual review recommended
- **🔴 RED** - Critical failures, do not proceed

---

## Contributing

When adding a new agent:

1. Follow the existing structure (AGENT.md, workflow script, examples)
2. Use `AgentWorkflow` base class
3. Include comprehensive acceptance criteria
4. Add unit tests
5. Document example results
6. Update this README
