---
paths: hms_commander/**/*.py
---

# HEC-HMS File Formats

## Overview

All HMS files are **plain text, ASCII format** with a consistent `Block: Name / Parameter: Value / End:` structure. This makes them parseable with regex/string operations — no binary formats.

**Authoritative Reference**: `tests/projects/2014.08_HMS/File Parsing Guide/`

## File Extensions and Classes

| Extension | Class | Purpose |
|-----------|-------|---------|
| `.hms` | `HmsPrj` | Project file — index of all components |
| `.basin` | `HmsBasin` | Basin model — subbasins, junctions, reaches |
| `.met` | `HmsMet` | Meteorologic model — precipitation |
| `.control` | `HmsControl` | Control specification — time window |
| `.gage` | `HmsGage` | Gage data — observed flow/precipitation |
| `.run` | `HmsRun` | Run configuration — links basin+met+control |
| `.dss` | `HmsDss` | Results/input data (binary HEC-DSS format) |
| `.log` | — | Run log — execution messages and errors |

## .hms Project File Structure

The index file that references all other components:

```
Project: Clear Creek Watershed
     Last Modified Date: 26 November 2024
     Last Modified Time: 12:00:00
     Unit System: English
     Flow Ratios: No

Basin File: Baseline.basin
Basin File: Updated_Basin.basin

Meteorologic Model File: Storms.met

Control Specifications File: TimeWindows.control

Run: Run1
     Last Modified Date: 26 November 2024
     Last Modified Time: 12:00:00
     Basin Model: Baseline
     Meteorologic Model: Storm_100yr
     Control Specifications: Feb2014_24hr
     DSS File: Run1.dss
     Start DSS Pathname: /Clear Creek/FLOW/01JAN2000/1Hour/Baseline/
End:
```

**Critical**: The `Project:` line value is what `OpenProject()` uses — NOT the folder name. See `.claude/rules/hec-hms/critical-bugs-workarounds.md` Bug 3.

## .basin File Structure

```
Basin Model: BasinName
     Last Modified Date: ...
     Unit System: English
     Flow Ratio: No

Subbasin: SubbasinName
     Area: 123.45
     Downstream: JunctionName
     Loss: Deficit and Constant
     Percent Impervious: 10.0
     Initial Deficit: 25.4
     Maximum Deficit: 76.2
     Constant Rate: 2.54
     Transform: SCS Unit Hydrograph
     Lag: 60.0
     Baseflow: None
End:

Junction: JunctionName
     Downstream: OutletName
End:

Reach: ReachName
     Route: Muskingum Cunge
     Downstream: DownstreamElement
     Index Parameter Type: Index Celerity
     Index Celerity: 1.5
End:
```

**Complete reference**: `tests/projects/2014.08_HMS/File Parsing Guide/02_Basin_File.md`

## .met File Structure

```
Meteorologic Model: StormName
     Last Modified Date: ...
     Unit System: English
     Rainfall Method: Frequency Storm
     Basin Average Precipitation: Yes
     Subbasin: SubbasinName
          Depth: 4.5
          Duration: 24.0
     End Subbasin:
End:
```

**Complete reference**: `tests/projects/2014.08_HMS/File Parsing Guide/03_Meteorologic_File.md`

## .control File Structure

```
Control: ControlName
     Start Date: 26 Feb 2014
     Start Time: 00:00
     End Date: 27 Feb 2014
     End Time: 00:00
     Time Interval: 15
End:
```

**Date format**: `DD Mmm YYYY` (e.g., `26 Feb 2014`) — NOT ISO format.

## General Parsing Pattern

```python
# Block structure applies to all HMS text files:
Block: ElementName
     Parameter1: Value1
     Parameter2: Value2
     NestedBlock: NestedName
          NestedParam: Value
     End NestedBlock:
End:
```

**Use `HmsFileParser` for all parsing** — see `.claude/rules/python/file-parsing.md`.

## DSS File Format (Binary)

`.dss` files are HEC-DSS binary format — NOT plain text. Use:
- `hms_commander/HmsDss.py` for read/write operations
- `pydsstools` or `pyhecdss` for low-level access

**DSS Pathnames** follow format: `/Part A/Part B/Part C/Part D/Part E/Part F/`

Example: `/Clear Creek/FLOW/01JAN2000/1Hour/Baseline/Run1/`

## Related

- **Met files**: `.claude/rules/hec-hms/met-files.md`
- **Control files**: `.claude/rules/hec-hms/control-files.md`
- **Basin files**: `.claude/rules/hec-hms/basin-files.md`
- **File parsing utilities**: `.claude/rules/python/file-parsing.md`
- **Critical bugs**: `.claude/rules/hec-hms/critical-bugs-workarounds.md`
