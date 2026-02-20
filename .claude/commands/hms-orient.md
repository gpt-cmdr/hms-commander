Orient yourself to the current hms-commander project. Read these files in order to understand context quickly:

## Orientation Sequence

1. **Read `agent_tasks/.agent/STATE.md`** — Current project state, active tasks, blockers
2. **Read `agent_tasks/.agent/BACKLOG.md`** (first 50 lines) — Task queue and priorities
3. **Read `.claude/INDEX.md`** — Framework navigation (agents, skills, commands, rules)
4. **Read `QUICK_REFERENCE.md`** (root) — Common operations quick reference

## Project Structure Summary

```
hms-commander/
├── hms_commander/          # Python library (AUTHORITATIVE source)
├── hms_agents/             # Production automation agents
├── examples/               # Jupyter notebook demonstrations
├── tests/                  # Test suite with real HMS projects
├── agent_tasks/            # Task coordination system
│   └── .agent/             # Session state (STATE.md, BACKLOG.md, PROGRESS.md)
└── .claude/                # Cognitive framework
    ├── agents/             # Specialist domain experts
    ├── skills/             # Task-specific workflows
    ├── commands/           # This directory
    └── rules/              # Patterns and guidelines
```

## Key Questions to Answer During Orientation

- What is the current active task? (STATE.md)
- What are the immediate priorities? (BACKLOG.md)
- Are there any blockers? (STATE.md)
- What was accomplished last session? (PROGRESS.md)

## After Orientation

Report back to user with:
- Current project status (GREEN/YELLOW/RED)
- Active task (if any)
- Top 3 next priorities
- Any blockers requiring user input
