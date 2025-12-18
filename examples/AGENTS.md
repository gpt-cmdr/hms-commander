# Example Notebooks Index

This file indexes all example notebooks and documents notebook-only logic.

**Maintained by**: `example-notebook-librarian` agent
**Purpose**: Quick navigation, logic tracking, extraction planning

---

## Notebook Inventory

| # | Notebook | Purpose | HMS Components | Key Features |
|---|----------|---------|----------------|--------------|
| 01 | 01_multi_version_execution.ipynb | Multi-version HMS execution | HmsExamples, HmsJython, HmsDss | Version detection, parallel execution across HMS 3.x/4.x |
| 02 | 02_run_all_hms413_projects.ipynb | Batch project execution | HmsExamples, HmsCmdr | Execute all HMS 4.13 example projects |
| 03 | 03_project_dataframes.ipynb | Project dataframe exploration | HmsPrj, init_hms_project | Basin, met, run, gage dataframes; accessor methods |
| 04 | 04_hms_workflow.ipynb | Complete HMS workflow | HmsPrj, HmsCmdr, HmsResults, DssCore | End-to-end: init, execute, results, DSS operations |
| 05 | 05_run_management.ipynb | Run configuration management | HmsRun, HmsPrj | Set basin/met/control with validation, prevent HMS auto-deletion |
| - | clone_workflow.ipynb | Clone & compare workflow | HmsBasin, HmsMet, HmsRun | CLB Engineering LLM Forward approach, non-destructive QAQC |

---

## Notebook Descriptions

### 01_multi_version_execution.ipynb
**What it demonstrates**:
- Discovering installed HMS versions (3.x and 4.x)
- Extracting example projects from different versions
- Generating version-appropriate Jython scripts
- Executing simulations across multiple HMS versions
- Direct Java invocation for HMS 4.4.1+ (bypasses HEC-HMS.cmd bugs)
- Memory configuration for large models
- DSS output verification

**HMS Projects Used**: tifton
**Best For**: Learning multi-version support, execution patterns
**Key APIs**: `HmsExamples.list_versions()`, `HmsJython.generate_compute_script()`, `HmsJython.execute_script()`

### 02_run_all_hms413_projects.ipynb
**What it demonstrates**:
- Batch execution of all HMS example projects
- Automated project discovery
- Parallel execution workflows
- Execution status tracking

**HMS Projects Used**: All HMS 4.13 examples (castro, tifton, river_bend, tenk)
**Best For**: Batch processing, parallel execution
**Key APIs**: `HmsExamples.list_projects()`, `HmsCmdr.compute_parallel()`

### 03_project_dataframes.ipynb
**What it demonstrates**:
- Initializing HMS projects with `init_hms_project()`
- Accessing 7 comprehensive dataframes:
  - `hms_df` - Project attributes
  - `basin_df` - Basin model summary
  - `subbasin_df` - Detailed subbasin parameters
  - `met_df` - Meteorologic models
  - `control_df` - Control specifications
  - `run_df` - Simulation runs
  - `gage_df` - Time series gages
  - `pdata_df` - Paired data tables
- Using accessor methods: `list_basin_names()`, `list_met_names()`, `list_control_names()`, etc.
- Multi-project support with separate `HmsPrj` instances

**HMS Projects Used**: castro, tifton
**Best For**: Learning project structure, dataframe access patterns
**Key APIs**: `init_hms_project()`, `hms.basin_df`, `hms.list_*_names()`

### 04_hms_workflow.ipynb
**What it demonstrates**:
- Complete end-to-end HMS workflow
- Project initialization and dataframe exploration
- Run configuration queries
- DSS file operations with standalone `DssCore` class
- Reading time series data (observed and computed)
- Results comparison and visualization
- Cross-reference queries (run → basin → subbasins)

**HMS Projects Used**: castro
**Best For**: Complete workflow reference, DSS operations
**Key APIs**: `init_hms_project()`, `HmsRun.get_dss_config()`, `DssCore.get_catalog()`, `DssCore.read_timeseries()`

### 05_run_management.ipynb
**What it demonstrates**:
- CRITICAL: HMS auto-deletion problem (runs with invalid components disappear)
- Querying run configurations
- Modifying run metadata (description, log file, DSS output)
- Modifying run components WITH VALIDATION (basin, met, control)
- Validation protection against HMS auto-deletion
- Direct file modification vs. project initialization trade-offs
- Integration with clone workflows for QAQC
- Best practices for safe run management

**HMS Projects Used**: tifton
**Best For**: Run configuration, QAQC workflows, understanding HMS auto-deletion
**Key APIs**: `HmsRun.set_description()`, `HmsRun.set_basin()`, `HmsRun.set_precip()`, `HmsRun.set_control()`, `HmsRun.get_dss_config()`, `HmsRun.clone_run()`

### clone_workflow.ipynb
**What it demonstrates**:
- CLB Engineering LLM Forward approach to QAQC
- Non-destructive cloning of basin models, met models, and runs
- Side-by-side comparison in HEC-HMS GUI
- Separate DSS files for baseline vs. updated scenarios
- Parallel execution of multiple scenarios
- Traceable metadata (descriptions updated with clone info)
- Parameter modification after cloning

**HMS Projects Used**: castro
**Best For**: QAQC workflows, scenario comparison, calibration
**Key APIs**: `HmsBasin.clone_basin()`, `HmsMet.clone_met()`, `HmsRun.clone_run()`, `HmsCmdr.compute_parallel()`

---

## Notebook-Only Logic

Track logic that exists only in notebooks but should be extracted to the library.

| Notebook | Logic | Recommended Extraction | Status |
|----------|-------|------------------------|--------|
| (none currently) | | | |

**Extraction Workflow**:
1. Identify repeated logic across notebooks
2. Document in this table
3. Create backlog item (GitHub issue or feature_dev_notes)
4. Extract to library API
5. Update notebooks to use library
6. Mark as complete, remove from table

---

## Quality Standards

All notebooks MUST meet these requirements (see `.claude/rules/documentation/notebook-standards.md`):

**Structure**:
- First cell: Markdown with H1 title
- Logical organization: Setup → Demonstration → Results → Summary
- 2-cell import pattern (pip install + dev note)

**Reproducibility**:
- Use `HmsExamples.extract_project()` (never hardcoded paths)
- No absolute paths (C:\Users\...)
- No credentials or sensitive data
- Works on any machine with HMS installed

**Code Quality**:
- Organized imports (standard, third-party, hms_commander)
- Static class pattern (no instantiation)
- Descriptive variable names
- Comments for non-obvious operations

**Execution**:
- All cells executed (Restart Kernel & Run All)
- No errors in output cells
- Results validated (assertions, checks)
- Output current (not stale)

**Documentation**:
- Markdown cells explain each step
- Related notebooks mentioned
- Links to API docs

**MkDocs Integration**:
- Added to mkdocs.yml navigation
- Renders correctly in preview
- No broken links

---

## MkDocs Configuration

**Location**: `mkdocs.yml`

**Settings**:
```yaml
plugins:
  - mkdocs-jupyter:
      include: ["*.ipynb"]
      execute: false          # Use saved output
      allow_errors: false     # Fail build on errors
      ignore:
        - "examples/*/example_projects/**"  # Ignore temp directories
```

**Navigation Structure**:
```yaml
nav:
  - Example Notebooks:
      - Multi-Version Execution: examples/01_multi_version_execution.ipynb
      - Run All Projects: examples/02_run_all_hms413_projects.ipynb
      - Project DataFrames: examples/03_project_dataframes.ipynb
      - Complete Workflow: examples/04_hms_workflow.ipynb
      - Run Management: examples/05_run_management.ipynb
      - Clone Workflow: examples/clone_workflow.ipynb
```

---

## Testing Notebooks

**Manual Testing**:
```bash
# Activate test environment
conda activate hmscmdr_local

# Launch Jupyter
cd C:\GH\hms-commander\examples
jupyter lab

# For each notebook:
# 1. Restart Kernel & Run All
# 2. Fix any errors
# 3. Save with fresh output
# 4. Commit
```

**Automated Testing** (when nbmake is configured):
```bash
# Test all notebooks
pytest --nbmake examples/

# Test specific notebook
pytest --nbmake examples/01_multi_version_execution.ipynb
```

**MkDocs Preview**:
```bash
# Preview documentation with notebooks
mkdocs serve

# Open browser to http://127.0.0.1:8000
# Navigate to Example Notebooks section
# Verify rendering and links
```

---

## Known Issues

**None currently documented**

When issues are discovered:
1. Document here with notebook name, error, and workaround
2. Create GitHub issue or feature_dev_notes entry
3. Fix in library or notebook
4. Remove from this list when resolved

---

## Contributing New Notebooks

**Before creating a new notebook**:
1. Check this index - does a similar notebook exist?
2. Read `.claude/rules/documentation/notebook-standards.md`
3. Use existing notebook as template
4. Follow quality standards checklist
5. Add to this index
6. Update mkdocs.yml navigation
7. Test execution in clean environment
8. Submit PR or request review from `example-notebook-librarian`

**Naming Convention**:
- Numbered: `##_descriptive_name.ipynb` (for sequential learning)
- Topic-based: `descriptive_name.ipynb` (for specific workflows)

---

## Maintenance Schedule

**Quarterly** (or after major library changes):
- Execute all notebooks in clean environment
- Verify against latest library API
- Update stale examples
- Check for notebook-only logic to extract
- Update this index

**Before Releases**:
- Execute all notebooks
- Verify no errors
- Update version numbers if referenced
- Ensure compatibility with new library version

**Agent Responsibilities**:
- `example-notebook-librarian`: Maintain this file, QA/QC notebooks
- `notebook-runner`: Execute notebooks, capture outputs
- Domain specialists: Verify feature-specific correctness

---

## Quick Reference

**Finding Notebooks**:
- Multi-version execution → 01
- Batch processing → 02
- Project exploration → 03
- Complete workflow → 04
- Run configuration → 05
- Clone & QAQC → clone_workflow

**Learning Path**:
1. Start with 03 (project dataframes) - understand structure
2. Then 04 (complete workflow) - see end-to-end process
3. Then 01 (multi-version) - learn execution patterns
4. Then 05 (run management) - master configuration
5. Then clone_workflow - advanced QAQC techniques
6. Then 02 (batch) - scale up to multiple projects

**Getting Help**:
- Agent: `example-notebook-librarian` - "which notebook shows X?"
- Documentation: `.claude/rules/documentation/notebook-standards.md`
- API Reference: `docs/api/*.md`
