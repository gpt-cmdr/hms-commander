# M3 Model Upgrade Helper Scripts

**Purpose**: Scripts to assist with manual HMS 4.11 upgrades of HCFCD M3 models

**Approach**: These are HELPERS, not full automation. Each M3 model has unique characteristics and will require individual attention.

---

## Scripts

### validate_upgrade.py

**Purpose**: Compare HMS 3.3 vs HMS 4.11 DSS results

**Usage**:
```bash
python validate_upgrade.py <dss_33_path> <dss_411_path> <model_name> [tolerance]
```

**Example**:
```bash
python validate_upgrade.py \
    ../m3_version_test/D/D100-00-00/D1000000.dss \
    ../m3_version_test/D/D100-00-00_HMS411/results.dss \
    "Brays Bayou" \
    1.0
```

**Output**:
- Console report with statistics
- `validation_results.json` with detailed results
- Exit code 0 (pass) or 1 (fail)

**When to Use**: After executing a model in HMS 4.11

---

## Workflow Reference

**Complete Manual Workflow**: See `../../feature_dev_notes/HCFCD_M3_HMS411_UPGRADE_WORKFLOW.md`

**Quick Steps**:
1. Extract M3 model
2. Inspect HMS 3.3 project
3. Test baseline execution
4. Execute in HMS 4.11 (manually in GUI)
5. Run validate_upgrade.py
6. Document results
7. Repeat for all storm events

---

## Helper Scripts Planned (Not Yet Implemented)

### extract_model_info.py
Quick extraction of model metadata for documentation

### batch_validate_all_runs.py
Validate multiple storm events at once

### generate_report.py
Auto-generate markdown report from validation JSON

**Status**: Add these as needed based on actual upgrade experience

---

## Important Notes

⚠️ **Don't expect full automation**: Each M3 model is different
⚠️ **Manual steps required**: HMS 4.11 GUI execution recommended
⚠️ **Document as you go**: Each model will teach you something new
⚠️ **Start simple**: Use helpers for validation, not execution

---

**Last Updated**: 2025-12-23
