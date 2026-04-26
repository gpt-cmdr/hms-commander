# Agent Hooks

This directory contains shared hook behavior for Claude Code and Codex.

Native harness configuration lives in:

- `.claude/settings.json`
- `.codex/hooks.json`
- `.codex/config.toml`

Those files are thin adapters. They call `hook_dispatch.py`, which owns the shared policy:

- add session-start context that `AGENTS.md` is the shared contract
- block direct edits to generated `.agents/skills/` bridge entries
- block obvious destructive commands such as `git reset --hard`, forced directory `git clean`, and recursive forced deletion

Hooks are guardrails, not a security boundary. Durable policy belongs in `AGENTS.md`, review, and validation.

## Smoke Tests

```powershell
'{"hook_event_name":"SessionStart"}' | python scripts\agent_hooks\hook_dispatch.py SessionStart
'{"tool_name":"shell_command","tool_input":{"command":"git reset --hard"}}' | python scripts\agent_hooks\hook_dispatch.py PreToolUse
'{"tool_name":"apply_patch","tool_input":{"path":".agents/skills/hms_execute_runs/SKILL.md"}}' | python scripts\agent_hooks\hook_dispatch.py PreToolUse
```
