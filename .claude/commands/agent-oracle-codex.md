Invoke the Claude-native Codex oracle for explicit cross-harness QAQC or implementation delegation.

Use when the user specifically asks for Codex, Codex CLI, OpenAI Codex, or a Codex second-model review.

Default behavior:
- Use `.claude/skills/dev_invoke_codex-cli/SKILL.md`.
- Create a handoff under `agent_tasks/handoffs/codex/`.
- Run `codex exec` from the repository root.
- Use read-only sandboxing for QAQC and reviews.
- Allow edits only when the user explicitly requests Codex implementation or refactoring.

Do not use legacy `codex-wrapper` commands, personal plugin cache paths, or hardcoded local repository paths.

Expected output to the user:
- Summary of Codex's result
- Severity-ranked findings for reviews
- Files inspected or modified
- Validation performed
- Path to the handoff folder
