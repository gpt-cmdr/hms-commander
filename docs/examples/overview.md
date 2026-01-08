# Example Notebooks

HMS Commander provides 17 comprehensive Jupyter notebook examples demonstrating real-world workflows, organized by learning progression.

## Running the Examples

### Setup

```bash
# Install with all dependencies
pip install hms-commander[all]

# Clone repository
git clone https://github.com/gpt-cmdr/hms-commander.git
cd hms-commander/examples

# Start Jupyter
jupyter notebook
```

### Using HMS Example Projects

Most notebooks use HEC-HMS example projects that are automatically extracted:

```python
from hms_commander import HmsExamples

# Extract an example project
project_path = HmsExamples.extract_project("castro")

# Or see available projects
projects = HmsExamples.list_projects()
```

---

## Learning Path

**New to hms-commander?** Start with [00 - Overview](../notebooks/00_overview.ipynb) for environment verification and learning path guidance.

### Beginner Track (30-45 minutes)

| Notebook | Description |
|----------|-------------|
| [00 - Overview](../notebooks/00_overview.ipynb) | Environment verification, HMS glossary, learning path |
| [01 - Basic Workflow](../notebooks/01_basic_workflow.ipynb) | Initialize, execute, extract results (start here!) |
| [02 - Project DataFrames](../notebooks/02_project_dataframes.ipynb) | Explore project structure via DataFrames |

### Intermediate Track (60-90 minutes)

| Notebook | Description |
|----------|-------------|
| [03 - File Operations](../notebooks/03_file_ops_basin_met_control_gage.ipynb) | HmsBasin, HmsMet, HmsControl, HmsGage file operations |
| [04 - Run Management](../notebooks/04_run_management.ipynb) | Configure and validate simulation runs |
| [05 - Clone Workflow](../notebooks/05_clone_workflow.ipynb) | Non-destructive model modifications for QAQC |
| [06 - Results and DSS](../notebooks/06_results_dss.ipynb) | DSS operations and results extraction |

### Advanced Track (45-90 minutes)

| Notebook | Description |
|----------|-------------|
| [07 - Jython Execution](../notebooks/07_execution_jython.ipynb) | Version detection, script generation, batch execution |
| [08 - M3 Models](../notebooks/08_m3_models.ipynb) | HCFCD M3 model discovery and extraction |
| [09 - M3 Conversion](../notebooks/09_m3_conversion.ipynb) | HMS 3.x to 4.x project conversion workflow |

### Storm Generation (30-45 minutes)

| Notebook | Description |
|----------|-------------|
| [10 - Atlas 14 Hyetograph](../notebooks/10_atlas14_hyetograph.ipynb) | Generate design storms from NOAA Atlas 14 |
| [11 - Frequency Storm](../notebooks/11_frequency_storm.ipynb) | Variable duration storms using TP-40/Hydro-35 patterns |

### Validation & Equivalence Proofs (20-30 minutes)

These notebooks demonstrate that hms-commander algorithms produce identical results to HEC-HMS (validated to 10^-6 precision):

| Notebook | Description |
|----------|-------------|
| [12 - SCS Type Validation](../notebooks/12_scs_type_validation.ipynb) | SCS Type I, IA, II, III equivalence proof |
| [13 - Atlas 14 Multi-Duration](../notebooks/13_atlas14_multiduration_validation.ipynb) | Multi-duration Atlas 14 validation (6h, 12h, 24h, 96h) |

### AORC Integration (30-60 minutes)

| Notebook | Description |
|----------|-------------|
| [14a - AORC Download](../notebooks/14a_aorc_download.ipynb) | Download AORC precipitation from NOAA AWS |
| [14b - AORC Grid Setup](../notebooks/14b_aorc_grid_setup.ipynb) | Create grid definitions and HRAP cell mappings |
| [14c - AORC HMS Execution](../notebooks/14c_aorc_hms_execution.ipynb) | Run HMS with gridded precipitation |

---

## All Notebooks Have

✅ **Executed outputs** - See expected results before running
✅ **Visualizations** - Charts and plots embedded
✅ **Validation** - Assertions and quality checks
✅ **Prerequisites** - Clear requirements documented
✅ **Troubleshooting** - Common issues and solutions

## Development Pattern

All notebooks use the standard two-cell import pattern:

```python
# Cell 1: pip install
# pip install hms-commander

# Cell 2: Development note
# For Development: Use hmscmdr_local conda environment (editable install)
```

## Testing with Real Projects

Examples use actual HEC-HMS projects for real-world applicability:
- **castro** - Simple watershed model
- **tifton** - Time series demonstration
- **tenk** - Gridded precipitation example
- **M3 models** - FEMA-effective H&H models (HCFCD)

## Contributing Examples

We welcome example contributions! To add a notebook:

1. Follow the [notebook standards](.claude/rules/documentation/notebook-standards.md)
2. Use `HmsExamples.extract_project()` for reproducibility
3. Include pip cell + dev environment note
4. Execute and save outputs
5. Add to `mkdocs.yml` navigation

See [Contributing Guide](../llm_dev/contributing.md) for details.

## Next Steps

- **New users**: Start with [01 - Basic Workflow](../notebooks/01_basic_workflow.ipynb)
- **API details**: See [API Reference](../api/hms_prj.md)
- **Concepts**: Review [User Guide](../user_guide/overview.md)
