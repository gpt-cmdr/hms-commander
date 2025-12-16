# Repository Organization

**Purpose**: Maintain clean, organized repository structure with well-defined locations for different types of files.

**Primary sources**:
- Repository root structure
- `.claude/` framework organization
- `feature_dev_notes/` development documentation (gitignored - local only)

---

## ⚠️ CRITICAL CONSTRAINT: feature_dev_notes/ is Gitignored

**Important**: `feature_dev_notes/` is in `.gitignore` and NOT tracked in version control.

**Rule for Production Agents**:
- ❌ **NEVER** reference `feature_dev_notes/` in production agent code or documentation
- ✅ **ALWAYS** put production reference data in `hms_agents/`
- ✅ Knowledge files, tools, examples → `hms_agents/agent_name/`

**Why This Matters**:
- Content in `feature_dev_notes/` won't be in git
- Won't exist for other users/contributors
- Agents referencing it will break for others
- Production agents must be self-contained

**Correct Usage**:
- `feature_dev_notes/` - Session notes, research, large local datasets
- `hms_agents/` - Production agents with ALL necessary reference data

**Example**:
```
❌ WRONG: See feature_dev_notes/hms_decompilation_library/INDEX.md
✅ CORRECT: See hms_agents/hms_decompiler/knowledge/INDEX.md
```

---

## Root Directory Guidelines

### Files That Should Stay in Root

**User-facing documentation** (essential for users discovering the project):
- `README.md` - Repository overview, installation, basic usage
- `GETTING_STARTED.md` - Quick start guide for new users
- `QUICK_REFERENCE.md` - Command/API reference
- `STYLE_GUIDE.md` - Code style and contribution guidelines

**Primary instructions for Claude**:
- `CLAUDE.md` - Main instruction file (hierarchical knowledge entry point)

**Standard repository files**:
- `LICENSE`, `setup.py`, `pyproject.toml`, `.gitignore`, etc.

### Files That Should Be Moved

**Session/completion reports** → `feature_dev_notes/`:
- `*_completion_report.md`
- `SESSION_*.md`
- `PHASE_*_COMPLETE.md`
- Any other session-specific documentation

**Planning/design documents** → `feature_dev_notes/`:
- `*_PLAN.md`
- `*_BLUEPRINT.md`
- `*_ROADMAP.md` (unless it's the primary ROADMAP.md)
- Feature implementation notes

**Deprecated/archived files** → `.old/`:
- Old versions of files (e.g., `CLAUDE.md.backup`)
- Superseded documentation
- Experimental code that's no longer active

---

## Regular Cleanup Protocol

**When to clean**:
- After completing a major feature or phase
- At the end of a coding session that generated reports
- When root directory has more than 10 .md files

**How to clean**:

```bash
# Check what's in root
ls *.md

# Move session reports to feature_dev_notes
mv *_completion_report.md feature_dev_notes/
mv SESSION_*.md feature_dev_notes/
mv *_PLAN.md feature_dev_notes/

# Move old/backup files to .old
mv *.backup .old/
mv *_old.md .old/

# Verify only essential files remain
ls *.md  # Should show: CLAUDE.md, README.md, GETTING_STARTED.md, QUICK_REFERENCE.md, STYLE_GUIDE.md
```

**Add cleanup reminder to session workflow**:
- ✅ Complete feature implementation
- ✅ Write completion report to `feature_dev_notes/`
- ✅ **Clean up root directory**
- ✅ Commit and merge

---

## Directory Structure

```
hms-commander/
├── CLAUDE.md                    # Primary instructions (root only)
├── README.md                    # User overview (root only)
├── GETTING_STARTED.md           # Quick start (root only)
├── QUICK_REFERENCE.md           # API reference (root only)
├── STYLE_GUIDE.md               # Code style (root only)
│
├── .claude/                     # Hierarchical knowledge framework
│   ├── CLAUDE.md                # Framework aggregation (@imports)
│   ├── rules/                   # Patterns, workflows, decisions
│   │   ├── python/              # Python development patterns
│   │   ├── hec-hms/             # HMS domain knowledge
│   │   ├── testing/             # Testing approaches
│   │   ├── integration/         # Cross-repo workflows
│   │   └── project/             # Repository organization (this file)
│   ├── skills/                  # Task-specific workflows
│   └── subagents/               # Specialist agents
│
├── feature_dev_notes/           # Development documentation
│   ├── *_COMPLETE.md            # Phase completion reports
│   ├── *_completion_report.md   # Session reports
│   ├── SESSION_*.md             # Session notes
│   ├── *_PLAN.md                # Planning documents
│   └── *_ROADMAP.md             # Development roadmaps
│
├── .old/                        # Archived/deprecated files
│   ├── *.backup                 # Old file versions
│   └── *_old.*                  # Superseded files
│
├── hms_commander/               # Source code
├── tests/                       # Test suite
├── examples/                    # Jupyter notebooks
└── docs/                        # Generated documentation
```

---

## File Naming Conventions

**Completion reports**: `PHASE_{N}_COMPLETE.md`, `{feature}_completion_report.md`
**Session notes**: `SESSION_{topic}.md`
**Planning docs**: `{FEATURE}_PLAN.md`, `{FEATURE}_BLUEPRINT.md`
**Roadmaps**: `DEVELOPMENT_ROADMAP.md` (in feature_dev_notes)
**Backups**: `{filename}.backup` (move to .old immediately)

---

## Why This Matters

**User experience**: Users discovering the repository should see essential documentation immediately, not clutter.

**Navigation efficiency**: Clean root makes it obvious what files are important.

**Version control clarity**: Commit history is clearer when temporary/session files are properly organized.

**Framework integrity**: `.claude/` framework relies on predictable structure.

---

## Quick Reference

**Essential root files**: CLAUDE.md, README.md, GETTING_STARTED.md, QUICK_REFERENCE.md, STYLE_GUIDE.md

**Move to feature_dev_notes**: Completion reports, session notes, planning docs
**Move to .old**: Backups, deprecated files

**Cleanup command**: `ls *.md` → move extras → verify only 5 essential files remain
