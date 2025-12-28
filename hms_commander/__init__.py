"""
hms-commander: HEC-HMS Automation Library

A Python library for automating HEC-HMS (Hydrologic Engineering Center's
Hydrologic Modeling System) operations, following the architectural patterns
established by ras-commander.

Core Features:
- Project management with DataFrames for all components
- Basin model parsing and modification
- Meteorologic model operations
- Control specification management
- Time-series gage operations
- Simulation execution via Jython scripts
- DSS file integration (via ras-commander)
- Results extraction and analysis
- GIS data extraction

Usage:
    from hms_commander import init_hms_project, hms
    from hms_commander import HmsBasin, HmsMet, HmsControl, HmsGage, HmsRun
    from hms_commander import HmsCmdr, HmsResults, HmsDss
    from hms_commander import HmsGeo, HmsUtils

    # Initialize project (uses global hms object)
    init_hms_project(
        r"C:/HMS_Projects/MyProject",
        hms_exe_path=r"C:/HEC/HEC-HMS/4.9/hec-hms.cmd"
    )

    # Access project data
    print(hms.basin_df)
    print(hms.run_df)

    # Configure DSS outputs for RAS (HMS-to-RAS workflow)
    config = HmsRun.get_dss_config("Current", hms_object=hms)
    HmsRun.set_output_dss("Current", "HMS_Output.dss", hms_object=hms)

    # Run simulations
    HmsCmdr.compute_run("Run 1")

    # Extract results
    peaks = HmsResults.get_peak_flows("results.dss")
"""

__version__ = "0.1.0"
__author__ = "hms-commander contributors"

# Core project management
from .HmsPrj import HmsPrj, init_hms_project, hms

# Logging configuration
from .LoggingConfig import (
    setup_logging,
    get_logger,
    log_call,
    DEBUG,
    INFO,
    WARNING,
    ERROR,
    CRITICAL
)

# Decorators
from .Decorators import log_call, standardize_path

# GIS extraction
from .HmsGeo import HmsGeo

# File operations (Phase 2)
from .HmsBasin import HmsBasin
from .HmsControl import HmsControl
from .HmsMet import HmsMet
from .HmsGage import HmsGage

# Run file operations (DSS Output Manager)
from .HmsRun import HmsRun

# Execution engine (Phase 3)
from .HmsJython import HmsJython
from .HmsCmdr import HmsCmdr

# DSS and Results (Phase 4)
from .HmsDss import HmsDss
from .HmsResults import HmsResults

# Utilities
from .HmsUtils import HmsUtils

# Example Projects (Phase 5)
from .HmsExamples import HmsExamples

# M3 Model HMS Projects
from .HmsM3Model import HmsM3Model

# HUC Watersheds and AORC Precipitation (Phase 6)
from .HmsHuc import HmsHuc
from .HmsAorc import HmsAorc
from .HmsGrid import HmsGrid
from .HmsDssGrid import HmsDssGrid

# Atlas 14 Hyetograph Generation
from .Atlas14Storm import Atlas14Storm, Atlas14Config

# TP-40 Frequency Storm Hyetograph Generation
from .FrequencyStorm import FrequencyStorm

# Public API exports
__all__ = [
    # Version
    "__version__",

    # Project Management
    "HmsPrj",
    "init_hms_project",
    "hms",

    # File Operations
    "HmsBasin",
    "HmsControl",
    "HmsMet",
    "HmsGage",
    "HmsRun",

    # Execution
    "HmsCmdr",
    "HmsJython",

    # DSS and Results
    "HmsDss",
    "HmsResults",

    # GIS Operations
    "HmsGeo",

    # Utilities
    "HmsUtils",

    # Example Projects
    "HmsExamples",

    # M3 Model HMS Projects
    "HmsM3Model",

    # HUC Watersheds and AORC
    "HmsHuc",
    "HmsAorc",
    "HmsGrid",
    "HmsDssGrid",


    # Atlas 14
    "Atlas14Storm",
    "Atlas14Config",

    # TP-40 Frequency Storm
    "FrequencyStorm",

    # Logging
    "setup_logging",
    "get_logger",
    "log_call",
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",

    # Decorators
    "standardize_path",
]

# Output Parsing
from .HmsOutput import HmsOutput, HmsMessage, ComputeResult

