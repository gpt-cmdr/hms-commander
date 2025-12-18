# Phase 1: Cognitive Infrastructure Implementation Plan

**Created**: 2025-12-17
**Status**: In Progress
**Focus**: Claude Code-centric infrastructure with maximum leverage

---

## Strategic Principle

**Cognitive infrastructure first, domain-specific later.**

This phase builds the foundation that makes ALL future work more efficient:
- Developer tooling and scaffolding
- Organization and navigation
- Knowledge curation patterns
- Subagent coordination

HMS-specific domain work (calibration, Jython, etc.) deferred to Phase 2.

---

## Phase 1 Deliverables

### 1. Developer Slash Commands

| Command | Purpose | Status |
|---------|---------|--------|
| `/hms-orient` | Orientation checklist | Done |
| `/hms-run` | Execution workflow | Done |
| `/hms-calibrate` | Calibration workflow | Done |
| `/hms-plot-dss` | DSS visualization | Done |
| `/hms-new-skill` | Scaffold new skill | **TODO** |
| `/hms-new-agent` | Scaffold new subagent | **TODO** |
| `/hms-docs` | MkDocs build/serve | **TODO** |

### 2. Cognitive Subagents

| Subagent | Purpose | Status |
|----------|---------|--------|
| `hms-orchestrator` | Route tasks to specialists | **TODO** |
| `hierarchical-knowledge-curator` | Knowledge organization | Exists |

### 3. Organization & Navigation

| Item | Purpose | Status |
|------|---------|--------|
| Feature dev notes reorganization | Clean structure | **TODO** |
| Skills/Subagents INDEX.md | Navigation | **TODO** |
| Development roadmap update | Unified plan | **TODO** |

---

## Parallel Implementation Plan

### Workstream A: Developer Commands
**Subagent**: Create scaffolding commands

Tasks:
1. `/hms-new-skill` - Generate skill folder structure with SKILL.md template
2. `/hms-new-agent` - Generate subagent .md file from template
3. `/hms-docs` - MkDocs commands (build, serve, deploy)

### Workstream B: Orchestrator Subagent
**Subagent**: Create hms-orchestrator.md

Tasks:
1. Define task routing logic
2. Map existing specialists to domains
3. Create delegation patterns
4. Document escalation rules

### Workstream C: Organization & Navigation
**Subagent**: Reorganize and index

Tasks:
1. Create `feature_dev_notes/` category structure
2. Move files to appropriate categories
3. Create `.claude/INDEX.md` for skills/subagents navigation
4. Update development roadmap with Phase 1/2 split

---

## Subagent Specifications

### Workstream A: Developer Commands Agent

```yaml
task: Create developer scaffolding slash commands
files_to_create:
  - .claude/commands/hms-new-skill.md
  - .claude/commands/hms-new-agent.md
  - .claude/commands/hms-docs.md
reference:
  - .claude/commands/hms-orient.md (format example)
  - .claude/skills/executing-hms-runs/SKILL.md (skill template)
  - .claude/subagents/basin-model-specialist.md (agent template)
```

### Workstream B: Orchestrator Agent

```yaml
task: Create hms-orchestrator subagent
file_to_create: .claude/subagents/hms-orchestrator.md
reference:
  - .claude/subagents/*.md (existing specialists)
  - .claude/skills/ (available skills)
content:
  - Task classification rules
  - Specialist routing table
  - Delegation patterns
  - When to handle directly vs delegate
```

### Workstream C: Organization Agent

```yaml
task: Reorganize feature_dev_notes and create navigation
files_to_create:
  - feature_dev_notes/INDEX.md
  - .claude/INDEX.md
files_to_reorganize:
  - feature_dev_notes/*.md → categorized subfolders
updates:
  - feature_dev_notes/DEVELOPMENT_ROADMAP.md (add Phase 0.5)
```

---

## Success Criteria

Phase 1 is complete when:

1. **Developer can scaffold**: `/hms-new-skill` and `/hms-new-agent` work
2. **Orchestrator routes correctly**: Task → appropriate specialist
3. **Navigation is clear**: INDEX.md files enable quick discovery
4. **Roadmap is unified**: Cognitive infrastructure integrated into plan
5. **Feature dev notes organized**: Clear category structure

---

## Phase 2 Preview (Deferred)

After Phase 1, these HMS-specific items become priority:

- `hms-calibration-analyst` subagent
- `hms-jython-engineer` subagent
- `calibration-metrics` skill
- `calibration-regions` skill
- KB generation system (moved to low priority)

---

## Notes

- Use Sonnet model for subagents (cost-effective for implementation)
- Subagents work in parallel for speed
- All work respects existing patterns (static classes, primary sources, etc.)
