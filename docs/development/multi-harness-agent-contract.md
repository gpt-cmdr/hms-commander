# Multi-Harness Agent Contract

This document records the accepted design for supporting Claude Code and Codex in the same repository without drifting into parallel instruction systems.

## Status

- Accepted for `hms-commander` on 2026-04-26.
- This document is the architectural record for the migration away from a Claude-first compatibility-wrapper model.

## Decision

The repository uses one shared instruction graph with harness-native entry points:

- `AGENTS.md` hierarchy = canonical shared contract
- `CLAUDE.md` hierarchy = Claude loaders and Claude-only notes
- `.claude/rules/` = Claude preload accelerators only
- `.claude/agents/` = Claude-native delegation roles
- `.claude/skills/dev_invoke_codex-cli/` = Claude-only Codex invocation adapter
- `.claude/MANIFEST.md` = Claude component registry
- `.agents/native-skills/` = Codex-native adapter skill sources
- `.agents/skills/` = generated Codex skill bridge
- `.codex/` = Codex-native hook configuration only
- `scripts/agent_hooks/` = shared hook implementation

## Why

Claude Code and Codex have different default discovery behavior:

- Codex automatically reads `AGENTS.md` files.
- Claude Code automatically reads `CLAUDE.md` files and `.claude/` infrastructure.

Trying to make both harnesses share one loader filename does not work. The durable shared layer is the `AGENTS.md` hierarchy. The only accepted duplication is loader-level duplication such as `CLAUDE.md` importing `AGENTS.md`.

## Design Principles

1. Shared rules live in `AGENTS.md` files, not only in `.claude/rules/`.
2. `CLAUDE.md` files stay small and import the matching `AGENTS.md`.
3. `.claude/rules/` can preload or accelerate Claude behavior, but they do not own shared policy.
4. `.claude/agents/` can stay Claude-native, but they should point back to shared instructions instead of becoming a second knowledge base.
5. No copied instruction trees for Codex.

## File Responsibilities

### Shared Contract

- `AGENTS.md`
- `hms_commander/AGENTS.md`
- `examples/AGENTS.md`
- `docs/AGENTS.md`
- `tests/AGENTS.md`

These files contain durable shared instructions that both Claude and Codex must follow.

### Claude Adapters

- `CLAUDE.md`
- subtree `CLAUDE.md` files
- `.claude/rules/`
- `.claude/agents/`
- `.claude/commands/`
- `.claude/MANIFEST.md`

These files exist because Claude has native discovery behavior that Codex does not share.

### Codex Adapters

- `.agents/README.md`
- `.agents/native-skills/`
- `.agents/skills/README.md`
- `.codex/config.toml`
- `.codex/hooks.json`

These files expose approved skill sources and hook adapters to Codex. They do not own shared project policy.

## Hooks

Hooks are the one place where both harnesses need native config files:

- Claude Code reads project hooks from `.claude/settings.json`.
- Codex reads project hooks from `.codex/hooks.json`, with `.codex/config.toml` enabling hook support for the project.

To avoid drift, these files stay as thin adapters. Shared hook behavior belongs in `scripts/agent_hooks/`, where it is implemented once in cross-platform Python and called by both harnesses.

Initial hook policy:

- inject a short session-start reminder that `AGENTS.md` is the shared contract
- block direct edits to generated `.agents/skills/` bridge entries
- block obvious destructive recursive deletion and hard reset commands

Hooks are guardrails, not a security boundary. Durable policy still belongs in `AGENTS.md`, code review, and explicit validation.

## Codex Skill Exposure

Codex skill auto-discovery is provided through a generated local bridge.

Reason:

- The current `.claude/skills/` corpus is useful to both Claude and Codex for HMS domain workflows.
- Generated symlinks or Windows junctions avoid tracked duplicate skill content.
- The bridge can fail closed and expose only skills with explicit metadata.

Implication:

- Codex uses the `AGENTS.md` hierarchy immediately.
- Codex can use native skill discovery after running `python scripts/agent_framework/sync_codex_skill_bridge.py`.
- `.agents/skills/*` entries are generated and ignored by git.
- Shared skill sources remain `.claude/skills/`.
- Codex-native provider handoff sources live in `.agents/native-skills/`.

Shared HMS skills must declare:

```yaml
shared_corpus: true
harness_scope: shared
source_owner: gpt-cmdr
security_review: internal
```

Codex-native adapter skills must declare:

```yaml
shared_corpus: false
harness_scope: codex_only
source_owner: gpt-cmdr
security_review: internal
```

Claude-native adapter skills must declare:

```yaml
shared_corpus: false
harness_scope: claude_only
source_owner: gpt-cmdr
security_review: internal
```

## Recommended Tool Policy

Recommended agent tooling must stay specific and first-party or strongly maintained:

- Claude Code is supported through `CLAUDE.md`, `.claude/agents/`, `.claude/skills/`, `.claude/rules/`, and `.claude/commands/`.
- Codex is supported through the `AGENTS.md` hierarchy and generated `.agents/skills/` bridge.
- Cross-harness QAQC is supported in both directions when explicitly requested.
- Claude-to-Codex QAQC uses `.claude/skills/dev_invoke_codex-cli/SKILL.md`, which is marked `harness_scope: claude_only`.
- Codex-to-Claude QAQC uses `.agents/native-skills/dev_invoke_claude-code/SKILL.md`, which is marked `harness_scope: codex_only`.
- Codex Browser Use may be recommended for local browser inspection of generated docs or future UI surfaces when it is available.
- GitHub's official CLI or MCP tooling may be recommended for repository issues, pull requests, and release work.

Do not add generic recommendation lists. Do not recommend Gemini, Context7, or a second copied agent-framework tree as part of this repository's standard setup.

## Supply Chain

Agent-facing external tools, plugins, and skills must follow the repository owner's supply-chain policy:

- Prefer components written and maintained by `gpt-cmdr` in this repository or sibling `gpt-cmdr` repositories.
- Official Anthropic or OpenAI repositories are acceptable upstream sources for harness-native plugins, skills, or examples.
- Third-party external plugins or skills from outside `gpt-cmdr`, Anthropic, or OpenAI must be treated as untrusted until reviewed.
- If a third-party component is useful, security-audit it and re-implement the needed behavior inside this repository rather than linking to it as an external plugin or skill dependency.

Gemini-related Claude components in this repository are legacy explicit-request-only compatibility entries and are not part of the shared Claude+Codex contract.

## Invariants

The repository should continue to satisfy these rules:

- A Codex session can follow the repo correctly by reading `AGENTS.md` files only.
- A Claude session can follow the repo correctly by reading `CLAUDE.md`, which imports the same `AGENTS.md` content.
- No shared rule exists only in `.claude/rules/`.
- No new copied instruction hierarchy is introduced for another harness.
- Shared architectural changes update this record.
