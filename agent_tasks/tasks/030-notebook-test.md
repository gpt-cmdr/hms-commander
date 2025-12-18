# Task 030: Run Example Notebooks with nbmake

**Created**: 2025-12-17
**Template**: feature.md
**Status**: Reusable

---

## Goal

Execute all example notebooks to verify they run without errors.

**Uses**: pytest with nbmake plugin for notebook testing

---

## Prerequisites

- hmscmdr_local environment activated (or hmscmdr_pip for published package testing)
- pytest and nbmake installed (`pip install -e ".[all]"` includes these)

---

## Quick Commands

### Run All Notebooks

```bash
pytest --nbmake examples/*.ipynb
```

### Run Specific Notebook

```bash
pytest --nbmake examples/03_project_dataframes.ipynb -v
```

### Run with Output Capture

```bash
pytest --nbmake examples/*.ipynb --nbmake-timeout=300 -v
```

---

## Detailed Steps

### 1. Verify Environment

```bash
conda activate hmscmdr_local
which python  # Should show hmscmdr_local path
```

### 2. List Example Notebooks

```bash
ls examples/*.ipynb
```

**Expected notebooks** (from `examples/AGENTS.md`):
- `01_multi_version_execution.ipynb`
- `02_file_operations.ipynb`
- `03_project_dataframes.ipynb`
- `04_steady_flow_analysis.ipynb`
- `05_unsteady_flow_analysis.ipynb`
- `basin_file_parsing.ipynb`

### 3. Run Individual Notebook

```bash
pytest --nbmake examples/03_project_dataframes.ipynb -v
```

**Expected output**:
```
examples/03_project_dataframes.ipynb::cell_0 PASSED
examples/03_project_dataframes.ipynb::cell_1 PASSED
...
```

### 4. Run All Notebooks

```bash
pytest --nbmake examples/*.ipynb --nbmake-timeout=300
```

**Timeout**: 300 seconds per cell (some HMS operations may be slow)

### 5. Check for Failures

If any notebook fails:
1. Note which cell failed
2. Open notebook in Jupyter to debug
3. Check if HMS version/environment issue
4. Update notebook or file bug report

---

## Acceptance Criteria

- [x] All notebooks execute without errors
- [x] No timeout errors
- [x] Output cells populated
- [x] Results validated (peak flows, dataframe shapes, etc.)

---

## Troubleshooting

### "ModuleNotFoundError" in notebook

**Solution**: Wrong kernel selected

```bash
# Ensure kernel registered
python -m ipykernel install --user --name=hmscmdr_local
```

**In Jupyter**:
- Select kernel: "Python (hmscmdr_local)"

### Timeout errors

**Solution**: Increase timeout
```bash
pytest --nbmake examples/*.ipynb --nbmake-timeout=600
```

### HMS execution fails

**Solution**: Check HMS installation
```python
from hms_commander import HmsUtils
print(HmsUtils.detect_hms_installation())
```

### Notebook has stale output

**Solution**: Clear output and re-run

```bash
# Open in Jupyter
jupyter lab examples/03_project_dataframes.ipynb

# Kernel > Restart Kernel and Run All Cells
# Save and commit
```

---

## Advanced Usage

### Generate Notebook Digest for Haiku Review

```bash
python scripts/notebooks/audit_ipynb.py examples/03_project_dataframes.ipynb
```

**Output**: Condensed summary for error checking

### Run Notebooks with Coverage

```bash
pytest --nbmake examples/*.ipynb --cov=hms_commander --cov-report=html
```

### Run Specific Notebook Cell Range

Not directly supported by nbmake. Use Jupyter for cell-by-cell debugging.

---

## Notebook Quality Standards

**Reference**: `.claude/rules/documentation/notebook-standards.md`

**Requirements**:
- [x] First cell is markdown with H1 title
- [x] Uses HmsExamples for reproducibility
- [x] Two-cell import pattern (pip + dev mode)
- [x] All cells executed before committing
- [x] Results validated

---

## Related Tasks

- **010-env-setup.md**: Set up environment before running notebooks
- **080-notebook-authoring.md**: Create new example notebook

---

## Related Agents

**Agents that can help**:
- `notebook-runner` - Executes notebooks with pytest/nbmake
- `notebook-output-auditor` (Haiku) - Checks for exceptions in output
- `notebook-anomaly-spotter` (Haiku) - Detects unexpected behavior
- `example-notebook-librarian` - Notebook QA/QC and navigation
