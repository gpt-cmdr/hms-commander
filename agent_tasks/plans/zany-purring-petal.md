# Plan: Batch Parameter Management for HmsBasin and HmsMet

## Context

Modelers working with real HMS projects (131 subbasins, 94 reaches in our test file) must currently loop element-by-element to read or modify parameters. There is no way to export all parameters to CSV, edit in Excel, and import back. This is the most requested workflow gap in hms-commander and establishes a cross-repo pattern for ras-commander.

**Bug fix included**: `get_subbasins()` line 74 uses `attrs.get('Loss')` but the HMS file key is `LossRate:`, so `loss_method` is always `None`. Same bug at line 191 in `get_loss_parameters()`.

---

## Files to Modify

| File | Action | Description |
|------|--------|-------------|
| `hms_commander/_constants.py` | EDIT | Add 4 parameter mapping dicts + reverse maps |
| `hms_commander/_parsing.py` | EDIT | Add `find_all_blocks()` returning match positions |
| `hms_commander/HmsBasin.py` | EDIT | Add 10 batch methods + fix LossRate bug + private helpers |
| `hms_commander/HmsMet.py` | EDIT | Add `set_all_gage_assignments()` |

---

## Step 1: Add Parameter Mapping Dicts to `_constants.py`

Add four mapping dicts that translate HMS file keys to snake_case DataFrame columns:

- `LOSS_PARAM_MAP`: `{'LossRate': 'loss_method', 'Percent Impervious Area': 'percent_impervious', 'Initial Deficit': 'initial_deficit', ...}`
- `TRANSFORM_PARAM_MAP`: `{'Transform': 'transform_method', 'Time of Concentration': 'time_of_concentration', ...}`
- `BASEFLOW_PARAM_MAP`: `{'Baseflow': 'baseflow_method', 'Recession Factor': 'recession_factor', ...}`
- `ROUTING_PARAM_MAP`: `{'Route': 'route_method', 'Muskingum K': 'muskingum_k', ...}`

Each dict also gets a reverse map (`LOSS_PARAM_REVERSE_MAP`, etc.) for writing snake_case columns back to HMS file keys.

**Key mappings to include** (from actual basin file inspection):

Loss (Green and Ampt): `LossRate`, `Percent Impervious Area`, `Initial Loss`, `Moisture Deficit`, `Wetting Front Suction`, `Hydraulic Conductivity`, `Initial Variable`

Loss (Deficit and Constant): `Initial Deficit`, `Maximum Deficit`, `Constant Rate`, `Percolation Rate`

Loss (SCS CN): `Curve Number`, `Initial Abstraction`

Transform (Clark): `Time of Concentration`, `Storage Coefficient`, `Clark Method`

Transform (SCS UH): `Lag`, `Graph Type`

Routing (Muskingum-Cunge): `Muskingum K`, `Muskingum x`, `Muskingum Steps`, `Reach Length`, `Reach Slope`, `Manning n`, `Index Parameter Type`, `Index Celerity`, `Space-Time Method`

---

## Step 2: Add `find_all_blocks()` to `_parsing.py`

Add one method to HmsFileParser that returns match objects WITH positions (not just parsed dicts), needed for the reverse-iteration write algorithm:

```python
@staticmethod
def find_all_blocks(content: str, block_keyword: str) -> List[Tuple[re.Match, str, Dict[str, str]]]:
    """Return list of (match_object, element_name, parsed_attrs) for all blocks."""
```

This extends the existing `parse_blocks()` pattern while preserving match positions for efficient in-place editing.

---

## Step 3: Fix `LossRate` Bug in HmsBasin

In `get_subbasins()` line 74:
```python
# Before
'loss_method': attrs.get('Loss'),
# After
'loss_method': attrs.get('LossRate', attrs.get('Loss')),
```

In `get_loss_parameters()` line 191:
```python
# Before
loss_method = attrs.get('Loss', 'None')
# After
loss_method = attrs.get('LossRate', attrs.get('Loss', 'None'))
```

---

## Step 4: Add Private Helpers to HmsBasin

Two generic private helpers to avoid duplication across 4 parameter types:

**`_get_all_element_params(basin_path, element_type, param_map)`** → DataFrame
- Reads file once via `HmsFileParser.read_file()`
- Parses blocks via `HmsFileParser.parse_blocks()`
- Maps HMS keys to snake_case columns using the param_map dict
- Returns DataFrame with one row per element, NaN for non-applicable params

**`_set_all_element_params(basin_path, element_type, params_df, reverse_map, validate_fn, create_backup)`** → Dict
- Reads file once
- Creates `.bak` backup
- Finds all blocks using `find_all_blocks()`
- Iterates blocks in reverse order (to preserve string offsets during replacement)
- For each element matching a DataFrame row: updates non-NaN columns via `update_parameter()`
- Writes file once
- Returns summary dict: `{subbasins_modified, parameters_changed, subbasins_not_found, warnings, backup_path}`

**Validation helpers**: `_validate_loss_param()`, `_validate_transform_param()` — return warning string or None. Warnings go in summary dict, don't prevent write.

---

## Step 5: Add Batch Methods to HmsBasin

Eight new public methods, all `@staticmethod @log_call`:

**Getters** (call `_get_all_element_params`):
1. `get_all_loss_parameters(basin_path, hms_object=None)` → DataFrame
2. `get_all_transform_parameters(basin_path, hms_object=None)` → DataFrame
3. `get_all_baseflow_parameters(basin_path, hms_object=None)` → DataFrame
4. `get_all_routing_parameters(basin_path, hms_object=None)` → DataFrame

**Setters** (call `_set_all_element_params`):
5. `set_all_loss_parameters(basin_path, params_df, create_backup=True, hms_object=None)` → Dict
6. `set_all_transform_parameters(basin_path, params_df, create_backup=True, hms_object=None)` → Dict
7. `set_all_baseflow_parameters(basin_path, params_df, create_backup=True, hms_object=None)` → Dict
8. `set_all_routing_parameters(basin_path, params_df, create_backup=True, hms_object=None)` → Dict

**CSV roundtrip**:
9. `export_parameters_csv(basin_path, output_csv, param_types=None, hms_object=None)` → Path
10. `import_parameters_csv(basin_path, input_csv, create_backup=True, hms_object=None)` → Dict

---

## Step 6: Add `set_all_gage_assignments()` to HmsMet

`HmsMet.get_gage_assignments()` already returns a DataFrame. Add the write counterpart:

```python
@staticmethod
@log_call
def set_all_gage_assignments(met_path, assignments_df, create_backup=True, hms_object=None) -> Dict:
```

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Export format** | **CSV only** | Universal — every engineer has Excel. No extra dependencies. Git-diffable. Metadata via comment header rows. |
| Column naming | snake_case | Matches existing `get_loss_parameters()` return keys |
| NaN handling | Skip (don't modify) | Safe default — only changes what user explicitly set |
| Method change | Allowed via `loss_method` column | Real workflow need, but warns if required params missing |
| Validation | Warnings, not errors | Batch of 131 subbasins shouldn't fail on one bad value |
| Backup | Auto `.bak` before write | Follows ras-commander pattern, opt-out via `create_backup=False` |
| Write algorithm | Reverse-iteration in-place | Single file read/write, O(n) string operations |

### CSV Format Details

Export writes comment header rows for metadata, then standard CSV:
```csv
# HMS Basin Parameters
# Source: A100_1PCT.basin
# Exported: 2026-02-21 14:30:00
# Unit System: English
name,area,loss_method,percent_impervious,initial_loss,moisture_deficit,...
A100A,3.213,Green and Ampt,0.9,0.1,0.385,...
A100B,2.213,Green and Ampt,9.2,0.1,0.385,...
```

Import uses `pd.read_csv(input_csv, comment='#')` to skip metadata rows. This means engineers can edit the CSV in Excel (which ignores `#` rows) and the metadata is preserved if they don't delete those rows.

---

## Verification

1. **Unit test with real basin file**: Read A100_1PCT.basin (131 subbasins, Green and Ampt + Clark), verify DataFrame has correct dimensions and values.

2. **CSV roundtrip test**: `export_parameters_csv()` → modify CSV → `import_parameters_csv()` → verify changes applied and .bak created.

3. **Idempotency test**: `get_all_loss_parameters()` → `set_all_loss_parameters()` with unchanged DataFrame → verify file content identical.

4. **LossRate bug fix test**: `get_subbasins()` should now return actual loss method names ("Green and Ampt"), not None.

5. **NaN handling test**: Create DataFrame with some NaN columns, verify only non-NaN values are modified.

```python
from hms_commander import HmsBasin

# Test with real project
df = HmsBasin.get_all_loss_parameters("tests/projects/2014.08_HMS/A1000000_baseline_33/A100_1PCT.basin")
assert len(df) == 131
assert df['loss_method'].iloc[0] == 'Green and Ampt'
assert df['hydraulic_conductivity'].notna().all()

# CSV roundtrip
HmsBasin.export_parameters_csv(basin_path, "test_params.csv")
result = HmsBasin.import_parameters_csv(basin_path, "test_params.csv")
assert result['loss']['subbasins_modified'] >= 0
```
