# HMS Documentation

You are helping a developer work with hms-commander documentation.

## Documentation System

**hms-commander uses MkDocs with Material theme** for documentation.

**Live Site**: [hms-commander.readthedocs.io](https://hms-commander.readthedocs.io)

**Repository**: Documentation source files are in `docs/`

## Quick Commands

### Build Documentation Locally

```bash
# Build static site
mkdocs build

# Output: site/ folder with HTML
```

**When to use**: Before committing documentation changes, to verify formatting.

### Serve Documentation Locally

```bash
# Start local dev server
mkdocs serve

# Access at: http://127.0.0.1:8000
# Auto-reloads on file changes
```

**When to use**: While writing documentation, to preview changes in real-time.

### Deploy to ReadTheDocs

**Automatic**: ReadTheDocs deploys on every push to `main` branch.

**Manual**: Not typically needed, but available via `mkdocs gh-deploy` (for GitHub Pages).

## Documentation Structure

```
hms-commander/
├── mkdocs.yml              # MkDocs configuration
├── docs/                   # Documentation source
│   ├── index.md            # Landing page
│   ├── getting-started.md  # Quick start guide
│   ├── api/                # API reference
│   │   ├── basin.md        # HmsBasin API
│   │   ├── met.md          # HmsMet API
│   │   ├── control.md      # HmsControl API
│   │   ├── cmdr.md         # HmsCmdr API
│   │   └── ...
│   ├── guides/             # How-to guides
│   │   ├── installation.md
│   │   ├── basic-usage.md
│   │   └── ...
│   └── examples/           # Tutorials
│       ├── basin-ops.md
│       ├── run-simulation.md
│       └── ...
└── site/                   # Generated HTML (gitignored)
```

## Adding New Pages

### 1. Create Markdown File

Create a new `.md` file in appropriate folder:
- `docs/api/` - API reference
- `docs/guides/` - How-to guides
- `docs/examples/` - Tutorials

### 2. Add to Navigation

Edit `mkdocs.yml` to add page to navigation:

```yaml
nav:
  - Home: index.md
  - Getting Started: getting-started.md
  - API Reference:
      - Basin: api/basin.md
      - Met: api/met.md
      - Your New Page: api/your-new-page.md  # Add here
  - Guides:
      - Installation: guides/installation.md
      - Your New Guide: guides/your-new-guide.md  # Add here
```

### 3. Preview Changes

```bash
mkdocs serve
# Navigate to your new page at http://127.0.0.1:8000
```

## Adding API Documentation

### Pattern: Document a Class

**File**: `docs/api/{classname}.md`

**Template**:

```markdown
# {ClassName}

{Brief description of class purpose}

## Overview

{Detailed description}

**Class**: `{ClassName}` (static methods, no instantiation)
**Location**: `hms_commander/{ClassName}.py`

## Core Methods

### {method_name}()

{Description}

**Parameters**:
- `param1` (type): Description
- `param2` (type): Description

**Returns**: {Return type and description}

**Example**:
```python
from hms_commander import {ClassName}

result = {ClassName}.{method_name}(param1, param2)
```

### {another_method}()

{Description}

**Parameters**:
- `param` (type): Description

**Returns**: {Return type and description}

**Example**:
```python
# Example code
```

## Common Workflows

### Workflow: {Workflow Name}

{Description}

```python
# Complete example
```

## See Also

- [{Related Class}](related-class.md)
- [Guide: {Related Guide}](../guides/related-guide.md)
```

**Reference**: See existing `docs/api/basin.md` for complete example.

## Adding Guides/Tutorials

### Pattern: How-To Guide

**File**: `docs/guides/{guide-name}.md`

**Template**:

```markdown
# {Guide Title}

{Brief description of what this guide teaches}

## Prerequisites

- {Prerequisite 1}
- {Prerequisite 2}

## Step 1: {Step Name}

{Description}

```python
# Code example
```

## Step 2: {Step Name}

{Description}

```python
# Code example
```

## Complete Example

```python
# Full working example
```

## Next Steps

- [Guide: {Next Guide}]({next-guide}.md)
- [API: {Related API}](../api/{api}.md)
```

**Reference**: See existing `docs/guides/basic-usage.md` for example.

## MkDocs Configuration

**File**: `mkdocs.yml`

**Key Sections**:

```yaml
site_name: HMS Commander
site_url: https://hms-commander.readthedocs.io
repo_url: https://github.com/jetillett/hms-commander

theme:
  name: material
  features:
    - navigation.tabs
    - navigation.sections
    - toc.integrate
    - search.highlight

nav:
  - Home: index.md
  - Getting Started: getting-started.md
  - API Reference:
      - Basin: api/basin.md
      # Add new API pages here
  - Guides:
      - Installation: guides/installation.md
      # Add new guides here

markdown_extensions:
  - admonition
  - codehilite
  - toc:
      permalink: true

plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          paths: [hms_commander]
```

**See**: [MkDocs Material Documentation](https://squidfunk.github.io/mkdocs-material/) for advanced features.

## Documentation Best Practices

### Write for Users, Not Developers

**Good**:
```markdown
Use `HmsBasin.get_subbasins()` to extract all subbasins to a DataFrame:

```python
subbasins = HmsBasin.get_subbasins("project.basin")
print(f"Found {len(subbasins)} subbasins")
```
```

**Bad**:
```markdown
The `get_subbasins` method uses HmsFileParser to extract Subbasin blocks...
```

### Show Examples, Not Just Signatures

**Good**:
```markdown
```python
from hms_commander import init_hms_project, HmsCmdr

init_hms_project(r"C:\Projects\watershed")
HmsCmdr.compute_run("Run 1")
```
```

**Bad**:
```markdown
`compute_run(run_name: str, hms_object=None) -> bool`
```

### Link to Related Content

```markdown
See also:
- [HmsMet API](met.md) - Update meteorologic models
- [Guide: Running Simulations](../guides/run-simulation.md)
- [Example: Basin Operations](../examples/basin-ops.md)
```

### Use Admonitions for Important Info

```markdown
!!! note
    HMS 3.x requires `python2_compatible=True` for script generation.

!!! warning
    This method modifies the file in-place. Use `clone_basin()` for non-destructive workflows.

!!! tip
    Use `HmsExamples.extract_project()` to get test data.
```

## Jupyter Notebook Integration

**Pattern**: Convert notebooks to markdown for docs

```bash
# Convert notebook to markdown
jupyter nbconvert --to markdown examples/01_multi_version_execution.ipynb

# Move to docs
mv examples/01_multi_version_execution.md docs/examples/multi-version-execution.md

# Add to mkdocs.yml nav
```

**Note**: Consider using `nbconvert` to keep notebook docs in sync.

**See**: `.claude/rules/documentation/notebook-standards.md` for notebook conventions.

## ReadTheDocs Configuration

**File**: `.readthedocs.yml` (root of repository)

**Template**:

```yaml
version: 2

mkdocs:
  configuration: mkdocs.yml

python:
  version: "3.10"
  install:
    - requirements: docs/requirements.txt
```

**File**: `docs/requirements.txt`

```
mkdocs>=1.4
mkdocs-material>=9.0
mkdocstrings>=0.20
mkdocstrings-python>=0.8
```

**See**: `.claude/rules/documentation/mkdocs-config.md` for complete ReadTheDocs setup.

## Common Tasks

### Task: Add New API Class Documentation

1. Create `docs/api/{classname}.md`
2. Document class, methods, examples
3. Add to `mkdocs.yml` under "API Reference"
4. Run `mkdocs serve` to preview
5. Commit and push (ReadTheDocs auto-deploys)

### Task: Add New Guide

1. Create `docs/guides/{guide-name}.md`
2. Write step-by-step tutorial with code examples
3. Add to `mkdocs.yml` under "Guides"
4. Run `mkdocs serve` to preview
5. Commit and push

### Task: Update Existing Documentation

1. Edit `.md` file in `docs/`
2. Run `mkdocs serve` to preview changes
3. Verify formatting and links
4. Commit and push

### Task: Reorganize Navigation

1. Edit `mkdocs.yml` `nav:` section
2. Rearrange or nest pages
3. Run `mkdocs serve` to verify navigation
4. Commit and push

## Troubleshooting

### Build Fails

```bash
# Check MkDocs configuration
mkdocs build --strict

# Common issues:
# - Missing page in nav
# - Broken internal links
# - Invalid YAML in mkdocs.yml
```

### Navigation Not Showing

- Verify page is added to `mkdocs.yml` `nav:` section
- Check indentation in YAML (use 2 spaces)
- Restart `mkdocs serve`

### Code Highlighting Not Working

- Verify `markdown_extensions` in `mkdocs.yml` includes `codehilite`
- Use triple backticks with language: ` ```python `

### ReadTheDocs Build Failing

- Check `.readthedocs.yml` configuration
- Verify `docs/requirements.txt` has all dependencies
- Check ReadTheDocs build logs: https://readthedocs.org/projects/hms-commander/

## Resources

**MkDocs**:
- [MkDocs Documentation](https://www.mkdocs.org/)
- [MkDocs Material Theme](https://squidfunk.github.io/mkdocs-material/)
- [MkDocStrings (API docs from docstrings)](https://mkdocstrings.github.io/)

**ReadTheDocs**:
- [ReadTheDocs Documentation](https://docs.readthedocs.io/)
- [HMS Commander on ReadTheDocs](https://readthedocs.org/projects/hms-commander/)

**Writing Style**:
- [Google Developer Documentation Style Guide](https://developers.google.com/style)
- [Write the Docs](https://www.writethedocs.org/)

## Quick Reference

**Build docs**: `mkdocs build`
**Serve docs**: `mkdocs serve`
**Add page**: Create `.md` in `docs/`, add to `mkdocs.yml` `nav:`
**Preview**: http://127.0.0.1:8000
**Deploy**: Push to `main` (ReadTheDocs auto-deploys)

**Key Files**:
- `mkdocs.yml` - Configuration and navigation
- `docs/` - Documentation source
- `.readthedocs.yml` - ReadTheDocs configuration
- `docs/requirements.txt` - Documentation dependencies

**See Also**:
- `.claude/rules/documentation/mkdocs-config.md` - ReadTheDocs patterns
- `.claude/rules/documentation/notebook-standards.md` - Jupyter integration
