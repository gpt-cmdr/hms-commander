---
name: hms_manage_versions
shared_corpus: true
harness_scope: shared
source_owner: gpt-cmdr
security_review: internal
description: |
  Manages HEC-HMS version differences (3.x vs 4.x), handles Python 2/3 compatibility,
  detects HMS installations, and generates version-appropriate Jython scripts. Use when
  working with legacy HMS 3.x projects, upgrading models from 3.x to 4.x, testing across
  multiple HMS versions, troubleshooting version-specific issues, or understanding 32-bit
  vs 64-bit architecture differences and memory limits.
  Trigger keywords: HMS version, HMS 3.x, HMS 4.x, legacy, upgrade, Python 2 compatible,
  32-bit, 64-bit, version detection, multi-version testing.
---

# Managing HMS Versions

## When This Skill Is Activated

You are the HMS version management specialist. Route the user's request through the decision tree below.

## Decision Tree

1. **User needs to detect installed version** → "Version Detection"
2. **User has a HMS 3.x project** → "Working with HMS 3.x"
3. **User wants to upgrade 3.x to 4.x** → "Version Upgrade"
4. **User wants multi-version testing** → "Multi-Version Testing"
5. **Automated upgrade workflow** → Delegate to `.claude/agents/update_3_to_4/AGENT.md`

## Version Detection

1. Find the HMS executable:
   ```python
   from hms_commander import HmsJython
   hms_exe = HmsJython.find_hms_executable()
   ```
2. Determine version from path:
   ```python
   is_3x = "(x86)" in str(hms_exe)
   print(f"HMS {'3.x (32-bit)' if is_3x else '4.x (64-bit)'}: {hms_exe}")
   ```

## Working with HMS 3.x

When working with any HMS 3.x project, you MUST set `python2_compatible=True`:

```python
script = HmsJython.generate_compute_script(
    project_path=path, run_name="Run 1",
    python2_compatible=True  # CRITICAL — HMS 3.x uses Python 2 Jython
)
success, stdout, stderr = HmsJython.execute_script(script, hms_exe_path=hms_3x_path)
```

Key 3.x constraints:
- 32-bit architecture, max ~1.3 GB memory
- Install path: `C:\Program Files (x86)\HEC\HEC-HMS\3.x\`
- Java: `java/bin/java.exe` (not `jre/`)
- Print syntax: `print "text"` (no parentheses)

## Version Upgrade

**Manual**: Open the project in HMS 4.x GUI and save — this converts the file format.

**Automated**: Delegate to the production agent:
`.claude/agents/update_3_to_4/AGENT.md`

**Before upgrading**: Clone the project first to preserve the 3.x baseline:
```python
# Delegate to hms_clone_components skill
```

## Multi-Version Testing

Test the same project across installed HMS versions:
```python
from hms_commander import HmsExamples

versions = HmsExamples.list_versions()
for version in versions:
    python2 = version.startswith("3.")
    script = HmsJython.generate_compute_script(
        path, run, python2_compatible=python2)
    hms_exe = HmsExamples.get_hms_exe(version)
    success, stdout, stderr = HmsJython.execute_script(script, hms_exe)
    print(f"HMS {version}: {'PASS' if success else 'FAIL'}")
```

## Version Quick Reference

| Aspect | HMS 3.x | HMS 4.x |
|--------|---------|---------|
| Architecture | 32-bit | 64-bit |
| Max memory | ~1.3 GB | 32+ GB |
| Python | `python2_compatible=True` | Default (Python 3) |
| Install path | `Program Files (x86)` | `Program Files` |
| Java | `java/bin/java.exe` | `jre/bin/java.exe` |
| Supported | HMS 3.3-3.5 | HMS 4.4.1+ |
| Not supported | — | HMS 4.0-4.3 (legacy classpath) |

## If Something Goes Wrong

- **SyntaxError**: Forgot `python2_compatible=True` for HMS 3.x — this is the #1 error
- **OutOfMemoryError**: HMS 3.x limited to ~1.3 GB — upgrade to 4.x
- **HMS not found**: Specify path manually via `hms_exe_path=`
- **File format errors after upgrade**: Some 3.x features don't map 1:1 — check HMS log

## Primary Sources

- `hms_commander/HmsJython.py` — Version detection and script generation
- `.claude/rules/hec-hms/version-support.md` — Complete differences
- `examples/01_multi_version_execution.ipynb` — Multi-version workflow
- `.claude/agents/update_3_to_4/` — Automated upgrade agent

## Delegation Points

- **Execute after version setup** → `hms_execute_runs` skill
- **Clone before upgrading** → `hms_clone_components` skill
- **Automated 3→4 upgrade** → `.claude/agents/update_3_to_4/AGENT.md`
