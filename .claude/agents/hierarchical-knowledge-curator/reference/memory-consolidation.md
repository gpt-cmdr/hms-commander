# Memory Consolidation Workflow

**Purpose**: Transform temporary subagent knowledge from `.claude/outputs/` into permanent patterns in `.claude/rules/` and `.claude/skills/`.

---

## Overview

### The Problem

Subagents generate valuable analysis and findings during their work. Without consolidation, this knowledge:
- Remains scattered in temporary files
- Isn't discoverable for future tasks
- Gets lost when files are cleaned up
- Doesn't benefit other agents or sessions

### The Solution

**Structured Memory Consolidation**:
1. **Accumulate**: Subagents write to `.claude/outputs/{subagent_name}/`
2. **Monitor**: Main agent reviews outputs regularly
3. **Extract**: Identify patterns and workflows worth preserving
4. **Consolidate**: Move knowledge to permanent locations (.claude/rules/ or .claude/skills/)
5. **Prune**: Clean up consolidated outputs (non-destructive, move to .old/)

---

## Subagent Output Pattern

### Writing Outputs

**Pattern**: Subagents should write analysis to structured markdown files.

```python
# Example from basin-model-specialist subagent

output_dir = ".claude/outputs/basin-model-specialist"
os.makedirs(output_dir, exist_ok=True)

timestamp = datetime.now().strftime("%Y-%m-%d")
output_file = f"{output_dir}/subbasin_analysis_{timestamp}.md"

with open(output_file, 'w') as f:
    f.write(f"# Subbasin Analysis - {timestamp}\n\n")
    f.write(f"## Project: {project_name}\n\n")
    f.write("## Findings\n\n")
    f.write(analysis_content)
    f.write("\n\n## Recommendations\n\n")
    f.write(recommendations)

# Return path to main agent
return f"Analysis complete. Results saved to: {output_file}"
```

**Key Elements**:
1. **Structured directory**: `.claude/outputs/{subagent_name}/`
2. **Descriptive filename**: Include date and topic
3. **Markdown format**: Clear sections, headers, lists
4. **Return path**: Main agent can read if needed for decisions

---

### Output Organization

**Directory Structure**:
```
.claude/outputs/
├── basin-model-specialist/
│   ├── subbasin_analysis_2025-12-17.md
│   ├── subbasin_analysis_2025-12-16.md
│   ├── loss_method_comparison_2025-12-15.md
│   ├── routing_validation_2025-12-14.md
│   └── reach_connectivity_audit_2025-12-13.md
│
├── met-model-specialist/
│   ├── gage_assignment_audit_2025-12-17.md
│   ├── gage_assignment_audit_2025-12-15.md
│   ├── precip_distribution_review_2025-12-16.md
│   └── snowmelt_parameter_check_2025-12-14.md
│
├── dss-integration-specialist/
│   ├── pathname_parsing_2025-12-17.md
│   ├── timeseries_extraction_2025-12-16.md
│   ├── dss_catalog_analysis_2025-12-15.md
│   └── unit_conversion_validation_2025-12-14.md
│
└── documentation-specialist/
    ├── api_coverage_report_2025-12-17.md
    ├── example_validation_2025-12-16.md
    └── docstring_audit_2025-12-15.md
```

**Benefits**:
- Organized by subagent (clear ownership)
- Timestamped (chronological tracking)
- Descriptive names (easy to find relevant analysis)
- Self-documenting (markdown with clear structure)

---

## Monitoring Workflow

### Regular Review Schedule

**Weekly Curation** (recommended):
```bash
# Monday: Review new outputs
find .claude/outputs/ -name "*.md" -mtime -7

# Wednesday: Extract patterns and create skills
# [Consolidation work]

# Friday: Prune consolidated outputs
# [Move to .old/]
```

**Ad-hoc Review** (when needed):
- After major feature completion
- When output directory gets large (>20 files per subagent)
- When similar patterns appear across multiple outputs

---

### Monitoring Commands

```bash
# Check all outputs
ls -la .claude/outputs/*/

# Count files per subagent
for dir in .claude/outputs/*/; do
    echo "$(basename $dir): $(ls $dir/*.md 2>/dev/null | wc -l) files"
done

# Find recent outputs (last 7 days)
find .claude/outputs/ -name "*.md" -mtime -7 -exec ls -lh {} \;

# Find large outputs (>10KB)
find .claude/outputs/ -name "*.md" -size +10k -exec ls -lh {} \;

# Search for specific topics
grep -r "reach connectivity" .claude/outputs/
```

---

## Consolidation Decision Framework

### Pattern Recognition

**Read outputs and identify**:
1. **Recurring patterns**: Same pattern appears in 3+ outputs
2. **Complete workflows**: Full sequence of steps documented
3. **Reusable knowledge**: Applicable beyond specific project
4. **Architectural decisions**: WHY certain approaches were chosen

**Questions to ask**:
- Is this pattern general or project-specific?
- Does this workflow appear multiple times?
- Is this knowledge stable or still evolving?
- Would other agents benefit from this?
- Does this belong in rules/ or skills/?

---

### Extraction Decision Tree

```
What type of knowledge is this?

1. General Pattern (applies broadly)
   → Extract to .claude/rules/{category}/{topic}.md
   → Example: "Basin files always validate reach connectivity"
   → File: .claude/rules/hec-hms/basin-validation-patterns.md

2. Specific Workflow (task-oriented)
   → Create skill in .claude/skills/{skill-name}/
   → Example: "Steps to audit gage assignments in met models"
   → Skill: .claude/skills/auditing-gage-assignments/

3. Deep Technical Detail
   → Add to existing skill reference/
   → Example: "Edge cases in DSS pathname parsing"
   → File: .claude/skills/extracting-dss-results/reference/pathname-edge-cases.md

4. Architectural Decision
   → Add to .agent/LEARNINGS.md
   → Example: "WHY we chose static classes over instances"
   → Update: .agent/LEARNINGS.md

5. Project-Specific Finding
   → Keep in .claude/outputs/ or move to .old/
   → Example: "Analysis of Tifton project subbasin routing"
   → Action: Move to .old/ after project complete
```

---

## Consolidation Actions

### Action 1: Extract to .claude/rules/

**When**: General pattern that applies broadly, always relevant

**Process**:
1. Identify pattern across multiple outputs
2. Determine appropriate rules category (python/, hec-hms/, testing/, etc.)
3. Create or update rules file
4. Document pattern with examples
5. Add navigation from CLAUDE.md if needed

**Example**:
```bash
# Review outputs
cat .claude/outputs/basin-model-specialist/reach_connectivity_audit_*.md

# Pattern identified: All basin validation checks reach connectivity
# Create rules file
mkdir -p .claude/rules/hec-hms
cat > .claude/rules/hec-hms/basin-validation-patterns.md << 'EOF'
# Basin Validation Patterns

## Reach Connectivity Validation

**Pattern**: Always validate reach connectivity after basin modifications.

**Why**: HEC-HMS requires complete routing network, disconnected reaches cause
simulation failures.

**Implementation**:
```python
# Check all reaches have upstream and downstream connections
reaches = HmsBasin.get_reaches(basin_file)
for reach in reaches:
    if not reach['upstream'] or not reach['downstream']:
        raise ValidationError(f"Reach {reach['name']} has missing connections")
```

[More patterns...]
EOF

# Update CLAUDE.md if this is new category
# [Add navigation guidance]
```

---

### Action 2: Create Skill

**When**: Complete workflow that's task-oriented and reusable

**Process**:
1. Identify workflow across multiple outputs
2. Extract key steps and decision points
3. Create skill structure (SKILL.md + reference/ + examples/)
4. Write YAML frontmatter with trigger keywords
5. Follow navigation principle (point to sources)

**Example**:
```bash
# Review outputs
cat .claude/outputs/met-model-specialist/gage_assignment_audit_*.md

# Workflow identified: Complete audit process for gage assignments
# Create skill
mkdir -p .claude/skills/auditing-gage-assignments/{reference,examples}

cat > .claude/skills/auditing-gage-assignments/SKILL.md << 'EOF'
---
name: auditing-gage-assignments
description: |
  Audits HEC-HMS met model gage assignments to subbasins. Validates all subbasins
  have assigned gages, checks gage data availability, identifies inconsistencies.
  Use when validating met models, checking gage assignments, or troubleshooting
  missing precipitation data. Keywords: gage assignment, met model validation,
  precipitation audit, gage check, subbasin gage.
skills: [parsing-basin-models, updating-met-models]
---

# Auditing Gage Assignments Skill

## Primary Sources

**Code**: `hms_commander/HmsMet.py` - Gage assignment operations
**Examples**: `examples/04_met_model_operations.ipynb` - Gage assignment examples
**Rules**: `.claude/rules/hec-hms/met-files.md` - Met file structure

## Workflow

### Step 1: Extract Gage Assignments
[Workflow steps...]

### Step 2: Validate Coverage
[Validation steps...]

### Step 3: Report Findings
[Reporting steps...]

## See Also

**Reference**: `reference/validation-checks.md` - Complete validation criteria
**Examples**: `examples/complete-audit.md` - Full audit walkthrough
EOF

# Create reference files
# [Add detailed validation checks]

# Create examples
# [Add complete audit example]
```

---

### Action 3: Add to Skill Reference

**When**: Deep technical detail that enhances existing skill

**Process**:
1. Identify relevant existing skill
2. Determine reference file (api.md, patterns.md, troubleshooting.md, etc.)
3. Add section with findings
4. Update SKILL.md navigation if needed

**Example**:
```bash
# Review outputs
cat .claude/outputs/dss-integration-specialist/pathname_parsing_2025-12-*.md

# Finding: Edge cases in DSS pathname parsing (E-part variations)
# Add to existing skill reference
cat >> .claude/skills/extracting-dss-results/reference/pathname-edge-cases.md << 'EOF'

## E-Part Variations (Added 2025-12-17)

**Finding**: HMS outputs use inconsistent E-part formatting across versions.

**Patterns Observed**:
- HMS 3.5: `RUN:Run Name`
- HMS 4.0: `RUN:RUN NAME` (uppercase)
- HMS 4.11: `RUN:Run_Name` (underscores)

**Handling**:
```python
# Case-insensitive, flexible separator matching
e_part_patterns = [
    r'RUN:.*',  # Standard
    r'RUN_.*',  # Legacy
]
```

**Source**: .claude/outputs/dss-integration-specialist/pathname_parsing_2025-12-17.md
EOF
```

---

### Action 4: Update LEARNINGS.md

**When**: Architectural decision or important discovery that affects development

**Process**:
1. Extract key decision or learning
2. Add to `.agent/LEARNINGS.md`
3. Include context, impact, and reference
4. Link to detailed documentation if needed

**Example**:
```bash
cat >> .agent/LEARNINGS.md << 'EOF'

## DSS Pathname Parsing Strategy (2025-12-17)

**Decision**: Use flexible regex patterns instead of strict parsing for DSS pathnames.

**Context**: HMS outputs vary E-part formatting across versions (3.x vs 4.x).
Analysis of 150+ DSS files showed 5 different E-part patterns.

**Impact**: Parsing must be tolerant of variations to support all HMS versions.

**Implementation**: See `.claude/skills/extracting-dss-results/reference/pathname-edge-cases.md`

**Source**: .claude/outputs/dss-integration-specialist/pathname_parsing_2025-12-17.md
EOF
```

---

## Pruning Workflow

### Non-Destructive Deletion

**Principle**: Never permanently delete knowledge, move to `.old/`

**Process**:
1. Identify outputs that have been consolidated
2. Create timestamped `.old/` directory
3. Move consolidated outputs
4. Recommend to user before moving

**Commands**:
```bash
# Create timestamped archive directory
mkdir -p .old/outputs-$(date +%Y-%m-%d)

# Move consolidated outputs
mv .claude/outputs/basin-model-specialist/ .old/outputs-2025-12-17/

# Verify move
ls -la .old/outputs-2025-12-17/basin-model-specialist/
```

---

### Recommend-to-Delete Pattern

**Never auto-delete**: Always ask user before pruning.

**Template**:
```markdown
## Memory Consolidation Complete

**Patterns Extracted**:
1. Basin validation patterns → `.claude/rules/hec-hms/basin-validation-patterns.md`
2. Gage assignment audit workflow → `.claude/skills/auditing-gage-assignments/`
3. DSS pathname edge cases → `.claude/skills/extracting-dss-results/reference/pathname-edge-cases.md`

**Outputs Ready for Archival** (patterns already extracted):
- `.claude/outputs/basin-model-specialist/` (5 files, 2025-12-13 to 2025-12-17)
  - Patterns extracted to basin-validation-patterns.md
  - All findings consolidated
- `.claude/outputs/dss-integration-specialist/` (3 files, 2025-12-15 to 2025-12-17)
  - Edge cases added to skill reference
  - All findings documented

**Recommendation**: Move to `.old/outputs-2025-12-17/` for archival?

**Outputs to Keep** (knowledge still accumulating):
- `.claude/outputs/met-model-specialist/` (workflow still evolving)
- `.claude/outputs/documentation-specialist/` (audit in progress)

Do you want me to proceed with archival? [Yes/No]
```

---

### Archival Records

**Track what was consolidated**: Maintain index of archived outputs.

```bash
# Create archival index
cat > .old/outputs-2025-12-17/INDEX.md << 'EOF'
# Archived Outputs - 2025-12-17

## Basin Model Specialist (5 files)
- subbasin_analysis_2025-12-13.md → `.claude/rules/hec-hms/basin-validation-patterns.md`
- subbasin_analysis_2025-12-14.md → Same as above
- loss_method_comparison_2025-12-15.md → `.claude/skills/comparing-loss-methods/`
- routing_validation_2025-12-16.md → `.claude/rules/hec-hms/basin-validation-patterns.md`
- reach_connectivity_audit_2025-12-17.md → Same as above

**Consolidated Patterns**:
- Basin validation always checks reach connectivity
- Loss method comparison workflow documented
- Routing validation criteria standardized

## DSS Integration Specialist (3 files)
- pathname_parsing_2025-12-15.md → `.claude/skills/extracting-dss-results/reference/pathname-edge-cases.md`
- pathname_parsing_2025-12-16.md → Same as above
- pathname_parsing_2025-12-17.md → Same as above

**Consolidated Patterns**:
- DSS E-part variations across HMS versions documented
- Flexible pathname parsing strategy adopted

---

**Total Files Archived**: 8
**Total Patterns Extracted**: 5
**Rules Created**: 1
**Skills Created**: 1
**Skill References Updated**: 1
EOF
```

---

## Consolidation Examples

### Example 1: Pattern to Rules

**Scenario**: Multiple basin analyses show same validation pattern.

**Outputs**:
```
.claude/outputs/basin-model-specialist/
├── subbasin_analysis_2025-12-13.md
│   → Finding: Missing reach connections cause failure
├── subbasin_analysis_2025-12-15.md
│   → Finding: Disconnected reaches not validated by HMS
└── reach_connectivity_audit_2025-12-17.md
    → Finding: Manual connectivity check prevents errors
```

**Action**: Extract to `.claude/rules/hec-hms/basin-validation-patterns.md`

**Result**:
```markdown
# Basin Validation Patterns

## Reach Connectivity Validation

**Pattern**: HMS does not validate reach connectivity at save time, only at
run time. Manual validation prevents simulation failures.

**Implementation**: Check all reaches have upstream/downstream connections
before saving basin file.

**Source**: Consolidated from 3 basin analyses (2025-12-13 to 2025-12-17)
```

---

### Example 2: Workflow to Skill

**Scenario**: Met model specialist repeatedly audits gage assignments using same workflow.

**Outputs**:
```
.claude/outputs/met-model-specialist/
├── gage_assignment_audit_2025-12-14.md
│   → Workflow: Extract assignments, check coverage, validate data
├── gage_assignment_audit_2025-12-16.md
│   → Workflow: Same steps, different project
└── gage_assignment_audit_2025-12-17.md
    → Workflow: Same steps, added reporting
```

**Action**: Create `.claude/skills/auditing-gage-assignments/`

**Result**:
```
.claude/skills/auditing-gage-assignments/
├── SKILL.md (workflow overview with navigation)
├── reference/
│   └── validation-checks.md (complete criteria)
└── examples/
    └── complete-audit.md (full walkthrough)
```

---

### Example 3: Edge Case to Reference

**Scenario**: DSS integration specialist finds edge cases in pathname parsing.

**Outputs**:
```
.claude/outputs/dss-integration-specialist/
├── pathname_parsing_2025-12-15.md
│   → Finding: E-part uses RUN: prefix
├── pathname_parsing_2025-12-16.md
│   → Finding: HMS 4.x uses uppercase RUN:
└── pathname_parsing_2025-12-17.md
    → Finding: HMS 3.x uses mixed case RUN:
```

**Action**: Add to `.claude/skills/extracting-dss-results/reference/pathname-edge-cases.md`

**Result**: Reference file updated with E-part variations, flexible parsing strategy documented.

---

## Maintenance Schedule

### Weekly Curation (Recommended)

**Monday**: Review and identify
- List recent outputs (last 7 days)
- Read outputs, identify patterns
- Flag consolidation candidates

**Wednesday**: Extract and consolidate
- Create/update .claude/rules/ files
- Create/update .claude/skills/
- Add to .agent/LEARNINGS.md

**Friday**: Prune and archive
- Move consolidated outputs to .old/
- Create archival index
- Recommend deletions to user

---

### Monthly Deep Consolidation

**Review**:
- All outputs from past month
- Cross-subagent patterns
- Skills that could be combined
- Rules that could be split

**Refactor**:
- Consolidate duplicate patterns
- Split oversized files
- Reorganize categories
- Update navigation

**Report**:
- Consolidation summary
- Patterns discovered
- Skills created
- Archival statistics

---

## Quality Checklist

Before consolidating:

**Pattern Extraction**:
- [ ] Pattern appears in 3+ outputs (or is clearly reusable)
- [ ] Pattern is stable (not rapidly evolving)
- [ ] Pattern is general (not project-specific)
- [ ] Pattern documented with examples

**Skill Creation**:
- [ ] Workflow is complete (all steps documented)
- [ ] Workflow is reusable (applicable beyond one project)
- [ ] YAML frontmatter has trigger keywords
- [ ] Navigation principle followed (points to sources)
- [ ] SKILL.md < 500 lines

**Rules Update**:
- [ ] Content fits rules category (python/, hec-hms/, etc.)
- [ ] File size 50-200 lines (or extract to skill reference)
- [ ] No API duplication (navigation principle)
- [ ] Clear examples of pattern

**Archival**:
- [ ] Outputs consolidated before archival
- [ ] Moved to .old/ (not deleted)
- [ ] Archival index created
- [ ] User approved pruning

---

## Success Metrics

**Knowledge Accumulation**:
- Subagents write to .claude/outputs/ consistently
- Outputs are structured markdown with clear sections
- Patterns emerge from multiple outputs

**Consolidation Effectiveness**:
- Weekly curation performed
- Patterns extracted to .claude/rules/
- Skills created from workflows
- Old outputs archived (not lost)

**Framework Growth**:
- .claude/rules/ grows with new patterns
- .claude/skills/ grows with new workflows
- .agent/LEARNINGS.md accumulates wisdom
- Knowledge is discoverable and reusable

**Maintenance Quality**:
- .claude/outputs/ kept under 20 files per subagent
- Archival index maintained in .old/
- No permanent deletion (can recover from .old/)
- User approves all pruning

---

**Status**: Active consolidation workflow
**Version**: 1.0 (2025-12-17)
**Purpose**: Transform temporary subagent knowledge into permanent framework patterns
