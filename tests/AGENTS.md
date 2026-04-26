# Test Instructions

This directory contains pytest tests and HMS fixture projects.

## Test Rules

- Prefer tests against real HMS file structures and fixtures over mocks.
- Keep tests deterministic and avoid writing large generated outputs into tracked fixture folders.
- Use existing pytest markers for optional capabilities:
  - `requires_hms`
  - `local_hms`
  - `requires_java`
  - `requires_gis`
  - `requires_network`
  - `slow`
- Put temporary files under pytest temporary directories or ignored working/output paths.

## Commands

- Targeted tests: `python -m pytest tests/test_name.py`
- Full test suite: `python -m pytest`
