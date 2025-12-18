# Governance Rules for Knowledge Organization

**Purpose**: Define clear rules for content distribution, size targets, and placement decisions across the HMS-Commander hierarchical knowledge framework.

---

## Content Distribution Rules

### 1. Root CLAUDE.md (Strategic Vision)

**Size Target**: <200 lines

**Content Type**:
- High-level project overview
- Delegation patterns (when to spawn subagents)
- Navigation guidance (where to find detailed information)
- Core architectural decisions
- Cross-repository integration overview

**What Belongs Here**:
- ✅ "HMS-Commander is a Python library for automating HEC-HMS operations"
- ✅ "Use basin-model-specialist for all basin file operations"
- ✅ "See .claude/rules/python/ for development patterns"
- ✅ "See hms_agents/ for production automation"

**What Does NOT Belong Here**:
- ❌ Detailed API signatures
- ❌ Step-by-step workflows
- ❌ Code examples
- ❌ Troubleshooting guides
- ❌ Implementation details

**Enforcement**:
- If > 200 lines → Extract detailed content to .claude/rules/
- Use @imports to reference extracted content
- Keep only strategic overview and navigation

---

### 2. Subpackage CLAUDE.md (Tactical Patterns)

**Size Target**: <150 lines

**Content Type**:
- Module organization
- Key conventions for this subpackage
- Tactical patterns specific to this code area
- Integration points with other modules

**What Belongs Here**:
- ✅ "HmsBasin uses static methods, no instantiation"
- ✅ "All file paths should be pathlib.Path objects"
- ✅ "Parse operations use HmsFileParser shared utilities"
- ✅ "See .claude/rules/hec-hms/basin-files.md for basin operations"

**What Does NOT Belong Here**:
- ❌ Complete API documentation
- ❌ Full code examples
- ❌ Comprehensive troubleshooting
- ❌ Edge case handling

**Enforcement**:
- If > 150 lines → Extract to .claude/rules/
- Inherit from root CLAUDE.md automatically
- Focus on what's unique to this subpackage

---

### 3. .claude/rules/*.md (Detailed Procedures)

**Size Target**: 50-200 lines per file

**Content Type**:
- Specific technical guidance
- Detailed patterns and conventions
- Language-specific rules (Python, bash)
- Domain-specific knowledge (HEC-HMS, basin, met, DSS)
- Testing approaches
- Documentation standards

**Directory Organization**:
```
.claude/rules/
├── python/              # Python development patterns
│   ├── static-classes.md
│   ├── file-parsing.md
│   ├── constants.md
│   ├── decorators.md
│   ├── path-handling.md
│   └── error-handling.md
├── hec-hms/             # HMS domain knowledge
│   ├── execution.md
│   ├── basin-files.md
│   ├── met-files.md
│   ├── control-files.md
│   ├── dss-operations.md
│   ├── version-support.md
│   └── clone-workflows.md
├── testing/             # Testing approaches
│   ├── example-projects.md
│   └── tdd-approach.md
├── documentation/       # Documentation standards
│   ├── mkdocs-config.md
│   └── notebook-standards.md
├── integration/         # Cross-repo workflows
│   └── hms-ras-linking.md
└── project/             # Repository organization
    ├── development-environment.md
    └── repository-organization.md
```

**What Belongs Here**:
- ✅ Complete pattern descriptions
- ✅ When/why to use specific approaches
- ✅ Examples of good vs bad patterns
- ✅ Navigation to primary sources
- ✅ Architectural decisions (WHY we chose approach X)

**What Does NOT Belong Here**:
- ❌ API signatures (point to code docstrings)
- ❌ Multi-step workflows (create skill instead)
- ❌ Executable code (use scripts/ instead)

**Enforcement**:
- Files > 200 lines → Split into multiple files or move details to skill reference/
- Files < 50 lines → Consider consolidating with related file
- All .md files auto-load when working in .claude/ context

---

### 4. .claude/skills/*/SKILL.md (Discoverable Workflows)

**Size Target**: <500 lines for main SKILL.md

**Content Type**:
- Multi-step workflows
- Task-oriented guidance
- How-to guides for library functionality
- Discoverable capabilities

**Progressive Disclosure Structure**:
```
skill-name/
├── SKILL.md              # Overview + navigation (<500 lines)
│                         # YAML frontmatter at top
│                         # Points to primary sources
│                         # High-level workflow steps
│
├── reference/            # Detailed docs (unlimited size)
│   ├── api.md
│   ├── patterns.md
│   ├── troubleshooting.md
│   └── advanced.md
│
├── examples/             # Complete workflows
│   ├── basic.md
│   ├── advanced.md
│   └── integration.md
│
└── scripts/              # Executable utilities (token-free!)
    ├── validate.py
    ├── convert.py
    └── analyze.py
```

**What Belongs Here**:
- ✅ Complete workflow descriptions
- ✅ Navigation to primary sources
- ✅ Decision points in workflow
- ✅ Integration with other skills
- ✅ Trigger keywords for discovery

**What Does NOT Belong Here**:
- ❌ API signature duplication (navigation principle)
- ❌ Code copied from examples/ notebooks
- ❌ Content duplicated from .claude/rules/
- ❌ Deep technical details (use reference/ instead)

**Enforcement**:
- SKILL.md > 500 lines → Extract to reference/ files
- No API duplication (follow navigation principle)
- Rich YAML description with trigger keywords

---

### 5. .claude/skills/*/reference/*.md (Deep Details)

**Size Target**: Unlimited

**Content Type**:
- Deep technical documentation
- API patterns specific to this skill
- Advanced scenarios and edge cases
- Comprehensive troubleshooting
- Architecture decisions

**Loading Pattern**: Manual (agent reads when needed)

**What Belongs Here**:
- ✅ Detailed API patterns
- ✅ Complex edge case handling
- ✅ Comprehensive examples
- ✅ Performance considerations
- ✅ Version-specific behavior

**Enforcement**:
- No size limit (not auto-loaded)
- Loaded only when skill explicitly reads it
- Can be very detailed and comprehensive

---

### 6. .claude/outputs/* (Subagent Analysis)

**Size Target**: Unlimited (temporary)

**Content Type**:
- Subagent analysis and findings
- Temporary knowledge accumulation
- Session-specific outputs
- Work in progress

**Organization**:
```
.claude/outputs/
├── basin-model-specialist/
│   ├── subbasin_analysis_2025-12-17.md
│   ├── loss_method_comparison_2025-12-16.md
│   └── routing_validation_2025-12-15.md
├── met-model-specialist/
│   ├── gage_assignment_audit_2025-12-17.md
│   └── precip_distribution_review_2025-12-16.md
└── dss-integration-specialist/
    ├── pathname_parsing_2025-12-17.md
    └── timeseries_extraction_2025-12-15.md
```

**Curation Workflow**:
1. **Monitor**: Check regularly for new outputs
2. **Consolidate**: Extract patterns to .claude/rules/ or create skills
3. **Prune**: Move old outputs to .old/ (non-destructive)
4. **Recommend**: Never auto-delete, always ask user

**Enforcement**:
- Weekly curation (review, consolidate, prune)
- Non-destructive deletion (move to .old/ with timestamp)
- Recommend-to-delete pattern (user confirms)

---

### 7. hms_agents/* (Production Automation)

**Size Target**: Unlimited (self-contained)

**Content Type**:
- Production-ready automation
- Standalone capabilities
- End-user tools
- ALL necessary reference data

**Structure**:
```
hms_agents/agent_name/
├── AGENT.md              # Main agent definition
├── scripts/              # Executable scripts
│   └── main.py
├── knowledge/            # Domain knowledge
│   ├── INDEX.md
│   └── reference.md
├── tools/                # Utility classes
│   └── helper.py
└── examples/             # Usage examples
    └── example.ipynb
```

**CRITICAL**: ALL production reference data goes here, NEVER in feature_dev_notes/

**What Belongs Here**:
- ✅ Complete automation workflows
- ✅ Domain-specific knowledge files
- ✅ Reference classes and utilities
- ✅ Examples and documentation
- ✅ Self-contained (no external dependencies except hms-commander library)

**What Does NOT Belong Here**:
- ❌ References to feature_dev_notes/ (gitignored)
- ❌ Incomplete or experimental code
- ❌ Development notes or planning docs

**Enforcement**:
- Must be fully self-contained
- No references to gitignored directories
- Production-ready quality

---

### 8. feature_dev_notes/* (Development Research, GITIGNORED)

**Size Target**: Unlimited

**Content Type**:
- Development notes
- Research artifacts
- Planning documents
- Session-specific analysis
- Large datasets for local reference only

**CRITICAL CONSTRAINT**: feature_dev_notes/ is in .gitignore

**What Belongs Here**:
- ✅ Development roadmaps
- ✅ Session notes
- ✅ Research findings
- ✅ Planning documents
- ✅ Large local datasets (e.g., 4,686 HMS class files)

**What Does NOT Belong Here**:
- ❌ Production reference data (use hms_agents/ instead)
- ❌ Knowledge files for production agents
- ❌ Anything referenced by production code

**Enforcement**:
- NEVER reference from production agents or skills
- Keep for local development only
- Move essential content to production locations before sharing

---

## Size Enforcement Protocol

### When Root CLAUDE.md > 200 Lines

**Process**:
1. Identify sections with detailed content
2. Extract to .claude/rules/{category}/{topic}.md
3. Replace with @import or navigation guidance
4. Verify context inheritance still works

**Example**:
```markdown
# Before (250 lines)
## Static Classes Pattern
[100 lines of detailed explanation]

# After (180 lines)
## Python Development Patterns
@.claude/rules/python/static-classes.md

See `.claude/rules/python/` for complete patterns.
```

---

### When Subpackage CLAUDE.md > 150 Lines

**Process**:
1. Identify tactical content that can move to rules
2. Extract to .claude/rules/{category}/{topic}.md
3. Keep only module-specific conventions
4. Add navigation to extracted content

---

### When .claude/rules/*.md > 200 Lines

**Decision Tree**:
```
Is this a single cohesive topic?
├─ Yes → Consider if some content should move to skill reference/
└─ No → Split into multiple rules files by subtopic

Is this multi-step workflow?
├─ Yes → Create skill in .claude/skills/
└─ No → Keep in rules but consider extracting examples

Can content be organized as reference?
├─ Yes → Move deep details to skill reference/
└─ No → Split rules file into logical subtopics
```

---

### When SKILL.md > 500 Lines

**Process**:
1. Identify deep technical details
2. Extract to skill-name/reference/{topic}.md
3. Keep workflow overview in SKILL.md
4. Update navigation to reference files

**Example**:
```markdown
# SKILL.md (keeps workflow overview)
## Advanced Scenarios

For deep technical details on edge cases, see:
- `reference/api.md` - API-specific patterns
- `reference/troubleshooting.md` - Common issues and solutions
- `reference/advanced.md` - Complex scenarios and performance tuning
```

---

## Placement Decision Framework

### Content Classification

**Question 1**: Is this strategic or tactical?
- Strategic → Root CLAUDE.md
- Tactical → Subpackage CLAUDE.md or .claude/rules/

**Question 2**: Is this always relevant or task-specific?
- Always relevant → .claude/rules/ (auto-loaded)
- Task-specific → .claude/skills/ (loaded on activation)

**Question 3**: Is this a pattern or a workflow?
- Pattern → .claude/rules/
- Workflow → .claude/skills/

**Question 4**: Is this development or production?
- Development → feature_dev_notes/ (gitignored)
- Production → hms_agents/ (version controlled)

**Question 5**: Is this library usage or domain automation?
- Library usage → .claude/skills/
- Domain automation → hms_agents/

---

## Navigation Principle (CRITICAL)

### Point to Primary Sources, Don't Duplicate

**Primary Sources**:
1. **Code**: `hms_commander/*.py` - Authoritative API with docstrings
2. **Examples**: `examples/*.ipynb` - Working demonstrations
3. **Tests**: `tests/test_*.py` - Edge cases and validation
4. **Docs**: `docs/api/*.md` - Generated API reference

**Framework Documentation** (.claude/ files):
- **Patterns**: Architectural decisions, conventions
- **Workflows**: How to accomplish tasks
- **Decisions**: Why we chose approach X
- **Navigation**: Where to find information

**What NOT to Duplicate**:
- ❌ API signatures (point to code docstrings)
- ❌ Code examples (point to examples/ notebooks)
- ❌ Test cases (point to tests/)
- ❌ Method parameters (read from code)

**Good Navigation Example**:
```markdown
## Primary Sources

**Code**: `hms_commander/HmsCmdr.py` - Execution engine with docstrings
**Examples**: `examples/01_multi_version_execution.ipynb` - Complete workflow
**Rules**: `.claude/rules/hec-hms/execution.md` - Execution patterns
**Tests**: `tests/test_hmscmdr.py` - Edge cases

## What This Document Adds

- **Version Detection**: Decision logic for HMS 3.x vs 4.x paths
- **Error Recovery**: Patterns for timeout/missing file handling
- **Parallel Execution**: Strategy for concurrent simulations
```

---

## Consolidation Decision Tree

### When to Consolidate from .claude/outputs/

```
Has a clear pattern emerged?
├─ Yes → Extract to .claude/rules/ or create skill
└─ No → Keep in .claude/outputs/ for further accumulation

Is the workflow complete?
├─ Yes → Create skill in .claude/skills/
└─ No → Keep in .claude/outputs/ until complete

Is the knowledge reusable?
├─ Yes → Consolidate to permanent location
└─ No → Move to .old/ (recommend delete)

Is the knowledge stable?
├─ Yes → Consolidate now
└─ No → Keep in .claude/outputs/ while evolving

Has this been superseded?
├─ Yes → Move to .old/ (recommend delete)
└─ No → Evaluate for consolidation
```

---

## Quality Standards

### CLAUDE.md Files
- Root: <200 lines
- Subpackage: <150 lines
- Strategic content only
- Clear navigation guidance
- No API duplication

### .claude/rules/ Files
- 50-200 lines per file
- Single focused topic
- Complete pattern description
- Points to primary sources
- No workflow instructions (use skills)

### .claude/skills/
- SKILL.md: <500 lines
- Rich YAML description with triggers
- Navigation principle followed
- Reference files for details
- Examples demonstrate usage

### hms_agents/
- Fully self-contained
- ALL reference data included
- No feature_dev_notes/ references
- Production-ready quality

---

## Common Violations and Solutions

### Violation: Root CLAUDE.md > 200 lines
**Solution**: Extract detailed content to .claude/rules/, use @imports

### Violation: API signatures duplicated in skills
**Solution**: Replace with navigation to code docstrings

### Violation: SKILL.md > 500 lines with deep details
**Solution**: Extract details to skill-name/reference/*.md

### Violation: Production agent references feature_dev_notes/
**Solution**: Move essential content to hms_agents/agent_name/knowledge/

### Violation: .claude/outputs/ not curated for months
**Solution**: Weekly curation (consolidate, extract, prune)

### Violation: Same content in multiple locations
**Solution**: Consolidate to single authoritative location, add navigation

---

## Enforcement Checklist

Before committing changes:

**Size Compliance**:
- [ ] Root CLAUDE.md < 200 lines
- [ ] Subpackage CLAUDE.md < 150 lines
- [ ] .claude/rules/*.md between 50-200 lines
- [ ] SKILL.md < 500 lines

**Content Placement**:
- [ ] Strategic content in root CLAUDE.md
- [ ] Patterns in .claude/rules/
- [ ] Workflows in .claude/skills/
- [ ] Production automation in hms_agents/
- [ ] No feature_dev_notes/ references in production

**Navigation Principle**:
- [ ] No API signature duplication
- [ ] Points to primary sources
- [ ] Documents patterns, not details
- [ ] Clear navigation guidance

**Quality Standards**:
- [ ] No duplicated content
- [ ] Logical hierarchy
- [ ] Context inheritance works
- [ ] Progressive disclosure implemented

---

**Status**: Active governance reference
**Version**: 1.0 (2025-12-17)
**Purpose**: Enforce consistent content organization across HMS-Commander framework
