# Agent Tasks - Cognitive Backbone

This directory provides structured task templates and reusable workflows for hms-commander development.

**Philosophy**: "This becomes your cognitive backbone: subagents and skills can reference these tasks, and your slash commands can pull them into action quickly."

---

## Directory Structure

```
agent_tasks/
  README.md            # This file
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
  .agent/              # Memory system (committed)
    STATE.md           # Current session state
    BACKLOG.md         # Task queue
    PROGRESS.md        # Chronological log
    LEARNINGS.md       # What works / doesn't work
    COGNITIVE_INFRASTRUCTURE_INSIGHTS.md  # Pattern documentation
```

---

## Purpose

Complex tasks span multiple sessions. This system enables:
- **Reusable workflows** - Task library provides repeatable patterns
- **Session continuity** - Memory system tracks state across conversations
- **Progress tracking** - Know what's done, what remains
- **Human oversight** - Clear audit trail of work

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

## Session Protocol

### Session Start

1. Read `.agent/STATE.md` - Current state
2. Read `.agent/PROGRESS.md` (last 3 entries) - Recent history
3. Read `.agent/BACKLOG.md` - Pending work
4. Summarize: "Last session worked on X, completed Y, pending Z"

### Session End

1. Update `.agent/STATE.md` with current status
2. Append to `.agent/PROGRESS.md` with accomplishments
3. Update `.agent/BACKLOG.md` with remaining items

## Cross-Repository Coordination

See `cross-repo/README.md` for workflow involving ras-commander.

**Key Principle**: All handoffs require human-in-the-loop approval.

## Sibling Repository

| Repository | Local Path | Purpose |
|------------|------------|---------|
| hms-commander | `C:\GH\hms-commander` | HEC-HMS automation (this repo) |
| ras-commander | `C:\GH\ras-commander` | HEC-RAS automation (sibling) |

## See Also

- `feature_dev_notes/` - Feature-specific research and development
- `feature_dev_notes/CROSS_REPO_INTEGRATION_BLUEPRINT.md` - Integration architecture
- `.claude/` - Hierarchical knowledge system
