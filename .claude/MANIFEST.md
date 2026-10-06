# .claude/ Component Manifest

Central registry for Claude-native components in `hms-commander`.

This file is the Claude-side discovery map only. Shared repository behavior lives in the `AGENTS.md` hierarchy, not in `.claude/`.

## Commander Entry Point

The shared `hms-commander` skill is the canonical intake workflow for both harnesses.
The Claude `hms-commander` role loads this skill. GIS uses current
hms2cng contracts; cross-model work routes to the existing HMS-RAS specialist and RAS guidance.
MCP queries are bounded informational subagent tasks; heavier work uses public Python APIs.

## HMS Domain Skills

| Component | Type | Path |
|-----------|------|------|
| `hms-cloud-native-gis` | shared skill | `.claude/skills/hms-cloud-native-gis/SKILL.md` |
| `hms-ras-integration` | shared skill | `.claude/skills/hms-ras-integration/SKILL.md` |
| `hms-commander` | shared skill | `.claude/skills/hms-commander/SKILL.md` |
| `hms-commander-contributing` | shared skill | `.claude/skills/hms-commander-contributing/SKILL.md` |
| `hms_execute_runs` | skill | `.claude/skills/hms_execute_runs/SKILL.md` |
| `hms_parse_basin-models` | skill | `.claude/skills/hms_parse_basin-models/SKILL.md` |
| `hms_update_met-models` | skill | `.claude/skills/hms_update_met-models/SKILL.md` |
| `hms_extract_dss-results` | skill | `.claude/skills/hms_extract_dss-results/SKILL.md` |
| `hms_clone_components` | skill | `.claude/skills/hms_clone_components/SKILL.md` |
| `hms_link_to-ras` | skill | `.claude/skills/hms_link_to-ras/SKILL.md` |
| `hms_export_cloud-native` | skill | `.claude/skills/hms_export_cloud-native/SKILL.md` |
| `hms_investigate_internals` | skill | `.claude/skills/hms_investigate_internals/SKILL.md` |
| `hms_query_docs` | skill | `.claude/skills/hms_query_docs/SKILL.md` |
| `hms_manage_versions` | skill | `.claude/skills/hms_manage_versions/SKILL.md` |

## Review and Standards Skills

| Component | Type | Path |
|-----------|------|------|
| `technical-writing-auditor` | shared skill | `.claude/skills/technical-writing-auditor/SKILL.md` |
| `api-consistency-auditor` | shared skill | `.claude/skills/api-consistency-auditor/SKILL.md` |

- Writing standards: `.claude/references/writing/technical-writing-guide.md` (concise) and `.claude/references/writing/technical-writing-standard.md` (extended); audit protocol in `.claude/skills/technical-writing-auditor/references/audit-protocol.md`.
- API rules and baseline: `.claude/skills/api-consistency-auditor/references/api-rules.md`; exceptions in root `.auditor.yaml`; report-only checker `.claude/skills/api-consistency-auditor/scripts/check_api_consistency.py`.
- Codex discovery: existing `sync_codex_skill_bridge.py` bridge. Scope: repository-maintained content and code only, never users' external work.

## Cross-Harness Adapter Skills

| Component | Type | Path |
|-----------|------|------|
| `dev_invoke_codex-cli` | Claude-only skill | `.claude/skills/dev_invoke_codex-cli/SKILL.md` |

## HMS Specialist Agents

| Component | Type | Path |
|-----------|------|------|
| `hms-commander` | Claude adapter | `.claude/agents/hms-commander.md` |
| `basin-model-specialist` | agent | `.claude/agents/basin-model-specialist.md` |
| `met-model-specialist` | agent | `.claude/agents/met-model-specialist.md` |
| `run-manager-specialist` | agent | `.claude/agents/run-manager-specialist.md` |
| `dss-integration-specialist` | agent | `.claude/agents/dss-integration-specialist.md` |
| `hms-ras-workflow-coordinator` | agent | `.claude/agents/hms-ras-workflow-coordinator.md` |
| `hms_atlas14` | production agent | `.claude/agents/hms_atlas14/AGENT.md` |
| `hms_decompiler` | production agent | `.claude/agents/hms_decompiler/AGENT.md` |
| `hms_doc_query` | production agent | `.claude/agents/hms_doc_query/AGENT.md` |
| `update_3_to_4` | production agent | `.claude/agents/update_3_to_4/AGENT.md` |

## Development Agents

| Component | Type | Path |
|-----------|------|------|
| `python-environment-manager` | agent | `.claude/agents/python-environment-manager.md` |
| `example-notebook-librarian` | agent | `.claude/agents/example-notebook-librarian.md` |
| `notebook-runner` | agent | `.claude/agents/notebook-runner.md` |
| `notebook-output-auditor` | agent | `.claude/agents/notebook-output-auditor.md` |
| `notebook-anomaly-spotter` | agent | `.claude/agents/notebook-anomaly-spotter.md` |
| `hierarchical-knowledge-curator` | agent | `.claude/agents/hierarchical-knowledge-curator.md` |
| `claude-code-guide` | agent | `.claude/agents/claude-code-guide.md` |
| `best-practice-extractor` | agent | `.claude/agents/best-practice-extractor.md` |
| `api-consistency-auditor` | Claude adapter | `.claude/agents/api-consistency-auditor.md` |

## Claude Commands

| Component | Type | Path |
|-----------|------|------|
| `hms-run` | command | `.claude/commands/hms-run.md` |
| `hms-calibrate` | command | `.claude/commands/hms-calibrate.md` |
| `hms-docs` | command | `.claude/commands/hms-docs.md` |
| `hms-new-agent` | command | `.claude/commands/hms-new-agent.md` |
| `hms-new-skill` | command | `.claude/commands/hms-new-skill.md` |
| `hms-orient` | command | `.claude/commands/hms-orient.md` |
| `hms-plot-dss` | command | `.claude/commands/hms-plot-dss.md` |
| `agent-oracle-codex` | command | `.claude/commands/agent-oracle-codex.md` |

## Rule Domains

| Domain | Path |
|--------|------|
| Python patterns | `.claude/rules/python/` |
| HEC-HMS knowledge | `.claude/rules/hec-hms/` |
| Testing | `.claude/rules/testing/` |
| Documentation | `.claude/rules/documentation/` |
| Integration | `.claude/rules/integration/` |
| Project organization | `.claude/rules/project/` |
| Workflow notes | `.claude/rules/workflow/` |

## Provider-Initiated Legacy Components

Some Claude-native provider orchestration entries, including Gemini-oriented command and agent files, remain for explicit user requests only. They are not part of the shared Claude+Codex contract and must not be exposed through the Codex skill bridge unless a future audited migration explicitly changes that.

## Portable package and release maintenance

The generated skills-only plugin is defined by `.claude/plugin/package.json` and assembled with `scripts/agent_framework/build_plugin.py`. Canonical sources remain `.claude/skills/`. The `hms-ras-workflow-coordinator` adapter and `hms_link_to-ras` skill route through `hms-ras-integration`.
