# Release Notes

Version history and current capability notes for HMS Commander.

## Version 0.3.0 (Current)

**Status:** Alpha package with active engineering oversight required

The package metadata in `pyproject.toml` identifies the current version as `0.3.0`.

### Public Package Surface

- Project initialization and DataFrame-backed project management (`HmsPrj`, `init_hms_project`)
- File operations for basin, meteorologic, control, gage, and run files (`HmsBasin`, `HmsMet`, `HmsControl`, `HmsGage`, `HmsRun`)
- Simulation execution, Jython script generation, and compute-output parsing (`HmsCmdr`, `HmsJython`, `HmsOutput`)
- DSS time-series, paired-data, catalog, and grid operations through ras-commander/HEC Monolith infrastructure (`DssCore`, `HmsDss`, `HmsDssGrid`)
- Results extraction and analysis (`HmsResults`)
- Geospatial, HUC, SQLite, AORC, grid, TauDEM, and watershed-verification helpers (`HmsGeo`, `HmsSqlite`, `HmsHuc`, `HmsAorc`, `HmsGrid`, `HmsTerrain`, `HmsTauDEM`, `HmsWatershedVerification`)
- Example and HCFCD M3 model project helpers (`HmsExamples`, `HmsM3Model`)
- Storm generation helpers (`Atlas14Config`, `Atlas14Storm`, `FrequencyStorm`, `ScsTypeStorm`)
- Clone-first, non-destructive workflows for side-by-side HMS GUI review

### Notable Current Limitations

- The Spring Creek TauDEM-to-HMS path is import-valid and compute-valid, but still needs a readiness gate, TauDEM parameter comparison, and human QAQC bundle before production promotion.
- `HmsAorc` and `HmsGrid` provide download, DSS grid conversion, grid definition, and mapping helpers, but gridded-precipitation met-model wiring is not yet exposed as a complete `HmsMet` public helper.
- `HmsAorc.check_availability()` is intentionally not implemented.
- CI is not yet represented by `.github/workflows/`.

### Documentation Notes

- API documentation is generated from package docstrings under `docs/api/`.
- `AGENTS.md` is the shared coding-agent contract. `CLAUDE.md`, `.claude/`, `.agents/`, and `.codex/` are harness adapters or generated bridges, not user API references.
- Notebook source lives in `examples/`; only selected notebooks are rendered under `docs/notebooks/`.

---

## Version 0.2.0

**Theme:** Precipitation DataFrame API standardization

### Breaking Change

`Atlas14Storm.generate_hyetograph()`, `FrequencyStorm.generate_hyetograph()`, and `ScsTypeStorm.generate_hyetograph()` return a `pandas.DataFrame` with:

```python
["hour", "incremental_depth", "cumulative_depth"]
```

Earlier v0.1-era code that treated the return value as a NumPy array should use DataFrame columns instead:

```python
hyeto = Atlas14Storm.generate_hyetograph(total_depth_inches=17.0, state="tx", region=3)
total_depth = hyeto["cumulative_depth"].iloc[-1]
peak_increment = hyeto["incremental_depth"].max()
```

---

## Version 0.1.x

Initial package architecture for HMS project management, file parsing, HMS execution, DSS/results integration, static class patterns, and example-project workflows.

---

## Planned Work

- Production-readiness gates for generated HMS scaffolds
- TauDEM parameter sensitivity and comparison support
- Human-review QAQC bundles for generated HMS projects
- CI for the non-HMS-dependent pytest subset
- Complete gridded-precipitation met-model configuration helpers
- Additional documentation publishing decisions for the full notebook catalog

---

## Support

Report bugs and request features on GitHub:
https://github.com/gpt-cmdr/hms-commander/issues

Include the HMS Commander version, HEC-HMS version, Python version, operating system, and a minimal reproducible example.
