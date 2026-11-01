# Native DSS backend

HMS Commander reads and writes HEC-DSS files through one of three backends. The
default uses HEC Monolith (the HEC-DSS Java library) through pyjnius. The native
backend uses `ras_commander_fast_dss`, a pure-Rust HEC-DSS engine for DSS6 and DSS7
files, and starts no Java VM. The shadow backend runs both and logs every difference.
The selection, shadow behavior and comparison labels follow ras-commander's `RasDss`.

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
| `shadow` | reads: native, then Java for comparison; writes: Java, then native on a temporary copy | runs Java only (one warning) | reads: the native result or error (grids: Java's grid); writes: the Java result or error |

`HmsDss.is_available()` follows the selected backend: `native` needs the engine and no
pyjnius; `java` needs pyjnius; `shadow` needs the engine (without it, shadow runs Java).

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
| `HmsDssGrid.write_grid_timeseries` | gated | All four data types; PER-CUM and PER-AVER grids need a period (see below) |

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
- **Grids.** See [Grid periods and AORC stamps](#grid-periods-and-aorc-stamps). Both
  backends store the same D and E parts.

## Grid periods and AORC stamps

`HmsDssGrid.write_grid_timeseries` treats PER-CUM and PER-AVER `timestamps` as period
**end** times. The period length is `interval_minutes`, otherwise the spacing of the stamps,
which must be uniform; a single grid or stamps with gaps must give `interval_minutes`. You can also pass one more time than
there are grids, as period boundaries. INST-VAL and INST-CUM grids keep one instant in both
parts.

| AORC stamp T | D part (T - 1h) | E part (T) |
|---|---|---|
| 2020-05-01 12:00 | `01MAY2020:1100` | `01MAY2020:1200` |
| 2020-05-02 00:00 | `01MAY2020:2300` | `01MAY2020:2400` |
| 2020-05-02 01:00 | `02MAY2020:0000` | `02MAY2020:0100` |

An AORC stamp is the end of its hour (NWS OWP AORC v1.1 methods, section 4.1: precipitation
"ending at the 'top' of each hour"). `HmsAorc.convert_to_dss_grid` therefore works on the
native backend, with a fixed 60-minute period. A period with its start at or after its end,
or an unknown data type, raises `ValueError` on every backend.

**Recheck existing AORC work.** Earlier versions wrote PER-CUM grids with equal D and E
parts. In a one-burst test (tenk sample, 100 mm in one hour), HEC-HMS 4.9, 4.11, 4.12 and
4.13 did not read such grids as rain, and this is not a timing shift:

| Stamps | Subbasin precipitation | Peak outflow at Tenkiller | HEC-HMS log |
|---|---|---|---|
| Equal D and E (earlier versions) | 0 | 620 cfs, the initial baseflow | `WARNING 40503` for every subbasin and hour; the run still reports success |
| Period (this version) | 3.937 in, all in the step ending at T | 79,546 cfs | No missing-precipitation warning (DSS7 on 4.11 to 4.13, DSS6 on 4.9 and 4.13) |

Results computed from those earlier files contain no precipitation from them. Look for
`WARNING 40503` in the run log, regenerate the DSS file with this version, and recheck any
calibration or result that used it. Do not merge old and new files: the same hour has two
different pathnames.

HEC-HMS 4.9 also did not read DSS7 grids from any writer, with either stamp (`ERROR 12520`,
no rain, and the run still reports success). For 4.9, write to an existing DSS6 file.

The test covers one sample project, an hourly control interval on these versions and a
15-minute interval on 4.13. It does not establish how other versions treat these records.
With period stamps, moving the record one hour later moved the rain and the outlet peak one
hour later.

## Shadow mode

Shadow mode runs the native backend and checks it against Java on your own files:

```python
from hms_commander import HmsDss, HmsResults

HmsDss.backend = "shadow"
peaks = HmsResults.get_peak_flows("results.dss")   # native results, compared with Java
print(HmsDss.get_shadow_summary())
# {'catalog|identical|identical': 1, 'get_peak_value|identical|identical': 42, ...}
```

Reads return the native result, or raise the native error. Java runs afterwards for the
comparison. When the native read fails with anything other than "not found" (or an
invalid file for `get_file_version`), Java is not run: the comparison is recorded as
skipped (`java skipped: native <Error>`) and the native error is raised. This also protects
the process: Java can create a missing file, and it crashes the JVM when it reads a record
of the wrong type. `get_peak_value` and `read_paired_data` keep their contract there and
return None. `read_grid` returns Java's grid and only compares the native grid. When Java cannot run (no pyjnius,
Java or HEC Monolith), comparisons are recorded as skipped (`java unavailable`).

Each comparison is logged on the `hms_commander.dss` logger: identical results at DEBUG,
the known differences above as `expected` at INFO (D1 at DEBUG), and anything else as
`UNEXPECTED` at WARNING. A comparison never raises. Other `expected` labels are
`D15 catalog order`, `D4 all-missing dataset (error type)`, `D4 HEC DSS6 no-data rule`,
`D4/D6 no data: typed native error`, `D7 Latin-1 pathname`, `D8 weekly data`,
`D9 blank units/type whitespace`, `J2b Java sub-minute tail`, `PD3 unit/type whitespace` and
`G2 whitespace`, as in ras-commander.

Shadow reads differ from ras-commander's `RasDss` in these ways, because the HMS methods
have other contracts:

- `get_peak_value` has a shadow comparison. `RasDss` has no such method.
- Paired data compares the HMS dictionary (curve 0, units, axis types), so the labels for
  curve labels, the DSS7 time zone and DSS6 precision (PD1, PD2, PD4) do not arise.
- Windows are the same inclusive stamp filter on both backends, so no window translation
  is needed.
- `D3` is not used. It needs a separate Java windowed read, which the HMS Java path does
  not have, so that case stays `UNEXPECTED` (`native data, Java error`).
- A wheel without `grid_srs_monolith_parity` gives a skipped grid comparison instead of the
  `G-CRS` label. Grid labels G3 and G4 do not arise: HMS grid times come from the pathname,
  and the dictionary has no `number_missing`.

Shadow writes run on Java first. The native writer then repeats the write on a temporary
copy of the target file (or a new temporary file), and both files are read back with the
native reader and compared. The caller's file only ever receives the Java write. Files
larger than `HmsDss.shadow_copy_limit_mb` (256 MB; environment variable
`HMS_COMMANDER_DSS_SHADOW_COPY_LIMIT_MB`) are not copied, and the comparison is logged
as skipped. An engine without the writer API also gives a skipped comparison
(`native writers not available`); a native refusal is `expected` (W1).

## HEC library messages on the Java backend

The Java backend sends the HEC-DSS library's messages to a private temporary file instead
of the console, and logs the failure lines on the `hms_commander.dss.core` logger as
`HEC-DSS library reported: ...`. A DSS file cannot receive library messages through a
redirected stdout (this corrupted files under pytest's output capture). Set
`DssCore.hec_message_level` before the first Java call to change the level (default 1).
Level 0 also drops most failure messages.

Two console paths remain outside that file. HEC Monolith's own Java messages, such as
`Cannot open data base file`, still print. The Fortran `readf fail` line after a failed read
of a damaged DSS6 file also still uses stdout and can reach a stale handle; hms-commander
holds no other DSS file open during a read, and the damage is also reported in the log.

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
