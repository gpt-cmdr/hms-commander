"""
HMS-specific constants and method definitions.

Centralized source of truth for:
- Loss methods (Deficit and Constant, SCS Curve Number, etc.)
- Transform methods (Clark, SCS Unit Hydrograph, etc.)
- Precipitation methods (Gage Weights, Gridded, etc.)
- Unit conversion factors
- Acceptance criteria defaults
- HMS version support thresholds

Extracted from HmsBasin, HmsMet, HmsControl, HmsGage, HmsUtils to eliminate
duplication and provide single source of truth.
"""

# =========================================================================
# UNIT CONVERSION FACTORS
# =========================================================================

# Length conversions
INCHES_TO_MM = 25.4
MM_TO_INCHES = 1 / 25.4
FEET_TO_METERS = 0.3048
METERS_TO_FEET = 1 / 0.3048

# Area conversions
SQMI_TO_SQKM = 2.58999
SQKM_TO_SQMI = 1 / 2.58999
ACRE_TO_SQKM = 0.00404686
SQKM_TO_ACRE = 1 / 0.00404686

# Flow conversions
CFS_TO_CMS = 0.028316847
CMS_TO_CFS = 1 / 0.028316847

# Volume conversions
ACFT_TO_M3 = 1233.48
M3_TO_ACFT = 1 / 1233.48
CFS_HOURS_TO_ACFT = 0.0413

# =========================================================================
# TIME CONSTANTS
# =========================================================================

MINUTES_PER_HOUR = 60
MINUTES_PER_DAY = 1440
SECONDS_PER_HOUR = 3600

# Execution timeout (1 hour in seconds)
DEFAULT_EXECUTION_TIMEOUT = 3600

# Time interval mapping (HMS format string → minutes)
TIME_INTERVALS = {
    '1 Minute': 1,
    '2 Minutes': 2,
    '3 Minutes': 3,
    '4 Minutes': 4,
    '5 Minutes': 5,
    '6 Minutes': 6,
    '10 Minutes': 10,
    '12 Minutes': 12,
    '15 Minutes': 15,
    '20 Minutes': 20,
    '30 Minutes': 30,
    '1 Hour': 60,
    '2 Hours': 120,
    '3 Hours': 180,
    '4 Hours': 240,
    '6 Hours': 360,
    '8 Hours': 480,
    '12 Hours': 720,
    '1 Day': 1440,
}

# =========================================================================
# HMS VERSION SUPPORT
# =========================================================================

MIN_HMS_3X_VERSION = (3, 3)
MIN_HMS_4X_VERSION = (4, 4, 1)
UNSUPPORTED_HMS_VERSIONS = [(4, 0), (4, 1), (4, 2), (4, 3)]

# =========================================================================
# JVM MEMORY CONFIGURATION
# =========================================================================

DEFAULT_MAX_MEMORY = "4G"
DEFAULT_INITIAL_MEMORY = "128M"
MAX_MEMORY_32BIT = "1280M"
MAX_MEMORY_32BIT_MB = 1280
INITIAL_MEMORY_32BIT = "64M"

# =========================================================================
# SCS CURVE NUMBER CALCULATION
# =========================================================================

IA_RATIO = 0.2
CN_FORMULA_BASE = 10
CN_FORMULA_NUMERATOR = 1000
CN_MIN = 0
CN_MAX = 100

# =========================================================================
# COMPARISON ACCEPTANCE CRITERIA (DEFAULT THRESHOLDS)
# =========================================================================

DEFAULT_PEAK_THRESHOLD_PCT = 1.0
DEFAULT_VOLUME_THRESHOLD_PCT = 0.5
DEFAULT_TIMING_THRESHOLD_HOURS = 1

# =========================================================================
# LOGGING CONFIGURATION
# =========================================================================

LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_MAX_MB = 10
LOG_BACKUP_COUNT = 5

# =========================================================================
# HMS METHOD ENUMERATIONS (from HmsBasin)
# =========================================================================

LOSS_METHODS = [
    "Deficit and Constant",
    "Green and Ampt",
    "Gridded Deficit Constant",
    "Gridded Green Ampt",
    "Gridded SCS Curve Number",
    "Gridded Soil Moisture Accounting",
    "Initial and Constant",
    "SCS Curve Number",
    "Smith Parlange",
    "Soil Moisture Accounting",
    "None"
]

TRANSFORM_METHODS = [
    "Clark Unit Hydrograph",
    "Kinematic Wave",
    "ModClark",
    "SCS Unit Hydrograph",
    "Snyder Unit Hydrograph",
    "User-Specified S-Graph",
    "User-Specified Unit Hydrograph",
    "None"
]

BASEFLOW_METHODS = [
    "Bounded Recession",
    "Constant Monthly",
    "Linear Reservoir",
    "Nonlinear Boussinesq",
    "Recession",
    "None"
]

ROUTING_METHODS = [
    "Kinematic Wave",
    "Lag",
    "Modified Puls",
    "Muskingum",
    "Muskingum-Cunge",
    "Straddle Stagger",
    "None"
]

# =========================================================================
# PRECIPITATION METHODS (from HmsMet)
# =========================================================================

PRECIP_METHODS = [
    "Frequency Storm",
    "Gage Weights",
    "Gridded Precipitation",
    "Inverse Distance",
    "SCS Storm",
    "Specified Hyetograph",
    "Standard Project Storm",
    "None"
]

# =========================================================================
# EVAPOTRANSPIRATION METHODS (from HmsMet)
# =========================================================================

ET_METHODS = [
    "Gridded Priestley Taylor",
    "Hamon",
    "Monthly Average",
    "Priestley Taylor",
    "Specified Evapotranspiration",
    "None"
]

# =========================================================================
# SNOWMELT METHODS (from HmsMet)
# =========================================================================

SNOWMELT_METHODS = [
    "Gridded Temperature Index",
    "Temperature Index",
    "None"
]

# =========================================================================
# GAGE DATA TYPES AND UNITS (from HmsGage)
# =========================================================================

GAGE_DATA_TYPES = [
    "Precipitation",
    "Discharge",
    "Stage",
    "Temperature",
    "Solar Radiation",
    "Wind Speed",
    "Relative Humidity",
    "Crop Coefficient"
]

# Gage units by type
PRECIP_UNITS = ["IN", "MM"]
DISCHARGE_UNITS = ["CFS", "CMS"]
STAGE_UNITS = ["FT", "M"]
TEMP_UNITS = ["DEG F", "DEG C"]

# =========================================================================
# FILE TYPES AND EXTENSIONS
# =========================================================================

FILE_EXTENSIONS = {
    'hms': '*.hms',
    'basin': '*.basin',
    'met': '*.met',
    'control': '*.control',
    'gage': '*.gage',
    'run': '*.run',
    'dss': '*.dss',
    'log': '*.log',
    'geo': '*.geo',
    'map': '*.map',
    'grid': '*.grid',
    'sqlite': '*.sqlite',
}

# =========================================================================
# DATE/TIME FORMATS (from HmsControl)
# =========================================================================

HMS_DATE_FORMAT = "%d%b%Y"  # e.g., "01Jan2020"
HMS_TIME_FORMAT = "%H:%M"   # e.g., "00:00"

# =========================================================================
# FILE ENCODING
# =========================================================================

PRIMARY_ENCODING = 'utf-8'
FALLBACK_ENCODING = 'latin-1'

# =========================================================================
# DSS RESULT PATTERNS (from HmsDss)
# =========================================================================

HMS_RESULT_PATTERNS = {
    'flow': r'/FLOW[^/]*/|/FLOW/',
    'flow-total': r'/FLOW/',
    'flow-observed': r'/FLOW-OBSERVED/',
    'flow-direct': r'/FLOW-DIRECT/',
    'flow-base': r'/FLOW-BASE/',
    'flow-combine': r'/FLOW-COMBINE/',
    'precipitation': r'/PRECIP[^/]*/|/PRECIP/',
    'precip-inc': r'/PRECIP-INC/',
    'precip-cum': r'/PRECIP-CUM/',
    'precip-excess': r'/PRECIP-EXCESS/',
    'precip-loss': r'/PRECIP-LOSS/',
    'stage': r'/STAGE/',
    'storage': r'/STORAGE[^/]*/|/STORAGE/',
    'storage-gw': r'/STORAGE-GW/',
    'storage-soil': r'/STORAGE-SOIL/',
    'elevation': r'/ELEV/',
    'outflow': r'/OUTFLOW[^/]*/|/OUTFLOW/',
    'inflow': r'/INFLOW[^/]*/|/INFLOW/',
    'excess': r'/EXCESS[^/]*/|/EXCESS/',
    'baseflow': r'/BASEFLOW/',
    'infiltration': r'/INFILTRATION/',
    'et': r'/ET[^/]*/|/ET/',
}
