# HMS-Commander Documentation Index

Guide to the main documentation surfaces in the `hms-commander` repository.

## Quick Start For Users

1. `README.md` - Project overview and installation
2. `GETTING_STARTED.md` - First steps and basic usage
3. `QUICK_REFERENCE.md` - API quick reference with examples
4. `docs/user_guide/` - User-facing workflow documentation
5. `docs/api/` - Generated API reference pages

## Developer Documentation

### Shared Agent Contract

- `AGENTS.md` - Canonical shared repository contract for Claude Code, Codex, and future repository-local agents
- `CLAUDE.md` - Thin Claude loader that imports `AGENTS.md` and adds Claude-only notes
- `docs/development/multi-harness-agent-contract.md` - Architecture record for the shared Claude+Codex harness setup

Shared rules that both Claude and Codex need belong in the `AGENTS.md` hierarchy. Do not treat `CLAUDE.md` or `.claude/rules/` as the canonical shared policy tree.

### Package, Examples, Docs, And Tests

- `hms_commander/AGENTS.md` - Package/API rules before changing library code
- `examples/AGENTS.md` - Notebook and example workflow rules
- `docs/AGENTS.md` - MkDocs and documentation rules
- `tests/AGENTS.md` - Real-project test expectations

### LLM Forward Documentation

- `docs/llm_dev/claude_md.md` - How the current `AGENTS.md` + `CLAUDE.md` loading model works
- `docs/llm_dev/cognitive_architecture.md` - Repository agent architecture and harness layers
- `docs/llm_dev/contributing.md` - Contributor workflow for LLM-forward documentation

## Agent Infrastructure

### Claude-Native Infrastructure

- `.claude/MANIFEST.md` - Concise registry of Claude-native components
- `.claude/INDEX.md` - Longer navigation index for Claude agents, skills, commands, and rules
- `.claude/agents/` - Claude-native delegation roles
- `.claude/skills/` - Claude-native skill sources, including HMS shared-domain skill sources
- `.claude/commands/` - Claude slash command definitions
- `.claude/rules/` - Claude preload accelerators; shared policy still belongs in `AGENTS.md`

### Codex-Native Infrastructure

- `.agents/README.md` - Codex skill bridge overview
- `.agents/native-skills/` - Codex-only adapter skill sources
- `.agents/skills/README.md` - Warning and notes for the generated skill bridge
- `.agents/skills/*` - Generated links only; do not edit directly
- `.codex/config.toml` - Codex feature toggles
- `.codex/hooks.json` - Codex hook adapter

### Shared Hook And Bridge Scripts

- `scripts/agent_framework/sync_codex_skill_bridge.py` - Generates the Codex skill bridge from approved source skills
- `scripts/agent_hooks/hook_dispatch.py` - Shared hook dispatcher used by Claude Code and Codex
- `scripts/agent_hooks/README.md` - Hook behavior and smoke checks

## Documentation Structure

```text
hms-commander/
├── AGENTS.md                    # Canonical shared agent contract
├── CLAUDE.md                    # Claude loader
├── README.md                    # Project overview
├── GETTING_STARTED.md           # Quick start guide
├── QUICK_REFERENCE.md           # API quick reference
├── STYLE_GUIDE.md               # Code style and contribution guidance
├── .claude/                     # Claude-native infrastructure
├── .agents/                     # Codex skill adapter layer
├── .codex/                      # Codex hook/config adapters
├── scripts/
│   ├── agent_framework/         # Skill bridge scripts
│   └── agent_hooks/             # Shared hook implementation
├── hms_commander/               # Library source
├── examples/                    # Notebooks and workflows
├── tests/                       # Test suite and HMS fixtures
└── docs/                        # MkDocs source
```

## Documentation Maintenance

| Document | Update Trigger |
|----------|----------------|
| `README.md` | Major feature additions or installation changes |
| `GETTING_STARTED.md` | Basic workflow changes |
| `QUICK_REFERENCE.md` | Public API additions or signature changes |
| `AGENTS.md` | Shared agent policy or repository workflow changes |
| `CLAUDE.md` | Claude-only loader or adapter changes |
| `docs/development/multi-harness-agent-contract.md` | Instruction architecture changes |
| `.claude/MANIFEST.md` | Claude component additions, removals, or renamed paths |

## Documentation Principles

1. `AGENTS.md` is the shared source of truth for agent behavior.
2. `CLAUDE.md` is a loader, not the complete development guide.
3. `.claude/` accelerates Claude Code but does not own shared policy.
4. `.agents/skills/` is generated and must not be edited directly.
5. Public documentation should point to current paths, not archived `agents/` or `.agent/` layouts.
6. Superseded internal notes should move to `.old/` or `feature_dev_notes/` when appropriate.

## Finding What You Need

**Get started with hms-commander**:
Read `README.md`, then `GETTING_STARTED.md`.

**Find a specific API method**:
Use `QUICK_REFERENCE.md` for quick lookup or `docs/api/` for generated reference.

**Understand the agent contract**:
Read `AGENTS.md`, then `docs/development/multi-harness-agent-contract.md`.

**Maintain Claude-native components**:
Use `.claude/MANIFEST.md` first, then `.claude/INDEX.md` for navigation.

**Maintain Codex skill exposure**:
Edit source skills only, then run `python scripts/agent_framework/sync_codex_skill_bridge.py`.

**Continue multi-session work**:
Use `agent_tasks/` and the task-specific handoff files owned by the active work.

## Version

**Index Version**: 2.0
**Created**: 2025-12-10
**Last Updated**: 2026-04-26
