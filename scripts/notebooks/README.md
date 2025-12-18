# Notebook Testing Scripts

Scripts for executing and auditing Jupyter notebooks in hms-commander.

## audit_ipynb.py

Generate condensed output digests from executed Jupyter notebooks.

### Purpose

Creates small "digest" files from notebooks for downstream review by Haiku agents:
- **notebook-output-auditor** - Finds exceptions/errors
- **notebook-anomaly-spotter** - Finds unexpected behavior

Avoids sending entire notebook JSON to Haiku agents (more efficient, focused review).

### Usage

**Basic usage**:
```bash
python audit_ipynb.py notebook.ipynb
```

**Specify output directory**:
```bash
python audit_ipynb.py notebook.ipynb --out-dir working/notebook_runs/latest
```

**Include pytest log**:
```bash
python audit_ipynb.py notebook.ipynb \
  --pytest-log working/notebook_runs/latest/stdout.txt \
  --out-dir working/notebook_runs/latest
```

### Output

Generates two files:

**audit.md** (human-readable):
```markdown
# Notebook Audit: notebook.ipynb

## Summary
- Total cells: 15
- Code cells: 8
- Cells with errors: 1

## Cells with Errors
### Cell 5 (code)
**Error**: ValueError: Run 'InvalidRun' not found
```

**audit.json** (machine-readable):
```json
{
  "notebook": "notebook.ipynb",
  "summary": {
    "total_cells": 15,
    "cells_with_errors": 1
  },
  "issues": {
    "error_cells": [5]
  }
}
```

### Exit Codes

- `0`: Notebook clean (no errors)
- `1`: Notebook has errors

### Example Workflow

```bash
# 1. Execute notebook with pytest
timestamp=$(date +%Y%m%d_%H%M%S)
run_dir="working/notebook_runs/${timestamp}"
mkdir -p "${run_dir}"

pytest --nbmake examples/notebook.ipynb -v \
  > "${run_dir}/stdout.txt" 2> "${run_dir}/stderr.txt"

# 2. Generate digest
python scripts/notebooks/audit_ipynb.py \
  examples/notebook.ipynb \
  --out-dir "${run_dir}"

# 3. Review digest
cat "${run_dir}/audit.md"

# 4. Use with agents
# Invoke notebook-output-auditor with audit.md path
# Invoke notebook-anomaly-spotter with audit.md path
```

## Integration with Agents

### notebook-runner Agent

The **notebook-runner** agent uses this script to generate digests after execution:

1. Executes notebook (pytest or nbconvert)
2. Captures stdout/stderr
3. Runs `audit_ipynb.py` to generate digest
4. Delegates to Haiku auditors for review

### Haiku Auditor Agents

**notebook-output-auditor**:
- Reads `audit.md`
- Finds exceptions, tracebacks, stderr
- Reports failures with cell indices and fixes

**notebook-anomaly-spotter**:
- Reads `audit.md`
- Finds empty results, missing artifacts
- Flags suspicious patterns (zeros, NaNs)

## Requirements

- Python 3.10+
- Standard library only (json, pathlib, sys, datetime)

## Related Documentation

- `.claude/agents/notebook-runner.md` - Notebook execution workflow
- `.claude/agents/notebook-output-auditor.md` - Exception detection
- `.claude/agents/notebook-anomaly-spotter.md` - Anomaly detection
- `.claude/rules/documentation/notebook-standards.md` - Notebook quality standards
