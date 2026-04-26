# Claude Infrastructure

This directory contains Claude-native infrastructure for `hms-commander`. Shared repository policy lives in root `AGENTS.md`.

## Read Order

1. Root `CLAUDE.md`
2. Root `AGENTS.md`, imported by the Claude loader
3. `.claude/MANIFEST.md` for component discovery
4. `.claude/INDEX.md` for longer navigation
5. Specific rules, agents, skills, or commands needed for the task

## Main Files

- `CLAUDE.md` - Claude framework aggregation with `@` imports
- `MANIFEST.md` - Concise component registry
- `INDEX.md` - Extended navigation index
- `settings.json` - Tracked hook adapter
- `settings.local.json` - Ignored local-only Claude settings

## Directories

- `agents/` - Claude-native delegation roles
- `skills/` - Claude-native skills and shared-domain HMS skill sources
- `commands/` - Claude slash commands
- `rules/` - Claude preload layer for patterns and workflows

## Cross-Harness Notes

- Use `AGENTS.md` for rules that both Claude and Codex need.
- Use `.claude/skills/dev_invoke_codex-cli/` when the user explicitly asks Claude to invoke Codex.
- Do not add shared policy only under `.claude/`.
- Do not edit generated Codex bridge entries directly; regenerate them from source skills.

## Task Coordination

Durable task handoffs and multi-session coordination belong under `agent_tasks/`, not this directory. Historical files such as `STATE.md`, `PROGRESS.md`, `BACKLOG.md`, and `PRIORITIES.md` may remain here as legacy context, but new coordination should use `agent_tasks/`.
