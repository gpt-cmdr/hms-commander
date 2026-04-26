# Examples Instructions

This directory contains example notebooks, helper scripts, and demonstration workflows.

## Notebook Rules

- Use `HmsExamples.extract_project()` or checked-in fixtures instead of absolute local paths.
- Keep notebooks reproducible on a clean machine with the documented optional dependencies.
- Do not commit generated DSS files, HMS logs, extracted HMS projects, cache directories, or large output artifacts.
- Preserve the learning-track structure in `mkdocs.yml` when adding or renaming notebooks.
- Notebook cells should demonstrate public APIs rather than duplicating library logic.

## Validation

- For notebook changes, run the affected notebook when practical and document any HMS installation requirement.
- For docs changes that include notebooks, run `python -m mkdocs build --strict -q`.
- Put temporary outputs in ignored working folders such as `examples/working/` or repo-level `working/`.
