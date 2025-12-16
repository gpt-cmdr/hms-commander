# HMS Commander Documentation

This directory contains the source files for HMS Commander's MkDocs documentation.

## Building Documentation Locally

### Install Dependencies

```bash
# Install with docs dependencies
pip install -e ".[docs]"
```

This installs:
- mkdocs
- mkdocs-material (theme)
- mkdocstrings (API docs from docstrings)
- mkdocs-jupyter (notebook integration)
- mkdocs-git-revision-date-localized-plugin

### Serve Documentation

```bash
# From repository root
mkdocs serve
```

Open http://localhost:8000 in your browser.

### Build Static Site

```bash
mkdocs build
```

Output will be in `site/` directory.

## Documentation Structure

```
docs/
├── index.md                      # Home page
├── getting_started/
│   ├── installation.md           # Installation guide
│   ├── quick_start.md            # Quick start guide
│   └── project_initialization.md # Project setup
├── user_guide/
│   ├── overview.md
│   ├── project_management.md
│   ├── basin_models.md
│   ├── meteorologic_models.md
│   ├── control_specs.md
│   ├── gages.md
│   ├── run_configuration.md
│   ├── execution.md
│   ├── geospatial.md
│   ├── dss_operations.md
│   ├── results_analysis.md
│   ├── clone_workflows.md
│   └── atlas14_updates.md
├── examples/
│   ├── overview.md               # Example notebook index
│   └── *.ipynb                   # Jupyter notebooks
├── api/
│   ├── hms_prj.md                # API reference pages
│   ├── hms_basin.md              # (auto-generated from docstrings)
│   └── ...
├── data_formats/
│   ├── overview.md
│   ├── project_file.md           # .hms file format
│   ├── basin_file.md             # .basin format
│   └── ...
├── llm_dev/
│   ├── overview.md
│   ├── contributing.md           # Contribution guide
│   ├── claude_md.md              # CLAUDE.md guide
│   ├── style_guide.md            # Style guide reference
│   ├── architecture.md
│   └── release_notes.md
├── assets/
│   ├── hms-commander_logo.svg    # Logo file
│   └── favicon.ico
└── stylesheets/
    └── extra.css                 # Custom CSS
```

## Navigation Structure

Navigation is defined in `mkdocs.yml` in the repository root. The structure follows:

1. **Home** - Landing page
2. **Getting Started** - Installation and quick start
3. **User Guide** - Comprehensive feature documentation
4. **Example Notebooks** - Jupyter notebook tutorials
5. **API Reference** - Complete API documentation
6. **HMS Data Formats** - File format specifications
7. **LLM Forward Approach** - Contributing and development guides

## Writing Documentation

### Markdown Files

Use standard Markdown with these extensions:

- **Code blocks**: Triple backticks with language
- **Admonitions**: `!!! note`, `!!! warning`, etc.
- **Tabs**: For alternative code examples
- **Icons**: Material Design icons via emoji syntax

Example:

```markdown
# Page Title

Brief introduction.

## Section

!!! note
    Important information for users.

### Code Example

```python
from hms_commander import HmsBasin

subbasins = HmsBasin.get_subbasins("model.basin")
```

See the [API Reference](../api/hms_basin.md) for details.
```

### API Reference

API documentation is auto-generated from docstrings using mkdocstrings:

```markdown
# HmsBasin

::: hms_commander.hms_basin.HmsBasin
```

This extracts all docstrings from the `HmsBasin` class.

### Jupyter Notebooks

Notebooks in `examples/` are automatically integrated via mkdocs-jupyter plugin.

To include a notebook in navigation:

```yaml
# mkdocs.yml
nav:
  - Example Notebooks:
      - Clone Workflow: examples/clone_workflow.ipynb
```

## Theme Customization

### Colors

HMS Commander uses a green theme (vs. RAS Commander's blue):

- Primary: Green (`#43A047`)
- Accent: Light Green (`#66BB6A`)

Defined in `mkdocs.yml`:

```yaml
theme:
  palette:
    - scheme: default
      primary: green
      accent: light green
```

### Custom CSS

Additional styling in `docs/stylesheets/extra.css`.

### Logo

Logo files:
- SVG: `docs/assets/hms-commander_logo.svg`
- Favicon: `docs/assets/favicon.ico` (if available)

## Deployment

### GitHub Pages

Documentation is automatically built and deployed to GitHub Pages via GitHub Actions.

### ReadTheDocs

Configuration in `.readthedocs.yaml`.

## Contributing to Documentation

When adding documentation:

1. Follow existing structure
2. Use clear, concise language
3. Include code examples
4. Add to `mkdocs.yml` navigation
5. Test locally with `mkdocs serve`
6. Ensure all links work

See [Contributing Guide](llm_dev/contributing.md) for details.

## Material Theme Features

The Material theme provides:

- **Search**: Full-text search
- **Dark mode**: User-selectable theme
- **Navigation tabs**: Top-level navigation
- **Code copy**: Copy button on code blocks
- **Annotations**: Interactive code annotations

## Maintenance

### Updating API Reference

API docs are auto-generated. Just update docstrings in code:

```python
def new_function(param: str) -> bool:
    """
    New function description.

    Args:
        param (str): Parameter description

    Returns:
        bool: Result

    Example:
        >>> new_function("test")
        True
    """
```

The documentation will update automatically.

### Adding Pages

1. Create Markdown file in appropriate directory
2. Add to `mkdocs.yml` navigation
3. Test locally
4. Submit PR

## Questions?

- Documentation structure questions: See `mkdocs.yml`
- Styling issues: Check `extra.css`
- Build errors: Review `.readthedocs.yaml`
- Content questions: Open an issue

---

For more information, see:
- [MkDocs Documentation](https://www.mkdocs.org/)
- [Material Theme](https://squidfunk.github.io/mkdocs-material/)
- [MkDocstrings](https://mkdocstrings.github.io/)
