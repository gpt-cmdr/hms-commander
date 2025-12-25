# HMS Commander Data Files

This folder contains reference data used by hms-commander.

## M3 HMS Project Catalog

**File**: `m3_hms_catalog.csv`

A catalog of HEC-HMS projects contained within the HCFCD M3 Models (Harris County Flood Control District FEMA Effective Models).

### Catalog Columns

| Column | Description |
|--------|-------------|
| `model_id` | M3 Model letter (A-W, excluding V) |
| `model_name` | Watershed/bayou name |
| `unit_id` | HCFCD Unit Number (e.g., D100-00-00) |
| `hms_file` | HMS project filename |
| `project_name` | HMS project name (from .hms file) |
| `description` | Project description |
| `hms_version` | HEC-HMS version (3.3 or 3.4) |
| `unit_system` | English or Metric |
| `loss_method` | Loss method (Green and Ampt, Initial+Constant) |
| `transform_method` | Transform method (Clark, Modified Clark) |
| `baseflow_method` | Baseflow method (None, Recession) |
| `routing_method` | Routing method (Lag, Modified Puls, Muskingum) |
| `design_storms` | Available design storm frequencies |
| `rainfall_region` | HCFCD rainfall region (1, 2, or 3) |
| `dss_file` | DSS output filename |
| `relative_path` | Relative path within M3 model zip |

### Statistics

- **Total HMS Projects**: 42 (unique)
- **M3 Models with HMS**: 20 (of 22 total M3 models)
- **HMS Versions**: 3.3 (41 projects), 3.4 (1 project)
- **Design Storms**: Typically 0.2%, 1%, 2%, 10% AEP (some have additional frequencies)

### Models by Watershed

| Model | Watershed | HMS Projects |
|-------|-----------|--------------|
| A | Clear Creek | 1 |
| B | Armand Bayou | 1 |
| C | Sims Bayou | 1 |
| D | Brays Bayou | 1 |
| E | White Oak Bayou | 1 |
| F | San Jacinto/Galveston Bay | 2 |
| G | San Jacinto River | 16 |
| H | Hunting Bayou | 1 |
| I | Vince Bayou | 1 |
| J | Spring Creek | 1 |
| K | Cypress Creek | 2 |
| L | Little Cypress Creek | 2 |
| M | Willow Creek | 1 |
| N | Carpenters Bayou | 1 |
| O | Spring Gully/Goose Creek | 2 |
| P | Greens Bayou | 1 |
| Q | Cedar Bayou | 1 |
| R | Jackson Bayou | 1 |
| S | Luce Bayou | 2 |
| T | Barker | 1 |
| U | Addicks | 1 |
| W | Buffalo Bayou | 1 |

### Usage

```python
from hms_commander import HmsM3Model

# List all HMS projects
projects = HmsM3Model.list_projects()

# Get projects for a specific model
brays_projects = HmsM3Model.list_projects(model_id='D')

# Extract a project
path = HmsM3Model.extract_project('D', 'D100-00-00')
```

### Source

- **M3 Models Website**: https://www.m3models.org/
- **Download Library**: https://www.m3models.org/Downloads/ModelLibrary
- **Data Source**: Harris County Flood Control District (HCFCD)
- **Model Type**: FEMA Effective H&H Models
- **Last Updated**: 2024 (various effective dates per model)

### Notes

1. All projects use HMS 3.x format (requires `python2_compatible=True` for Jython execution)
2. Most projects use Metric units
3. Design storms are based on HCFCD rainfall regions (not Atlas 14)
4. Models K and L share some HMS projects (Cypress Creek watershed)
5. Model G (San Jacinto River) has the most HMS projects (16)
6. Some unit IDs have duplicate paths (alternate versions)
