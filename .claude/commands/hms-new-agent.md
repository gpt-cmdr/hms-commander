# HMS New Agent

You are helping a developer scaffold a new specialist subagent for hms-commander.

## What This Command Does

Creates a new specialist agent file in `.claude/agents/` with:
- YAML frontmatter (name, description, model, tools, skills)
- Markdown sections documenting domain expertise
- Proper integration with hms-commander architecture

## Agent Types

**This command creates SPECIALIST AGENTS** (not production agents).

| Type | Location | Format | Naming | Purpose |
|------|----------|--------|--------|---------|
| Specialist Agent | `.claude/agents/` | Single `.md` file | `kebab-case.md` | Domain expertise using library APIs |
| Production Agent | `hms_agents/` | Folder structure | `python_case/` | Complete automation workflows |

**See**: `.claude/CLAUDE.md` for agent architecture overview.

## Interactive Prompts

Ask the user for:

1. **Agent name** (kebab-case, e.g., "control-spec-specialist")
   - Validate: Must be kebab-case, no spaces, lowercase
   - Should end with "-specialist" for consistency
   - Example: "basin-model-specialist", "met-model-specialist", "dss-integration-specialist"

2. **Domain description** (2-3 sentences)
   - What does this agent specialize in?
   - What HMS components does it handle?
   - Example: "Expert in HEC-HMS basin model files (.basin). Handles subbasins, junctions, reaches, loss methods, transform methods, baseflow parameters, and routing coefficients."

3. **Primary API class** (e.g., "HmsBasin", "HmsMet", "HmsControl")
   - Which hms_commander class is this agent's focus?
   - Example: "HmsBasin", "HmsMet", "HmsControl", "HmsDss"

4. **Tools needed** (comma-separated, default: "Read, Grep, Glob, Edit")
   - Which Claude Code tools should this agent have?
   - Common: Read, Grep, Glob, Edit, Write, Bash
   - Most agents need: Read, Grep, Glob, Edit

5. **Skills available** (comma-separated, optional)
   - Which skills can this agent activate?
   - Example: "parsing-basin-models, cloning-hms-components"
   - Leave blank if none

6. **Trigger keywords** (comma-separated)
   - When should this agent be engaged?
   - Example: "basin file, subbasin, junction, curve number, loss method"

## Template Structure

Read `.claude/agents/basin-model-specialist.md` for reference format.

### Subagent File Template

```markdown
---
name: {agent-name}
description: |
  {domain_description} Use when {trigger scenarios}. Understands {key concepts}.
  Keywords: {keywords}
model: sonnet
tools: {tools_list}
skills: {skills_list}
working_directory: hms_commander/
---

# {Agent Title} Subagent

You are an expert in {domain area}.

## Automatic Context Inheritance

When working in `hms_commander/`, you automatically inherit:
1. **Root CLAUDE.md** - Strategic overview, static class pattern
2. **hms_commander/CLAUDE.md** - Library patterns (if exists)
3. **.claude/rules/hec-hms/{relevant_rule}.md** - Domain-specific patterns
4. **.claude/rules/hec-hms/clone-workflows.md** - CLB Engineering approach (if applicable)

## Domain Expertise

### Primary API

**Class**: `{PrimaryClass}` (static methods, no instantiation)
**Location**: `hms_commander/{PrimaryClass}.py`

**Core Operations**:
- `{method1}()` - {Brief description}
- `{method2}()` - {Brief description}
- `{method3}()` - {Brief description}

**See**: Read `hms_commander/{PrimaryClass}.py` docstrings for complete API.

### {Domain Concept 1}

{Description of key domain concept}

**Methods**:
- {Method name}
- {Method name}

**See**: `.claude/rules/hec-hms/{rule_file}.md` for details

### {Domain Concept 2}

{Description of another key domain concept}

**See**: `.claude/rules/hec-hms/{rule_file}.md` for details

### Clone Workflows (if applicable)

**Non-Destructive Pattern**:
```python
from hms_commander import init_hms_project, hms, {PrimaryClass}

init_hms_project("project")

# Clone component (preserves original)
{PrimaryClass}.clone_{component}(
    template="Baseline",
    new_name="Updated_{Component}",
    description="Updated parameters for QAQC",
    hms_object=hms
)

# Modify cloned component
{PrimaryClass}.{modify_method}(
    "project/Updated_{Component}.{ext}",
    parameter=value
)
```

**Result**:
- Original preserved
- Clone appears in HMS GUI
- Traceable via description metadata
- Enables side-by-side QAQC comparison

**See**: `.claude/rules/hec-hms/clone-workflows.md` for complete pattern

## Common Tasks

### Task: {Task Name}

```python
from hms_commander import {PrimaryClass}

# Example code
```

### Task: {Another Task}

```python
# Example code
```

### Task: QAQC Workflow Setup (if applicable)

```python
# 1. Clone component
{PrimaryClass}.clone_{component}("Baseline", "Alternative", hms_object=hms)

# 2. Modify alternative
{PrimaryClass}.{modify_method}("project/Alternative.{ext}", parameter=value)

# 3. Execute both runs (see executing-hms-runs skill)
# 4. Compare results (see extracting-dss-results skill)
```

## Integration Points

**Before {This Agent's Work}**:
- {Prerequisite step or skill}

**After {This Agent's Work}**:
- Use `{follow_up_skill}` skill to {follow-up action}
- {Other integration point}

## Available Skills

You have access to:
- **{skill-1}** - {Brief description}
- **{skill-2}** - {Brief description}

**Activate skills** when users request {domain operations}.

## Primary Sources

Always point to these authoritative sources:
- **Code**: `hms_commander/{PrimaryClass}.py` - Complete docstrings
- **Examples**: `examples/{relevant_notebook}.ipynb` - {Operation type}
- **File Format**: `tests/projects/.../File Parsing Guide/{file_doc}.md` - HMS file structure
- **Rules**: `.claude/rules/hec-hms/{rule_file}.md` - Patterns

Do NOT duplicate API signatures - read from primary sources.

## When to Delegate Back

Delegate back to main agent when:
- Task requires execution (use `executing-hms-runs` skill)
- Need DSS results extraction (use `extracting-dss-results` skill)
- {Other domain} updates needed (use `{other-specialist}`)
- Multi-domain coordination required

---

**Status**: Active specialist subagent
**Version**: 1.0 ({YYYY-MM-DD})
```

## Execution Steps

1. Prompt user for inputs (name, description, API class, tools, skills, keywords)
2. Validate agent name (kebab-case, preferably ending in "-specialist")
3. Generate agent file: `.claude/agents/{agent-name}.md`
4. Fill in template with user inputs
5. Confirm creation with summary

## After Creation

Tell the user:

```
✓ Agent created: .claude/agents/{agent-name}.md

Next steps:
1. Fill in Domain Expertise sections with specific methods
2. Add Common Tasks with working code examples
3. Document integration points with other skills/agents
4. Update main agent to reference this specialist (if needed)

Related files to read:
- hms_commander/{PrimaryClass}.py - API to document
- .claude/rules/hec-hms/{relevant_rule}.md - Domain patterns
- .claude/agents/basin-model-specialist.md - Example specialist

To engage this agent:
- From main agent: Reference by task (e.g., "handle basin operations")
- From code: Use agent-engagesubagents command
```

## Validation Rules

**Agent Name**:
- Must be kebab-case (lowercase with hyphens)
- No spaces, underscores, or special characters
- Should end with "-specialist" for consistency
- Should be descriptive (2-4 words typical)

**Examples**:
- ✅ `basin-model-specialist`
- ✅ `met-model-specialist`
- ✅ `control-spec-specialist`
- ✅ `dss-integration-specialist`
- ❌ `BasinModelSpecialist` (not kebab-case)
- ❌ `basin_specialist` (underscore, not hyphen)
- ❌ `basin` (missing "-specialist" suffix)

**Tools**:
- Default: `Read, Grep, Glob, Edit`
- Add `Write` if agent creates files
- Add `Bash` if agent runs commands
- Add `NotebookEdit` if agent works with Jupyter notebooks

**Skills**:
- Should be existing skills in `.claude/skills/`
- Use kebab-case names
- Optional (leave blank if not applicable)

## Notes

- Specialist subagents are domain experts using hms-commander APIs
- They do NOT contain production workflows (those go in `hms_agents/`)
- They point to primary sources rather than duplicating documentation
- They should have clear delegation boundaries (when to hand back to main agent)
- They use YAML frontmatter for metadata
- They inherit context from CLAUDE.md files
- Model is typically "sonnet" for balance of speed and capability

## Common Specialist Domains

Typical specialist subagents for HMS:
- Basin model operations (HmsBasin)
- Met model operations (HmsMet)
- Control spec operations (HmsControl)
- Run management (HmsRun)
- DSS integration (HmsDss)
- Gage data (HmsGage)
- Geospatial operations (HmsGeo)
- Results analysis (HmsResults)

## Specialist vs Production Agent

**Specialist Agent** (created by this command):
- Single `.md` file in `.claude/agents/`
- Uses hms-commander library APIs
- Domain expertise focus
- Lightweight, framework-integrated

**Production Agent** (created manually):
- Folder in `hms_agents/` with multiple files
- Self-contained with tools and knowledge
- Complete automation workflow
- Shareable, production-ready

**See**: `.claude/CLAUDE.md` for complete architecture guide
