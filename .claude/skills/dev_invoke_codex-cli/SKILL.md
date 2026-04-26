---
name: dev_invoke_codex-cli
description: |
  Claude-native adapter for invoking OpenAI Codex CLI through markdown handoff files. Use when Claude Code needs an explicit Codex QAQC review, Codex code review, cross-harness verification, implementation pass, refactoring pass, or second-model opinion. Default to read-only review unless the user explicitly asks Codex to edit files. Uses current `codex exec` commands, repository-local paths, and TASK.md/OUTPUT.md artifacts under `agent_tasks/handoffs/codex/`.
shared_corpus: false
harness_scope: claude_only
source_owner: gpt-cmdr
security_review: internal
---

# Invoke Codex CLI

Claude-only adapter for delegating to Codex CLI. This skill is excluded from the generated Codex skill bridge by `harness_scope: claude_only`.

## Default Workflow

1. Create a handoff folder under `agent_tasks/handoffs/codex/<yyyymmdd-hhmmss-topic>/`.
2. Write `TASK.md` with the objective, repo context, files to inspect, constraints, and required output format.
3. Invoke Codex with `codex exec` from the repository root.
4. Ask Codex to write its final response to `OUTPUT.md` in the handoff folder.
5. Read `OUTPUT.md`, verify any claimed changes, and summarize the result to the user.

Do not overwrite root-level `TASK.md` or `OUTPUT.md` unless the active task explicitly owns those files.

## Read-Only QAQC Invocation

Use this for reviews, verification, or second-model opinions:

```powershell
$handoff = "agent_tasks/handoffs/codex/20260426-120000-qaqc"
New-Item -ItemType Directory -Force -Path $handoff | Out-Null

codex exec -C . `
  --ignore-user-config `
  --disable plugins `
  --disable general_analytics `
  --sandbox read-only `
  --ephemeral `
  --output-last-message "$handoff/OUTPUT.md" `
  --color never `
  "Read $handoff/TASK.md. Perform the requested read-only review. Do not edit files. Write the complete result to $handoff/OUTPUT.md."
```

## Implementation Invocation

Use this only when the user explicitly asks Claude to delegate file edits to Codex:

```powershell
$handoff = "agent_tasks/handoffs/codex/20260426-120000-implementation"
New-Item -ItemType Directory -Force -Path $handoff | Out-Null

codex exec -C . `
  --ignore-user-config `
  --disable plugins `
  --disable general_analytics `
  --full-auto `
  --skip-git-repo-check `
  --output-last-message "$handoff/OUTPUT.md" `
  --color never `
  "Read $handoff/TASK.md. Follow the instructions exactly. Write deliverables and changed-file notes to $handoff/OUTPUT.md."
```

## TASK.md Template

```markdown
# Task: <brief title>

## Objective
<one clear result>

## Context
- Repository: hms-commander
- Canonical shared instructions: AGENTS.md
- Relevant files:
  - `path/to/file`

## Instructions
1. <specific instruction>
2. <specific instruction>

## Constraints
- Default to read-only unless this task explicitly authorizes edits.
- Do not edit generated Codex skill bridge entries.
- Do not run destructive git or filesystem commands.
- Preserve unrelated user changes.

## Deliverables
Write to `OUTPUT.md`:
- Summary
- Findings or changes
- Files inspected or modified
- Validation performed
- Residual risks
```

## Notes

- Prefer repository-relative paths in prompts and handoff files.
- Use `--ignore-user-config --disable plugins --disable general_analytics` when the goal is project-local validation and global Codex plugins may add noise.
- Remove those isolation flags only when the user explicitly needs global Codex plugins or personal config.
- If Codex fails to start, report the exact CLI error and do not infer results.
