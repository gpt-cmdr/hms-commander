# Example Notebooks

HMS Commander provides comprehensive Jupyter notebook examples demonstrating real-world workflows.

## Running the Examples

### Setup

```bash
# Install with development dependencies
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

## Available Notebooks

### Basic Usage

#### [01 - Multi-Version Execution](01_multi_version_execution.ipynb)
Test models across different HMS versions (3.x and 4.x).

**What you'll learn:**
- Detecting installed HMS versions
- Version-specific script generation
- Python 2 vs. Python 3 compatibility
- Cross-version testing

#### [02 - Run All HMS 4.13 Projects](02_run_all_hms413_projects.ipynb)
Execute all example projects from HMS 4.13 installation.

**What you'll learn:**
- Batch project execution
- Result collection
- Error handling
- Automated testing workflows

#### [03 - Project DataFrames](03_project_dataframes.ipynb)
Explore project components using pandas DataFrames.

**What you'll learn:**
- HmsPrj initialization
- Accessing basin_df, met_df, control_df, run_df
- Filtering and analyzing project data
- DataFrame-based workflows

#### [04 - HMS Workflow](04_hms_workflow.ipynb)
Complete end-to-end HMS workflow.

**What you'll learn:**
- Project initialization
- Parameter modifications
- Execution
- Results extraction

### File Operations

#### Basin File Parsing
Working with basin model files (.basin).

**Topics:**
- Subbasin extraction
- Loss parameters (Deficit Constant, SCS CN)
- Transform parameters (SCS Unit Hydrograph, Clark)
- Baseflow parameters
- Routing parameters (Muskingum, Lag)

#### Met File Operations
Meteorologic model operations (.met).

**Topics:**
- Precipitation methods
- Gage assignments
- Frequency storm parameters
- Atlas 14 updates

### Analysis & Results

#### DSS Results Extraction
Extract and analyze DSS results.

**Topics:**
- Reading time-series data
- Peak flow extraction
- Volume calculations
- Hydrograph statistics

#### Peak Flow Analysis
Comprehensive peak flow analysis.

**Topics:**
- Multi-element peak flows
- Statistical analysis
- Exceedance probability
- Visualization

### Advanced Workflows

#### [Clone & Compare Workflow](clone_workflow.ipynb)
QAQC workflow with side-by-side comparison.

**What you'll learn:**
- Cloning basin, met, and run configurations
- Non-destructive modifications
- Parallel execution
- Result comparison
- GUI verification

**Use cases:**
- Parameter sensitivity
- Model calibration
- Scenario analysis
- QAQC review

#### Atlas 14 Update
Update precipitation from TP40 to NOAA Atlas 14.

**What you'll learn:**
- Project centroid calculation
- CRS transformations
- Precipitation depth updates
- Frequency storm modifications

**Use cases:**
- Updating legacy models
- Meeting current standards
- Regional analysis

## Notebook Organization

Notebooks are organized by workflow type:

```
examples/
├── 01_multi_version_execution.ipynb    # Version testing
├── 02_run_all_hms413_projects.ipynb    # Batch execution
├── 03_project_dataframes.ipynb         # Data exploration
├── 04_hms_workflow.ipynb               # Complete workflow
├── basin_file_parsing.ipynb            # File operations
├── met_file_operations.ipynb           # Met models
├── dss_results.ipynb                   # Results analysis
├── peak_flow_analysis.ipynb            # Statistical analysis
├── clone_workflow.ipynb                # QAQC workflow
└── atlas14_update.ipynb                # Precipitation updates
```

## Development Pattern

All notebooks use flexible imports for development:

```python
from pathlib import Path
import sys

try:
    # Try installed package
    from hms_commander import init_hms_project, HmsPrj
except ImportError:
    # Fall back to local development
    sys.path.append(str(Path().resolve().parent))
    from hms_commander import init_hms_project, HmsPrj
```

## Testing with Real Projects

Instead of synthetic test data, examples use actual HEC-HMS projects:

- **Castro** - Simple watershed model
- **River Bend** - Complex routing example
- **Custom projects** - Your own HMS models

This approach ensures:
- Real-world applicability
- Comprehensive testing
- Practical demonstrations

## Contributing Examples

We welcome example contributions! To add a notebook:

1. Use flexible import pattern (see above)
2. Extract HMS example projects when possible
3. Include clear markdown explanations
4. Add to `mkdocs.yml` navigation
5. Test execution from clean environment

See [Contributing Guide](../llm_dev/contributing.md) for details.

## Next Steps

- Start with [Quick Start Guide](../getting_started/quick_start.md)
- Review [API Reference](../api/hms_prj.md) for details
- Check [User Guide](../user_guide/overview.md) for comprehensive documentation
