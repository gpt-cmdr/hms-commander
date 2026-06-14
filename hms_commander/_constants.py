"""
HMS-specific constants and method definitions.

This module is the single source of truth for all magic numbers, enumerations, and
configuration constants used throughout hms-commander. It eliminates scattered
magic numbers and provides clear, documented values.

Categories:
    - Unit conversion factors (INCHES_TO_MM, CFS_TO_CMS, etc.)
    - Time constants (MINUTES_PER_HOUR, TIME_INTERVALS)
    - HMS method enumerations (LOSS_METHODS, TRANSFORM_METHODS, etc.)
    - Version support thresholds (MIN_HMS_3X_VERSION, etc.)
    - File formats (HMS_DATE_FORMAT, FILE_EXTENSIONS)
    - Acceptance criteria defaults (DEFAULT_PEAK_THRESHOLD_PCT, etc.)

Usage:
    from hms_commander._constants import (
        INCHES_TO_MM,
        LOSS_METHODS,
        TIME_INTERVALS
    )

    # Convert units
    precip_mm = precip_inches * INCHES_TO_MM

    # Validate method
    if method in LOSS_METHODS:
        pass  # Valid loss method
"""

from typing import Final, List, Dict, Tuple

# =========================================================================
# UNIT CONVERSION FACTORS
# =========================================================================
# Standard conversion factors for hydrologic units.
# Use these instead of magic numbers like 25.4 or 0.028316847.

# Length conversions
INCHES_TO_MM: Final[float] = 25.4
"""Convert inches to millimeters: mm = inches * 25.4"""

MM_TO_INCHES: Final[float] = 1.0 / 25.4
"""Convert millimeters to inches: inches = mm / 25.4"""

FEET_TO_METERS: Final[float] = 0.3048
"""Convert feet to meters: m = ft * 0.3048"""

METERS_TO_FEET: Final[float] = 1.0 / 0.3048
"""Convert meters to feet: ft = m / 0.3048"""

# Area conversions
SQMI_TO_SQKM: Final[float] = 2.58999
"""Convert square miles to square kilometers"""

SQKM_TO_SQMI: Final[float] = 1.0 / 2.58999
"""Convert square kilometers to square miles"""

ACRE_TO_SQKM: Final[float] = 0.00404686
"""Convert acres to square kilometers"""

SQKM_TO_ACRE: Final[float] = 1.0 / 0.00404686
"""Convert square kilometers to acres"""

# Flow conversions
CFS_TO_CMS: Final[float] = 0.028316847
"""Convert cubic feet per second to cubic meters per second"""

CMS_TO_CFS: Final[float] = 1.0 / 0.028316847
"""Convert cubic meters per second to cubic feet per second"""

# Volume conversions
ACFT_TO_M3: Final[float] = 1233.48
"""Convert acre-feet to cubic meters"""

M3_TO_ACFT: Final[float] = 1.0 / 1233.48
"""Convert cubic meters to acre-feet"""

CFS_HOURS_TO_ACFT: Final[float] = 0.0413
"""Convert CFS*hours to acre-feet: V(acft) = Q(cfs) * t(hr) * 0.0413"""

# =========================================================================
# TIME CONSTANTS
# =========================================================================
# Time-related constants for duration calculations and HMS intervals.

MINUTES_PER_HOUR: Final[int] = 60
"""Minutes in one hour"""

MINUTES_PER_DAY: Final[int] = 1440
"""Minutes in one day (60 * 24)"""

SECONDS_PER_HOUR: Final[int] = 3600
"""Seconds in one hour (60 * 60)"""

HOURS_PER_DAY: Final[int] = 24
"""Hours in one day"""

# Execution timeout (1 hour in seconds)
DEFAULT_EXECUTION_TIMEOUT: Final[int] = 3600
"""Default HMS execution timeout in seconds (1 hour)"""

# Time interval mapping (HMS format string -> minutes)
TIME_INTERVALS: Final[Dict[str, int]] = {
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
"""HMS time interval strings mapped to minutes. Used for control file parsing."""

# =========================================================================
# HMS VERSION SUPPORT
# =========================================================================
# Version constraints for HEC-HMS scripting compatibility.
# HMS 3.3+ and 4.4.1+ support Jython scripting; 4.0-4.3 have legacy issues.

MIN_HMS_3X_VERSION: Final[Tuple[int, int]] = (3, 3)
"""Minimum HMS 3.x version with Jython scripting support"""

MIN_HMS_4X_VERSION: Final[Tuple[int, int, int]] = (4, 4, 1)
"""Minimum HMS 4.x version with reliable Jython scripting"""

UNSUPPORTED_HMS_VERSIONS: Final[List[Tuple[int, int]]] = [
    (4, 0), (4, 1), (4, 2), (4, 3)
]
"""HMS versions with legacy classpath issues (not supported)"""

# =========================================================================
# JVM MEMORY CONFIGURATION
# =========================================================================
# Java Virtual Machine memory settings for HMS execution.
# 32-bit JVM has ~1.5GB limit; 64-bit can use much more.

DEFAULT_MAX_MEMORY: Final[str] = "4G"
"""Default maximum JVM heap size for 64-bit HMS"""

DEFAULT_INITIAL_MEMORY: Final[str] = "128M"
"""Default initial JVM heap size"""

MAX_MEMORY_32BIT: Final[str] = "1280M"
"""Maximum JVM heap size for 32-bit HMS (physical limit ~1.5GB)"""

MAX_MEMORY_32BIT_MB: Final[int] = 1280
"""Maximum 32-bit memory in megabytes for numeric comparisons"""

INITIAL_MEMORY_32BIT: Final[str] = "64M"
"""Initial JVM heap size for 32-bit HMS"""

# =========================================================================
# SCS CURVE NUMBER CALCULATION
# =========================================================================
# Constants for SCS Curve Number and Initial Abstraction calculations.
# S = (1000/CN) - 10, Ia = 0.2 * S (standard method)

IA_RATIO: Final[float] = 0.2
"""Initial abstraction ratio (Ia = 0.2 * S for standard method)"""

CN_FORMULA_BASE: Final[int] = 10
"""Base value in CN formula: S = (1000/CN) - 10"""

CN_FORMULA_NUMERATOR: Final[int] = 1000
"""Numerator in CN formula: S = (1000/CN) - 10"""

CN_MIN: Final[int] = 0
"""Minimum valid curve number"""

CN_MAX: Final[int] = 100
"""Maximum valid curve number"""

# =========================================================================
# FREQUENCY STORM DEFAULTS (HCFCD M3 COMPATIBILITY)
# =========================================================================
# Default values for TP-40/Hydro-35 frequency storms (HCFCD M3 models).

DEFAULT_PEAK_POSITION_PCT: Final[float] = 67.0
"""Default peak position (% of duration before peak). HCFCD standard is 67%."""

DEFAULT_STORM_DURATION_MIN: Final[int] = 1440
"""Default storm duration in minutes (24 hours)"""

DEFAULT_STORM_INTERVAL_MIN: Final[int] = 5
"""Default time interval in minutes for frequency storms"""

# =========================================================================
# ATLAS 14 CONFIGURATION
# =========================================================================
# Configuration for NOAA Atlas 14 precipitation frequency data.

ATLAS14_DEFAULT_INTERVAL_MIN: Final[int] = 30
"""Default time interval for Atlas 14 hyetographs (30 minutes)"""

ATLAS14_DEFAULT_DURATION_HR: Final[int] = 24
"""Default storm duration for Atlas 14 (24 hours)"""

ATLAS14_QUARTILES: Final[List[str]] = [
    "First Quartile",
    "Second Quartile",
    "Third Quartile",
    "Fourth Quartile",
    "All Cases"
]
"""Available Atlas 14 temporal distribution quartiles"""

# =========================================================================
# COMPARISON ACCEPTANCE CRITERIA (DEFAULT THRESHOLDS)
# =========================================================================
# Default thresholds for comparing HMS results between runs.
# Used for QAQC validation of baseline vs. updated models.

DEFAULT_PEAK_THRESHOLD_PCT: Final[float] = 1.0
"""Default peak flow comparison threshold (percent difference)"""

DEFAULT_VOLUME_THRESHOLD_PCT: Final[float] = 0.5
"""Default volume comparison threshold (percent difference)"""

DEFAULT_TIMING_THRESHOLD_HOURS: Final[int] = 1
"""Default time-to-peak comparison threshold (hours)"""

DEPTH_TOLERANCE_INCHES: Final[float] = 0.001
"""Tolerance for precipitation depth comparisons (inches)"""

# =========================================================================
# LOGGING CONFIGURATION
# =========================================================================
# Settings for rotating log file management.

LOG_MAX_BYTES: Final[int] = 10 * 1024 * 1024  # 10 MB
"""Maximum log file size in bytes before rotation"""

LOG_MAX_MB: Final[int] = 10
"""Maximum log file size in megabytes"""

LOG_BACKUP_COUNT: Final[int] = 5
"""Number of backup log files to retain"""

# =========================================================================
# HMS METHOD ENUMERATIONS
# =========================================================================
# Valid method names for basin model components. Use these for validation
# when setting loss, transform, baseflow, and routing methods.

LOSS_METHODS: Final[List[str]] = [
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
"""Valid loss/infiltration methods for subbasins in HEC-HMS"""

TRANSFORM_METHODS: Final[List[str]] = [
    "Clark Unit Hydrograph",
    "Kinematic Wave",
    "ModClark",
    "SCS Unit Hydrograph",
    "Snyder Unit Hydrograph",
    "User-Specified S-Graph",
    "User-Specified Unit Hydrograph",
    "None"
]
"""Valid transform/unit hydrograph methods for subbasins"""

BASEFLOW_METHODS: Final[List[str]] = [
    "Bounded Recession",
    "Constant Monthly",
    "Linear Reservoir",
    "Nonlinear Boussinesq",
    "Recession",
    "None"
]
"""Valid baseflow methods for subbasins"""

ROUTING_METHODS: Final[List[str]] = [
    "Kinematic Wave",
    "Lag",
    "Modified Puls",
    "Muskingum",
    "Muskingum-Cunge",
    "Straddle Stagger",
    "None"
]
"""Valid channel routing methods for reaches"""

# =========================================================================
# PRECIPITATION METHODS
# =========================================================================
# Valid precipitation methods for meteorologic models.

PRECIP_METHODS: Final[List[str]] = [
    "Frequency Based Hypothetical",
    "Frequency Storm",
    "Gage Weights",
    "Gridded Precipitation",
    "Inverse Distance",
    "SCS Storm",
    "Specified Hyetograph",
    "Standard Project Storm",
    "None"
]
"""Valid precipitation methods for meteorologic models"""

# =========================================================================
# EVAPOTRANSPIRATION METHODS
# =========================================================================
# Valid evapotranspiration methods for meteorologic models.

ET_METHODS: Final[List[str]] = [
    "Gridded Priestley Taylor",
    "Hamon",
    "Monthly Average",
    "Priestley Taylor",
    "Specified Evapotranspiration",
    "None"
]
"""Valid evapotranspiration methods for meteorologic models"""

# =========================================================================
# SNOWMELT METHODS
# =========================================================================
# Valid snowmelt methods for meteorologic models.

SNOWMELT_METHODS: Final[List[str]] = [
    "Gridded Temperature Index",
    "Temperature Index",
    "None"
]
"""Valid snowmelt methods for meteorologic models"""

# =========================================================================
# GAGE DATA TYPES AND UNITS
# =========================================================================
# Gage types and their associated units for time-series data.

GAGE_DATA_TYPES: Final[List[str]] = [
    "Precipitation",
    "Discharge",
    "Stage",
    "Temperature",
    "Solar Radiation",
    "Wind Speed",
    "Relative Humidity",
    "Crop Coefficient"
]
"""Valid gage data types for .gage files"""

# Gage units by type
PRECIP_UNITS: Final[List[str]] = ["IN", "MM"]
"""Valid precipitation units (inches or millimeters)"""

DISCHARGE_UNITS: Final[List[str]] = ["CFS", "CMS"]
"""Valid discharge units (cubic feet or meters per second)"""

STAGE_UNITS: Final[List[str]] = ["FT", "M"]
"""Valid stage units (feet or meters)"""

TEMP_UNITS: Final[List[str]] = ["DEG F", "DEG C"]
"""Valid temperature units (Fahrenheit or Celsius)"""

# =========================================================================
# FILE TYPES AND EXTENSIONS
# =========================================================================
# HMS file extensions for project file discovery and validation.

FILE_EXTENSIONS: Final[Dict[str, str]] = {
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
"""HMS file extension patterns by component type"""

DSS_EXTENSION: Final[str] = ".dss"
"""DSS file extension"""

# =========================================================================
# DATE/TIME FORMATS
# =========================================================================
# HMS date and time string formats for control file parsing.

HMS_DATE_FORMAT: Final[str] = "%d %B %Y"
"""HMS date format string, e.g., '1 January 2020' (full month name with spaces)"""

HMS_TIME_FORMAT: Final[str] = "%H:%M"
"""HMS time format string, e.g., '00:00' or '14:30'"""

# =========================================================================
# FILE ENCODING
# =========================================================================
# File encoding for reading/writing HMS text files.

PRIMARY_ENCODING: Final[str] = 'utf-8'
"""Primary file encoding for HMS files"""

FALLBACK_ENCODING: Final[str] = 'latin-1'
"""Fallback encoding for older HMS files with extended characters"""

SUPPORTED_ENCODINGS: Final[List[str]] = ['utf-8', 'latin-1', 'cp1252']
"""Ordered list of encodings to try when reading HMS files"""

# =========================================================================
# DSS RESULT PATTERNS
# =========================================================================
# Regular expressions for matching HMS result types in DSS pathnames.
# The C-part of DSS pathnames indicates the data type (FLOW, PRECIP, etc.).

# =========================================================================
# BATCH PARAMETER MAPPING DICTS
# =========================================================================
# Maps HMS file keys to snake_case DataFrame columns for batch read/write.
# Each dict maps HMS_file_key -> snake_case_column_name.
# Reverse maps are auto-generated for writing back to HMS files.

LOSS_PARAM_MAP: Final[Dict[str, str]] = {
    'LossRate': 'loss_method',
    'Percent Impervious Area': 'percent_impervious',
    'Initial Loss': 'initial_loss',
    'Moisture Deficit': 'moisture_deficit',
    'Wetting Front Suction': 'wetting_front_suction',
    'Hydraulic Conductivity': 'hydraulic_conductivity',
    'Initial Variable': 'initial_variable',
    # Deficit and Constant
    'Initial Deficit': 'initial_deficit',
    'Maximum Deficit': 'maximum_deficit',
    'Constant Rate': 'constant_rate',
    'Percolation Rate': 'percolation_rate',
    # SCS Curve Number
    'Curve Number': 'curve_number',
    'Initial Abstraction': 'initial_abstraction',
    # Initial and Constant
    'Initial Rate': 'initial_rate',
    # Smith Parlange
    'Saturated Conductivity': 'saturated_conductivity',
    'Wetting Front Capillary': 'wetting_front_capillary',
    # Note: 'Initial Variable' also appears in ROUTING_PARAM_MAP (Muskingum-Cunge).
    # In loss context: Green & Ampt initial condition type.
    # In routing context: Muskingum-Cunge initial condition type.
    # No collision because they operate on different element types (Subbasin vs Reach).
    # Soil Moisture Accounting
    'Soil': 'soil',
    'Groundwater 1': 'groundwater_1',
    'Groundwater 2': 'groundwater_2',
    'Max Infiltration': 'max_infiltration',
}
"""Maps HMS loss parameter file keys to snake_case column names."""

LOSS_PARAM_REVERSE_MAP: Final[Dict[str, str]] = {v: k for k, v in LOSS_PARAM_MAP.items()}
"""Reverse map: snake_case column names to HMS file keys."""

TRANSFORM_PARAM_MAP: Final[Dict[str, str]] = {
    'Transform': 'transform_method',
    # Clark Unit Hydrograph
    'Time of Concentration': 'time_of_concentration',
    'Storage Coefficient': 'storage_coefficient',
    'Clark Method': 'clark_method',
    # SCS Unit Hydrograph
    'Lag': 'lag',
    'Graph Type': 'graph_type',
    # Snyder
    'Snyder Tp': 'snyder_tp',
    'Snyder Cp': 'snyder_cp',
    # Kinematic Wave
    'Number of Subreaches': 'number_of_subreaches',
}
"""Maps HMS transform parameter file keys to snake_case column names."""

TRANSFORM_PARAM_REVERSE_MAP: Final[Dict[str, str]] = {v: k for k, v in TRANSFORM_PARAM_MAP.items()}
"""Reverse map: snake_case column names to HMS file keys."""

BASEFLOW_PARAM_MAP: Final[Dict[str, str]] = {
    'Baseflow': 'baseflow_method',
    # Recession
    'Recession Factor': 'recession_factor',
    'Initial Discharge': 'initial_discharge',
    'Threshold Type': 'threshold_type',
    'Threshold Flow': 'threshold_flow',
    'Threshold Ratio': 'threshold_ratio',
    # Linear Reservoir
    'GW 1 Initial': 'gw1_initial',
    'GW 1 Coefficient': 'gw1_coefficient',
    'GW 1 Reservoirs': 'gw1_reservoirs',
    'GW 2 Initial': 'gw2_initial',
    'GW 2 Coefficient': 'gw2_coefficient',
    'GW 2 Reservoirs': 'gw2_reservoirs',
    # Bounded Recession
    'Max Baseflow': 'max_baseflow',
    # Constant Monthly
    'January Baseflow': 'january_baseflow',
    'February Baseflow': 'february_baseflow',
    'March Baseflow': 'march_baseflow',
    'April Baseflow': 'april_baseflow',
    'May Baseflow': 'may_baseflow',
    'June Baseflow': 'june_baseflow',
    'July Baseflow': 'july_baseflow',
    'August Baseflow': 'august_baseflow',
    'September Baseflow': 'september_baseflow',
    'October Baseflow': 'october_baseflow',
    'November Baseflow': 'november_baseflow',
    'December Baseflow': 'december_baseflow',
}
"""Maps HMS baseflow parameter file keys to snake_case column names."""

BASEFLOW_PARAM_REVERSE_MAP: Final[Dict[str, str]] = {v: k for k, v in BASEFLOW_PARAM_MAP.items()}
"""Reverse map: snake_case column names to HMS file keys."""

ROUTING_PARAM_MAP: Final[Dict[str, str]] = {
    'Route': 'route_method',
    # Muskingum
    'Muskingum K': 'muskingum_k',
    'Muskingum x': 'muskingum_x',
    'Muskingum Steps': 'muskingum_steps',
    # Lag
    'Lag': 'lag',
    # Modified Puls
    'Number of Reaches': 'number_of_reaches',
    'Initial Outflow Equals Inflow': 'initial_outflow_equals_inflow',
    'Storage Outflow Table Name': 'storage_outflow_table_name',
    # Muskingum-Cunge
    'Channel': 'channel',
    'Length': 'length',
    'Energy Slope': 'energy_slope',
    'Mannings n': 'mannings_n',
    'Left Mannings n': 'left_mannings_n',
    'Right Mannings n': 'right_mannings_n',
    'Cross Section Name': 'cross_section_name',
    # Note: 'Initial Variable' also appears in LOSS_PARAM_MAP (Green & Ampt).
    # No collision because they operate on different element types (Subbasin vs Reach).
    'Initial Variable': 'initial_variable',
    'Space-Time Method': 'space_time_method',
    'Index Parameter Type': 'index_parameter_type',
    'Index Celerity': 'index_celerity',
    'Index Flow': 'index_flow',
    'Maximum Depth Iterations': 'maximum_depth_iterations',
    'Maximum Route Step Iterations': 'maximum_route_step_iterations',
    # Channel Loss (shared)
    'Channel Loss': 'channel_loss',
}
"""Maps HMS routing parameter file keys to snake_case column names."""

ROUTING_PARAM_REVERSE_MAP: Final[Dict[str, str]] = {v: k for k, v in ROUTING_PARAM_MAP.items()}
"""Reverse map: snake_case column names to HMS file keys."""

HMS_RESULT_PATTERNS: Final[Dict[str, str]] = {
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
"""Regex patterns for matching HMS result types in DSS C-part"""
