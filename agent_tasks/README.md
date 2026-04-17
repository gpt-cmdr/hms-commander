# Agent Tasks - Cognitive Backbone

This directory provides structured task templates and reusable workflows for hms-commander development.

**Philosophy**: "This becomes your cognitive backbone: subagents and skills can reference these tasks, and your slash commands can pull them into action quickly."

**Current shared workflow**: committed plan files in `agent_tasks/plans/` are the primary cross-session roadmap for major features, investigations, and refactors. The older `.agent/` memory files remain useful for personal scratch state, but they are optional and should not be treated as the only source of truth for work that spans commits or multiple agents.

**Cross-repo handoff rule**: land work where it is most generalizable. Keep reusable hydrology, TauDEM, GIS preprocessing, and HMS-facing workflow patterns in `hms-commander`; upstream reusable HEC-RAS primitives to `ras-commander`; keep region-specific product adaptation in sibling application repos such as `ras-agent`. When another repo needs a feature here, or this repo needs a feature elsewhere, the canonical request should be a GitHub issue in the target repository. Freeze region-specific prototype snapshots under `feature_dev_notes/completed/` when they are no longer the active target.

---

## Directory Structure

```
agent_tasks/
  README.md            # This file
  plans/               # Committed roadmap / investigation plans for major work
  templates/           # Task templates for common patterns
    bugfix.md          # Bug investigation and fix
    feature.md         # Feature implementation
    refactor.md        # Code improvement
    investigation.md   # Research and discovery
  tasks/               # Reusable task library (numbered)
    000-bootstrap.md
    010-env-setup.md
    020-run-simulation.md
    030-notebook-test.md
    040-atlas14-update.md
    ...
  runs/                # Execution logs (gitignored)
  artifacts/           # Generated outputs (gitignored)
  .agent/              # Session state (gitignored - ephemeral)
    STATE.md           # Current session state
    BACKLOG.md         # Task queue
    PROGRESS.md        # Chronological log
    CURRENT_STATUS.md  # Project status snapshot
    TASK_*.md          # Task-specific documentation
    LEARNINGS.md       # What works / doesn't work
```

---

## Current Repo Usage

### `plans/` - Shared, Committed Roadmap

Use `agent_tasks/plans/` for any work item that should survive sessions, conversations, and branch changes:
- major features (`HmsGui`, watershed delineation, version upgrades)
- research-backed investigations
- roadmap refreshes
- multi-step refactors where commit history alone is not enough

Recommended plan hygiene:
- one plan file per major initiative
- keep status current when commits land
- if a plan is fully implemented, mark it complete and move/archive it rather than silently reusing the same file for a different topic
- include the validating commit hash(es), notebook(s), or test file(s) that prove completion
- if the implementation work moves to another repository, mark the local plan as archived/completed-for-learning and point to the successor repo/plan explicitly

### `.agent/` - Optional Local Scratch State

Use `.agent/` only for transient local coordination:
- current focus
- short-lived backlog
- session notes that do not belong in git history

If information needs to be visible to other sessions, other agents, or future branch work, it belongs in `plans/`, `feature_dev_notes/`, or `.claude/outputs/` instead.

---

## Purpose

Complex tasks span multiple sessions. This system enables:
- **Reusable workflows** - Task library provides repeatable patterns
- **Session continuity** - Memory system tracks state across conversations
- **Progress tracking** - Know what's done, what remains
- **Human oversight** - Clear audit trail of work

## Getting Started

### Initialize .agent/ Directory (Optional)

The `.agent/` directory is gitignored (personal session state). Create it locally:

```bash
mkdir -p agent_tasks/.agent
```

Then create these files:

**STATE.md** - Current session state
```markdown
# Session State

**Current Focus**: [Your current task]
**Active Tasks**: [List of in-progress tasks]
**Blockers**: [Any blockers]
```

**BACKLOG.md** - Task queue
```markdown
# Task Backlog

## Priority
- [ ] Task 1
- [ ] Task 2

## Recently Completed
- [x] Task 0
```

**PROGRESS.md** - Chronological log
```markdown
# Progress Log

## 2025-MM-DD
- Started working on X
- Completed Y
```

### Task Numbering

- **000-050**: Generic templates and examples (committed to repo)
- **051+**: Personal tasks (create locally, not committed by default)

### Plan Naming

Plans in `plans/` should use descriptive filenames that match their contents (for example `hmsgui-jab-gui-automation.md`). Keep names stable once referenced elsewhere, but prefer clarity over generated slugs.

---

## Memory Files

### STATE.md - Current State

**Read at session start, update at session end.**

Contains:
- Current focus area
- Active tasks
- Blockers
- Quick context for new session

### PROGRESS.md - Progress Log

**Append at session end.**

Contains:
- Chronological entries by date
- What was accomplished
- Decisions made
- Notes for future sessions

### BACKLOG.md - Task Backlog

**Update as tasks are added/completed.**

Contains:
- Prioritized task list
- Cross-repo coordination items
- Recently completed items

### CURRENT_STATUS.md - Project Status Snapshot

**Update after major task completion.**

Contains:
- What was just completed
- Current state of codebase
- Immediate next steps
- Test results and validation status

Use for quick orientation at session start.

### TASK_*.md - Task-Specific Records

**Create for significant implementations.**

Contains:
- Task description and requirements
- Implementation approach
- Technical details and decisions
- Validation results
- Lessons learned

Use for detailed reference on specific implementations.

## Session Protocol

### Session Start

1. Read the relevant file in `plans/` for the active initiative
2. Check recent commits and tests that landed after the plan was written
3. Read `.agent/STATE.md` / `.agent/PROGRESS.md` only if local scratch context is needed
4. Summarize: what is complete, what is still active, and what evidence proves each claim

### Session End

1. Update the relevant `plans/` entry if roadmap status changed
2. Update `.agent/STATE.md` / `.agent/PROGRESS.md` if you are using local scratch memory
3. Move completed plan files out of the active set when the implementation is actually shipped

## Cross-Repository Coordination

See `cross-repo/README.md` for workflow involving ras-commander.

**Key Principle**: All handoffs require human-in-the-loop approval.

## Sibling Repository

| Repository | Local Path | Purpose |
|------------|------------|---------|
| hms-commander | `G:\GH\hms-commander` | HEC-HMS automation (this repo) |
| ras-commander | `G:\GH\ras-commander` | HEC-RAS automation (sibling) |

## See Also

- `feature_dev_notes/` - Feature-specific research and development
- `feature_dev_notes/CROSS_REPO_INTEGRATION_BLUEPRINT.md` - Integration architecture
- `.claude/` - Hierarchical knowledge system
