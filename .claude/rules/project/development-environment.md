# Development Environment

**Purpose**: Define environment setup, package management, and testing protocols for hms-commander development.

**Primary sources**:
- `README.md` - Installation instructions
- `GETTING_STARTED.md` - Quick start guide
- `setup.py` - Package dependencies

---

## Package Management

### Use uv and python for Agent Scripts and Tools

**Agent scripts** (`hms_agents/*.py`) and development tools should use:
- `uv` for fast package installation
- Standard `python` for execution

```bash
# Install dependencies with uv
uv pip install -e ".[all]"

# Run agent scripts
python hms_agents/HMS_DocQuery.py
python hms_agents/Update_3_to_4.py
```

**Why uv**:
- 10-100x faster than pip
- Compatible with pip workflows
- Identical package resolution

**When to use pip instead**:
- User-facing documentation (broader compatibility)
- CI/CD pipelines (unless uv is installed)
- Legacy systems without uv

---

## Conda Environment Setup for Testing

### Two Testing Environments

**Purpose**: Separate environments for local development vs published package testing.

### Environment 1: `hmscmdr_local` (Local Development)

**Use when**: Making code changes in the repository, testing new features, debugging.

```bash
# Create environment
conda create -n hmscmdr_local python=3.11

# Activate
conda activate hmscmdr_local

# Install local development version
cd C:\GH\hms-commander
pip install -e ".[all]"

# Verify using local code
python -c "import hms_commander; print(hms_commander.__file__)"
# Should show: C:\GH\hms-commander\hms_commander\...
```

**Characteristics**:
- Editable install (`-e` flag)
- Changes to code immediately reflected
- Includes dev dependencies (`[all]`)
- Used for Jupyter notebook testing during development

### Environment 2: `hmscmdr_pip` (Published Package)

**Use when**: Testing published package, validating release, running examples as users would.

```bash
# Create environment
conda create -n hmscmdr_pip python=3.11

# Activate
conda activate hmscmdr_pip

# Install from PyPI
pip install hms-commander

# Verify using published package
python -c "import hms_commander; print(hms_commander.__file__)"
# Should show: .../anaconda3/envs/hmscmdr_pip/lib/python3.11/site-packages/hms_commander/...
```

**Characteristics**:
- Standard install (no `-e`)
- Uses published version from PyPI
- Matches end-user experience
- Used for release validation

---

## Testing Jupyter Notebooks

### Workflow Selection

**Making code changes**:
1. Use `hmscmdr_local` environment
2. Ensure editable install: `pip install -e ".[all]"`
3. Launch Jupyter from environment: `jupyter lab`
4. Test notebooks with live code changes

**Testing published examples**:
1. Use `hmscmdr_pip` environment
2. Install published package: `pip install hms-commander`
3. Launch Jupyter from environment: `jupyter lab`
4. Verify examples work with published version

### Example Workflow

```bash
# Scenario: Testing new feature in basin operations

# Step 1: Develop in local environment
conda activate hmscmdr_local
cd C:\GH\hms-commander
jupyter lab

# Open examples/03_project_dataframes.ipynb
# Make changes to hms_commander/HmsBasin.py
# Re-run notebook cells - changes immediately reflected

# Step 2: Validate with published version (before release)
conda activate hmscmdr_pip
pip install hms-commander --upgrade
jupyter lab

# Run same notebook
# Verify old version behavior
# Compare with local changes
```

---

## Environment Preparation

### Check if Environment Exists

```bash
# List all conda environments
conda env list

# If hmscmdr_local or hmscmdr_pip not listed, create them
```

### Create Missing Environments

```bash
# Prepare local development environment
conda create -n hmscmdr_local python=3.11 -y
conda activate hmscmdr_local
cd C:\GH\hms-commander
pip install -e ".[all]"

# Prepare published package environment
conda create -n hmscmdr_pip python=3.11 -y
conda activate hmscmdr_pip
pip install hms-commander
```

### Verify Correct Environment

```python
# In Jupyter notebook or Python script
import sys
print(f"Python: {sys.executable}")
print(f"Environment: {sys.prefix}")

import hms_commander
print(f"HMS Commander location: {hms_commander.__file__}")

# For hmscmdr_local, should see: C:\GH\hms-commander\hms_commander
# For hmscmdr_pip, should see: ...\anaconda3\envs\hmscmdr_pip\...\hms_commander
```

---

## Cross-Repository Consistency

**Note**: Similar environments exist for ras-commander:
- `rascmdr_local` - Local development for ras-commander
- `rascmdr_pip` - Published ras-commander package

**When working on HMS→RAS integration**:
- May need both `hmscmdr_local` and `rascmdr_local` for cross-repo development
- Or both `hmscmdr_pip` and `rascmdr_pip` for published package testing

---

## Development Dependencies

### Minimal Install (Core Only)

```bash
pip install hms-commander
```

Includes: pandas, numpy, pathlib, tqdm, requests

### Full Install (All Optional Dependencies)

```bash
pip install hms-commander[all]
# or for editable:
pip install -e ".[all]"
```

Includes additional:
- **GIS**: geopandas, pyproj, shapely
- **DSS**: ras-commander, pyjnius
- **Dev**: pytest, jupyter, mkdocs

---

## Quick Reference

**Agent scripts**: Use `uv` for installation, `python` for execution

**Jupyter testing with code changes**: `hmscmdr_local` environment
**Jupyter testing published package**: `hmscmdr_pip` environment

**Create environments**:
```bash
conda create -n hmscmdr_local python=3.11
conda create -n hmscmdr_pip python=3.11
```

**Install in each**:
```bash
# Local
conda activate hmscmdr_local && pip install -e ".[all]"

# Published
conda activate hmscmdr_pip && pip install hms-commander
```

**Verify**:
```python
import hms_commander; print(hms_commander.__file__)
```
