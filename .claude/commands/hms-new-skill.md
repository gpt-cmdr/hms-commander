# HMS New Skill

You are helping a developer scaffold a new skill for hms-commander.

## What This Command Does

Creates a complete skill folder structure with:
- `SKILL.md` main file (with proper template)
- `examples/` folder for workflow examples
- `reference/` folder for detailed API docs
- `scripts/` folder for helper scripts

## Interactive Prompts

Ask the user for:

1. **Skill name** (kebab-case, e.g., "calibration-metrics")
   - Validate: Must be kebab-case, no spaces, lowercase
   - Example: "calibration-metrics", "dss-time-series", "spatial-analysis"

2. **Skill description** (one-line summary)
   - Used in YAML frontmatter
   - Should be concise but descriptive
   - Example: "Extract and analyze calibration statistics from HMS simulation results"

3. **Trigger keywords** (comma-separated)
   - When should Claude activate this skill?
   - Example: "calibration, Nash-Sutcliffe, RMSE, goodness of fit, observed vs simulated"

4. **Primary API classes** (comma-separated, optional)
   - Which hms_commander classes does this skill use?
   - Example: "HmsDss, HmsResults, HmsBasin"
   - Leave blank if not applicable

## Template Structure

Read `.claude/skills/executing-hms-runs/SKILL.md` for reference format.

### SKILL.md Template

```markdown
---
name: {skill-name}
description: |
  {description}
  Trigger keywords: {keywords}
---

# {Skill Title}

## Quick Start

```python
from hms_commander import {primary_classes}

# Example code here
```

## Primary Sources

**Code (Authoritative API)**:
- `hms_commander/{Class}.py` - Complete docstrings for {primary functionality}

**Examples (Working Demonstrations)**:
- `examples/{relevant_notebook}.ipynb` - Complete workflow

**Rules (Patterns & Decisions)**:
- `.claude/rules/hec-hms/{relevant_rule}.md` - {Specific pattern}

## When to Use This Skill

**Trigger Scenarios**:
- User says "{trigger phrase 1}"
- User says "{trigger phrase 2}"
- User mentions "{keyword}"
- Working with {specific HMS component}

## Core Capabilities

### 1. {Capability Name}

**Pattern**: {Pattern description}

See `reference/{detail_file}.md` for complete API details.

**Key Decision**: {Important decision point}
- {Option 1}: {When to use}
- {Option 2}: {When to use}

### 2. {Another Capability}

**Pattern**: {Pattern description}

See `reference/{detail_file}.md` for details.

## Common Workflows

### Workflow 1: {Workflow Name}

```python
# Example code
```

**See**: `examples/{example_file}.md` for complete walkthrough

### Workflow 2: {Another Workflow}

```python
# Example code
```

**See**: `examples/{example_file}.md` for details

## Troubleshooting

**Common Issues**:

1. **{Issue Name}**: See `reference/{file}.md#{section}`
2. **{Another Issue}**: See `reference/{file}.md#{section}`

## Integration Points

**Before This Skill**:
- Use {prerequisite skill/class} to {prerequisite action}

**After This Skill**:
- Use {follow-up skill/class} to {follow-up action}

## Reference Files

**Detailed API Documentation** (load on-demand):
- `reference/{file1}.md` - {Description}
- `reference/{file2}.md` - {Description}

**Complete Examples** (working code):
- `examples/{example1}.md` - {Description}
- `examples/{example2}.md` - {Description}

## Testing This Skill

Use real HMS projects for testing:

```python
from hms_commander import HmsExamples

# Extract example project
HmsExamples.extract_project("{project_name}")

# Test skill
# ... test code ...
```

**See**: `.claude/rules/testing/tdd-approach.md` for testing philosophy

## Key Patterns (Not in Primary Sources)

### Pattern 1: {Pattern Name}

{Description of pattern}

**Decision**: {Why this pattern}

### Pattern 2: {Another Pattern}

{Description of pattern}

**Decision**: {Why this pattern}

## Related Skills

- **{related-skill-1}** - {Brief description}
- **{related-skill-2}** - {Brief description}

---

**Navigation**: This skill points to primary sources. For complete API details, read the code docstrings in `hms_commander/{Class}.py`.
```

## Folder Structure to Create

```
.claude/skills/{skill-name}/
├── SKILL.md                    # Main skill file (created from template)
├── examples/                   # Empty folder for workflow examples
│   └── .gitkeep               # Ensure folder is tracked
├── reference/                  # Empty folder for detailed API docs
│   └── .gitkeep               # Ensure folder is tracked
└── scripts/                    # Empty folder for helper scripts
    └── .gitkeep               # Ensure folder is tracked
```

## Execution Steps

1. Prompt user for inputs (name, description, keywords, API classes)
2. Validate skill name (kebab-case)
3. Create skill folder: `.claude/skills/{skill-name}/`
4. Create subfolders: `examples/`, `reference/`, `scripts/`
5. Create `.gitkeep` files in each subfolder
6. Generate `SKILL.md` from template with user inputs
7. Confirm creation with summary

## After Creation

Tell the user:

```
✓ Skill created: .claude/skills/{skill-name}/

Next steps:
1. Fill in SKILL.md sections with specific workflows
2. Add reference docs to reference/ folder
3. Add example workflows to examples/ folder
4. Update .claude/CLAUDE.md if this is a core skill

Related files to read:
- .claude/skills/executing-hms-runs/SKILL.md - Example of complete skill
- .claude/rules/testing/tdd-approach.md - Testing philosophy
- hms_commander/{PrimaryClass}.py - API to document
```

## Validation Rules

**Skill Name**:
- Must be kebab-case (lowercase with hyphens)
- No spaces, underscores, or special characters
- Should be descriptive (2-4 words typical)

**Examples**:
- ✅ `calibration-metrics`
- ✅ `dss-time-series`
- ✅ `spatial-analysis`
- ❌ `CalibrationMetrics` (not kebab-case)
- ❌ `calibration_metrics` (underscore, not hyphen)
- ❌ `cal` (too short, not descriptive)

## Notes

- Skills are task-specific workflows, not comprehensive documentation
- Skills point to primary sources (code, examples) rather than duplicating them
- Skills document patterns, decisions, and navigation
- Reference files in `reference/` folder contain detailed API docs (loaded on-demand)
- Example files in `examples/` folder contain complete working code
