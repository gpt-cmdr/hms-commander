# HMS-Commander Agents

This directory contains specialist agents for hms-commander development and testing.

## Agent Architecture

### Notebook Testing Workflow

**notebook-runner** (Sonnet)
- Executes notebooks with pytest/nbmake or nbconvert
- Captures stdout, stderr, execution logs
- Generates output digests for review
- Delegates to Haiku agents for analysis

**notebook-output-auditor** (Haiku)
- Reviews audit.md/audit.json for exceptions
- Identifies tracebacks, errors, failures
- Categorizes error types and suggests fixes
- Fast, focused on explicit failures

**notebook-anomaly-spotter** (Haiku)
- Reviews audit.md/audit.json for unexpected behavior
- Identifies empty results, missing artifacts
- Flags suspicious patterns (all zeros, NaNs)
- Catches issues that don't raise exceptions

### Conversation Intelligence Workflow

**conversation-insights-orchestrator** (Sonnet)
- Orchestrates multi-phase conversation analysis
- Coordinates sub-agents (Haiku scanner, Sonnet analyzers, Opus researcher)
- Extracts patterns, best practices, strategic insights
- Generates comprehensive insight reports

**best-practice-extractor** (Sonnet)
- Identifies explicit and implicit best practices
- Categorizes by domain (code, testing, workflows, docs)
- Scores actionability
- Phase 2 analyzer for orchestrator

**conversation-deep-researcher** (Opus)
- Multi-pass strategic analysis
- Cross-conversation linking
- Architectural pattern recognition
- Phase 4 deep analysis for orchestrator

### HMS Domain Specialists

**hms-orchestrator** (Sonnet)
- Traffic controller and task classifier for HMS operations
- Routes tasks to appropriate specialist agents
- Handles simple queries directly
- Coordinates multi-domain workflows

**basin-model-specialist** (Sonnet)
- Expert in HEC-HMS basin files (.basin)
- Handles subbasins, junctions, reaches, loss/transform methods
- Curve number and lag time updates
- Clone workflows for QAQC comparison

**met-model-specialist** (Sonnet)
- Expert in meteorologic models (.met)
- Precipitation methods, gage assignments
- Atlas 14 updates, TP40 to Atlas 14 conversion
- Evapotranspiration and snowmelt configuration

**run-manager-specialist** (Sonnet)
- Expert in run file operations (.run)
- Run configuration and validation
- Component linking (basin + met + control)
- Critical consistency validation (prevents HMS auto-deletion)

**dss-integration-specialist** (Sonnet)
- Expert in HEC-DSS file operations
- Peak flow extraction, hydrograph analysis
- Volume summaries, time series export
- Leverages RasDss from ras-commander

**hms-ras-workflow-coordinator** (Sonnet)
- Coordinates HMS-to-RAS integrated workflows
- HMS hydrograph extraction for RAS boundary conditions
- Spatial matching (HMS outlets to RAS cross sections)
- Cross-tool quality validation

**hierarchical-knowledge-curator** (Sonnet)
- Expert in Claude's hierarchical memory framework
- Manages CLAUDE.md hierarchy, .agent/ memory system
- Creates skills, defines agents
- Maintains documentation structure

### Other Agents

**example-notebook-librarian** (Sonnet)
- Maintains notebook quality standards
- Updates notebooks to follow conventions
- Adds new example notebooks
- Ensures MkDocs integration

**python-environment-manager** (Sonnet)
- Manages conda environments (hmscmdr_local, hmscmdr_pip)
- Troubleshoots dependency issues
- Handles uv and pip workflows

**claude-code-guide** (Sonnet)
- Navigation and framework assistance
- Project orientation
- Documentation queries

## Typical Workflow

### 1. Run Notebooks as Tests

```bash
# Use notebook-runner agent
# Executes: pytest --nbmake examples/*.ipynb
# Captures: stdout.txt, stderr.txt in working/notebook_runs/{timestamp}/
# Generates: audit.md, audit.json
```

### 2. Review for Exceptions

```bash
# Use notebook-output-auditor agent
# Input: working/notebook_runs/{timestamp}/audit.md
# Output: Failure report with cell indices, error types, suggested fixes
```

### 3. Review for Anomalies

```bash
# Use notebook-anomaly-spotter agent
# Input: working/notebook_runs/{timestamp}/audit.md
# Output: Anomaly report with suspicious patterns, missing artifacts
```

### 4. Fix Issues

```bash
# Use example-notebook-librarian agent (if conventions violated)
# Or domain specialist agents (if HMS-specific failures)
# Or python-environment-manager (if dependency issues)
```

## Supporting Scripts

**scripts/notebooks/audit_ipynb.py**
- Generates condensed output digests from executed notebooks
- Creates audit.md (human-readable) and audit.json (machine-readable)
- Avoids sending full notebook JSON to Haiku agents

**Usage**:
```bash
python scripts/notebooks/audit_ipynb.py notebook.ipynb --out-dir working/notebook_runs/latest
```

## Agent Invocation

These agents are designed to be invoked by other agents or CI/CD pipelines:

**From notebook-runner**:
```
After execution:
  1. Generate digest: python scripts/notebooks/audit_ipynb.py ...
  2. Invoke notebook-output-auditor with digest path
  3. Invoke notebook-anomaly-spotter with digest path
```

**Standalone**:
```
# Run audit script manually
python scripts/notebooks/audit_ipynb.py examples/notebook.ipynb --out-dir working/notebook_runs/debug

# Then manually invoke auditors with audit.md path
```

## Directory Structure

```
.claude/agents/
  # HMS Domain Specialists
  hms-orchestrator.md                     # Traffic controller (Sonnet)
  basin-model-specialist.md               # Basin file expert (Sonnet)
  met-model-specialist.md                 # Met model expert (Sonnet)
  run-manager-specialist.md               # Run config expert (Sonnet)
  dss-integration-specialist.md           # DSS results expert (Sonnet)
  hms-ras-workflow-coordinator.md         # HMS-RAS integration (Sonnet)
  hierarchical-knowledge-curator.md       # Knowledge architecture (Sonnet)

  # Conversation Intelligence
  conversation-insights-orchestrator.md   # Phase 1-4 orchestrator (Sonnet)
  best-practice-extractor.md              # Phase 2 analyzer (Sonnet)
  conversation-deep-researcher.md         # Phase 4 deep analysis (Opus)

  # Notebook Testing
  notebook-runner.md                      # Execution agent (Sonnet)
  notebook-output-auditor.md              # Exception detector (Haiku)
  notebook-anomaly-spotter.md             # Behavioral reviewer (Haiku)
  example-notebook-librarian.md           # Notebook standards (Sonnet)

  # Development Support
  python-environment-manager.md           # Env management (Sonnet)
  claude-code-guide.md                    # Navigation (Sonnet)

scripts/
  conversation_insights/
    conversation_parser.py       # Conversation data parsing utilities
    __init__.py                  # Public API
  notebooks/
    audit_ipynb.py              # Digest generator

agent_tasks/
  conversation_insights/
    {timestamp}/
      phase1_filtered_conversations.json
      phase2_patterns.json
      phase3_preliminary_insights.md
      phase4_strategic_analysis.md
      conversation_insights_report.md

working/notebook_runs/
  {timestamp}/                   # Run artifacts
    run_command.txt              # Command executed
    stdout.txt                   # Standard output
    stderr.txt                   # Error output
    audit.md                     # Human-readable digest
    audit.json                   # Machine-readable digest
    *.nbconvert.ipynb            # Executed notebook (if nbconvert used)
```

## Related Documentation

- `.claude/rules/documentation/notebook-standards.md` - Quality requirements
- `.claude/rules/testing/tdd-approach.md` - Testing philosophy
- `examples/` - Notebook collection
