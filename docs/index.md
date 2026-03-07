# HMS Commander Documentation

<div align="center">
  <img src="assets/hms-commander_logo.svg" alt="HMS Commander Logo" width="400"/>
  <p>
    <strong>An open-source project of <a href="https://clbengineering.com/">CLB Engineering Corporation</a></strong><br>
    <em>LLM-Forward Engineering Solutions</em>
  </p>
</div>

---

**HMS Commander** is a Python library for automating HEC-HMS (Hydrologic Engineering Center's Hydrologic Modeling System) operations. It provides a comprehensive API for interacting with HEC-HMS project files, executing simulations, and processing results. Developed by [CLB Engineering Corporation](https://clbengineering.com/) using the **[LLM Forward](https://clbengineering.com/llm-forward)** approach, hms-commander is part of the most comprehensive open-source HEC-HMS and HEC-RAS automation solution available.

## Key Features

### 🔧 **Comprehensive HMS Automation**
- Complete project management through Python API
- Basin model, meteorologic model, and control specification operations
- Run configuration and execution engine with parallel compute support

### 📊 **Data Integration**
- DSS file operations (via ras-commander integration)
- Time-series gage management
- Results extraction and analysis
- GeoJSON export for spatial visualization

### 🚀 **Modern Workflows**
- Clone operations for QAQC workflows (baseline vs. updated models)
- Atlas 14 precipitation updates
- Multi-version HMS support (3.x and 4.x)
- Jython script generation for HEC-HMS automation

### 🤖 **LLM Forward Engineering**
- Built using CLB Engineering's LLM Forward Approach
- Comprehensive CLAUDE.md for AI context
- Static class architecture for simple, predictable API
- Example-based testing with real HMS projects

## Quick Start

### Installation

```bash
# Basic installation
pip install hms-commander

# With DSS support (includes ras-commander)
pip install hms-commander[dss]
```

### Basic Usage

```python
from hms_commander import init_hms_project, HmsBasin, HmsCmdr

# Initialize project
init_hms_project(r"C:/Projects/MyHmsModel")

# Get subbasin information
subbasins = HmsBasin.get_subbasins("MyModel.basin")
print(subbasins.head())

# Modify loss parameters
HmsBasin.set_loss_parameters(
    "MyModel.basin",
    "Subbasin-1",
    curve_number=85
)

# Execute simulation
HmsCmdr.compute_run("Run 1")
```

## Architecture

```mermaid
graph TD
    A[HMS Project Files] --> B[HmsPrj]
    B --> C[HmsBasin]
    B --> D[HmsMet]
    B --> E[HmsControl]
    B --> F[HmsGage]
    B --> G[HmsRun]
    B --> H[HmsGeo]

    C --> I[HmsCmdr<br/>Execution]
    D --> I
    E --> I
    F --> I
    G --> I

    I --> J[HmsJython<br/>Script Generation]
    J --> K[HEC-HMS Engine]
    K --> L[DSS Results]

    L --> M[HmsResults<br/>Analysis]
    L --> N[HmsDss<br/>Operations]

    style B fill:#e1f5ff
    style I fill:#fff4e1
    style M fill:#e7f5e7
```

HMS Commander follows the proven patterns established by [ras-commander](https://github.com/gpt-cmdr/ras-commander):

### Static Class Pattern

```mermaid
classDiagram
    class HmsBasin {
        <<static>>
        +get_subbasins(basin_file)$
        +set_loss_parameters(basin_file, subbasin, **params)$
        +clone_basin(template, new_name)$
    }

    class HmsMet {
        <<static>>
        +get_precipitation_method(met_file)$
        +set_gage_assignment(met_file, subbasin, gage)$
        +clone_met(template, new_name)$
    }

    class HmsCmdr {
        <<static>>
        +compute_run(run_name)$
        +compute_parallel(run_names, max_workers)$
        +compute_batch(run_names)$
    }

    note for HmsBasin "No instantiation required\nDirect method calls only"
```

- **Static Class Pattern**: Direct method calls without instantiation
- **Flexible Imports**: Supports both installed package and local development
- **Example-Based Testing**: Uses real HMS example projects instead of unit tests
- **Comprehensive Logging**: Centralized logging with `@log_call` decorators

## HMS Version Support

| Version | Support | Notes |
|---------|---------|-------|
| **HMS 4.4.1+** | ✅ Full | 64-bit, recommended |
| **HMS 3.3-3.5** | ✅ Full | 32-bit, requires `python2_compatible=True` |
| HMS 4.0-4.3 | ❌ | Legacy classpath structure not supported |
| HMS 3.0-3.2 | ❓ | Untested |

## Documentation Structure

<div class="grid cards" markdown>

-   :material-clock-fast:{ .lg .middle } **Getting Started**

    ---

    Installation, quick start, and project initialization

    [:octicons-arrow-right-24: Get Started](getting_started/installation.md)

-   :material-book-open-variant:{ .lg .middle } **User Guide**

    ---

    Comprehensive guide to all HMS Commander features

    [:octicons-arrow-right-24: Read Guide](user_guide/overview.md)

-   :material-code-braces:{ .lg .middle } **Example Notebooks**

    ---

    Working examples with Jupyter notebooks

    [:octicons-arrow-right-24: View Examples](examples/overview.md)

-   :material-api:{ .lg .middle } **API Reference**

    ---

    Complete API documentation for all classes

    [:octicons-arrow-right-24: API Docs](api/hms_prj.md)

</div>

## About CLB Engineering

<a href="https://clbengineering.com/">
  <img src="assets/CLBEngineeringHzLogo.png" alt="CLB Engineering Corporation" width="280" align="right" style="margin-left: 16px; margin-bottom: 8px;">
</a>

HMS Commander is a free and open-source project of **[CLB Engineering Corporation](https://clbengineering.com/)**, the creators of the **LLM Forward** engineering framework. Within two years, CLB built the most robust and feature-complete HEC-RAS and HEC-HMS automation solution on the open internet -- proving that licensed professional engineers working alongside Large Language Models can create extraordinary value in compressed timeframes.

**For agencies and organizations** looking to modernize H&H workflows: [Contact CLB Engineering](https://clbengineering.com/) to partner with the early LLM pioneers who are redefining what's possible in hydrologic engineering automation.

**Learn more:** [LLM Forward Engineering](https://clbengineering.com/llm-forward) | [CLB Engineering](https://clbengineering.com/)

## Related Projects

- **[ras-commander](https://github.com/gpt-cmdr/ras-commander)** - Python API for HEC-RAS automation
- **[HEC-Commander](https://github.com/gpt-cmdr/HEC-Commander)** - Open-source suite for HEC software automation

## Contributing

HMS Commander is an open-source project built with LLM-driven development. Contributions are welcome!

See the [Contributing Guide](llm_dev/contributing.md) for details.

## License

MIT License - See LICENSE file for details. HMS Commander is a free and open-source project of [CLB Engineering Corporation](https://clbengineering.com/).
