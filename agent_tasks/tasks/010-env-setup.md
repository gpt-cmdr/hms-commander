# Task 010: Set Up hmscmdr_local Development Environment

**Created**: 2025-12-17
**Template**: feature.md
**Status**: Reusable

---

## Goal

Create the `hmscmdr_local` conda environment for hms-commander development with editable install.

**Why hmscmdr_local**: Code changes immediately reflected without reinstalling. Essential for development and testing.

**See also**: `hmscmdr_pip` environment for testing published package (`.claude/rules/project/development-environment.md`)

---

## Prerequisites

- Anaconda or Miniconda installed
- hms-commander repository cloned

---

## Steps

### 1. Create Conda Environment

```bash
conda create -n hmscmdr_local python=3.11 -y
```

### 2. Activate Environment

```bash
conda activate hmscmdr_local
```

### 3. Install in Editable Mode

```bash
cd C:\GH\hms-commander  # or your local path
pip install -e ".[all]"
```

**What `.[all]` includes**:
- Core dependencies (pandas, numpy, pathlib, tqdm, requests)
- GIS dependencies (geopandas, pyproj, shapely)
- DSS dependencies (ras-commander, pyjnius)
- Dev dependencies (pytest, jupyter, mkdocs, ruff)

### 4. Verify Editable Install

```python
import hms_commander
print(hms_commander.__file__)
# Should show: C:\GH\hms-commander\hms_commander\__init__.py
# NOT: ...\anaconda3\envs\hmscmdr_local\...\hms_commander\__init__.py
```

### 5. Register Jupyter Kernel (For Notebook Development)

```bash
python -m ipykernel install --user --name=hmscmdr_local --display-name="Python (hmscmdr_local)"
```

### 6. Test in Jupyter

```bash
jupyter lab
```

**In notebook**:
- Select kernel: "Python (hmscmdr_local)"
- Run: `import sys; print(sys.executable)`
- Should show hmscmdr_local environment path

---

## Acceptance Criteria

- [x] Environment created
- [x] Package installed in editable mode (-e flag)
- [x] Import shows local repository path
- [x] Jupyter kernel registered
- [x] Code changes immediately reflected

---

## Testing Editable Install

### Verify Changes Propagate

**Test**:
1. Edit `hms_commander/__init__.py` (add comment)
2. In Python shell: `import hms_commander` (without restarting)
3. Check if comment appears in `hms_commander.__file__`

**Expected**: Changes visible immediately

---

## Troubleshooting

### "Not an editable install" error

**Solution**: Ensure `-e` flag used: `pip install -e ".[all]"`

### Import shows site-packages path

**Solution**: Wrong environment active. Run `conda activate hmscmdr_local`

### Jupyter kernel not found

**Solution**: Re-run `python -m ipykernel install --user --name=hmscmdr_local`

---

## Comparison: hmscmdr_local vs hmscmdr_pip

| Aspect | hmscmdr_local | hmscmdr_pip |
|--------|---------------|-------------|
| **Install** | `pip install -e ".[all]"` | `pip install hms-commander` |
| **Location** | Repository directory | site-packages |
| **Changes** | Immediate | Requires reinstall |
| **Use when** | Developing code | Testing published package |

**Rule**: Use `hmscmdr_local` when making code changes, `hmscmdr_pip` to validate published version.

---

## Next Tasks

- **020-run-simulation.md**: Execute HMS simulation workflow
- **030-notebook-test.md**: Run example notebooks in this environment
