# Agent Instructions

This repository follows **Claude Code** conventions for agents, rules, and skills.

**Non-Claude agents**: Import `CLAUDE.md` for project instructions and context.

## Key Paths

| Resource | Path |
|----------|------|
| **Primary Instructions** | `CLAUDE.md` |
| **Hierarchical Knowledge** | `.claude/CLAUDE.md` |
| **Agents** | `.claude/agents/` |
| **Skills** | `.claude/skills/` |
| **Rules** | `.claude/rules/` |
| **Commands** | `.claude/commands/` |

## Naming Conventions

- **Agents**: `python_case/` folders or `kebab-case.md` files
- **Skills**: `kebab-case/` folders with `SKILL.md`
- **Rules**: `kebab-case.md` files by domain
