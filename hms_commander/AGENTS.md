# hms_commander Package Instructions

This directory contains the public Python package for HMS automation.

## Package Rules

- Follow the static-class namespace pattern used by existing `Hms*` classes.
- Prefer existing helpers such as `HmsFileParser`, `LoggingConfig`, and shared constants before adding new parsing or logging patterns.
- Use `pathlib.Path` internally and accept both `str` and path-like inputs where existing APIs do.
- Preserve backward-compatible public method names unless the task explicitly authorizes a breaking change.
- Add Google-style docstrings for new public APIs and keep examples short and runnable.
- Use `@log_call` consistently where surrounding public APIs use it.

## HMS File Handling

- Treat `.hms`, `.basin`, `.met`, `.control`, `.gage`, and `.run` files as structured text sections, not free-form blobs.
- Preserve HMS formatting and section ordering unless the feature requires a controlled change.
- Avoid destructive edits to original model files; prefer clone workflows for scenario changes.
- Validate cross-file references when changing run, basin, met, control, or DSS output settings.

## Tests

- Add targeted tests under `tests/` for parser, file-edit, storm-generation, or results behavior.
- Prefer real sample project structures and fixtures over mocks.
- Isolate tests that require installed HEC-HMS, Java, GIS, DSS, or network access with the existing pytest markers.
