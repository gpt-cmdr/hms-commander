# Agent Memory System for HMS-Commander

This directory contains the agent memory and coordination system for multi-session development work on hms-commander.

## Quick Start

### Starting a New Session

1. **Read STATE.md** - Understand current project state
2. **Read PROGRESS.md** (last 2 sessions) - Get recent context
3. **Continue in-progress work** OR **Pick task from BACKLOG.md**
4. **Check CONSTITUTION.md** when making decisions
5. **Update STATE.md and PROGRESS.md** at session end

## File Descriptions

### STATE.md (READ FIRST)
Single source of truth for current project state:
- Last session number and health status (🟢🟡🔴)
- Current focus (what task is in-progress)
- Next up (prioritized tasks)
- Blockers (issues requiring user input)
- Quick context (2-3 sentences explaining where we are)

**Update frequency**: Every session end

### CONSTITUTION.md (Decision Guide)
Project identity, principles, and constraints:
- What hms-commander is and why it exists
- Core principles (mirror ras-commander, support multi-version, agent-first)
- Must/Must Not/Prefer constraints
- Quality bar ("done" criteria)
- Project-specific patterns and decision framework

**Update frequency**: Rarely (when principles change or new patterns established)

### BACKLOG.md (Task Queue)
All tasks organized by status and dependencies:
- Ready (no dependencies, can start now)
- Blocked (has dependencies, wait until unblocked)
- Completed (done, with session number)

Each task has: ID, title, description, complexity estimate

**Update frequency**: Every session (mark completed, add new tasks discovered)

### PROGRESS.md (Session Log)
Append-only log of all sessions:
- Goal for session
- What was completed
- What's in-progress
- Decisions made (with rationale)
- Handoff notes for next session (detailed, assume amnesia)

**Update frequency**: Every session end (append new entry)

### LEARNINGS.md (Pattern Library)
What works, what doesn't, and why:
- Patterns that work well (with examples)
- Anti-patterns to avoid (with why they fail)
- Project-specific discoveries
- Decision patterns

**Update frequency**: After completing tasks (capture lessons learned)

## Session Lifecycle

```
┌─────────────────────────────────────────────────────────┐
│                 SESSION LIFECYCLE                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  START (5%)          WORK (80%)         END (15%)      │
│  ─────               ────               ───             │
│  Read STATE          One task only      Update STATE   │
│  Read PROGRESS       Check CONSTITUTION Append PROGRESS│
│  Continue or         Commit often       Update BACKLOG │
│  pick new task       Log blockers       Write handoff  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Rules

### Always
- ✅ Continue in-progress work first (check STATE.md)
- ✅ Work on ONE task at a time
- ✅ Verify before marking complete
- ✅ Write detailed handoff notes (assume next session has amnesia)
- ✅ Update STATE.md health (🟢 Green = good, 🟡 Yellow = issues, 🔴 Red = blocked)

### Never
- ❌ Skip orientation (reading STATE.md and PROGRESS.md)
- ❌ End session without updating files
- ❌ Work on multiple tasks simultaneously
- ❌ Mark task complete without verification

## Task States

Tasks in BACKLOG.md move through these states:

1. **Ready** - No dependencies, can start now
2. **In-Progress** - Documented in STATE.md "Current Focus"
3. **Blocked** - Waiting on dependencies or user input
4. **Completed** - Verified working, marked with session number

## Health Status

STATE.md health indicator meanings:

- 🟢 **Green** - Project healthy, making good progress
- 🟡 **Yellow** - Minor issues, needs attention but not critical
- 🔴 **Red** - Blocked, critical issues, needs user intervention

## Integration with HMS-Commander

This memory system supports:

### Agent Workflows
Agent workflows (in `agents/` directory) use this system for:
- Session save/resume (long-running tasks)
- Change tracking (MODELING_LOG.md pattern)
- Quality verdicts (GREEN/YELLOW/RED)

### Code Development
Multi-session coding tasks use this system for:
- Tracking complex refactoring across sessions
- Documenting decisions and rationale
- Ensuring continuity after interruptions

### Documentation Work
Documentation reorganization uses this for:
- Maintaining consistent organization strategy
- Tracking which files moved where
- Documenting rationale for structure decisions

## Example Session

### Session Start
```bash
# 1. Read orientation files
cat .agent/STATE.md
cat .agent/PROGRESS.md | tail -50  # Last session's notes

# 2. Check if there's in-progress work
# If STATE.md shows task in-progress → continue it
# Otherwise → pick from BACKLOG.md "Ready" section

# 3. Start working
git checkout -b feature/task-id
```

### During Session
```python
# Work on the task
# Make incremental commits
# If blocked → document in STATE.md
# If making decisions → check CONSTITUTION.md
```

### Session End
```bash
# 1. Update STATE.md
#    - Set current focus to your task status
#    - Update health indicator
#    - Write 2-3 sentence quick context

# 2. Append to PROGRESS.md
#    - Document what you completed
#    - Document what's in-progress
#    - Write detailed handoff notes

# 3. Update BACKLOG.md
#    - Mark completed tasks
#    - Add newly discovered tasks

# 4. Commit everything
git add .agent/
git commit -m "Session N: [brief description]"
```

## Files NOT in This Directory

### Project Files
- Source code: `hms_commander/` directory
- Tests: `tests/` directory
- Examples: `examples/` directory
- Agent workflows: `agents/` directory

### Documentation
- User docs: Root directory (.md files)
- API reference: `docs/` directory
- Old/deprecated: `.old/` directory

## When to Use This System

### Use for
- ✅ Multi-session development work
- ✅ Complex refactoring spanning days
- ✅ Agent workflow development
- ✅ Documentation reorganization
- ✅ When you need to hand off to another session

### Don't Use for
- ❌ Quick one-session bug fixes
- ❌ Trivial changes
- ❌ Exploratory work with no deliverable

## Related Documentation

- **Agent Workflows**: See `agents/README.md`
- **Project Constitution**: See `CONSTITUTION.md` in this directory
- **Development Guidelines**: See `../CLAUDE.md`
- **Reorganization Plan**: See `../REORGANIZATION_PLAN.md`

## Questions?

If you're starting a new session and something is unclear:

1. Read STATE.md - Does it answer your question?
2. Read last session in PROGRESS.md - Is there context there?
3. Check CONSTITUTION.md - Is there a principle that applies?
4. Check LEARNINGS.md - Has this been encountered before?
5. Still unclear? Ask the user.

## Version

**System Version**: 1.0
**Initialized**: 2025-12-10
**Last Updated**: 2025-12-10
