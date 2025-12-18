# Memory System Guide

**Source**: https://code.claude.com/docs/en/memory

**Last Updated**: 2025-12-17 (cached from Anthropic docs)

---

## The 4-Level Memory Hierarchy

Claude Code uses a hierarchical memory system to load instructions, with each level overriding the previous:

```
1. Enterprise Memory (~/.claude/CLAUDE.md)
   ↓ [overridden by]
2. Project Memory (repository root CLAUDE.md)
   ↓ [overridden by]
3. Rules & Sub-files (.claude/rules/*.md)
   ↓ [overridden by]
4. User Instructions (conversation input)
```

### Level 1: Enterprise Memory (Optional)

**Location**: `~/.claude/CLAUDE.md` (user home directory)

**Purpose**:
- Cross-project preferences
- Personal coding standards
- Organizational conventions

**Use Cases**:
- Company-wide coding style
- Preferred patterns across all projects
- Personal workflow preferences

**Example**:
```markdown
# My Enterprise Preferences

## Code Style
- Always use docstrings with Google format
- Prefer pathlib over os.path
- Use type hints for all functions

## Testing
- Write tests before implementation
- Use pytest fixtures
```

**Note**: Not commonly used; most users rely on project-level memory.

### Level 2: Project Memory

**Location**: `CLAUDE.md` in repository root

**Purpose**:
- **Primary entry point** for project-specific instructions
- Project overview and navigation
- Imports other memory files

**Structure**:
```markdown
# Project Name

## Overview
Brief project description

## Architecture
@.claude/rules/architecture/overview.md

## Python Patterns
@.claude/rules/python/static-classes.md
@.claude/rules/python/file-parsing.md

## Domain Knowledge
@.claude/rules/domain/specific-topic.md

## Quick Reference
Links to code, docs, examples
```

**Best Practices**:
- Keep focused on navigation and high-level guidance
- Use @imports for detailed rules
- Provide links to primary sources (code, docs)
- Aim for <2000 lines (including imports)

### Level 3: Rules Directory

**Location**: `.claude/rules/` and subdirectories

**Purpose**:
- Organized, modular knowledge files
- Domain-specific patterns and workflows
- Technical references

**Organization Example**:
```
.claude/rules/
├── python/
│   ├── static-classes.md
│   ├── file-parsing.md
│   └── error-handling.md
├── hec-hms/
│   ├── execution.md
│   ├── basin-files.md
│   └── clone-workflows.md
├── testing/
│   └── tdd-approach.md
└── integration/
    └── hms-ras-linking.md
```

**File Organization**:
- **Subdirectories by domain**: Group related topics
- **One topic per file**: Keep files focused
- **Descriptive names**: Clear, kebab-case filenames

### Level 4: User Instructions

**Location**: Conversation messages

**Purpose**:
- Highest priority instructions
- Override all file-based memory
- Session-specific guidance

**Example**:
```
User: For this session, use tabs instead of spaces.
```

This overrides any spacing preferences in CLAUDE.md or rules files.

---

## Recursive Loading with @imports

### Syntax

**Basic Import**:
```markdown
@path/to/file.md
```

**Multiple Imports**:
```markdown
## Python Patterns
@.claude/rules/python/static-classes.md
@.claude/rules/python/file-parsing.md
@.claude/rules/python/constants.md

## HMS Knowledge
@.claude/rules/hec-hms/execution.md
@.claude/rules/hec-hms/basin-files.md
```

### Import Rules

1. **One import per line**: Each @import on its own line
2. **Relative paths**: From the importing file's location
3. **Recursive loading**: Imported files can import other files
4. **Load order matters**: Later imports override earlier ones
5. **No circular imports**: Don't create import loops

### Example Structure

**Root CLAUDE.md**:
```markdown
# HMS Commander

@.claude/CLAUDE.md
```

**.claude/CLAUDE.md**:
```markdown
# HMS Framework

## Python Patterns
@.claude/rules/python/static-classes.md
@.claude/rules/python/file-parsing.md

## HMS Knowledge
@.claude/rules/hec-hms/execution.md
@.claude/rules/hec-hms/basin-files.md
```

**Loading Order**:
1. Root CLAUDE.md loads first
2. @.claude/CLAUDE.md loads second
3. @.claude/rules/python/static-classes.md loads third
4. @.claude/rules/python/file-parsing.md loads fourth
5. (etc. for remaining imports)

### Benefits of @imports

- **Modularity**: Organize knowledge by topic
- **Reusability**: Import same file in multiple places
- **Maintainability**: Update rules in one place
- **Clarity**: Clear dependency structure
- **Separation**: Decouple high-level navigation from detailed rules

---

## Path-Specific Rules

**Purpose**: Apply rules only to specific files or directories.

### YAML Frontmatter Syntax

```yaml
---
applies_to:
  files: ["*.py", "tests/**/*.py"]
  directories: ["hms_commander/", "tests/"]
---

# Rule content here
```

### Example: Python Static Classes Rule

**File**: `.claude/rules/python/static-classes.md`

```yaml
---
applies_to:
  files: ["hms_commander/*.py"]
  directories: ["hms_commander/"]
---

# Static Classes Pattern

All HMS commander classes use static methods, no instantiation required.

## Pattern

```python
class HmsBasin:
    @staticmethod
    def get_subbasins(basin_file):
        # Implementation
        pass
```

## Don't Do This

```python
basin = HmsBasin()  # Wrong! Don't instantiate
```
```

### Example: Testing-Specific Rule

**File**: `.claude/rules/testing/tdd-approach.md`

```yaml
---
applies_to:
  files: ["tests/**/*.py"]
  directories: ["tests/"]
---

# TDD Approach

Use real HMS projects from HmsExamples, not mocks.

```python
from hms_commander import HmsExamples, HmsBasin

HmsExamples.extract_project("tifton")
subbasins = HmsBasin.get_subbasins("tifton/tifton.basin")
```
```

### Glob Patterns

**Files**:
- `*.py` - All Python files in current directory
- `**/*.py` - All Python files recursively
- `test_*.py` - Files starting with test_
- `*.{py,pyx}` - Multiple extensions

**Directories**:
- `src/` - Specific directory
- `src/**/` - Directory and all subdirectories
- `**/tests/` - Any tests directory

### Benefits

- **Scoped Context**: Only load relevant rules
- **Reduced Tokens**: Don't load Python rules when editing markdown
- **Clear Applicability**: Obvious which rules apply where
- **Maintainability**: Organize rules by scope

---

## Size Recommendations

### File Sizes

**Individual Rule Files**: <500 lines
- Keep focused on single topic
- Easier to maintain and update
- Better for selective loading

**Aggregation Files** (CLAUDE.md): <2000 lines
- Including all @imports
- If larger, modularize further
- Use subdirectory aggregation files

**Skills**: <1000 lines
- Complex skills can use multi-file structure
- Reference external files if needed

### Token Management

**Total Context**: Be mindful of token limits
- Use path-specific rules to reduce unnecessary loading
- Prefer @imports over duplicating content
- Reference primary sources instead of copying

**Optimization**:
- Put frequently-needed rules early in load order
- Use path-specific rules for specialized knowledge
- Modularize large files into focused topics

---

## Memory System Best Practices

### 1. Organize Hierarchically

**Good Structure**:
```
Repository/
├── CLAUDE.md                    # Entry point, imports .claude/CLAUDE.md
├── .claude/
│   ├── CLAUDE.md                # Aggregates rules with @imports
│   ├── rules/
│   │   ├── python/              # Python patterns
│   │   ├── domain/              # Domain knowledge
│   │   └── testing/             # Testing approaches
│   └── skills/                  # Task workflows
```

**Bad Structure**:
```
Repository/
├── CLAUDE.md                    # 5000 lines of everything
├── python_stuff.md              # In wrong location
└── random_notes.md              # Disorganized
```

### 2. Use @imports for Modularity

**Good** (modular):
```markdown
## Python Patterns
@.claude/rules/python/static-classes.md
@.claude/rules/python/file-parsing.md
```

**Bad** (monolithic):
```markdown
## Python Patterns

### Static Classes
[500 lines of content]

### File Parsing
[500 lines of content]
```

### 3. Reference, Don't Duplicate

**Good**:
```markdown
## API Reference

See docstrings in `hms_commander/HmsBasin.py` for complete API.

Key methods:
- `get_subbasins()` - Extract subbasin list
- `set_loss_method()` - Modify loss method
```

**Bad**:
```markdown
## API Reference

### get_subbasins(basin_file)
Returns list of subbasins...
[Duplicating entire docstring]
```

### 4. Use Path-Specific Rules

**When Working on Multiple Languages**:
```yaml
# .claude/rules/python/style.md
---
applies_to:
  files: ["*.py"]
---
Use Google-style docstrings.
```

```yaml
# .claude/rules/javascript/style.md
---
applies_to:
  files: ["*.js", "*.ts"]
---
Use JSDoc comments.
```

### 5. Keep Files Focused

**Good** (single topic):
```
.claude/rules/python/static-classes.md
.claude/rules/python/file-parsing.md
.claude/rules/python/error-handling.md
```

**Bad** (kitchen sink):
```
.claude/rules/python/everything.md  # 3000 lines covering all topics
```

---

## Common Patterns

### Pattern 1: Two-Layer CLAUDE.md

**Root CLAUDE.md** (navigation):
```markdown
# Project Name

Brief overview and navigation.

@.claude/CLAUDE.md
```

**.claude/CLAUDE.md** (aggregation):
```markdown
# Framework

@.claude/rules/python/static-classes.md
@.claude/rules/domain/patterns.md
@.claude/rules/testing/approach.md
```

### Pattern 2: Domain-Organized Rules

```
.claude/rules/
├── python/              # Language patterns
│   └── static-classes.md
├── hec-hms/             # Domain knowledge
│   ├── execution.md
│   └── basin-files.md
└── integration/         # Cross-cutting concerns
    └── hms-ras-linking.md
```

### Pattern 3: Aggregation Sub-Files

For large rule collections, create subdirectory aggregation:

**.claude/rules/python/PYTHON.md**:
```markdown
@static-classes.md
@file-parsing.md
@error-handling.md
@naming-conventions.md
```

**.claude/CLAUDE.md**:
```markdown
@.claude/rules/python/PYTHON.md
@.claude/rules/hec-hms/HMS.md
```

---

## Troubleshooting

### Issue 1: Rules Not Loading

**Symptoms**: Claude doesn't follow rules in memory files

**Check**:
1. Verify file path in @import is correct
2. Ensure CLAUDE.md is in repository root
3. Check for syntax errors in YAML frontmatter
4. Verify file encoding (UTF-8)

**Solution**: Use absolute paths in @imports relative to importing file.

### Issue 2: Wrong Rules Applying

**Symptoms**: Rules meant for Python applying to other files

**Check**:
1. Verify path-specific rules have correct YAML frontmatter
2. Check glob patterns match intended files
3. Ensure applies_to paths are correct

**Solution**: Add or refine `applies_to` frontmatter.

### Issue 3: Token Limits

**Symptoms**: Large context, slow responses

**Check**:
1. Total size of all imported files
2. Unnecessary duplication across files
3. Path-specific rules not being used

**Solution**:
1. Use path-specific rules to reduce loading
2. Reference primary sources instead of duplicating
3. Modularize large files

### Issue 4: Conflicting Rules

**Symptoms**: Unclear which rule takes precedence

**Remember Load Order**:
1. Enterprise → Project → Rules → User
2. Within level: First imported → Last imported
3. User instructions override all files

**Solution**: Structure imports so most specific comes last.

---

## Quick Reference

### File Locations

- **Enterprise**: `~/.claude/CLAUDE.md` (optional)
- **Project**: `CLAUDE.md` (repository root)
- **Rules**: `.claude/rules/**/*.md`
- **Framework**: `.claude/CLAUDE.md` (aggregation)

### Import Syntax

```markdown
@relative/path/to/file.md
```

### Path-Specific Rules

```yaml
---
applies_to:
  files: ["*.py"]
  directories: ["src/"]
---
```

### Best Practices

- ✅ Organize hierarchically
- ✅ Use @imports for modularity
- ✅ Reference primary sources
- ✅ Keep files focused (<500 lines)
- ✅ Use path-specific rules
- ❌ Don't duplicate content
- ❌ Don't create monolithic files
- ❌ Don't exceed token limits

---

## Key Takeaways

1. **4-level hierarchy**: Enterprise → Project → Rules → User
2. **@imports enable modularity**: Organize knowledge, import where needed
3. **Path-specific rules**: Use YAML frontmatter to scope rules
4. **Reference, don't duplicate**: Point to source code and docs
5. **Keep files focused**: Single topic per file, <500 lines ideal
6. **Load order matters**: Later overrides earlier, user overrides all
