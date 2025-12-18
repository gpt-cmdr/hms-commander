# Task 000: Bootstrap hms-commander Development Environment

**Created**: 2025-12-17
**Template**: investigation.md
**Status**: Reusable

---

## Goal

Set up a complete hms-commander development environment from scratch.

---

## Prerequisites

- Python 3.10 or higher
- Git installed
- HMS 4.11 or higher installed (optional for full functionality)

---

## Steps

### 1. Clone Repository

```bash
git clone https://github.com/gpt-cmdr/hms-commander.git
cd hms-commander
```

### 2. Create Development Environment

**Option A: Using `uv` (recommended for agents)**
```bash
uv venv
uv pip install -e ".[all]"
```

**Option B: Using `pip` (standard)**
```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -e ".[all]"
```

### 3. Verify Installation

```bash
python -c "import hms_commander; print(hms_commander.__version__)"
python -c "from hms_commander import HmsExamples; print('HmsExamples available')"
```

### 4. Run Example Test

```python
from hms_commander import HmsExamples, init_hms_project

# Extract example project
HmsExamples.extract_project("tifton")

# Initialize
hms = init_hms_project("hms_example_projects/tifton")

# Verify data loaded
print(f"Loaded {len(hms.basin_df)} basin elements")
print(f"Loaded {len(hms.run_df)} runs")
```

### 5. Run Test Suite (Optional)

```bash
pytest
```

---

## Acceptance Criteria

- [x] Repository cloned
- [x] Virtual environment created
- [x] Package installed in editable mode
- [x] All dependencies installed
- [x] Import test passes
- [x] Example project extracts successfully

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'hms_commander'"

**Solution**: Ensure you activated the virtual environment and ran `pip install -e ".[all]"`

### "HMS not found" warnings

**Solution**: HMS installation is optional. Library will work for file operations without HMS installed.

### Import errors for optional dependencies

**Solution**: Install all optional dependencies with `pip install -e ".[all]"`

---

## Next Tasks

After bootstrapping:
- **010-env-setup.md**: Set up hmscmdr_local conda environment for development
- **030-notebook-test.md**: Run example notebooks
