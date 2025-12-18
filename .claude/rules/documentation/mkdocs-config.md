# MkDocs Configuration Guide

**Purpose**: Document MkDocs setup, configuration patterns, and deployment for hms-commander.

**Primary sources**:
- `mkdocs.yml` - Main configuration file
- `docs/` - Documentation content
- MkDocs documentation: https://www.mkdocs.org/

---

## Overview

hms-commander uses MkDocs with Material theme for documentation, deployed to:
- **ReadTheDocs**: https://hms-commander.readthedocs.io/
- **GitHub Pages**: https://gpt-cmdr.github.io/hms-commander/

---

## ⚠️ CRITICAL: ReadTheDocs Symlink Issue

**ReadTheDocs uses `rsync --safe-links` which STRIPS ALL SYMLINKS during build.**

### The Problem

**Local (works)**:
```bash
ln -s ../examples docs/notebooks  # Symlink works locally and on GitHub Pages
mkdocs build                       # ✅ Builds successfully
```

**ReadTheDocs (fails)**:
```bash
# During ReadTheDocs build:
# rsync --safe-links strips symlink
# docs/notebooks/ doesn't exist
# mkdocs build fails or notebooks missing
```

### The Solution

**Option 1: Physical Copy (Recommended)**
```bash
# Before building
cp -r examples docs/notebooks

# Add to .gitignore
echo "docs/notebooks/" >> .gitignore

# Build
mkdocs build
```

**Option 2: Configure mkdocs-jupyter to Read from Source**
```yaml
# mkdocs.yml
plugins:
  - mkdocs-jupyter:
      include: ["examples/*.ipynb"]  # Read from original location
      # Don't use docs/notebooks symlink
```

**Option 3: Pre-build Hook (ReadTheDocs)**
```yaml
# .readthedocs.yml
build:
  os: ubuntu-22.04
  tools:
    python: "3.11"
  jobs:
    pre_build:
      - cp -r examples docs/notebooks
```

**Why This Matters**:
- GitHub Pages: Uses git checkout (symlinks preserved)
- ReadTheDocs: Uses rsync with --safe-links (symlinks DELETED)
- Result: Notebooks work on GitHub Pages but missing from ReadTheDocs

**Decision**: Use physical copies or configure mkdocs-jupyter to read from source location.

---

## Configuration File Structure

### Basic Structure (mkdocs.yml)

```yaml
site_name: HMS Commander Documentation
site_description: Python library for automating HEC-HMS operations
site_url: https://gpt-cmdr.github.io/hms-commander/
repo_url: https://github.com/gpt-cmdr/hms-commander
repo_name: gpt-cmdr/hms-commander

theme:
  name: material
  # ... theme configuration

plugins:
  - search
  - mkdocstrings
  - mkdocs-jupyter
  - git-revision-date-localized

markdown_extensions:
  - pymdownx.highlight
  - pymdownx.superfences
  # ... extensions

nav:
  - Home: index.md
  - Getting Started: ...
  - User Guide: ...
  - API Reference: ...
```

---

## Theme Configuration

### Material Theme Features

```yaml
theme:
  name: material
  palette:
    # Light mode
    - scheme: default
      primary: blue
      accent: light blue
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    # Dark mode
    - scheme: slate
      primary: blue
      accent: light blue
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
  features:
    - navigation.tabs        # Top-level tabs
    - navigation.sections    # Collapsible sections
    - navigation.expand      # Expand all by default
    - navigation.top         # Back to top button
    - search.suggest         # Search suggestions
    - search.highlight       # Highlight search results
    - content.code.copy      # Copy button for code blocks
    - content.code.annotate  # Line annotations
  icon:
    repo: fontawesome/brands/github
  logo: assets/hms-commander_logo.svg
  favicon: assets/favicon.ico
```

**Key features**:
- Dual color scheme (light/dark mode)
- Tabbed navigation for major sections
- Search with suggestions
- Copy buttons on code blocks
- GitHub integration

---

## Plugin Configuration

### 1. mkdocstrings (API Documentation)

**Purpose**: Auto-generate API docs from docstrings

```yaml
plugins:
  - mkdocstrings:
      handlers:
        python:
          options:
            docstring_style: google      # Google-style docstrings
            show_source: true            # Show source code links
            show_root_heading: true      # Show module name
            heading_level: 2             # Start at H2
```

**Usage in docs**:
```markdown
# HmsBasin

::: hms_commander.HmsBasin
    options:
      show_source: true
      heading_level: 2
```

**Generated**: API reference with methods, parameters, returns, examples

### 2. mkdocs-jupyter (Notebook Integration)

**Purpose**: Include Jupyter notebooks in documentation

```yaml
plugins:
  - mkdocs-jupyter:
      include: ["*.ipynb"]           # Include all notebooks
      execute: false                 # Don't re-run cells (use saved output)
      allow_errors: false            # Fail build if notebook has errors
      ignore:
        - "examples/*/hms413_*/**"   # Ignore temp directories
        - "examples/*/multi_version_test/**"
```

**Key settings**:
- `execute: false` - Use saved notebook output (faster, reproducible)
- `allow_errors: false` - Quality gate (notebooks must run without errors)
- `ignore` - Skip temp/test directories

**See**: `.claude/rules/documentation/notebook-standards.md` for notebook requirements

### 3. git-revision-date-localized

**Purpose**: Show "Last updated" timestamps on pages

```yaml
plugins:
  - git-revision-date-localized:
      enable_creation_date: true     # Show creation date
      type: timeago                  # "2 days ago" format
```

**Result**: Footer shows "Last updated: 2 days ago"

### 4. search

**Purpose**: Built-in search functionality

```yaml
plugins:
  - search  # Enabled by default
```

**Features**:
- Full-text search
- Search suggestions (if theme supports)
- Keyboard shortcuts (/)

---

## Markdown Extensions

### Code Highlighting

```yaml
markdown_extensions:
  - pymdownx.highlight:
      anchor_linenums: true    # Linkable line numbers
  - pymdownx.inlinehilite      # Inline code highlighting
  - pymdownx.superfences       # Fenced code blocks
```

**Usage**:
````markdown
```python
from hms_commander import HmsBasin
```
````

### Tabs

```yaml
markdown_extensions:
  - pymdownx.tabbed:
      alternate_style: true
```

**Usage**:
```markdown
=== "Tab 1"
    Content for tab 1

=== "Tab 2"
    Content for tab 2
```

### Admonitions

```yaml
markdown_extensions:
  - admonition
  - pymdownx.details
```

**Usage**:
```markdown
!!! warning "Important"
    This is a warning message

??? note "Expandable Note"
    This is collapsible
```

### Table of Contents

```yaml
markdown_extensions:
  - toc:
      permalink: true          # Add ¶ links to headers
      toc_depth: 3            # Include up to H3 in TOC
```

---

## Navigation Structure

### Best Practices

**Organize by user journey**:
```yaml
nav:
  - Home: index.md
  - Getting Started:           # New users start here
      - Installation: ...
      - Quick Start: ...
  - User Guide:                # Feature documentation
      - Project Management: ...
      - Basin Models: ...
      - Execution: ...
  - Example Notebooks:         # Working examples
      - Basic Usage: ...
      - File Operations: ...
  - API Reference:             # Detailed reference
      - Core Classes: ...
      - Execution: ...
  - LLM Forward Approach:      # Contributing
      - Overview: ...
      - Contributing: ...
```

**Principles**:
- Top-level sections as tabs (Material theme)
- Group related content in subsections
- Order by typical usage (beginner → advanced)
- API reference separate from guides

### Navigation Validation

**Check for**:
- All files referenced in nav exist
- No orphaned pages (exist but not in nav)
- Logical grouping and order
- Consistent nesting depth

**Tool**: Run `mkdocs build --strict` to catch broken links

---

## Deployment

### Local Preview

```bash
# Install dependencies
pip install -e ".[all]"  # Includes mkdocs dependencies

# Preview locally
cd C:\GH\hms-commander
mkdocs serve

# Access at: http://127.0.0.1:8000
```

**Use for**: Testing changes before commit

### GitHub Pages Deployment

```bash
# Build and deploy to gh-pages branch
mkdocs gh-deploy --force

# Result: https://gpt-cmdr.github.io/hms-commander/
```

**Process**:
1. Builds documentation (mkdocs build)
2. Pushes to gh-pages branch
3. GitHub Pages serves from gh-pages branch

**Configuration**: Enabled in GitHub repo settings

### ReadTheDocs Deployment

**Automatic**: Webhook triggers build on every git push

**Configuration** (.readthedocs.yml):
```yaml
version: 2

build:
  os: ubuntu-22.04
  tools:
    python: "3.11"

mkdocs:
  configuration: mkdocs.yml

python:
  install:
    - method: pip
      path: .
      extra_requirements:
        - all
```

**URL**: https://hms-commander.readthedocs.io/

**Note**: Remember symlink issue! Use physical copies or configure paths appropriately.

---

## Directory Structure

```
hms-commander/
├── mkdocs.yml                 # Main config
├── docs/                      # Documentation source
│   ├── index.md              # Home page
│   ├── getting_started/
│   ├── user_guide/
│   ├── api/                  # API reference (mkdocstrings)
│   ├── examples/             # ⚠️ Symlink issue (use copy or config path)
│   ├── data_formats/
│   ├── llm_dev/
│   ├── assets/               # Images, logos
│   └── stylesheets/          # Custom CSS
├── examples/                  # Jupyter notebooks (source)
├── site/                      # Generated output (gitignored)
└── .readthedocs.yml          # ReadTheDocs config
```

---

## Custom Styling

### Custom CSS

**File**: `docs/stylesheets/extra.css`

**Usage**:
```yaml
# mkdocs.yml
extra_css:
  - stylesheets/extra.css
```

**Example customizations**:
- Adjust colors
- Font sizes
- Code block styling
- Table formatting

---

## Quality Checks

### Pre-Commit Checklist

- [ ] `mkdocs build` succeeds without errors
- [ ] `mkdocs build --strict` catches all broken links
- [ ] `mkdocs serve` preview renders correctly
- [ ] All nav links functional
- [ ] No 404s in browser console
- [ ] Notebooks render correctly (if using mkdocs-jupyter)
- [ ] API docs generate from docstrings
- [ ] Search functionality works

### Build Validation

```bash
# Clean build
rm -rf site/
mkdocs build

# Strict mode (fail on warnings)
mkdocs build --strict

# Preview
mkdocs serve

# Check for:
# - Build warnings/errors
# - Missing pages
# - Broken links
# - Rendering issues
```

### ReadTheDocs Specific

- [ ] No symlinks (or pre-build hook copies files)
- [ ] All paths relative to docs/ or absolute
- [ ] Requirements installable via pip
- [ ] Build succeeds on ReadTheDocs platform

---

## Common Issues

### Issue: "File not found" in Navigation

**Symptom**: mkdocs build warns "File not found: docs/path/file.md"

**Solution**: Either:
- Create the missing file
- Remove from nav
- Fix path (check case sensitivity)

### Issue: API Docs Not Generating

**Symptom**: `::: module.Class` doesn't render

**Solution**:
- Check module is importable (`python -c "import module"`)
- Check docstring format (Google style)
- Check mkdocstrings plugin installed
- Try: `mkdocs build --verbose`

### Issue: Notebooks Not Rendering

**Symptom**: Notebooks don't appear in docs

**Solutions**:
- Check symlink issue (use copy instead)
- Check notebook in nav
- Check mkdocs-jupyter `ignore` patterns
- Check notebook first cell is markdown H1

### Issue: Broken Links After Restructure

**Symptom**: Many 404 errors after moving files

**Solution**:
- Run `mkdocs build --strict` to find all broken links
- Update nav in mkdocs.yml
- Update internal links in .md files
- Check relative vs absolute paths

### Issue: ReadTheDocs Build Different from Local

**Symptom**: Looks good locally but broken on ReadTheDocs

**Solutions**:
- Check symlink usage (physical copy instead)
- Check .readthedocs.yml Python version matches local
- Check all dependencies in setup.py `[all]`
- View ReadTheDocs build log for errors

---

## Related Documentation

**Notebook Standards**: `.claude/rules/documentation/notebook-standards.md`
**Documentation Agent**: `.claude/agents/documentation-generator/SUBAGENT.md`
**MkDocs Docs**: https://www.mkdocs.org/
**Material Theme**: https://squidfunk.github.io/mkdocs-material/
**mkdocstrings**: https://mkdocstrings.github.io/
**mkdocs-jupyter**: https://github.com/danielfrg/mkdocs-jupyter

---

## Quick Reference

**Local preview**: `mkdocs serve`
**Build**: `mkdocs build`
**Strict build**: `mkdocs build --strict`
**Deploy GitHub Pages**: `mkdocs gh-deploy --force`
**Clean**: `rm -rf site/`

**Key files**:
- `mkdocs.yml` - Configuration
- `docs/` - Content source
- `site/` - Generated output (gitignored)
- `.readthedocs.yml` - ReadTheDocs config
