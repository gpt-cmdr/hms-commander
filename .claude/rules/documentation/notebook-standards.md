# Jupyter Notebook Standards

**Purpose**: Define quality requirements and patterns for hms-commander example notebooks.

**Primary sources**:
- `examples/` - Existing notebooks (reference implementations)
- `mkdocs.yml` - mkdocs-jupyter configuration
- `hms_commander/HmsExamples.py` - Reproducibility utilities

---

## Core Requirements

### 1. First Cell MUST Be Markdown with H1 Title

**Required pattern**:
```markdown
# Notebook Title

Brief description of what this notebook demonstrates and its purpose.
```

**Why**:
- MkDocs uses first H1 as page title
- Provides context for users browsing documentation
- Ensures consistent documentation structure

**Example**:
```markdown
# HMS Workflow Example

This notebook demonstrates a complete HMS modeling workflow:
- Project initialization
- Basin model operations
- Simulation execution
- Results extraction
```

**Validation**: Check first cell type and content:
```python
notebook = json.load(open("example.ipynb"))
first_cell = notebook["cells"][0]
assert first_cell["cell_type"] == "markdown"
assert first_cell["source"][0].startswith("# ")
```

### 2. Use HmsExamples for Reproducibility

**Required**: All notebooks MUST use `HmsExamples.extract_project()` for HMS projects.

**Wrong** (hardcoded path):
```python
hms = init_hms_project(r"C:\Users\JohnDoe\Projects\watershed")  # ❌ Not reproducible
```

**Correct** (reproducible):
```python
from hms_commander import HmsExamples

HmsExamples.extract_project("tifton")  # ✅ Works for all users
hms = init_hms_project("hms_example_projects/tifton")
```

**Why**:
- Example projects are bundled with HMS installations
- Works on any machine with HMS installed
- Consistent test data across users
- No need to distribute large project files

**Available projects**: See `HmsExamples.list_projects()` docstring

### 3. Two-Cell Import Pattern

**Purpose**: Support both pip users and development mode

**Cell 1 (Code - Pip Mode)**:
```python
# pip install hms-commander
```

**Cell 2 (Markdown - Dev Mode)**:
```markdown
**For Development**: If working on hms-commander source code, use the `hmscmdr_local`
conda environment (editable install) instead of pip install.
```

**Why**:
- Pip users see installation command
- Dev users know to use hmscmdr_local environment
- Clear separation between usage modes

**See**: `.claude/rules/project/development-environment.md` for environment details

### 4. Run All Cells Before Committing

**Required**: Execute all cells (Restart Kernel & Run All) before committing.

**Why**:
- Validates notebook is working
- Ensures output is current
- Detects broken code early
- Users see expected results

**MkDocs config**: `execute: false` in mkdocs.yml means saved output is shown

**Process**:
1. Make notebook changes
2. Restart Kernel & Run All (in Jupyter)
3. Fix any errors
4. Save notebook with fresh output
5. Commit to git

### 5. HMS-Specific Validation

**Validate HMS operations produce expected results**:

```python
# Example validation patterns

# Check DSS output exists
from pathlib import Path
dss_file = Path("hms_example_projects/tifton/results.dss")
assert dss_file.exists(), "DSS output not generated"

# Validate results dataframe
peaks = HmsResults.get_peak_flows(dss_file)
assert len(peaks) > 0, "No peak flows extracted"
assert (peaks["Peak Flow (cfs)"] > 0).all(), "Invalid peak flows"

# Check basin operations
subbasins = HmsBasin.get_subbasins("hms_example_projects/tifton/tifton.basin")
assert len(subbasins) > 0, "No subbasins found"
```

**Why**: Ensures notebooks demonstrate working HMS operations, not just code snippets

---

## Notebook Structure

### Recommended Organization

```markdown
# Notebook Title
Description of purpose and scope

## Setup
- Installation instructions
- Import statements
- Project extraction

## Demonstration
- Main workflow steps
- HMS operations
- Result validation

## Results
- Summary output
- Visualizations
- Key findings

## Next Steps
- Related notebooks
- Additional resources
```

### Cell Types

**Markdown cells**:
- Section headers (##, ###)
- Explanatory text
- Usage notes
- Warnings/cautions

**Code cells**:
- Import statements
- HMS operations
- Data analysis
- Visualizations

**Output cells** (automatic):
- Print statements
- DataFrame displays
- Plots/charts

---

## Example Patterns

### Pattern 1: Basic HMS Workflow

```python
# Cell 1 (markdown)
# Basic HMS Workflow
Demonstrates project initialization, execution, and results extraction.

# Cell 2 (code)
# pip install hms-commander

# Cell 3 (markdown)
**For Development**: Use `hmscmdr_local` conda environment

# Cell 4 (code)
from hms_commander import HmsExamples, init_hms_project, HmsCmdr, HmsResults

# Extract example project
HmsExamples.extract_project("castro")

# Initialize
hms = init_hms_project("hms_example_projects/castro")

# Execute
HmsCmdr.compute_run("Run 1")

# Extract results
dss_file = hms.run_df.loc["Run 1", "dss_file"]
peaks = HmsResults.get_peak_flows(dss_file)
print(peaks)
```

### Pattern 2: File Operations

```python
# Cell 1 (markdown)
# Basin File Operations
Shows how to read and modify HMS basin model files.

# Cell 2 (code)
from hms_commander import HmsExamples, HmsBasin

# Extract project
HmsExamples.extract_project("tifton")
basin_file = "hms_example_projects/tifton/tifton.basin"

# Read subbasins
subbasins = HmsBasin.get_subbasins(basin_file)
print(f"Found {len(subbasins)} subbasins")
display(subbasins)

# Modify parameter
HmsBasin.set_loss_parameters(
    basin_file,
    "Sub1",
    curve_number=85
)
print("Updated CN to 85")
```

### Pattern 3: Multi-Version Testing

```python
# Cell 1 (markdown)
# Multi-Version HMS Execution
Demonstrates running same project across HMS 3.x and 4.x versions.

# Cell 2 (code)
from hms_commander import HmsExamples, HmsJython

# List available versions
versions = HmsExamples.list_versions()
print(f"Installed versions: {versions}")

# Extract project
HmsExamples.extract_project("tifton")

# Generate version-appropriate script
for version in versions:
    # Detect Python 2 vs 3
    python2_compatible = version.startswith("3.")

    script = HmsJython.generate_compute_script(
        project_path="hms_example_projects/tifton/tifton.hms",
        run_name="Run 1",
        python2_compatible=python2_compatible
    )

    print(f"HMS {version}: Python 2 mode = {python2_compatible}")
```

### Pattern 4: Results Analysis with Visualization

```python
# Cell 1 (markdown)
# HMS Results Analysis
Extract and visualize HMS simulation results.

# Cell 2 (code)
from hms_commander import HmsResults
import matplotlib.pyplot as plt

dss_file = "hms_example_projects/castro/results.dss"

# Extract hydrograph
flows = HmsResults.get_outflow_timeseries(dss_file, "Junction1")

# Plot
plt.figure(figsize=(10, 6))
plt.plot(flows.index, flows["Flow"], linewidth=2)
plt.xlabel("Time")
plt.ylabel("Flow (cfs)")
plt.title("Outlet Hydrograph - Junction1")
plt.grid(True, alpha=0.3)
plt.show()

# Summary statistics
print(f"Peak Flow: {flows['Flow'].max():.1f} cfs")
print(f"Time to Peak: {flows['Flow'].idxmax()}")
```

---

## MkDocs Integration

### Configuration (mkdocs.yml)

```yaml
plugins:
  - mkdocs-jupyter:
      include: ["*.ipynb"]
      execute: false          # Use saved output
      allow_errors: false     # Fail build on notebook errors
      ignore:
        - "examples/*/hms413_*/**"  # Ignore temp directories
```

**Key settings**:
- `execute: false` - Don't re-run cells during build (use saved output)
- `allow_errors: false` - Build fails if notebook has errors
- `ignore` - Skip certain directories

### Navigation Structure

```yaml
nav:
  - Example Notebooks:
      - Overview: examples/overview.md
      - Basic Usage:
          - Multi-Version: examples/01_multi_version_execution.ipynb
          - DataFrames: examples/03_project_dataframes.ipynb
      - File Operations:
          - Basin Files: examples/basin_file_parsing.ipynb
          - Met Files: examples/met_file_operations.ipynb
```

**Pattern**: Group related notebooks under descriptive categories

---

## Quality Checklist

Before committing a notebook:

**Structure**:
- [ ] First cell is markdown with H1 title
- [ ] Description explains purpose clearly
- [ ] Logical section organization (Setup, Demo, Results)

**Reproducibility**:
- [ ] Uses `HmsExamples.extract_project()` (not hardcoded paths)
- [ ] All imports are from `hms_commander` (no local imports)
- [ ] No absolute paths (e.g., `C:\Users\...`)
- [ ] No credentials or sensitive data

**Code Quality**:
- [ ] Imports organized (standard, third-party, hms_commander)
- [ ] HMS operations follow static class pattern (no instantiation)
- [ ] Variable names are descriptive
- [ ] Comments explain non-obvious operations

**Execution**:
- [ ] All cells executed (Restart Kernel & Run All)
- [ ] No errors in output cells
- [ ] Results validated (DSS files exist, peaks > 0, etc.)
- [ ] Output is current (not stale from old API)

**Documentation**:
- [ ] Markdown cells explain each step
- [ ] 2-cell import pattern included
- [ ] Related notebooks mentioned (Next Steps)
- [ ] Links to relevant API docs

**MkDocs Integration**:
- [ ] Added to mkdocs.yml navigation
- [ ] Renders correctly in `mkdocs serve` preview
- [ ] No broken links
- [ ] Images/plots display correctly

---

## Common Issues and Solutions

### Issue: Notebook Doesn't Render in Docs

**Symptom**: Notebook file exists but doesn't appear in documentation

**Solutions**:
1. Check mkdocs.yml navigation (file path correct?)
2. Check first cell is markdown H1
3. Check mkdocs-jupyter `ignore` patterns
4. Run `mkdocs build` and check for errors

### Issue: Old Output in Notebook

**Symptom**: Notebook shows outdated results or old API usage

**Solution**: Restart Kernel & Run All, fix errors, save, commit

### Issue: Notebook Has Absolute Paths

**Symptom**: Code references `C:\Users\JohnDoe\...` or similar

**Solution**: Replace with `HmsExamples.extract_project()` pattern

### Issue: Notebook Depends on Local Files

**Symptom**: References files not in repository

**Solution**: Either:
- Use HmsExamples projects (reproducible)
- Or include required files in repository
- Or document where to get files

### Issue: Notebook Cells Not Executed

**Symptom**: Empty output cells or `[ ]:` instead of `[1]:`

**Solution**: Restart Kernel & Run All before committing

---

## Related Documentation

**MkDocs Config**: `.claude/rules/documentation/mkdocs-config.md`
**HmsExamples API**: `hms_commander/HmsExamples.py` (docstrings)
**Dev Environments**: `.claude/rules/project/development-environment.md`
**Documentation Agent**: `.claude/agents/documentation-generator/SUBAGENT.md`

---

## Examples in Repository

**Reference implementations**:
- `examples/01_multi_version_execution.ipynb` - Version detection pattern
- `examples/03_project_dataframes.ipynb` - DataFrame operations
- `examples/04_hms_workflow.ipynb` - Complete workflow
- `examples/basin_file_parsing.ipynb` - File operations

Read these notebooks for implementation patterns.
