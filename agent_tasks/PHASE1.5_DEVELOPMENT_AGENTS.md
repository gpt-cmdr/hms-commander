# Phase 1.5: Development-Focused Agent Infrastructure

**Created**: 2025-12-17
**Status**: Planning
**Source**: Adapted from ras-commander development agents
**Priority**: Next after Phase 1 (Cognitive Infrastructure)

---

## Strategic Overview

This phase implements development-focused agents that accelerate all future work:
- Documentation generation (MkDocs, notebooks)
- Environment management (conda, pip, kernels)
- Knowledge curation (hierarchy, skills, agents)
- Notebook testing infrastructure
- Conversation intelligence
- Claude Code best practices

**Principle**: These agents create leverage - they make every subsequent feature faster to develop, document, and validate.

---

## Agent Categories

### Tier 1: Critical Foundation (Implement First)

| Agent | Model | Purpose | HMS Adaptation |
|-------|-------|---------|----------------|
| `documentation-generator` | sonnet | MkDocs, notebooks, API docs | HmsExamples pattern, HMS workflows |
| `python-environment-manager` | sonnet | Environment setup and troubleshooting | hmscmdr_local/hmscmdr_pip environments |
| `hierarchical-knowledge-curator` | opus | Knowledge organization and curation | Exists as subagent, enhance to full agent |
| `claude-code-guide` | haiku | Official Anthropic docs reference | Copy with reference files |

### Tier 2: Notebook Testing (Implement Second)

| Agent | Model | Purpose | HMS Adaptation |
|-------|-------|---------|----------------|
| `example-notebook-librarian` | sonnet | Notebook conventions, QA/QC | HmsExamples, HMS-specific notebooks |
| `notebook-runner` | sonnet | Execute notebooks as tests | nbmake integration |
| `notebook-output-auditor` | haiku | Review for exceptions | Same pattern |
| `notebook-anomaly-spotter` | haiku | Review for unexpected behavior | HMS-specific anomalies |

### Tier 3: Conversation Intelligence (Implement Third)

| Agent | Model | Purpose | HMS Adaptation |
|-------|-------|---------|----------------|
| `conversation-insights-orchestrator` | sonnet | Coordinates conversation analysis | Same pattern |
| `conversation-deep-researcher` | opus | Expert-level deep analysis | Same pattern |
| `best-practice-extractor` | sonnet | Extract best practices | HMS-specific patterns |

---

## Detailed Implementation Specifications

### 1. documentation-generator

**Source**: `ras-commander/.claude/agents/documentation-generator/SUBAGENT.md`

**Key Adaptations for HMS**:

```yaml
name: documentation-generator
model: sonnet
tools: [Read, Write, Edit, Bash, Glob, Grep]
working_directory: examples
description: |
  Creates and maintains example notebooks, API documentation, and mkdocs content
  for hms-commander. Specializes in Jupyter notebook authoring with HmsExamples
  pattern, mkdocs deployment (GitHub Pages and ReadTheDocs), and HMS workflow
  documentation. Use when creating tutorials, examples, notebook documentation,
  API references, mkdocs pages, or fixing documentation build issues.
```

**Files to Create**:
- `.claude/agents/documentation-generator/SUBAGENT.md`
- `.claude/rules/documentation/notebook-standards.md` (HMS-specific)
- `.claude/rules/documentation/mkdocs-config.md` (HMS-specific)

**Key Content**:
- CRITICAL: ReadTheDocs symlink issue (use `cp -r`, not `ln -s`)
- HmsExamples pattern (reproducible notebooks)
- HMS notebook structure (H1 title, import cells)
- mkdocs-jupyter configuration
- Dual-platform deployment (GitHub Pages + ReadTheDocs)

### 2. python-environment-manager

**Source**: `ras-commander/.claude/agents/python-environment-manager.md`

**Key Adaptations for HMS**:

```yaml
name: python-environment-manager
model: sonnet
tools: [Bash, Read, Write, Grep, Glob]
description: |
  Automated setup and management of Python environments for hms-commander.
  Use when: users need help setting up Python environments, troubleshooting
  import errors, upgrading hms-commander, or configuring Jupyter kernels.

  Standard environments:
  - hmscmdr_pip (pip package) - for users NOT editing source
  - hmscmdr_local (editable install) - for developers editing source
```

**HMS-Specific Differences from RAS**:
- Environment names: `hmscmdr_local` and `hmscmdr_pip` (already documented in `.claude/rules/project/development-environment.md`)
- Dependencies: pandas, numpy, pathlib, tqdm, requests + optional GIS/DSS
- Toggle cell pattern for development mode
- No HEC-RAS.exe path concerns, but HMS path configuration

**Files to Create**:
- `.claude/agents/python-environment-manager.md`

### 3. hierarchical-knowledge-curator (Enhanced)

**Source**: `ras-commander/.claude/agents/hierarchical-knowledge-agent-skill-memory-curator.md`

**Current State**: `hierarchical-knowledge-curator` exists as simple subagent in `.claude/subagents/`

**Enhancement**: Promote to full agent with reference materials

```yaml
name: hierarchical-knowledge-curator
model: opus
tools: [Read, Write, Edit, Grep, Glob, Bash]
working_directory: .
description: |
  Expert in Claude's hierarchical memory framework, skills architecture, agent memory
  systems, and knowledge organization for hms-commander. Manages CLAUDE.md hierarchy,
  agent_tasks/ memory system, creates skills, defines agents, and maintains documentation
  structure. Understands relationship between persistent knowledge (HOW to code) and
  temporal memory (WHAT we're doing).
```

**Key Content to Include**:
- Subagent markdown output pattern
- Memory system architecture (4-level hierarchy)
- Three-tier agent architecture (Opus/Sonnet/Haiku)
- Content distribution rules (CLAUDE.md size targets)
- Skills framework best practices
- Subagent definition patterns
- `.claude/outputs/` curation workflow

**Files to Create**:
- `.claude/agents/hierarchical-knowledge-curator/AGENT.md`
- `.claude/agents/hierarchical-knowledge-curator/reference/`
  - `memory-knowledge-consolidation.md`
  - `implementation-phases.md`
  - `governance-rules.md`

### 4. claude-code-guide

**Source**: `ras-commander/.claude/agents/claude-code-guide.md` + `reference/`

**Direct Copy**: This agent is generic and applies to both repositories

```yaml
name: claude-code-guide
model: haiku
tools: [Read, Write, Edit, WebFetch, Grep, Glob]
working_directory: .
description: |
  Expert in Claude Code best practices, configuration, and official Anthropic documentation.
  Consults official docs for skills creation, memory hierarchy (CLAUDE.md, .claude/rules/),
  imports, path-specific rules, and Claude Code configuration.
```

**Files to Create**:
- `.claude/agents/claude-code-guide.md`
- `.claude/agents/claude-code-guide/reference/`
  - `skills-creation.md` (from Anthropic blog)
  - `memory-system.md` (from Claude Code docs)
  - `official-docs.md` (URL reference)
  - `README.md`

### 5. example-notebook-librarian

**Source**: `ras-commander/.claude/agents/example-notebook-librarian.md`

**Key Adaptations for HMS**:

```yaml
name: example-notebook-librarian
model: sonnet
tools: [Read, Write, Edit, Bash, Grep, Glob]
working_directory: examples
description: |
  Expert librarian for hms-commander's example notebooks in examples/*.ipynb.
  Maintains notebook conventions, helps users author new notebooks using proven
  patterns, and autonomously QA/QC's the example suite as a functional test
  harness (run → review → fix → document).

  Uses notebook-runner to execute notebooks and spawns Haiku reviewers to
  inspect condensed notebook output digests.
```

**HMS-Specific Content**:
- HmsExamples pattern (extract_project)
- HMS workflow demonstrations
- Links to HEC-HMS documentation via hms_doc_query
- HMS-specific validation criteria

**Files to Create**:
- `.claude/agents/example-notebook-librarian.md`
- `examples/AGENTS.md` (notebook index)

### 6. notebook-runner

**Source**: `ras-commander/.claude/agents/notebook-runner.md`

**Mostly Direct Copy** with HMS adaptations:

```yaml
name: notebook-runner
model: sonnet
tools: [Read, Write, Edit, Bash, Grep, Glob]
working_directory: .
description: |
  Runs and troubleshoots Jupyter notebooks (.ipynb) as repeatable tests and
  executable documentation for hms-commander. Specializes in nbmake/pytest
  execution, nbconvert fallbacks, capturing run artifacts.
```

**Files to Create**:
- `.claude/agents/notebook-runner.md`
- `scripts/notebooks/audit_ipynb.py` (copy/adapt from ras-commander)

### 7 & 8. notebook-output-auditor & notebook-anomaly-spotter

**Source**: `ras-commander/.claude/agents/notebook-output-auditor.md` and `notebook-anomaly-spotter.md`

**Direct Copy**: These Haiku agents are generic

**Files to Create**:
- `.claude/agents/notebook-output-auditor.md`
- `.claude/agents/notebook-anomaly-spotter.md`

### 9-11. Conversation Intelligence Suite

**Source**: Multiple ras-commander agents

**Components**:
- `conversation-insights-orchestrator` (sonnet) - Main coordinator
- `conversation-deep-researcher` (opus) - Expert analysis
- `best-practice-extractor` (sonnet) - Practice identification

**Implementation Note**: These require supporting scripts in `scripts/conversation_insights/`

**Files to Create**:
- `.claude/agents/conversation-insights-orchestrator.md`
- `.claude/agents/conversation-deep-researcher.md`
- `.claude/agents/best-practice-extractor.md`
- `scripts/conversation_insights/` (directory with Python utilities)

---

## Implementation Order

### Sprint 1: Documentation Foundation
**Estimated**: 2-3 parallel subagents

1. **documentation-generator** (Workstream A)
   - Create SUBAGENT.md
   - Create notebook-standards.md (HMS-specific)
   - Create mkdocs-config.md (HMS-specific)

2. **python-environment-manager** (Workstream B)
   - Create agent definition
   - Verify alignment with existing development-environment.md

3. **claude-code-guide** (Workstream C)
   - Copy agent definition
   - Copy reference files with any HMS adjustments

### Sprint 2: Knowledge & Notebooks
**Estimated**: 2-3 parallel subagents

4. **hierarchical-knowledge-curator** (Workstream A)
   - Enhance existing subagent to full agent
   - Create reference materials

5. **example-notebook-librarian** (Workstream B)
   - Create agent definition
   - Create examples/AGENTS.md index

6. **notebook-runner + auditors** (Workstream C)
   - Create notebook-runner.md
   - Create notebook-output-auditor.md
   - Create notebook-anomaly-spotter.md
   - Copy/adapt audit_ipynb.py script

### Sprint 3: Conversation Intelligence
**Estimated**: 1-2 parallel subagents

7. **conversation-insights-orchestrator** (Workstream A)
   - Create orchestrator agent
   - Create supporting scripts

8. **conversation-deep-researcher + best-practice-extractor** (Workstream B)
   - Create both agents
   - These are simpler, can be done together

---

## Supporting Infrastructure

### Scripts Directory
```
scripts/
├── notebooks/
│   └── audit_ipynb.py          # Notebook output digest generator
└── conversation_insights/
    ├── conversation_parser.py   # Parse history.jsonl
    ├── pattern_analyzer.py      # N-gram and pattern detection
    ├── insight_extractor.py     # Extract insights
    └── report_generator.py      # Generate reports
```

### Working Directory
```
working/
└── notebook_runs/              # Notebook execution artifacts
    └── {timestamp}/
        ├── run_command.txt
        ├── stdout.txt
        ├── stderr.txt
        └── audit.md
```

### Examples Index
```
examples/
├── AGENTS.md                   # Notebook index and conventions
├── 00_Using_HmsExamples.ipynb
├── 01_project_initialization.ipynb
└── ...
```

---

## Success Criteria

Phase 1.5 is complete when:

1. **Documentation Build Works**
   - `mkdocs serve` builds without errors
   - Notebooks render correctly
   - ReadTheDocs deployment succeeds

2. **Environment Setup Automated**
   - Agent can create hmscmdr_local and hmscmdr_pip
   - Troubleshooting workflows function
   - Jupyter kernels configured correctly

3. **Notebook Testing Functions**
   - `pytest --nbmake examples/*.ipynb` runs
   - Output digests generated
   - Haiku reviewers identify issues

4. **Knowledge Curation Active**
   - `.claude/outputs/` managed
   - CLAUDE.md hierarchy maintained
   - Skills/agents created via patterns

5. **Conversation Insights Available**
   - Can analyze conversation history
   - Extract best practices
   - Generate insight reports

---

## Relationship to Other Phases

**Phase 1** (Cognitive Infrastructure): ✓ COMPLETE
- Slash commands, orchestrator, organization

**Phase 1.5** (Development Agents): THIS DOCUMENT
- Documentation, environment, notebooks, conversation intelligence

**Phase 2** (HMS Domain Infrastructure): AFTER THIS
- Calibration infrastructure
- Jython engineer subagent
- Additional HMS skills

---

## Notes

- Use Sonnet model for implementation subagents
- Agents work in parallel for speed
- All work respects existing patterns
- Reference ras-commander implementations but adapt for HMS context
- agent_tasks/.agent/ memory system tracks progress

---

**Next Action**: Launch parallel subagents to implement Sprint 1 agents
