---
paths: hms_commander/**/*.py
---

# Critical HMS Bugs and Workarounds

**MUST READ**: These are hard-won facts discovered through decompilation, testing, and ERROR analysis. Agents that skip this file will waste hours on known issues.

---

## Bug 1: Relative Paths Cause ERROR 10132

**Symptom**: HMS fails with `ERROR 10132: Could not open project` or `ERROR 10132: File not found`

**Root Cause**: HMS Jython `OpenProject()` requires an **absolute** path. Relative paths fail silently or with ERROR 10132 depending on HMS version and working directory context.

**Workaround**:
```python
from pathlib import Path

# ❌ WRONG - will cause ERROR 10132
project_path = "projects/watershed"

# ✅ CORRECT - always resolve to absolute
project_path = Path("projects/watershed").resolve()
# or
project_path = Path(r"C:\Projects\watershed")
```

**Rule**: Every path passed to HmsCmdr, HmsJython, or init_hms_project MUST be absolute. Use `Path(...).resolve()` when receiving paths from user input.

---

## Bug 2: `Depth: 0.0` is Treated as NULL (HMS 4.x)

**Symptom**: After saving/reopening a project in HMS 4.x, `Depth: 0.0` values in `.met` files are **blanked out** (deleted). The model loses precipitation data.

**Root Cause**: HMS 4.x treats `0.0` as a sentinel value for "missing/unset data" in meteorologic model depth fields. When HMS rewrites the file, it skips these values.

**Workaround — Apply BEFORE `OpenProject()`**:
```python
# In .met file preprocessing, before HMS opens the project:
content = met_file.read_text(encoding='utf-8')
content = content.replace('Depth: 0.0\n', 'Depth: 0.0001\n')
met_file.write_text(content, encoding='utf-8')

# Engineering impact: negligible (0.0001 inches = 0.00254 mm)
```

**Critical**: This replacement MUST happen BEFORE calling `OpenProject()`. Making files read-only to prevent HMS from overwriting causes ERROR 12150.

**When to use**: All workflows that open HMS projects containing `.met` files with zero-depth precipitation values (e.g., Atlas 14 storms that have dry periods, frequency storms).

---

## Bug 3: `OpenProject()` Name Must Match `Project:` Line in `.hms` File

**Symptom**: HMS opens but the wrong project loads, or `ERROR: Project not found`

**Root Cause**: The `OpenProject(name)` Jython API call uses the `name` argument to look up the `Project: <name>` line in the `.hms` file — **not** the folder name or filename.

**Correct Usage**:
```python
# If the .hms file contains: "Project: Clear Creek Watershed"
# Then you MUST use that exact name:
script = f'''
from hms.model import JythonHms
hms = JythonHms.OpenProject("Clear Creek Watershed", r"{project_dir}")
'''

# ❌ WRONG - using folder name instead of project name
hms = JythonHms.OpenProject("clear_creek_watershed", r"C:\Projects\clear_creek_watershed")

# ✅ CORRECT - read Project: line from .hms file first
project_name = HmsPrj.get_project_name(project_path)  # reads "Project:" line
hms = JythonHms.OpenProject(project_name, str(project_dir))
```

**How to find the project name**:
```python
# Read the .hms file and extract the Project: line
hms_file = next(Path(project_dir).glob("*.hms"))
for line in hms_file.read_text(encoding='utf-8').splitlines():
    if line.startswith("Project:"):
        project_name = line.split(":", 1)[1].strip()
        break
```

---

## Bug 4: Muskingum Cunge Requires `Index Parameter Type: Index Celerity` (Exact String)

**Symptom**: HMS 4.x emits `ERROR 41087: Index parameter type is not set` for Muskingum Cunge reaches, even after setting what appears to be the right parameter.

**Root Cause**: The exact parameter name is `Index Parameter Type:` (with spaces), NOT `Index Method:`. Discovered by decompiling `hms.jar` (Q.java class).

**Decompilation Evidence** (Q.java, HMS 4.11):
```java
// Writing to basin file (line 494):
printWriter.println("     Index Parameter Type: " + s2.toString());

// Valid values from S.java enum:
public static final S INDEX_CELERITY = new S("Index Celerity", ...);
public static final S INDEX_FLOW = new S("Index Flow", ...);
```

**Required Basin File Format**:
```
Reach: ReachName
     Route: Muskingum Cunge
     Downstream: DownstreamElement
     Space-Time Method: Automatic DX and DT
     Index Parameter Type: Index Celerity
     Index Celerity: 1.5
End:
```

**Required Parameters for HMS 4.x Muskingum Cunge**:
| Parameter | Required Value | Notes |
|-----------|---------------|-------|
| `Index Parameter Type:` | `Index Celerity` or `Index Flow` | REQUIRED in HMS 4.x, absent in HMS 3.x |
| `Index Celerity:` | float (e.g., `1.5`) | Required when Index Parameter Type = Index Celerity |
| `Space-Time Method:` | `Automatic DX and DT` | Recommended |

**Version Upgrade Note**: When upgrading HMS 3.x to 4.x, all Muskingum Cunge reaches in all `.basin` files must have `Index Parameter Type:` added. See `.claude/agents/update_3_to_4/` for the production upgrade agent.

---

## Bug 5: DSS Comparison Acceptance Criteria (Quality Verdicts)

**Not a bug, but critical thresholds** for all agent workflows that validate model results:

| Metric | Threshold | Unit |
|--------|-----------|------|
| Peak Flow Difference | < 1.0% | percent |
| Volume Difference | < 0.5% | percent |
| Timing Difference | ≤ 1 timestep | timesteps |
| Execution Success | 100% of valid runs | (pre-existing failures excluded) |

**Quality Verdict System**:
- **GREEN**: All criteria passed → proceed
- **YELLOW**: Minor issues → manual review before proceeding
- **RED**: Critical failures → STOP, do not proceed

**Example usage**:
```python
from agents._shared import AgentWorkflow, QualityVerdict

peak_diff = abs(new_peak - baseline_peak) / baseline_peak * 100
volume_diff = abs(new_vol - baseline_vol) / baseline_vol * 100
timing_diff = abs(new_time - baseline_time)  # in timesteps

verdict = QualityVerdict.GREEN
if peak_diff >= 1.0 or volume_diff >= 0.5 or timing_diff > 1:
    verdict = QualityVerdict.YELLOW
if peak_diff >= 5.0 or volume_diff >= 2.0 or timing_diff > 3:
    verdict = QualityVerdict.RED
```

**Source**: LEARNINGS.md, CONSTITUTION.md, A1000000 project validation results.

---

## Related

- **Version support**: `.claude/rules/hec-hms/version-support.md`
- **Execution workflow**: `.claude/rules/hec-hms/execution.md`
- **Full LEARNINGS**: `.claude/LEARNINGS.md`
- **Full CONSTITUTION**: `.claude/CONSTITUTION.md`
- **Decompilation evidence**: `.old/research/decompile_findings.md`
