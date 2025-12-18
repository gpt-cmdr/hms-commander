# Task Backlog

Tasks organized by phase and priority.

---

## Phase 1: Cognitive Infrastructure (Current)

**Focus**: Claude Code-centric infrastructure with maximum leverage

### PHASE1-001: Workflow Slash Commands
**Status**: COMPLETE
- [x] `/hms-orient` - Orientation checklist
- [x] `/hms-run` - Execution workflow
- [x] `/hms-calibrate` - Calibration workflow
- [x] `/hms-plot-dss` - DSS visualization

### PHASE1-002: Developer Scaffolding Commands
**Status**: COMPLETE
- [x] `/hms-new-skill` - Scaffold new skill
- [x] `/hms-new-agent` - Scaffold new subagent
- [x] `/hms-docs` - MkDocs workflows

### PHASE1-003: Orchestrator Subagent
**Status**: COMPLETE
- [x] Create `hms-orchestrator.md`
- [x] Task classification rules
- [x] Routing table to specialists
- [x] Multi-domain coordination patterns

### PHASE1-004: Organization & Navigation
**Status**: COMPLETE
- [x] Reorganize `feature_dev_notes/` structure
- [x] Create `feature_dev_notes/INDEX.md`
- [x] Create `.claude/INDEX.md`
- [x] Update DEVELOPMENT_ROADMAP.md with Phase 0.5

### PHASE1-005: Foundation Agents Integration
**Status**: COMPLETE
- [x] Verify hms_decompiler (Code Archaeologist) integration
- [x] Verify hms_doc_query (Documentation Agent) integration
- [x] Create `querying-hms-documentation` skill
- [x] Add routing entries in orchestrator

---

## Phase 1.5: Development-Focused Agent Infrastructure (Next)

**Focus**: Documentation, environment, notebooks, conversation intelligence
**Source**: Adapted from ras-commander development agents

### PHASE1.5-001: Documentation Foundation (Sprint 1)
**Status**: COMPLETE
**Effort**: 2-3 parallel subagents

- [x] Create `documentation-generator` agent (MkDocs, notebooks, API docs)
- [x] Create `python-environment-manager` agent (conda, pip, kernels)
- [x] Create `claude-code-guide` agent + reference files
- [x] Create `.claude/rules/documentation/notebook-standards.md`
- [x] Create `.claude/rules/documentation/mkdocs-config.md`
- [x] Update orchestrator with new agent routing
- [x] Update INDEX.md with Development Agents section

### PHASE1.5-002: Knowledge & Notebooks (Sprint 2)
**Status**: COMPLETE
**Effort**: 2-3 parallel subagents

- [x] Enhance `hierarchical-knowledge-curator` to full agent
- [x] Create `example-notebook-librarian` agent
- [x] Create `notebook-runner` agent + Haiku auditors
- [x] Create `examples/AGENTS.md` notebook index
- [x] Copy/adapt `scripts/notebooks/audit_ipynb.py`

### PHASE1.5-003: Conversation Intelligence (Sprint 3)
**Status**: COMPLETE
**Effort**: 1-2 parallel subagents

- [x] Create `conversation-insights-orchestrator` agent
- [x] Create `conversation-deep-researcher` agent
- [x] Create `best-practice-extractor` agent
- [x] Create `scripts/conversation_insights/` utilities

---

## Phase 1.75: Cognitive Infrastructure Enhancements (In Progress)

**Focus**: Task templates and reusable workflows (cognitive backbone)

### PHASE1.75-001: Task Template System
**Status**: COMPLETE
**Effort**: 1 session

- [x] Create `agent_tasks/templates/` directory
- [x] Create `bugfix.md` template
- [x] Create `feature.md` template
- [x] Create `refactor.md` template
- [x] Create `investigation.md` template
- [x] Document COGNITIVE_INFRASTRUCTURE_INSIGHTS.md

### PHASE1.75-002: Reusable Task Library
**Status**: COMPLETE (Starter Set)
**Effort**: 1 session

- [x] Create `agent_tasks/tasks/` directory
- [x] Create `000-bootstrap.md` (initial setup)
- [x] Create `010-env-setup.md` (hmscmdr_local environment)
- [x] Create `020-run-simulation.md` (HMS execution workflow)
- [x] Create `030-notebook-test.md` (notebook testing with nbmake)
- [x] Create `040-atlas14-update.md` (precipitation update workflow)
- [x] Update `.gitignore` for runs/artifacts
- [x] Transform `agent_tasks/README.md` to cognitive backbone documentation

### PHASE1.75-003: Task Library Expansion
**Status**: DEFERRED - Moving to Future Development
**Rationale**: Core infrastructure complete. Shift focus to critical features (MkDocs documentation).

**Planned task workflows** (for future):
- `050-version-upgrade.md` - HMS 3.x → 4.x upgrade workflow
- `060-calibration-workflow.md` - NSE, PBIAS, RMSE calibration
- `070-dss-extraction.md` - Advanced DSS operations
- `080-notebook-authoring.md` - Create new example notebook
- `090-skill-creation.md` - Create new skill following standards
- `100-subagent-creation.md` - Create new subagent
- `110-slash-command-creation.md` - Create new slash command

### PHASE1.75-004: Enhanced Slash Commands
**Status**: DEFERRED - Moving to Future Development

**Planned enhancements** (for future):
- Add `!` prefix bash context gathering to existing commands
- Create `/task` command to execute task library entries
- Add task execution logging system
- Create artifact generation workflows

---

## Current Priority: Mermaid Diagrams Implementation

**Status**: COMPLETE
**Completed**: 2025-12-17

**Goal**: Add comprehensive Mermaid diagrams to documentation for visual learning and cognitive architecture explanation

- [x] Create cognitive architecture documentation page
- [x] Enable Mermaid support in mkdocs.yml
- [x] Implement Core Class Architecture diagram (index.md)
- [x] Implement Static Class Pattern diagram (index.md)
- [x] Implement HMS File Dependencies diagram (data_formats/overview.md)
- [x] Implement Execution Pipeline diagram (user_guide/execution.md)
- [x] Implement Non-Destructive Clone Pattern diagram (user_guide/clone_workflows.md)
- [x] Implement QAQC Workflow Sequence diagram (user_guide/clone_workflows.md)
- [x] Implement LLM Forward QAQC Cycle diagram (CLB_ENGINEERING_APPROACH.md)
- [x] Implement Quick Start Workflow diagram (getting_started/quick_start.md)
- [x] Add Cognitive Architecture to navigation menu
- [x] Test all diagrams locally (mkdocs serve)
- [x] Fix broken links in cognitive_architecture.md

**Result**: Successfully implemented 9 Mermaid diagrams across 7 documentation files. Created comprehensive cognitive architecture page with 6 diagrams explaining hierarchical knowledge, progressive disclosure, and agent orchestration. All diagrams rendering correctly in 44.35 second build.

**Files Created**:
- `docs/llm_dev/cognitive_architecture.md` (445 lines, 6 diagrams)
- `feature_dev_notes/MERMAID_DIAGRAMS_PROPOSAL.md` (proposal with all diagram code)

**Files Modified**:
- `mkdocs.yml` (Mermaid support + navigation entry)
- `docs/index.md` (2 diagrams added)
- `docs/data_formats/overview.md` (1 diagram)
- `docs/user_guide/execution.md` (1 diagram)
- `docs/user_guide/clone_workflows.md` (2 diagrams)
- `docs/CLB_ENGINEERING_APPROACH.md` (1 diagram)
- `docs/getting_started/quick_start.md` (1 diagram)

**Additional Lower-Priority Diagrams Available**: See `feature_dev_notes/MERMAID_DIAGRAMS_PROPOSAL.md` for file parsing flow, parallel execution, GUI verifiability, run configuration, and HMS→RAS integration diagrams.

---

## MkDocs Documentation

**Status**: COMPLETE - Ready for Deployment
**Completed**: 2025-12-17

**Goal**: Set up MkDocs documentation site leveraging existing Jupyter notebooks

- [x] Verify mkdocs.yml configuration
- [x] Set up ReadTheDocs deployment (with pre_build notebook copy)
- [x] Configure GitHub Pages deployment
- [x] Verify notebook integration (mkdocs-jupyter plugin)
- [x] Test local preview and build
- [x] Fix all broken links to root files
- [x] Update navigation to match actual notebooks
- [ ] Deploy to ReadTheDocs (auto-deploys on git push)
- [ ] Deploy to GitHub Pages (`mkdocs gh-deploy --force`)

**Result**: Documentation builds successfully in 49.78 seconds with all 6 notebooks rendering correctly. Server verified at http://127.0.0.1:8000/hms-commander/

**Files Modified**:
- `.readthedocs.yaml` - Added pre_build notebook copy
- `mkdocs.yml` - Updated navigation to match actual 6 notebooks
- `docs/examples/overview.md` - Fixed notebook links
- `docs/data_formats/*.md` - Fixed API reference links (8 files)
- `docs/user_guide/overview.md` - Fixed root file links
- `docs/llm_dev/contributing.md` - Fixed GitHub repository links

---

## Future Development Roadmap

### Phase 2: HMS Domain Infrastructure (Deferred)

**Focus**: HMS-specific subagents, skills, and domain knowledge

**Phases identified**:
- PHASE2-001: Calibration Infrastructure (hms-calibration-analyst subagent, calibration-metrics skill)
- PHASE2-002: Jython Engineer Subagent (Jython 2.7 patterns, HMS scripting API)
- PHASE2-003: Additional HMS Skills (evaluate gaps, create missing workflows)

**Rationale for deferral**: Low-hanging fruit exhausted. Focus on critical user-facing features first.

---

## Phase 3: Documentation & Polish (Deferred)

**Focus**: Documentation maturity and knowledge bases

### PHASE3-001: MkDocs Output Schema Documentation
**Status**: Deferred
**Effort**: 2-3 days

- [ ] Document DataFrame schemas
- [ ] Add to MkDocs reference section
- [ ] Create examples for each schema

### PHASE3-002: LLM Knowledge Base Generation
**Status**: LOW PRIORITY (Moved from Critical)
**Effort**: 1-2 weeks

- [ ] Create `ai_tools/generate_llm_knowledge_bases.py`
- [ ] Implement 7 KB output types
- [ ] Notebook cleaning pipeline
- [ ] Regeneration policy documentation

---

## Cross-Repository [cross-repo]

- See `../cross-repo/` for detailed request files
- Shared DSS operations via RasDss integration
- HMS→RAS boundary condition workflows

---

## Completed

### 2025-12-17
- [x] `/hms-orient` command
- [x] `/hms-run` command
- [x] `/hms-calibrate` command
- [x] `/hms-plot-dss` command
- [x] Phase 1 implementation plan created
- [x] `/hms-new-skill`, `/hms-new-agent`, `/hms-docs` commands
- [x] `hms-orchestrator.md` subagent with routing
- [x] `feature_dev_notes/INDEX.md` and `.claude/INDEX.md`
- [x] `querying-hms-documentation` skill
- [x] Foundation agents (hms_decompiler, hms_doc_query) integrated
- [x] **Phase 1.5 Sprint 1**: documentation-generator, python-environment-manager, claude-code-guide agents
- [x] **Phase 1.5 Sprint 2**: hierarchical-knowledge-curator, example-notebook-librarian, notebook-runner + auditors
- [x] **Phase 1.5 Sprint 3**: conversation-insights-orchestrator, conversation-deep-researcher, best-practice-extractor
- [x] `scripts/conversation_insights/` Python utilities (5 modules)
- [x] `scripts/notebooks/audit_ipynb.py` notebook digest generator

### 2024-12-13
- [x] Cross-repo infrastructure setup

---

**Legend**:
- `PHASE1-XXX` - Cognitive infrastructure (current)
- `PHASE2-XXX` - HMS domain infrastructure (next)
- `PHASE3-XXX` - Documentation/polish (deferred)
- `[cross-repo]` - Involves sibling repository
