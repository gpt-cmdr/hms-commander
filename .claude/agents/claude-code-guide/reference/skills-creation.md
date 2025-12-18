# Skills Creation Guide

**Source**: https://claude.com/blog/how-to-create-skills-key-steps-limitations-and-examples

**Last Updated**: 2025-12-17 (cached from Anthropic blog)

---

## The 5-Step Skills Creation Process

### Step 1: Understand When to Use Skills

**Skills are for**:
- Complex, multi-step workflows requiring detailed instructions
- Task-specific tool sequences and decision logic
- Specialized domain knowledge with extensive guidance
- Workflows that benefit from explicit step-by-step procedures

**CLAUDE.md rules are for**:
- Project-wide conventions and patterns
- Architectural decisions and coding standards
- Reference information (APIs, documentation locations)
- Simple reminders and preferences

**Decision Criteria**:
- If task requires >5 steps with tool calls → Skill
- If task is a general pattern/convention → CLAUDE.md rule
- If task needs specialized knowledge → Skill
- If task is a quick reference → CLAUDE.md rule

### Step 2: Name Your Skill

**Naming Convention**: `lowercase-with-hyphens`

**Good Examples**:
- `update-met-models`
- `parse-basin-files`
- `execute-hms-simulation`
- `link-hms-to-ras`

**Bad Examples**:
- `UpdateMetModels` (CamelCase)
- `parse_basin_files` (snake_case)
- `basin` (too vague)
- `do-stuff` (not descriptive)

**Best Practices**:
- Action-oriented (verb + noun)
- Descriptive but concise
- Matches directory name for multi-file skills
- Lowercase with hyphens for consistency

### Step 3: Write the Description (MOST CRITICAL)

**CRITICAL**: The description is **the only part that influences skill triggering**.

#### What Makes a Good Description

**Include**:
- **Action verbs**: What the skill does
- **Use cases**: When to use it
- **Trigger phrases**: Keywords users might say
- **File types**: Specific extensions or formats
- **Task types**: Categories of work

**Structure**:
```
[What it does]. [When to use it]. [Specific trigger phrases/keywords].
```

#### Examples

**Bad Description** (too vague, won't trigger):
```yaml
description: Helps with basin models
```

**Good Description** (action-oriented, keyword-rich):
```yaml
description: |
  Parse HEC-HMS basin files to extract subbasin properties, loss methods, and routing
  parameters. Use when working with .basin files, extracting subbasin data, analyzing
  basin model configurations, or modifying hydrologic elements.
  Keywords: .basin, subbasins, loss methods, transform methods, routing, baseflow.
```

**Excellent Description** (comprehensive, multiple trigger paths):
```yaml
description: |
  Automate HEC-HMS precipitation model updates from NOAA Atlas 14 data. Downloads frequency
  grids, converts to HMS format, updates gage weights, and validates spatial coverage.
  Use when updating met models with Atlas 14, modernizing precipitation inputs, converting
  NOAA grids to HMS gages, or automating precipitation model workflows.
  Trigger phrases: "update Atlas 14", "modernize precipitation", "NOAA frequency grids",
  "automate met model update", "convert Atlas 14 to HMS".
  Keywords: Atlas 14, NOAA, precipitation frequency, met models, gage weights, gridded data.
```

#### Description Checklist

- [ ] Action-oriented (starts with verb or clear statement of capability)
- [ ] Includes specific use cases (when to use)
- [ ] Contains trigger phrases users might naturally say
- [ ] Lists relevant file types or formats
- [ ] Includes domain-specific keywords
- [ ] Provides multiple triggering pathways
- [ ] Clear and concise (2-5 sentences)

### Step 4: Write Detailed Instructions

**Structure**:
```markdown
# Skill Name

## Overview
Brief summary of what skill does

## Prerequisites
Required files, environment setup, dependencies

## Workflow

### Step 1: [First Major Step]
Detailed instructions with tool calls

### Step 2: [Second Major Step]
More instructions

### Step 3: [etc...]

## Error Handling
Common issues and how to resolve

## Validation
How to verify success

## Examples
Concrete usage examples
```

**Best Practices**:
- **Be explicit**: Don't assume Claude knows your workflow
- **Include tool calls**: Specify which tools to use (Read, Grep, Bash, etc.)
- **Show decision logic**: "If X, then Y; else Z"
- **Provide examples**: Code snippets, file formats, commands
- **Handle errors**: Common failure modes and solutions
- **Reference other files**: Skills can import other markdown files in skill directory

**Multi-File Skills**:
```
.claude/skills/my-skill/
├── SKILL.md          # Main instructions with YAML frontmatter
├── examples.md       # Usage examples
├── reference.md      # Technical reference
└── tools/            # Scripts or utilities
    └── helper.py
```

### Step 5: Upload and Test

**Testing Process**:

1. **Upload skill**: Place in `.claude/skills/`
2. **Test with realistic prompts**: Try multiple phrasings
   - "Can you update the Atlas 14 data?"
   - "I need to modernize precipitation inputs"
   - "Convert NOAA grids to HMS format"
3. **Verify triggering**: Check if skill activates correctly
4. **Refine description**: If not triggering, add more keywords
5. **Validate execution**: Ensure skill follows instructions correctly
6. **Iterate**: Refine based on testing results

**Common Triggering Issues**:

**Problem**: Skill doesn't activate when expected
**Solution**: Add more keywords and trigger phrases to description

**Problem**: Skill activates for wrong tasks
**Solution**: Make description more specific, narrow use cases

**Problem**: Skill activates too broadly
**Solution**: Add qualifiers and specific contexts to description

---

## Skills Best Practices

### Description Writing Tips

1. **Front-load keywords**: Put most important terms early
2. **Use natural language**: Match how users would ask
3. **Include variations**: Different ways to phrase same request
4. **Specify file types**: If skill works with specific files, list them
5. **Name technologies**: Mention specific tools or formats
6. **Action verbs matter**: "Parse", "update", "convert", "automate", "extract"

### Instruction Writing Tips

1. **Step-by-step**: Break complex workflows into clear steps
2. **Tool-specific**: Tell Claude which tools to use and how
3. **Defensive**: Handle edge cases and errors
4. **Validating**: Include verification steps
5. **Documenting**: Explain why, not just what

### Organizational Tips

1. **Single file for simple skills**: If <200 lines, use `.claude/skills/skill-name.md`
2. **Multi-file for complex skills**: If >200 lines or needs reference files, use `.claude/skills/skill-name/`
3. **Reference external docs**: Point to code/docs rather than duplicating
4. **Keep focused**: One skill per major workflow

---

## Skill Template

```yaml
---
name: skill-name
description: |
  [Action-oriented statement of what skill does]. [When to use it]. [Specific
  trigger phrases and keywords that users might naturally say].
  Keywords: [comma, separated, relevant, terms]
---

# Skill Name

## Overview
Brief summary of skill purpose and capabilities.

## Prerequisites
- Required file(s)
- Environment setup
- Dependencies

## Workflow

### Step 1: [First Major Action]

Detailed instructions:
1. Use [Tool] to [action]
2. Check [condition]
3. If [condition], then [action]; else [alternative]

**Example**:
```
[code or command example]
```

### Step 2: [Second Major Action]

More detailed instructions...

### Step 3: [Final Action]

Completion instructions...

## Error Handling

**Common Issue 1**: [Description]
- **Cause**: [Why it happens]
- **Solution**: [How to fix]

**Common Issue 2**: [Description]
- **Cause**: [Why it happens]
- **Solution**: [How to fix]

## Validation

How to verify the skill executed successfully:
1. Check [condition]
2. Verify [output]
3. Validate [result]

## Examples

### Example 1: [Scenario]
[Complete example with input and output]

### Example 2: [Another Scenario]
[Another example]
```

---

## Key Takeaways

1. **Description is everything**: It's the only part that affects triggering
2. **Be keyword-rich**: Include all relevant terms users might say
3. **Test thoroughly**: Try multiple phrasings to verify triggering
4. **Step-by-step instructions**: Don't assume Claude knows your workflow
5. **Iterate**: Refine based on testing and real-world use

The difference between a good skill and a great skill is almost entirely in the **description quality**.
