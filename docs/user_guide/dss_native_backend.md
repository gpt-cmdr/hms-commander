# Native DSS backend

HMS Commander reads and writes HEC-DSS files through one of three backends. The
default uses HEC Monolith (the HEC-DSS Java library) through pyjnius. The native
backend uses `ras_commander_fast_dss`, a pure-Rust HEC-DSS engine for DSS6 and DSS7
files, and starts no Java VM. The shadow backend runs both and logs every difference.

!!! warning "Pre-release engine"
    The engine's distribution, `ras-commander-fast-dss`, is not published on PyPI and is
    not an `hms-commander` dependency or extra. The Java backend stays the default. Install
    the wheel you were given into the same environment:
    ```bash
    pip install ras_commander_fast_dss-<version>-<tag>.whl
    ```

## Select a backend

Set the class attribute, or the environment variable, which takes precedence:

```python
from hms_commander import HmsDss

HmsDss.backend = "native"      # "java" (default), "native" or "shadow"
print(HmsDss.get_backend())    # 'native'
```

```bash
set HMS_COMMANDER_DSS_BACKEND=native
```

The setting applies to every DSS call in the process: `DssCore`, `HmsDss`, `HmsDssGrid`,
and the readers built on them (`HmsResults`, the DSS metadata in `HmsPrj`). One attribute,
`HmsDss.backend`, controls them all.

| Backend | Reads and writes through | Without the engine | Returns |
|---|---|---|---|
| `java` | HEC Monolith (pyjnius, Java 8+) | works; the engine is never imported | the Java result |
| `native` | `ras_commander_fast_dss` | raises `ImportError` | the native result |
| `shadow` | Java, then native for comparison | runs Java only (one warning) | the Java result or error |

`HmsDss.is_available()` follows the selected backend: `native` needs the engine and no
pyjnius; `java` and `shadow` need pyjnius.

## What the native backend covers

`HmsDss.get_capabilities()` returns this table as a DataFrame, with the installed engine's
state in `attrs` (`native_available`, `native_writes_available`, `native_grid_qualified`,
`engine_features`).

| Operation | Native | Notes |
|---|---|---|
| `get_catalog` | yes | Same pathnames in the same (HEC catalog) order |
| `read_timeseries`, `read_multiple_timeseries` | yes | Whole dataset with any D part; `start_date`/`end_date` are the same inclusive stamp filter on both backends |
| `get_peak_value` (and `get_peak_flows_batched`) | yes | Missing values excluded; first maximum on ties |
| `read_paired_data` | yes | The HMS dict: first curve, axis types under `x_label`/`y_label` |
| `read_grid` | gated | Needs an engine that advertises `grid_srs_monolith_parity` |
| `get_file_version` | yes | 6 or 7 |
| `write_timeseries` | gated | Regular intervals only |
| `write_paired_data`, `write_multiple_paired_data`, `import_atlas14_temporal` | gated | Float32 (PD) records, as Monolith stores them |
| `HmsDssGrid.write_grid_timeseries` | gated | INST-VAL and INST-CUM grids; PER-CUM and PER-AVER are refused (see below) |

"Gated" operations check the installed engine's capabilities, not its version. Writes need
the complete writer API (`create`, `write_timeseries`, `write_paired_data`, `write_grid`,
DSS6 support); grid reads need the `grid_srs_monolith_parity` feature. When a gate is
closed the call raises `hms_commander.dss.DssCapabilityError`. The native backend never
falls back to Java.

## Differences from the Java backend

The native backend returns the Java backend's shapes: the same DataFrame columns, index
dtype and `attrs` for time series, the same dict keys for paired data and grids. These
differences remain:

| Label | Difference | Where |
|---|---|---|
| D1 | Java returns HEC missing values as stored (-901, -902, -3.4028e38); native returns NaN | time series |
| D5 | Java cannot read time-series patterns (`TS-PATTERN` D part) and raises "No data found"; native returns them with stamps in year 3000 | time series |
| G1 | Native also maps -901/-902 to NaN in grid cells; Java maps only -3.4028e38 | grids |
| W1 | The native writers refuse input that the Java path writes, before anything is written (next section) | writes |

## Write rules

- **New files** are DSS7, as HEC Monolith 3.3.27 creates them. `write_timeseries` takes
  `dss_version=6` for a new DSS6 file. An existing file keeps its version.
- **Missing values.** `write_timeseries` stores NaN as -3.4028e38 on DSS7 and -901 on
  DSS6 on both backends, and refuses infinity.
- **DSS6 text limits.** A DSS6 paired-data record stores at most 8 characters per unit
  and type. HEC Monolith truncates longer strings without a warning (`CUMULATIVE` is
  stored as `CUMULATI`). The native writer refuses them with `ValueError` and writes
  nothing; pass an 8-character string, or write to a DSS7 file.
- **Atlas 14 temporal curves.** `import_atlas14_temporal` writes one record per quartile
  and probability, `//{region}/{QUARTILE}/{duration}HR//{probability}/`, with the Y type
  `CUMULATIVE` on DSS7 and `CUMULATI` on DSS6. `CUMULATI` is the value HEC Monolith
  stores on DSS6, so both backends write the same record.
- **Paired-data precision on DSS6.** Monolith stores the precision word as 0, which
  Monolith reads back as "unset"; the native writer stores -1, also "unset". The HMS
  `read_paired_data` dict does not report precision.
- **Grids.** `write_grid_timeseries` stores one time per grid: the D part is the time and
  the E part the same time (midnight is the previous day's `2400` in E), as Monolith
  stores it. HEC period data (PER-CUM, PER-AVER) needs an end time after the start time,
  so the native writer refuses those data types. The Java path writes them. AORC
  precipitation (`HmsAorc.convert_to_dss_grid`, PER-CUM) therefore needs the Java backend.

## Shadow mode

Shadow mode qualifies the native backend on your own files without changing results:

```python
from hms_commander import HmsDss, HmsResults

HmsDss.backend = "shadow"
peaks = HmsResults.get_peak_flows("results.dss")   # Java results
print(HmsDss.get_shadow_summary())
# {'get_catalog|identical|identical': 1, 'get_peak_value|identical|identical': 42, ...}
```

Each comparison is logged on the `hms_commander.dss` logger: identical results at DEBUG,
the known differences above as `expected` at INFO (D1 at DEBUG), and anything else as
`UNEXPECTED` at WARNING. A comparison never raises.

Shadow writes run on Java first. The native writer then repeats the write on a temporary
copy of the target file (or a new temporary file), and both files are read back with the
native reader and compared. The caller's file only ever receives the Java write. Files
larger than `HmsDss.shadow_copy_limit_mb` (256 MB; environment variable
`HMS_COMMANDER_DSS_SHADOW_COPY_LIMIT_MB`) are not copied, and the comparison is logged
as skipped.

## Qualification evidence

`tests/test_dss_native_backend.py` compares the two backends on the HEC-HMS example
projects that `HmsExamples` extracts (castro, tenk and river_bend from the HEC-HMS 4.13
`samples.zip`; all DSS6):

- Reads: every catalog and file version, every time-series record (more than 1,000;
  peak values included), every paired-data record and 25 HRAP precipitation grids of
  `tenk/hrap.dss`. Only the D1 and D5 differences occur.
- Writes, DSS6 and DSS7: a castro hydrograph, the six storage-outflow and
  elevation-storage tables of tenk and river_bend, the NOAA Atlas 14 Texas region 3
  24-hour temporal distributions (45 records), and three hours of tenk HRAP cells written
  as INST-VAL grids. Each is written natively and with Java, read back with Java and
  compared. The stored values match bit for bit.

The tests skip when the engine, Java/pyjnius or an HEC-HMS installation with
`samples.zip` is missing.

## Related topics

- [DSS Operations](dss_operations.md) - Reading and writing DSS files
- [Results Analysis](results_analysis.md) - Processing HMS results
- [HEC-DSS documentation](https://www.hec.usace.army.mil/confluence/dssdocs) - HEC's
  description of the DSS file format and pathnames
