# Example Notebooks

HMS Commander provides a growing set of Jupyter notebook examples demonstrating real-world workflows, organized by learning progression.

The canonical notebook source is the repository-level [`examples/`](https://github.com/gpt-cmdr/hms-commander/tree/main/examples) directory. MkDocs currently renders only selected benchmark notebooks under `docs/notebooks/`; the catalog below links to the source notebooks on GitHub when a rendered docs copy is not intentionally published.

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

**New to hms-commander?** Start with [00 - Overview](https://github.com/gpt-cmdr/hms-commander/blob/main/examples/00_overview.ipynb) for environment verification and learning path guidance.

### Beginner Track (30-45 minutes)

| Notebook | Description |
|----------|-------------|
| [00 - Overview](https://github.com/gpt-cmdr/hms-commander/blob/main/examples/00_overview.ipynb) | Environment verification, HMS glossary, learning path |
| [01 - Basic Workflow](https://github.com/gpt-cmdr/hms-commander/blob/main/examples/01_basic_workflow.ipynb) | Initialize, execute, extract results (start here!) |
| [02 - Project DataFrames](https://github.com/gpt-cmdr/hms-commander/blob/main/examples/02_project_dataframes.ipynb) | Explore project structure via DataFrames |

### Intermediate Track (60-90 minutes)

| Notebook | Description |
|----------|-------------|
| [03 - File Operations](https://github.com/gpt-cmdr/hms-commander/blob/main/examples/03_file_ops_basin_met_control_gage.ipynb) | HmsBasin, HmsMet, HmsControl, HmsGage file operations |
| [04 - Run Management](https://github.com/gpt-cmdr/hms-commander/blob/main/examples/04_run_management.ipynb) | Configure and validate simulation runs |
| [05 - Clone Workflow](https://github.com/gpt-cmdr/hms-commander/blob/main/examples/05_clone_workflow.ipynb) | Non-destructive model modifications for QAQC |
| [06 - Results and DSS](https://github.com/gpt-cmdr/hms-commander/blob/main/examples/06_results_dss.ipynb) | DSS operations and results extraction |

### Advanced Track (45-90 minutes)

| Notebook | Description |
|----------|-------------|
| [07 - Jython Execution](https://github.com/gpt-cmdr/hms-commander/blob/main/examples/07_execution_jython.ipynb) | Version detection, script generation, batch execution |
| [08 - M3 Models](https://github.com/gpt-cmdr/hms-commander/blob/main/examples/08_m3_models.ipynb) | HCFCD M3 model discovery and extraction |
| [09 - M3 Conversion](https://github.com/gpt-cmdr/hms-commander/blob/main/examples/09_m3_conversion.ipynb) | HMS 3.x to 4.x project conversion workflow |

### Storm Generation (30-45 minutes)

| Notebook | Description |
|----------|-------------|
| [10 - Atlas 14 Hyetograph](https://github.com/gpt-cmdr/hms-commander/blob/main/examples/10_atlas14_hyetograph.ipynb) | Generate design storms from NOAA Atlas 14 |
| [11 - Frequency Storm](https://github.com/gpt-cmdr/hms-commander/blob/main/examples/11_frequency_storm.ipynb) | Variable duration storms using TP-40/Hydro-35 patterns |

### Official HEC-HMS Guide Mirrors (45-90 minutes)

These notebooks cite the official HEC-HMS Tutorials and Guides category pages
and show the hms-commander equivalent for workflows that are already supported
by the public API.

| Notebook | Official guide category |
|----------|-------------------------|
| [101 - Basic Model Setup](../notebooks/101_guide_basic_model_setup.ipynb) | Basic model setup, simulation execution, and DSS hydrograph review |
| [102 - Meteorologic Methods](../notebooks/102_guide_meteorologic_methods.ipynb) | Historical gage hyetographs, gridded met assets, frequency storms, Atlas 14, and SCS temporal patterns |
| [103 - GIS and Terrain Data](../notebooks/103_guide_gis_terrain_data.ipynb) | GIS tools, model-type detection, subbasin/stream maps, and GeoJSON extraction |
| [104 - Basin Methods, Loss, Transform, and Routing](../notebooks/104_guide_basin_methods_loss_transform.ipynb) | Parameter estimation, CN sensitivity, unit hydrographs, baseflow, and reach routing attenuation |
| [105 - Calibration and Validation](../notebooks/105_guide_calibration_validation.ipynb) | Observed-vs-modeled hydrographs, residuals, calibration scaffolding, and Manning roughness sensitivity |
| [106 - Advanced Analysis](../notebooks/106_guide_advanced_analysis.ipynb) | Batch-run scaffolding, computed parameter ensembles, fan charts, and objective convergence |

### TauDEM to HMS Assembly (30-60 minutes)

| Notebook | Description |
|----------|-------------|
| [21 - TauDEM to HMS Atlas 14 Bootstrap](../notebooks/21_taudem_to_hms_atlas14.ipynb) | Build a TauDEM-derived HMS basin, validate import, and run a Spring Creek Atlas 14 frequency storm |

Status note:

- the notebook is a live Spring Creek benchmark and now proves the path is import-valid and compute-valid
- the resulting scaffold still carries modeling residuals that must be handled before production use: missing ET/canopy methods, Muskingum stability warnings, lag-vs-time-step warnings, and negative inflow clipping
- future roadmap work adds the readiness gate, TauDEM parameter tuning/comparison support, and human-review QAQC bundle around this notebook-driven workflow

### Validation & Equivalence Proofs (20-30 minutes)

These notebooks demonstrate hms-commander storm-generation equivalence against reference data and HEC-HMS output:

| Notebook | Description |
|----------|-------------|
| [12 - SCS Type Validation](https://github.com/gpt-cmdr/hms-commander/blob/main/examples/12_scs_type_validation.ipynb) | SCS Type I, IA, II, III equivalence proof |
| [13 - Atlas 14 Multi-Duration](https://github.com/gpt-cmdr/hms-commander/blob/main/examples/13_atlas14_multiduration_validation.ipynb) | Multi-duration Atlas 14 validation (6h, 12h, 24h, 96h) |
| [22 - Ground Truth Validation](https://github.com/gpt-cmdr/hms-commander/blob/main/examples/22_ground_truth_validation.ipynb) | HEC-HMS 4.13 PRECIP-INC fixtures for SCS Type I/II/III and TP-40 frequency storms |

### AORC Integration (30-60 minutes)

| Notebook | Description |
|----------|-------------|
| [14a - AORC Download](https://github.com/gpt-cmdr/hms-commander/blob/main/examples/14a_aorc_download.ipynb) | Download AORC precipitation from NOAA AWS |
| [14b - AORC Grid Setup](https://github.com/gpt-cmdr/hms-commander/blob/main/examples/14b_aorc_grid_setup.ipynb) | Create grid definitions and HRAP cell mappings |
| [14c - AORC HMS Execution](https://github.com/gpt-cmdr/hms-commander/blob/main/examples/14c_aorc_hms_execution.ipynb) | Run HMS with gridded precipitation |

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
# For source development, use the active repo development environment
# and make sure this checkout is on PYTHONPATH or installed editable.
```

## Testing with Real Projects

Examples use actual HEC-HMS projects for real-world applicability:
- **castro** - Simple watershed model
- **tifton** - Time series demonstration
- **tenk** - Gridded precipitation example
- **M3 models** - FEMA-effective H&H models (HCFCD)

## Contributing Examples

We welcome example contributions! To add a notebook:

1. Follow the repository notebook rules in [`examples/AGENTS.md`](https://github.com/gpt-cmdr/hms-commander/blob/main/examples/AGENTS.md)
2. Use `HmsExamples.extract_project()` for reproducibility
3. Include pip cell + dev environment note
4. Execute and save outputs
5. Add to `mkdocs.yml` navigation

See [Contributing Guide](../llm_dev/contributing.md) for details.

## Next Steps

- **New users**: Start with [01 - Basic Workflow](https://github.com/gpt-cmdr/hms-commander/blob/main/examples/01_basic_workflow.ipynb)
- **API details**: See [API Reference](../api/hms_prj.md)
- **Concepts**: Review [User Guide](../user_guide/overview.md)
