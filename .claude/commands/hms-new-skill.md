Scaffold a new skill for hms-commander following the existing skill structure.

## Skill Structure

```
.claude/skills/{skill_name}/
├── SKILL.md          # Main skill document (required)
├── examples/         # Working code examples (optional)
│   └── *.md
└── reference/        # Detailed API docs (optional)
    └── *.md
```

## Step 1: Create Skill Directory

```bash
mkdir .claude/skills/{skill_name}
```

## Step 2: Create SKILL.md

Use this template (see `hms_execute_runs/SKILL.md` for a full example):

```markdown
---
name: {skill_name}
description: |
  One paragraph description of what this skill does.
  Trigger keywords: key, terms, that, invoke, this, skill.
---

# {Skill Title}

## Quick Start

Minimal working example to accomplish the core task.

## Primary Sources

**Code (Authoritative API)**:
- `hms_commander/{MainClass}.py` — Complete docstrings

**Examples (Working Demonstrations)**:
- `examples/{NN_notebook}.ipynb` — Cells X-Y

**Rules (Patterns & Decisions)**:
- `.claude/rules/hec-hms/{relevant-rule}.md`

## When to Use This Skill

**Trigger Scenarios**:
- User says "..."
- User mentions "..."

## Core Capabilities

### Capability 1
Pattern description.

## Common Workflows

### Workflow 1: Title
```python
# Code example
```

## Troubleshooting

Common issues and solutions.

## Integration Points

**Before this skill**: What to do first
**After this skill**: What to do next

## Related Skills

- **other_skill** — Description
```

## Step 3: Add Examples (Optional)

Create `examples/` with markdown files showing real usage patterns.

## Step 4: Update INDEX.md

Add the new skill to `.claude/INDEX.md` "Active Skills" table:

```markdown
| **{skill_name}/** | Purpose description | trigger, keywords, here |
```

## Skill Naming Conventions

- Directory name: `snake_case` (e.g., `hms_execute_runs`)
- Main file: `SKILL.md` (always uppercase)
- Examples: `kebab-case.md` (e.g., `basic-run.md`)

## Reference

- Example full skill: `.claude/skills/hms_execute_runs/SKILL.md`
- Simpler skill: `.claude/skills/hms_clone_components/SKILL.md`
- Index: `.claude/INDEX.md` "Skills" section
