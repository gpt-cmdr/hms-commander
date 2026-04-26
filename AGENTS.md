# hms-commander Agent Contract

This file is the canonical shared instruction contract for repository-local coding agents.

## Harness Loading

- Codex reads this file directly.
- Claude Code must import this file from the matching `CLAUDE.md`.
- The `AGENTS.md` hierarchy is the shared source of truth. Read the nearest file first, then inherit parent `AGENTS.md` files.
- `CLAUDE.md` files are loaders and Claude-specific adapters. They must not become a second documentation system.
- Shared rules belong in the `AGENTS.md` hierarchy or a shared skill corpus. Do not leave a rule that Codex also needs only in `.claude/rules/`.
- `.claude/rules/` is a Claude preload layer. It can restate or accelerate shared guidance, but it is not the canonical shared contract.
- `.claude/MANIFEST.md` is the Claude component registry. It is useful for discovery, but it is not the source of truth for shared behavior.
- `.claude/agents/` contains Claude-native delegation roles. Keep them thin and point them back to shared instructions.
- `.claude/settings.json` and `.codex/hooks.json` are thin hook adapters that call shared hook logic under `scripts/agent_hooks/`.
- Primary first-class harnesses in this repository are Claude Code and Codex.

## Current Codex Skill Status

- Codex auto-loads `AGENTS.md`.
- Codex skill discovery can be enabled locally by generating `.agents/skills/` links:
  - `python scripts/agent_framework/sync_codex_skill_bridge.py`
- The bridge links explicitly allowlisted shared-domain skills from `.claude/skills/` and Codex-native adapter skills from `.agents/native-skills/`.
- A shared skill must declare `shared_corpus: true`, `harness_scope: shared`, accepted `source_owner`, and accepted `security_review` metadata before the bridge exposes it to Codex.
- A Codex-native adapter skill must declare `shared_corpus: false`, `harness_scope: codex_only`, accepted `source_owner`, and accepted `security_review` metadata.
- Skills marked `shared_corpus: false` or `harness_scope: claude_only` are excluded.
- `.agents/skills/*` entries are generated symlinks or Windows junctions, not source files. Do not edit them directly.
- Shared skill sources remain `.claude/skills/` until a later migration changes that explicitly.
- Codex-only provider handoff skills, such as Claude Code QAQC invocation, live in `.agents/native-skills/`.
- Claude-only provider handoff skills, such as `dev_invoke_codex-cli`, live in `.claude/skills/` with `harness_scope: claude_only` so the Codex bridge excludes them.

## Recommended Harness Tools

- First-class harnesses for this repo are Claude Code and Codex.
- For Codex, use the repo's generated skill bridge before creating any copied skill tree.
- Codex may call Claude Code for independent QAQC through the Codex-native `dev_invoke_claude-code` adapter when the user explicitly requests Claude review.
- Claude may call Codex for independent QAQC through the Claude-native `dev_invoke_codex-cli` adapter when the user explicitly requests Codex review.
- For local browser inspection of docs or future UI work, Codex Browser Use is the only recommended browser plugin when available.
- For issue and PR workflows, GitHub's official CLI or MCP tooling is acceptable.
- Do not add generic agent-tool recommendation lists, Gemini, Context7, or copied parallel framework folders as repo-standard guidance.

## Agent Tool Supply Chain

- Agent-facing external tools, plugins, and skills should be written by `gpt-cmdr` or sourced from official Anthropic or OpenAI repositories.
- Treat third-party external plugins and skills from outside `gpt-cmdr`, Anthropic, or OpenAI as untrusted until audited.
- If a third-party plugin or skill is useful, audit it and re-implement the required behavior in this repository instead of linking to it as an external dependency.
- Do not make opaque third-party agent plugins, MCP servers, skills, or command wrappers part of the standard repo workflow.
- Gemini-related Claude components in this repository are legacy, explicit-request-only Claude-native compatibility entries. They are not part of the shared Claude+Codex standard.

## Project Overview

`hms-commander` is a Python library for automating HEC-HMS operations. It provides APIs for HEC-HMS project files, model component editing, simulation execution, DSS results, geospatial processing, and HMS-to-RAS workflows, following architectural patterns established by `ras-commander`.

Core areas:

- File operations: `HmsBasin`, `HmsMet`, `HmsControl`, `HmsGage`, `HmsRun`, `HmsGeo`
- Execution: `HmsCmdr`, `HmsJython`
- Data/results: `HmsDss`, `HmsResults`
- Utilities/examples: `HmsUtils`, `HmsExamples`, `HmsM3Model`
- AORC/HUC/grids: `HmsHuc`, `HmsAorc`, `HmsGrid`, `HmsDssGrid`
- Storm generation: `Atlas14Storm`, `FrequencyStorm`
- Project state: `HmsPrj`, `init_hms_project`, global `hms`

## Environment

- Default host context is Windows.
- Python requirement is 3.10+.
- Use `pathlib.Path` for path handling. Accept forward slashes and backslashes.
- Agent scripts and tools should prefer `uv` for installation and `python` for execution.
- User-facing documentation should show `pip` commands for broad compatibility.
- Fast local install: `uv pip install -e ".[all]"`
- Standard local install: `pip install -e .`
- Release validation install: `pip install hms-commander`
- Conda environments used by this project:
  - `hmscmdr_local` for editable local development
  - `hmscmdr_pip` for published-package validation
- HMS execution requires installed HEC-HMS. HMS 3.x is 32-bit and may require Python 2-compatible Jython script generation; HMS 4.x is the default Python 3 path.

## Repository Map

- `hms_commander/` - core library code. Read `hms_commander/AGENTS.md` before changing package code.
- `examples/` - notebooks and example workflows. Read `examples/AGENTS.md` before notebook or example work.
- `docs/` - MkDocs documentation source. Read `docs/AGENTS.md` before docs work.
- `tests/` - pytest tests and project fixtures. Read `tests/AGENTS.md` before test work.
- `.claude/` - Claude-native rules, skills, agents, commands, and manifests.
- `.agents/` - Codex-facing skill adapter layer and generated skill bridge.
- `.codex/` - Codex-native hook configuration only. Shared Codex instructions still live in `AGENTS.md`.
- `scripts/agent_hooks/` - shared cross-harness hook dispatcher used by Claude Code and Codex.
- `agent_tasks/` - long-running task coordination and worktree tracking.
- `feature_dev_notes/` - feature research and development notes.

## Working Rules

- Most `Hms*` classes are static namespaces. Do not instantiate them unless the API clearly requires an instance.
- Use `HmsFileParser` and existing parser utilities instead of ad hoc text manipulation when editing HMS ASCII files.
- Use real HEC-HMS projects, typically through `HmsExamples.extract_project()`. Do not default to mocks or synthetic datasets for domain validation.
- Keep original HMS project folders immutable when practical. Prefer clone workflows or separate working directories for experiments and QAQC.
- Preserve GUI-verifiable workflows: generated HMS artifacts should open cleanly in the HEC-HMS GUI when the feature affects model files.
- Always specify `hms_object` when an API supports multiple initialized HMS projects and ambiguity is possible.
- Handle encodings with UTF-8 and Latin-1 fallback where existing code expects it.
- Public API work should follow the repository logging pattern and existing decorators.
- Do not commit generated DSS files, HMS logs, extracted example projects, or local model outputs.

## HMS Domain Rules

- HMS project discovery starts from `.hms` project files, not RAS `.prj` files.
- HMS primary editable text files are `.hms`, `.basin`, `.met`, `.control`, `.gage`, and `.run`.
- HMS results are DSS-based. `hms-commander` uses `ras-commander` DSS infrastructure rather than duplicating DSS tooling.
- HMS 3.x projects need extra version awareness, especially for Python 2-compatible Jython execution.
- Clone workflows should be non-destructive, traceable, and side-by-side comparable in HEC-HMS.
- HMS-to-RAS workflows should hand off DSS file, pathname, outlet/spatial reference, time window, units, and validation notes.

## Notebooks And Docs

- Notebooks are reference material for humans. Extract repeatable logic into scripts or library APIs when it becomes core behavior.
- Prefer project examples via `HmsExamples.extract_project()` over absolute local paths.
- Replace notebook-only shell snippets with documented terminal commands where practical.
- Keep notebooks reproducible and free of credentials, local machine paths, and stale outputs.
- MkDocs documentation lives under `docs/`; update `mkdocs.yml` when adding public docs pages.

## Testing And Validation

- Use `pytest` for targeted tests.
- Prefer tests that touch real library behavior and real example project structures.
- Use `python -m pytest ...` or the active environment's equivalent command.
- Use `python -m mkdocs build --strict -q` for documentation validation when docs or navigation change.
- Execution tests that require installed HEC-HMS should be explicitly marked or isolated so they do not break basic CI/local validation.

## Coordination And Handoffs

- For multi-session tasks, use `agent_tasks/` and its `.agent/` state files when the task is large enough to need a durable handoff.
- If a task spans HMS and RAS repositories, document the request in markdown and keep the Python API layers independent.
- Claude Code to Codex handoffs may use `TASK.md` and `OUTPUT.md`; avoid overwriting root-level handoff files unless the active task owns them.

## Update Discipline

- If a rule matters to both Claude and Codex, update the relevant `AGENTS.md` file.
- If a change is Claude-only, keep it in `CLAUDE.md`, `.claude/rules/`, `.claude/agents/`, or `.claude/commands/` as appropriate.
- If a change is Codex-only, keep it in `.agents/native-skills/` or `.codex/` as appropriate.
- If you change the instruction architecture, also update `docs/development/multi-harness-agent-contract.md`.
