# Documentation Instructions

This directory contains the MkDocs documentation source.

## Docs Rules

- Keep user-facing documentation accurate for pip-based users, even when agent workflows use `uv`.
- Update `mkdocs.yml` navigation when adding, moving, or deleting pages.
- Do not describe `CLAUDE.md` as the shared source of truth. `AGENTS.md` is the shared contract; `CLAUDE.md` is a Claude loader.
- Keep LLM development docs clear about harness boundaries: `.claude/` is Claude-native, `.agents/` is Codex-facing, and `.codex/` is Codex project config.
- Avoid documenting generated `.agents/skills/` entries as editable source.

## Validation

- Run `python -m mkdocs build --strict -q` after documentation or navigation changes.
- Keep internal links relative and valid.
