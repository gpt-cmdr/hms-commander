# Subagent Markdown Output Pattern

**Context**: Design pattern for subagent knowledge persistence
**Priority**: Critical - ensures knowledge survival across sessions
**Auto-loads**: Yes (all agents)

## Core Principles

### Principle 1: Subagents Write Files, Return Paths

**Always write markdown files and return the file path to the main agent for reading.**

This guarantees:
1. **Knowledge Persistence** - Outputs survive session boundaries
2. **Filterable Results** - Main agent can selectively read relevant sections
3. **Consolidation Path** - Hierarchical knowledge agent can organize and prune
4. **Audit Trail** - Work products are reviewable and traceable
5. **Non-Destructive Lifecycle** - Files move to `.old/` when outdated, never deleted

### Principle 2: Orchestrator Passes Context via File Paths

**Pass context to subagents via markdown file paths (relative paths), never raw text.**

This guarantees:
1. **Context Availability** - Subagent reads files, gets full context
2. **No Prompt Bloat** - Large context doesn't inflate prompts
3. **Reusable Context** - Same context files work across multiple subagent calls
4. **Traceable Handoffs** - Clear record of what context was provided

**Path Format**: Always use relative paths from repository root:
- `agent_tasks/.agent/STATE.md`
- `.claude/outputs/hms-gui/analysis.md`
- never absolute repository paths in prompts

## The Pattern

### Subagent Workflow

1. Subagent receives task from the main agent
2. Subagent performs research, analysis, or implementation work
3. Subagent writes markdown file(s) with results
4. Subagent returns file path(s) to the main agent
5. Main agent reads file(s) as needed
6. Knowledge persists for future sessions

### Output Location

Write working outputs to `.claude/outputs/` or a task-specific directory:

```
.claude/outputs/
├── {subagent-name}/
│   ├── {task-id}-{description}.md
│   ├── {date}-{topic}.md
│   └── summary-{topic}.md
```

Alternative locations:
- `agent_tasks/.agent/` for local multi-session coordination
- `feature_dev_notes/` for feature-specific research
- task-specific directories when explicitly instructed

### Structured Output Template

Use this structure in subagent markdown outputs:

```markdown
# {Task Title}

**Subagent**: {subagent-name}
**Date**: {YYYY-MM-DD}
**Task ID**: {optional-task-reference}

## Summary
{2-3 sentence executive summary}

## Findings
{Detailed findings, organized by topic}

## Recommendations
{Actionable recommendations if applicable}

## Data/Evidence
{Supporting data, file references, or code snippets}

## Next Steps
{Suggested follow-up actions}
```

## Knowledge Lifecycle

### Active -> Old -> Delete

1. **Active**
   `.claude/outputs/{subagent}/{file}.md`
2. **Outdated**
   `.old/{file}.md`
3. **Recommend Delete**
   `.old/recommend_to_delete/{file}.md`
4. **Deleted**
   user decision only

### Cleanup Model

**At task close**:
- consolidate related findings
- extract durable knowledge to rules, skills, or plans
- move clearly outdated scratch outputs to `.old/`

**During periodic cleanup**:
- apply conservative judgment
- flag uncertain files instead of deleting

## Benefits

- knowledge survives context-window resets
- outputs are readable and auditable
- main agents can load only the parts they need
- hierarchical knowledge agents have a clear consolidation path

## Anti-Patterns

### Wrong

- returning large unpersisted text blobs
- not writing files at all
- scattering outputs in ad-hoc locations
- overwriting prior analysis without versioning

### Correct

- write a dated markdown artifact
- return the relative path
- let the main agent read and consolidate from there

## Cross-References

- `.claude/rules/documentation/hierarchical-knowledge-best-practices.md`
- `.claude/agents/hierarchical-knowledge-curator.md`
- `agent_tasks/README.md`
