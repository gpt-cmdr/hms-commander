Scaffold a new agent for hms-commander using the two-tier architecture.

## Step 1: Decide Agent Type

**Specialist Agent** (lightweight, `.claude/agents/`):
- Single `.md` file
- Domain expert using hms-commander library APIs
- Claude Code framework-integrated
- Use when: focused domain expertise, uses existing hms-commander code

**Production Agent** (`.claude/agents/{name}/` folder):
- Full folder with scripts, knowledge, tools
- Complete self-contained automation workflow
- Use when: multi-step workflow, external tools, production deployment

## Step 2a: Create Specialist Agent

Create `.claude/agents/{kebab-case-name}.md`:

```markdown
---
name: {agent-name}
description: |
  One paragraph describing this agent's domain expertise and when to use it.
  Trigger keywords: key, terms, that, invoke, this, agent.
skills:
  - hms_execute_runs
  - hms_parse_basin-models
rules:
  - .claude/rules/hec-hms/execution.md
---

# {Agent Name} Specialist

## Domain Expertise

What this agent knows about.

## When to Use This Agent

- Trigger scenario 1
- Trigger scenario 2

## Capabilities

### Capability 1
...

## Integration Points

**Input from**: Other agent or user
**Output to**: Other agent or file
```

## Step 2b: Create Production Agent

```bash
mkdir .claude/agents/{python_case_name}/
```

Create `.claude/agents/{python_case_name}/AGENT.md`:

```markdown
# {Agent Name}

## Purpose
One sentence description.

## Capabilities
- Capability 1
- Capability 2

## Usage
How to invoke this agent.

## Acceptance Criteria
- GREEN: All checks pass
- YELLOW: Minor issues
- RED: Critical failure

## File Structure
- AGENT.md — This file
- workflow.py — Main workflow script
- knowledge/ — Domain knowledge files
```

## Step 3: Update INDEX.md

Add the new agent to `.claude/INDEX.md` in the appropriate section:
- Specialist agents: "Active HMS Domain Specialists" table
- Development agents: "Active Development Agents" table
- Production agents: `.claude/agents/README.md`

## Naming Conventions

| Type | Location | Naming |
|------|----------|--------|
| Specialist | `.claude/agents/` | `kebab-case.md` |
| Production | `.claude/agents/` | `python_case/` (folder) |

## Reference

- Architecture: `.claude/CLAUDE.md` "Agent Naming Conventions"
- Examples: `.claude/agents/basin-model-specialist.md`
- Production example: `.claude/agents/update_3_to_4/AGENT.md`
