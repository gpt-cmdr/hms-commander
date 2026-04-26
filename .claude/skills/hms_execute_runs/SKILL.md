---
name: hms_execute_runs
shared_corpus: true
harness_scope: shared
source_owner: gpt-cmdr
security_review: internal
description: |
  Executes HEC-HMS simulations using HmsCmdr.compute_run(), handles parallel
  execution across multiple runs, and manages Jython script generation. Use when
  running HMS simulations, executing runs, computing models, setting up parallel
  computation workflows, generating Jython scripts, or running batch simulations.
  Handles HMS 3.x and 4.x version differences and Python 2/3 compatibility.
  Trigger keywords: run simulation, execute HMS, compute run, parallel execution,
  batch runs, Jython script, HMS compute, run model.
---

# Executing HEC-HMS Runs

## When This Skill Is Activated

You are the HMS execution specialist. Follow this sequential workflow.

## Execution Workflow

### 1. Ensure Project Is Initialized

```python
from hms_commander import init_hms_project, hms
init_hms_project(r"C:\Projects\watershed")
```

If already initialized, verify with `hms.project_name`. If not initialized, ask the user for the project path.

### 2. Identify the Run(s)

Check available runs:
```python
print(hms.run_df)
```
Ask the user which run(s) to execute if not specified.

### 3. Detect HMS Version

```python
from hms_commander import HmsJython
hms_exe = HmsJython.find_hms_executable()
is_3x = "(x86)" in str(hms_exe)
```

If HMS 3.x is detected, you MUST use `python2_compatible=True`. This is the most common source of failures.

### 4. Execute

**Single run**:
```python
from hms_commander import HmsCmdr
success = HmsCmdr.compute_run("Run 1")
```

**Multiple runs in parallel**:
```python
HmsCmdr.compute_parallel(["Run 1", "Run 2", "Run 3"], max_workers=2)
```

**Legacy HMS 3.x** (manual script generation):
```python
script = HmsJython.generate_compute_script(
    project_path=path, run_name="Run 1",
    python2_compatible=True  # CRITICAL for HMS 3.x
)
success, stdout, stderr = HmsJython.execute_script(script, hms_exe_path=hms_3x_path)
```

### 5. Check Results

```python
if success:
    dss_file = hms.run_df.loc["Run 1", "dss_file"]
    peaks = HmsResults.get_peak_flows(dss_file)
    print(peaks)
else:
    # Check log file for errors
    log_file = hms.project_folder / f"RUN_Run 1.log"
    print(open(log_file).read())
```

## Worker Count Guidance

- Default: `max_workers=2` (safe for all systems)
- CPU-bound: `os.cpu_count() - 1`
- Memory-constrained: `max_workers=1`

## Version Quick Reference

| Aspect | HMS 3.x | HMS 4.x |
|--------|---------|---------|
| Architecture | 32-bit | 64-bit |
| Python | `python2_compatible=True` | Default (Python 3) |
| Install Path | `Program Files (x86)` | `Program Files` |

## If Something Goes Wrong

- **SyntaxError in Jython**: Forgot `python2_compatible=True` for HMS 3.x
- **OutOfMemoryError**: HMS 3.x limited to ~1.3 GB — upgrade to 4.x or reduce model complexity
- **HMS not found**: Specify path manually via `hms_exe_path=` parameter
- **Timeout**: Large models may need longer — check log file for progress
- **Check HMS log**: `hms.project_folder / f"RUN_{run_name}.log"`

## Primary Sources

- `hms_commander/HmsCmdr.py` — Execution engine
- `hms_commander/HmsJython.py` — Script generation and version detection
- `examples/01_multi_version_execution.ipynb` — Complete workflow
- `.claude/rules/hec-hms/execution.md` — Execution patterns

See `reference/compute_run.md` for complete HmsCmdr.compute_run() patterns.

## Implementing Agent

For complex execution scenarios, delegate to:
`.claude/agents/run-manager-specialist.md`

## Delegation Points

- **Modify parameters before running** → `hms_parse_basin-models` skill
- **Update precipitation before running** → `hms_update_met-models` skill
- **Extract results after running** → `hms_extract_dss-results` skill
- **Clone for QAQC comparison runs** → `hms_clone_components` skill
- **Version issues or upgrades** → `hms_manage_versions` skill
