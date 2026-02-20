---
paths: hms_commander/**/*.py
---

# Meteorologic Model Operations

## Primary Sources

**Code**: `hms_commander/HmsMet.py`
- `HmsMet.get_met_models()` — list all met models in .met file
- `HmsMet.get_precipitation()` — read precipitation configuration
- `HmsMet.set_precipitation()` — write precipitation parameters
- `HmsMet.clone_met()` — non-destructive copy

**File Format**: `tests/projects/2014.08_HMS/File Parsing Guide/03_Meteorologic_File.md`

## Critical: HMS Rewrites .met Files on Open

**WARNING**: When HMS opens a project, it rewrites ALL `.met` files. This can corrupt precipitation depth values.

**Specific Bug**: `Depth: 0.0` values are blanked by HMS 4.x (treated as unset/null).

**Mandatory Workaround** — See `.claude/rules/hec-hms/critical-bugs-workarounds.md` Bug 2:
```python
# Replace 0.0 with 0.0001 BEFORE calling OpenProject()
content = met_file.read_text()
content = content.replace('Depth: 0.0\n', 'Depth: 0.0001\n')
met_file.write_text(content)
# Then open project
```

## .met File Structure

```
Meteorologic Model: StormName
     Last Modified Date: 26 November 2024
     Last Modified Time: 12:00:00
     Unit System: English
     Rainfall Method: Frequency Storm
     Basin Average Precipitation: Yes
     Subbasin: SubbasinName
          Depth: 4.5
          Duration: 24.0
     End Subbasin:
End:
```

## Common Patterns

### Read Met Models
```python
from hms_commander import HmsMet

models = HmsMet.get_met_models("project.met")
# Returns: ['Storm_1yr', 'Storm_10yr', 'Storm_100yr', ...]
```

### Get Precipitation for Subbasin
```python
precip = HmsMet.get_precipitation("project.met", "Storm_100yr", "SubbasinA")
# Returns: {'Depth': 4.5, 'Duration': 24.0, ...}
```

### Clone Met Model (Non-Destructive)
```python
from hms_commander import HmsMet, hms

HmsMet.clone_met("Baseline_Storm", "Updated_Storm", hms_object=hms)
# Creates new .met entry, updates .hms project file
```

## Supported Rainfall Methods

| Method | Key | Notes |
|--------|-----|-------|
| Frequency Storm | `Frequency Storm` | TP-40/Hydro-35, Atlas 14 |
| SCS Hypothetical | `SCS Hypothetical Storm` | |
| User-Specified Hyetograph | `User-Specified Hyetograph` | Time series |
| Gridded Precipitation | `Gridded Precipitation` | AORC, radar |
| Specified Hyetograph | `Specified Hyetograph` | |

## AORC Integration

For AORC (Analysis of Record for Calibration) precipitation:
- See `.claude/rules/hec-hms/aorc-integration.md`
- Production agent: `.claude/agents/hms_atlas14/`

## Related

- **Critical bugs**: `.claude/rules/hec-hms/critical-bugs-workarounds.md` (Bug 2)
- **Basin files**: `.claude/rules/hec-hms/basin-files.md`
- **Atlas 14**: `.claude/rules/hec-hms/atlas14-storms.md`
- **File formats**: `.claude/rules/hec-hms/file-formats.md`
