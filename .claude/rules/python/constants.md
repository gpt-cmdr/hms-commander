---
paths: hms_commander/**/*.py
---

# Centralized Constants

## Primary Source

**Authoritative**: `hms_commander/_constants.py`

Complete definitions for all magic numbers and enumerations.

## Why _constants.py Exists

Eliminates ~45+ magic numbers scattered across modules.

**Before**: `25.4` appeared 8 times in different files
**After**: `from hms_commander._constants import INCHES_TO_MM`

## Categories

### Unit Conversions
Import: `INCHES_TO_MM`, `FEET_TO_METERS`, `CFS_TO_CMS`, `ACFT_TO_M3`

### Time Constants
Import: `MINUTES_PER_HOUR`, `MINUTES_PER_DAY`, `TIME_INTERVALS`

### HMS Method Enumerations
Import: `LOSS_METHODS`, `TRANSFORM_METHODS`, `ROUTING_METHODS`, `PRECIP_METHODS`

### Version Support
Import: `MIN_HMS_3X_VERSION`, `MIN_HMS_4X_VERSION`, `UNSUPPORTED_HMS_VERSIONS`

### File Formats
Import: `HMS_DATE_FORMAT`, `HMS_TIME_FORMAT`, `FILE_EXTENSIONS`

### Acceptance Criteria
Import: `DEFAULT_PEAK_THRESHOLD_PCT`, `DEFAULT_VOLUME_THRESHOLD_PCT`

## Usage Pattern

```python
from hms_commander._constants import (
    INCHES_TO_MM,
    LOSS_METHODS,
    TIME_INTERVALS
)

# Convert units
precip_mm = precip_inches * INCHES_TO_MM

# Validate method
if method in LOSS_METHODS:
    # Valid loss method
    pass

# Parse time interval
interval_minutes = TIME_INTERVALS.get("15 Minutes", 15)
```

## Complete Reference

**Read**: `hms_commander/_constants.py` for all available constants and their values

## Related

- **HmsUtils**: Uses constants for unit conversion
- **File parsing**: Uses FILE_EXTENSIONS, PRIMARY_ENCODING
