# Agent Instructions Guide

This page explains the repository instruction files used by AI-assisted development in HMS Commander.

## Current Contract

`AGENTS.md` is the shared source of truth for repository-local coding agents. It contains the durable project rules that both Claude Code and Codex must follow.

`CLAUDE.md` is now a thin Claude Code loader. It imports `AGENTS.md` and adds only Claude-specific adapter notes.

This split prevents drift between harnesses:

- Codex naturally reads `AGENTS.md`.
- Claude Code naturally reads `CLAUDE.md`, which immediately imports `AGENTS.md`.
- Shared rules are not copied into `.codex/` or duplicated across `.claude/`.

## File Responsibilities

```text
hms-commander/
├── AGENTS.md          <- canonical shared contract
├── CLAUDE.md          <- Claude loader that imports AGENTS.md
├── .claude/           <- Claude-native rules, agents, skills, commands
├── .agents/           <- Codex skill bridge and Codex-native adapter skills
├── .codex/            <- Codex hook/config adapters only
└── scripts/
    ├── agent_framework/
    └── agent_hooks/
```

## How Agents Should Load Context

### Codex

1. Read the nearest `AGENTS.md`.
2. Inherit parent `AGENTS.md` files.
3. Use generated `.agents/skills/` entries when the bridge has been generated.
4. Treat `.codex/` as project config only, not an instruction tree.

### Claude Code

1. Read `CLAUDE.md`.
2. Follow `@AGENTS.md`.
3. Use `.claude/MANIFEST.md` and `.claude/INDEX.md` for Claude-native discovery.
4. Treat `.claude/rules/` as preload helpers, not the shared source of truth.

## Updating Instructions

Update `AGENTS.md` when:

- a rule matters to both Claude Code and Codex
- package, docs, tests, or examples need scoped shared guidance
- harness boundaries or generated-file rules change

Update `CLAUDE.md` only when:

- Claude Code needs a loader note
- Claude-specific discovery behavior changes

Update `.claude/` when:

- adding Claude-native agents, commands, rules, or skills
- adding Claude-specific workflow acceleration

Update `.agents/` when:

- adding Codex-native adapter skills
- documenting the generated Codex skill bridge

Do not edit generated `.agents/skills/*` entries directly. Regenerate them with:

```bash
python scripts/agent_framework/sync_codex_skill_bridge.py
```

## Related Documentation

- [Multi-Harness Agent Contract](../development/multi-harness-agent-contract.md)
- [Contributing](contributing.md)
- [Cognitive Architecture](cognitive_architecture.md)
- [Style Guide](style_guide.md)
