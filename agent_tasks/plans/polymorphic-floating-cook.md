# Plan: HMS SQLite Grid Database Support

## Context

HEC-HMS 4.x gridded models (Modified Clark, SCS Grid) store authoritative spatial geometry in SQLite databases, not in `.geo`/`.map` text files. hms-commander cannot extract geometry from any gridded HMS project.

**Test data**: `river_bend` example project (bundled with HMS 4.x, extractable via `HmsExamples`)

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `hms_commander/HmsSqlite.py` | **CREATE** | New static class for SQLite grid database operations |
| `hms_commander/__init__.py` | EDIT | Add HmsSqlite import and `__all__` export |
| `hms_commander/HmsGeo.py` | EDIT | Add `detect_model_type()` static method |
| `hms_commander/HmsPrj.py` | EDIT | Add SQLite discovery, `is_gridded` flag, CRS-from-SQLite |
| `tests/test_hms_sqlite.py` | **CREATE** | Tests using river_bend example project |

---

## Step 1: Create `hms_commander/HmsSqlite.py`

New static class following HmsHuc.py patterns (lazy imports, `_check_dependencies()`, `@log_call`).

**Methods**:

| Method | Returns | Notes |
|--------|---------|-------|
| `list_layers(sqlite_path)` | `pd.DataFrame` | Table name, row count, geometry type. Uses stdlib `sqlite3` only. |
| `get_crs(sqlite_path)` | `Optional[str]` | WKT string from `spatial_ref_sys`. Uses stdlib `sqlite3` only. |
| `get_subbasins(sqlite_path)` | `GeoDataFrame` | From `subbasin2d` table (polygons) |
| `get_reaches(sqlite_path)` | `GeoDataFrame` | From `reach2d` table (linestrings with topology) |
| `get_outlets(sqlite_path)` | `GeoDataFrame` | From `outlet` table (points) |
| `get_junctions(sqlite_path)` | `GeoDataFrame` | From `junction` table (points, often empty) |
| `get_discretization(sqlite_path)` | `GeoDataFrame` | Grid cells (large, opt-in) |
| `read_grid_database(sqlite_path, include_discretization=False, skip_empty=True)` | `Dict[str, GeoDataFrame]` | All layers in one call |
| `discover_sqlite_files(project_dir)` | `List[Path]` | Find all .sqlite files |
| `join_with_parameters(sqlite_gdf, subbasin_df, join_column='name')` | `GeoDataFrame` | Merge geometry + basin parameters |

**Dependencies**: `geopandas` (lazy import, requires `pip install hms-commander[gis]`), `sqlite3` (stdlib)

**Reuse patterns from**: `hms_commander/HmsHuc.py` (dependency checking, static class, geopandas lazy import)

---

## Step 2: Update `__init__.py`

Add `from .HmsSqlite import HmsSqlite` and add `"HmsSqlite"` to `__all__`, near the existing GIS section.

---

## Step 3: Add `detect_model_type()` to HmsGeo

One new static method:

```python
@staticmethod
@log_call
def detect_model_type(project_dir) -> str:
    """Returns 'gridded' if .sqlite files found, 'lumped' otherwise."""
```

No HmsSqlite import needed -- just filesystem check via `Path.glob("*.sqlite")`.

---

## Step 4: Add SQLite Discovery and CRS to HmsPrj

1. **New attributes** in `__init__()`: `self.sqlite_files: List[Path] = []` and `self.is_gridded: bool = False`
2. **New method** `_discover_sqlite_files()`: `sorted(self.project_folder.glob("*.sqlite"))`
3. **CRS detection** from SQLite's `spatial_ref_sys` table as **Strategy 0** in `_detect_crs()` (before .prj files). Uses stdlib `sqlite3` + `pyproj.CRS.from_wkt()`. Handles custom CRS (no EPSG code) by storing CRS object with `crs_epsg=None`.
4. Call `_discover_sqlite_files()` in `initialize()` and log results.

---

## Step 5: Tests

`tests/test_hms_sqlite.py` using river_bend example project (via `HmsExamples.extract_project`).

**Test cases**: list_layers, get_crs, get_subbasins (2 rows), get_reaches (0 rows), get_outlets (missing table), get_junctions (0 rows handled gracefully), read_grid_database, discover_sqlite_files (3 files), join_with_parameters, HmsPrj integration (sqlite_files, is_gridded, CRS), HmsGeo.detect_model_type.

---

## Verification

1. Run tests: `python -m pytest tests/test_hms_sqlite.py -v`
2. Smoke test in Python:
   ```python
   from hms_commander import HmsSqlite, init_hms_project
   HmsExamples.extract_project("river_bend")
   subs = HmsSqlite.get_subbasins("hms_example_projects/river_bend/Minimum_Facility.sqlite")
   assert len(subs) == 2
   hms = init_hms_project("hms_example_projects/river_bend")
   assert hms.is_gridded == True
   assert len(hms.sqlite_files) == 3
   ```
3. Verify import works: `from hms_commander import HmsSqlite`
