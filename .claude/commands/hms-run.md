Execute an HEC-HMS simulation using the `hms_execute_runs` skill.

## Steps

1. **Identify the project and run(s)**:
   - Ask user for project path if not provided
   - List available runs from `.run` files or HmsPrj

2. **Pre-flight checks** (from `.claude/rules/hec-hms/critical-bugs-workarounds.md`):
   - Ensure project path is **absolute** (ERROR 10132 if relative)
   - Check for `Depth: 0.0` in `.met` files — replace with `0.0001` before opening
   - Verify `OpenProject()` name matches `Project:` line in `.hms` file

3. **Execute**:
   ```python
   from hms_commander import init_hms_project, HmsCmdr
   from pathlib import Path

   project_path = Path(r"<PROJECT_PATH>").resolve()  # MUST be absolute
   init_hms_project(project_path)

   # Single run
   HmsCmdr.compute_run("<RUN_NAME>")

   # Multiple runs in parallel
   HmsCmdr.compute_parallel(["Run 1", "Run 2"], max_workers=2)
   ```

4. **Verify results**:
   - Check log file for `NOTE 10185` or `NOTE 15302` (completion markers)
   - Check for `ERROR` entries in log
   - Confirm DSS output file was created

## HMS Version Handling

- **HMS 3.x** (32-bit, `Program Files (x86)`): Use `python2_compatible=True`
- **HMS 4.x** (64-bit, `Program Files`): Default (Python 3)

## Reference

- Skill: `.claude/skills/hms_execute_runs/SKILL.md`
- Critical bugs: `.claude/rules/hec-hms/critical-bugs-workarounds.md`
- Execution patterns: `.claude/rules/hec-hms/execution.md`
