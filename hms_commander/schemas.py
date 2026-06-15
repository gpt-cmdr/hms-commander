"""
schemas.py -- canonical, declarative column contracts for hms-commander's public DataFrames.

Single source of truth for the *stable* column surface of the project DataFrames that
hms-commander attaches to the :class:`HmsPrj` singleton (``hms_df`` / ``basin_df`` /
``subbasin_df`` / ``met_df`` / ``control_df`` / ``run_df`` / ``gage_df`` / ``pdata_df``).

Consumed by the shared agent-native API-surface generator (the ras-commander-docs hub) to emit the
machine-readable surface at ``/hms/llms/api/dataframes.json`` -- so LLMs and MCP servers can resolve
"what columns does ``basin_df`` have?" without scraping HTML. The construction methods
(``HmsPrj._build_*_dataframe()``) remain the runtime authority and may add extra columns; pinning
the documented contract here gives agents a stable, reviewable schema and one place to update.

Each entry of :data:`DATAFRAME_SCHEMAS`:
    description   -- one-line summary of the frame
    accessor      -- how a caller obtains the frame from the HmsPrj singleton
    source        -- the construction site (for maintainers)
    columns       -- list of {name, dtype, description} for the STABLE core columns
    extra_columns -- True if additional parsed columns may appear at runtime
    dynamic       -- True if the full column set is only knowable at runtime
"""

SCHEMA_VERSION = "1.0"

DATAFRAME_SCHEMAS = {
    "hms_df": {
        "description": "Project-level key/value metadata from the .hms file plus computed attributes.",
        "accessor": "hms.hms_df",
        "source": "HmsPrj._build_hms_dataframe()",
        "extra_columns": True,  # dynamic key/value rows from the .hms file
        "dynamic": False,
        "columns": [
            {"name": "key", "dtype": "str", "description": "Metadata key (e.g. 'Version', 'project_folder')."},
            {"name": "value", "dtype": "str", "description": "Metadata value."},
            {"name": "source", "dtype": "str", "description": "'project' (from the .hms file) or 'computed'."},
        ],
    },
    "basin_df": {
        "description": "One row per basin model (.basin), with component counts and method summaries.",
        "accessor": "hms.basin_df",
        "source": "HmsPrj._build_basin_dataframe()",
        "extra_columns": False,
        "dynamic": False,
        "columns": [
            {"name": "name", "dtype": "str", "description": "Basin model name."},
            {"name": "file_name", "dtype": "str", "description": "Basin file name (e.g. 'model.basin')."},
            {"name": "full_path", "dtype": "str", "description": "Absolute path to the basin file."},
            {"name": "exists", "dtype": "bool", "description": "Whether the file exists on disk."},
            {"name": "description", "dtype": "str", "description": "Basin model description."},
            {"name": "last_modified_date", "dtype": "str", "description": "File last-modified date."},
            {"name": "last_modified_time", "dtype": "str", "description": "File last-modified time."},
            {"name": "num_subbasins", "dtype": "int", "description": "Count of subbasins."},
            {"name": "num_reaches", "dtype": "int", "description": "Count of reaches."},
            {"name": "num_junctions", "dtype": "int", "description": "Count of junctions."},
            {"name": "num_reservoirs", "dtype": "int", "description": "Count of reservoirs."},
            {"name": "num_sources", "dtype": "int", "description": "Count of source elements."},
            {"name": "num_sinks", "dtype": "int", "description": "Count of sink elements."},
            {"name": "total_area", "dtype": "float", "description": "Total catchment area across subbasins."},
            {"name": "loss_methods", "dtype": "str", "description": "Comma-separated unique loss methods used."},
            {"name": "transform_methods", "dtype": "str", "description": "Comma-separated unique transform methods."},
            {"name": "baseflow_methods", "dtype": "str", "description": "Comma-separated unique baseflow methods."},
            {"name": "routing_methods", "dtype": "str", "description": "Comma-separated unique reach routing methods."},
        ],
    },
    "subbasin_df": {
        "description": "One row per subbasin, with loss/transform/baseflow parameters and canvas position.",
        "accessor": "hms.subbasin_df",
        "source": "HmsPrj._build_subbasin_dataframe() (parsed from .basin files)",
        "extra_columns": True,  # method-specific parameter columns vary by method
        "dynamic": False,
        "columns": [
            {"name": "name", "dtype": "str", "description": "Subbasin element name."},
            {"name": "area", "dtype": "float", "description": "Subbasin drainage area."},
            {"name": "downstream", "dtype": "str", "description": "Downstream element this subbasin connects to."},
            {"name": "basin_model", "dtype": "str", "description": "Owning basin model name."},
            {"name": "source_file", "dtype": "str", "description": "Basin file the subbasin was parsed from."},
            {"name": "loss_method", "dtype": "str", "description": "Loss method (e.g. 'Deficit and Constant', 'SCS Curve Number')."},
            {"name": "initial_deficit", "dtype": "float", "description": "Initial deficit (deficit-constant loss)."},
            {"name": "maximum_deficit", "dtype": "float", "description": "Maximum deficit (deficit-constant loss)."},
            {"name": "constant_rate", "dtype": "float", "description": "Constant loss rate."},
            {"name": "percolation_rate", "dtype": "float", "description": "Percolation rate."},
            {"name": "percent_impervious", "dtype": "float", "description": "Percent impervious area."},
            {"name": "curve_number", "dtype": "float", "description": "SCS curve number."},
            {"name": "initial_abstraction", "dtype": "float", "description": "SCS initial abstraction."},
            {"name": "transform_method", "dtype": "str", "description": "Transform method (e.g. 'SCS Unit Hydrograph', 'Snyder', 'Clark')."},
            {"name": "time_of_concentration", "dtype": "float", "description": "Time of concentration (Clark)."},
            {"name": "storage_coefficient", "dtype": "float", "description": "Storage coefficient (Clark)."},
            {"name": "lag_time", "dtype": "float", "description": "Lag time (SCS UH)."},
            {"name": "snyder_tp", "dtype": "float", "description": "Snyder standard lag (Tp)."},
            {"name": "snyder_cp", "dtype": "float", "description": "Snyder peaking coefficient (Cp)."},
            {"name": "baseflow_method", "dtype": "str", "description": "Baseflow method (e.g. 'Recession')."},
            {"name": "recession_factor", "dtype": "float", "description": "Recession constant."},
            {"name": "initial_discharge", "dtype": "float", "description": "Initial baseflow discharge."},
            {"name": "gw1_initial", "dtype": "float", "description": "Groundwater layer 1 initial value."},
            {"name": "gw1_coefficient", "dtype": "float", "description": "Groundwater layer 1 routing coefficient."},
            {"name": "canvas_x", "dtype": "float", "description": "Element X position on the basin canvas."},
            {"name": "canvas_y", "dtype": "float", "description": "Element Y position on the basin canvas."},
        ],
    },
    "met_df": {
        "description": "One row per meteorologic model (.met), with method assignments.",
        "accessor": "hms.met_df",
        "source": "HmsPrj._build_met_dataframe() (parsed from .met files)",
        "extra_columns": False,
        "dynamic": False,
        "columns": [
            {"name": "name", "dtype": "str", "description": "Meteorologic model name."},
            {"name": "file_name", "dtype": "str", "description": "Met file name (e.g. 'model.met')."},
            {"name": "full_path", "dtype": "str", "description": "Absolute path to the met file."},
            {"name": "exists", "dtype": "bool", "description": "Whether the file exists on disk."},
            {"name": "description", "dtype": "str", "description": "Met model description."},
            {"name": "last_modified_date", "dtype": "str", "description": "File last-modified date."},
            {"name": "last_modified_time", "dtype": "str", "description": "File last-modified time."},
            {"name": "precip_method", "dtype": "str", "description": "Precipitation method (e.g. 'Specified Hyetograph', 'Gridded', 'Frequency Storm')."},
            {"name": "et_method", "dtype": "str", "description": "Evapotranspiration method."},
            {"name": "snowmelt_method", "dtype": "str", "description": "Snowmelt method."},
            {"name": "num_subbasin_assignments", "dtype": "int", "description": "Count of subbasin met assignments."},
        ],
    },
    "control_df": {
        "description": "One row per control specification (.control), with the simulation time window.",
        "accessor": "hms.control_df",
        "source": "HmsPrj._build_control_dataframe() (parsed from .control files)",
        "extra_columns": False,
        "dynamic": False,
        "columns": [
            {"name": "name", "dtype": "str", "description": "Control specification name."},
            {"name": "file_name", "dtype": "str", "description": "Control file name (e.g. 'model.control')."},
            {"name": "full_path", "dtype": "str", "description": "Absolute path to the control file."},
            {"name": "exists", "dtype": "bool", "description": "Whether the file exists on disk."},
            {"name": "description", "dtype": "str", "description": "Control spec description."},
            {"name": "start_date", "dtype": "datetime", "description": "Simulation start date/time."},
            {"name": "end_date", "dtype": "datetime", "description": "Simulation end date/time."},
            {"name": "time_interval", "dtype": "str", "description": "Time step as written in the file."},
            {"name": "time_interval_minutes", "dtype": "int", "description": "Time step in minutes."},
            {"name": "duration_hours", "dtype": "float", "description": "Simulation duration in hours."},
        ],
    },
    "run_df": {
        "description": "One row per simulation run (.run), linking basin/met/control + DSS output config.",
        "accessor": "hms.run_df",
        "source": "HmsPrj._build_run_dataframe() (parsed from .run files)",
        "extra_columns": False,
        "dynamic": False,
        "columns": [
            {"name": "name", "dtype": "str", "description": "Run name."},
            {"name": "file_name", "dtype": "str", "description": "Run file name (e.g. 'model.run')."},
            {"name": "full_path", "dtype": "str", "description": "Absolute path to the run file."},
            {"name": "exists", "dtype": "bool", "description": "Whether the file exists on disk."},
            {"name": "description", "dtype": "str", "description": "Run description."},
            {"name": "basin_model", "dtype": "str", "description": "Linked basin model name."},
            {"name": "met_model", "dtype": "str", "description": "Linked meteorologic model name."},
            {"name": "control_spec", "dtype": "str", "description": "Linked control specification name."},
            {"name": "dss_file", "dtype": "str", "description": "Output DSS file for results."},
            {"name": "log_file", "dtype": "str", "description": "Run log file."},
            {"name": "last_modified_date", "dtype": "str", "description": "File last-modified date."},
            {"name": "last_modified_time", "dtype": "str", "description": "File last-modified time."},
            {"name": "last_execution_date", "dtype": "str", "description": "Date the run was last computed."},
            {"name": "last_execution_time", "dtype": "str", "description": "Time the run was last computed."},
            {"name": "save_state_type", "dtype": "str", "description": "Save-state configuration."},
            {"name": "time_series_output", "dtype": "str", "description": "Time-series output configuration."},
        ],
    },
    "gage_df": {
        "description": "One row per time-series gage (.gage), with DSS references and optional DSS metadata.",
        "accessor": "hms.gage_df",
        "source": "HmsPrj._build_gage_dataframe() (parsed from .gage files; DSS metadata via _load_dss_metadata())",
        "extra_columns": True,  # DSS metadata columns are populated lazily
        "dynamic": False,
        "columns": [
            {"name": "name", "dtype": "str", "description": "Gage name."},
            {"name": "gage_type", "dtype": "str", "description": "Gage type (e.g. 'Precipitation', 'Discharge')."},
            {"name": "dss_file", "dtype": "str", "description": "DSS file referenced by the gage."},
            {"name": "dss_pathname", "dtype": "str", "description": "DSS record pathname."},
            {"name": "data_source_type", "dtype": "str", "description": "Data source type."},
            {"name": "last_modified_date", "dtype": "str", "description": "File last-modified date."},
            {"name": "last_modified_time", "dtype": "str", "description": "File last-modified time."},
            {"name": "reference_height", "dtype": "float", "description": "Reference height (where applicable)."},
            {"name": "reference_height_units", "dtype": "str", "description": "Units of reference_height."},
            {"name": "source_file", "dtype": "str", "description": "Gage file the row was parsed from."},
            {"name": "has_dss_reference", "dtype": "bool", "description": "Whether a DSS record is referenced."},
            {"name": "dss_start_date", "dtype": "str", "description": "DSS series start (lazy; via _load_dss_metadata)."},
            {"name": "dss_end_date", "dtype": "str", "description": "DSS series end (lazy)."},
            {"name": "dss_num_values", "dtype": "int", "description": "DSS series value count (lazy)."},
            {"name": "dss_units", "dtype": "str", "description": "DSS series units (lazy)."},
        ],
    },
    "pdata_df": {
        "description": "Paired-data tables referenced by the project (.pdata).",
        "accessor": "hms.pdata_df",
        "source": "HmsPrj._build_pdata_dataframe()",
        "extra_columns": True,
        "dynamic": True,
        "columns": [],
        "note": (
            "Paired-data table columns depend on the table type (storage-discharge, elevation-area, "
            "percentage curves, etc.) and are not statically enumerable; see HmsPrj._build_pdata_dataframe()."
        ),
    },
}
