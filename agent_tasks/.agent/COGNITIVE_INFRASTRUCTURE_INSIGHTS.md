# Cognitive Infrastructure Insights

**Source**: External advice on TnTech repository maturity patterns (2025-12-17)
**Purpose**: Document transferable insights for hms-commander development

---

## Key Insights Extracted

### 1. Task Templates System ⭐ HIGH PRIORITY

**Concept**: Structured templates for common development workflows

**Implementation**:
```
agent_tasks/
  templates/
    bugfix.md         # Structured bug investigation + fix
    feature.md        # Feature implementation workflow
    refactor.md       # Code improvement workflow
    investigation.md  # Research/discovery workflow
```

**Template Structure**:
Each template includes:
- **Context files** (`@` references to relevant files)
- **Constraints** (safety rules, don't-do items)
- **Plan** (structured approach)
- **Acceptance criteria** (definition of done)
- **Verification steps** (how to validate)
- **Notes for future** (learnings, gotchas)

**Value**:
- Provides repeatable workflow structure
- Ensures nothing gets forgotten
- Makes tasks resumable across sessions
- Builds institutional memory

**Status in hms-commander**: ❌ Not implemented
**Action**: Create `agent_tasks/templates/` with 4 core templates

---

### 2. Reusable Task Library ⭐ HIGH PRIORITY

**Concept**: Numbered, reusable task files that agents and humans can invoke

**Implementation**:
```
agent_tasks/
  tasks/
    000-bootstrap.md           # Initial setup workflow
    010-env-setup.md           # Environment configuration
    020-run-simulation.md      # Execute HMS workflow
    030-notebook-test.md       # Run notebook suite
    040-atlas14-update.md      # Atlas 14 migration
    050-version-upgrade.md     # HMS 3.x → 4.x
```

**Pattern**: Each task is a self-contained workflow with:
- Prerequisites
- Step-by-step instructions
- Expected outcomes
- Troubleshooting guide

**Value**:
- "Cognitive backbone" for agent delegation
- Slash commands reference these (`/task 020-run-simulation`)
- Skills reference these for structured workflows
- Reduces "how do I do X again?" questions

**Status in hms-commander**: ❌ Not implemented (we have BACKLOG phases, not reusable tasks)
**Action**: Create `agent_tasks/tasks/` with 10-15 core HMS workflows

---

### 3. Runs and Artifacts Organization

**Concept**: Separate execution logs from task definitions

**Implementation**:
```
agent_tasks/
  runs/        # Execution logs, session outputs (gitignored)
  artifacts/   # Generated outputs, reports (gitignored)
```

**Pattern**:
- Task execution generates `runs/<task-id>-<timestamp>.log`
- Artifacts (reports, diffs, analysis) go to `artifacts/`
- Neither committed to git

**Value**:
- Keeps task library clean
- Provides audit trail for executions
- Separates "what to do" from "what happened"

**Status in hms-commander**: ❌ Not implemented
**Action**: Create directories, update `.gitignore`

---

### 4. Enhanced Slash Command Patterns

**Concept**: Commands with pre-run context gathering via `!` prefix

**Pattern**:
```markdown
---
description: Run HMS simulation
allowed-tools: Bash(uv run python:*), Read, Write
---

## Context
- Repo root: !`pwd`
- Git status: !`git status`
- HMS version: !`uv run python -c "import hms_commander; print(hms_commander.__version__)"`

## Task
[Command instructions]
```

**Value**:
- Commands gather context before executing
- Reduces back-and-forth for environment info
- Makes commands more autonomous

**Status in hms-commander**: ⚠️ Partial (we have commands, but not using `!` prefix pattern)
**Action**: Enhance existing commands with context gathering

---

### 5. "Cognitive Backbone" Philosophy ⭐ CORE INSIGHT

**Quote**: "This becomes your cognitive backbone: subagents and skills can reference these tasks, and your slash commands can pull them into action quickly."

**Architecture**:
```
Slash Commands (user interface)
    ↓ invoke
Task Library (reusable workflows)
    ↓ reference
Skills (domain expertise)
    ↓ activate
Subagents (specialists)
    ↓ execute
Code (implementation)
```

**Integration Pattern**:
- User runs `/hms-calibrate`
- Command loads `agent_tasks/tasks/050-calibration-workflow.md`
- Task references `calibration-metrics` skill
- Skill activates `hms-calibration-analyst` subagent
- Subagent calls `HmsCalibration.compute_nse()` code

**Value**:
- Each layer adds value without duplication
- Tasks are reusable across multiple entry points
- Agent memory accumulates in task library

**Status in hms-commander**: ⚠️ Partial architecture exists, needs formalization
**Action**: Document this pattern in `.claude/INDEX.md`

---

### 6. Lightweight Knowledge Layer

**Anti-pattern to avoid**:
- ❌ Full-blown knowledge base generation unless actively needed
- ❌ Committing generated "fullrepo" context dumps
- ❌ Large domain skill catalogs that duplicate upstream work

**Correct pattern**:
- ✅ Skills point to canonical repo docs + files
- ✅ Keep knowledge in primary sources
- ✅ Agents/skills provide navigation, not duplication

**Status in hms-commander**: ✅ Already following this pattern
**Validation**: Our skills reference primary sources (code docstrings, notebooks, rules)

---

### 7. Hierarchical AGENTS.md Pattern (Optional)

**Concept**: Context-specific AGENTS.md files near the code

**Pattern**:
```
CLAUDE.md                          # Root project memory
hms_commander/AGENTS.md            # Package-level patterns
hms_commander/HmsBasin.py          # Implementation
```

**Value**:
- Local rules close to the code
- Context-appropriate guidance

**Status in hms-commander**: ❌ Not using (we use CLAUDE.md + .claude/rules/ instead)
**Decision**: SKIP - our current pattern is working well

---

### 8. Three-Level Safety Boundaries

**Pattern**:
- **Safe zones**: Clone data (HmsExamples pattern, `data/EarlyDevTesting/`)
- **Read-only**: Production data (observe, don't mutate)
- **Forbidden**: Credentials, destructive operations

**Status in hms-commander**: ✅ Already implemented
- HmsExamples provides reproducible test data
- Clone workflows ensure non-destructive QAQC
- `.gitignore` protects credentials

---

## Implementation Priority

### Phase 0: Immediate (This Session)
1. Create `agent_tasks/templates/` with 4 templates
2. Create `agent_tasks/tasks/` with 5 starter tasks
3. Update `.gitignore` for runs/artifacts
4. Document cognitive backbone in INDEX.md

### Phase 1: Next Session
5. Enhance slash commands with `!` context gathering
6. Create 10 more reusable tasks for common HMS workflows
7. Update existing skills to reference task library

### Phase 2: Future
8. Consider hierarchical AGENTS.md if needed
9. Build task execution logging system
10. Create task analytics (which tasks are used most?)

---

## Templates to Create

### 1. agent_tasks/templates/bugfix.md
- Context gathering
- Reproduction steps
- Root cause analysis
- Fix implementation
- Verification checklist

### 2. agent_tasks/templates/feature.md
- Requirements gathering
- Design decisions
- Implementation plan
- Testing strategy
- Documentation updates

### 3. agent_tasks/templates/refactor.md
- Current state analysis
- Improvement rationale
- Refactoring steps
- Regression testing
- Performance validation

### 4. agent_tasks/templates/investigation.md
- Research question
- Information sources
- Findings
- Recommendations
- Next steps

---

## Starter Tasks to Create

### 1. `000-bootstrap.md`
Bootstrap hms-commander development environment

### 2. `010-env-setup.md`
Set up hmscmdr_local conda environment

### 3. `020-run-simulation.md`
Execute HMS simulation workflow

### 4. `030-notebook-test.md`
Run example notebooks with nbmake

### 5. `040-atlas14-update.md`
Update met model from TP40 to Atlas 14

### 6. `050-version-upgrade.md`
Upgrade HMS project from 3.x to 4.x

### 7. `060-calibration-workflow.md`
Calibrate HMS model parameters

### 8. `070-dss-extraction.md`
Extract results from DSS files

### 9. `080-notebook-authoring.md`
Create new example notebook

### 10. `090-skill-creation.md`
Create new skill following standards

---

## What NOT to Copy

From the advice: "What I would not copy from ras-commander (to keep TnTech lightweight)"

Applied to hms-commander:
- ❌ Don't create full knowledge base generation pipeline (we already decided against this)
- ❌ Don't duplicate ras-commander domain skills here (HMS skills stay HMS-focused)
- ❌ Don't commit generated context dumps

These align with our existing decisions.

---

## Key Takeaways

1. **Task templates** provide structure and repeatability
2. **Reusable task library** is the "cognitive backbone"
3. **Runs/artifacts separation** keeps task definitions clean
4. **Enhanced commands** gather context autonomously
5. **Lightweight knowledge** points to sources, doesn't duplicate

**Next actions**: Implement Phase 0 items (templates + starter tasks)
