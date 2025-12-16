# HMS Agents

Task-specific agents for automating HEC-HMS workflows. Each agent is a specialized workflow that performs a specific modeling operation with quality validation.

## Available Agents

### update_3_to_4 - HMS Version Upgrade Agent

Upgrades HEC-HMS projects from version 3.x to 4.x with comprehensive validation.

**Features:**
- Automatic parameter conversion (Muskingum Cunge 8-point → standard)
- DSS file comparison (peak flow, volume, timing)
- Quality verdict system (GREEN/YELLOW/RED)
- Comprehensive change logging
- Session persistence (save/resume)

**Location:** `hms_agents/update_3_to_4/`

**Documentation:** See `hms_agents/update_3_to_4/AGENT.md`

**Example Results:** `hms_agents/update_3_to_4/example_results_tifton.md`

### hms_doc_query - Documentation Query Agent

Query official HEC-HMS documentation to answer technical questions.

**Features:**
- Web-based documentation retrieval (User's Manual, Technical Reference)
- **Image and screenshot processing** - Can view UI diagrams and parameter screenshots
- Method validation and parameter lookup
- Release note searching
- Version-specific information
- Known HMS method enumeration

**Location:** `hms_agents/hms_doc_query/`

**Documentation:** See `hms_agents/hms_doc_query/AGENT.md`

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

**Location:** `hms_agents/hms_decompiler/`

**Documentation:** See `hms_agents/hms_decompiler/AGENT.md`

**Quick Start:** `hms_agents/hms_decompiler/QUICK_START.md`

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

All agents inherit from the shared framework located in `agents/_shared/`:

- **`workflow_base.py`** - Base class with session persistence, quality verdicts, change tracking
- **`comparison_utils.py`** - DSS comparison utilities for validation

### Creating a New Agent

1. Create directory: `hms_agents/your_agent/`
2. Create workflow script inheriting from `AgentWorkflow`
3. Define acceptance criteria
4. Implement `execute()` method
5. Create `AGENT.md` documentation
6. Add entry to this README

See `agents/README.md` for framework documentation.

---

## Directory Structure

```
hms_agents/
├── README.md (this file)
├── update_3_to_4/
│   ├── AGENT.md
│   ├── upgrade_workflow.py
│   ├── compare_dss_outputs.py
│   ├── RESULTS_TEMPLATE.md
│   └── example_results_tifton.md
├── hms_doc_query/
│   ├── AGENT.md
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
│   │   ├── cfr.jar
│   │   ├── decompile.bat
│   │   ├── decompile.sh
│   │   └── TOOL_USAGE.md
│   └── examples/
│       ├── query_jython_api.md
│       ├── version_compatibility.md
│       └── decompile_new_class.md
└── (future agents)
```

---

## Usage Pattern

All agents follow the same usage pattern:

```python
from hms_agents.your_agent.workflow import YourAgentWorkflow

# Initialize
workflow = YourAgentWorkflow(
    project_path=Path("path/to/project"),
    acceptance_criteria=[...]
)

# Execute
verdict = workflow.execute()

# Export results
workflow.export_modeling_log(Path("MODELING_LOG.md"))

# Save session for later resume
workflow.save_session(Path("session.json"))
```

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
