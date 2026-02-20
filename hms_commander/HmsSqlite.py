"""
HmsSqlite - SQLite Grid Database Operations for HMS Commander

Provides static methods for reading spatial geometry from HEC-HMS 4.x SQLite
grid databases. These databases store authoritative subbasin polygons, reach
linestrings, outlet points, and discretization grids for gridded HMS models
(Modified Clark, SCS Grid).

Classes:
    HmsSqlite: Static class for SQLite grid database operations

Key Functions:
    list_layers: List tables with row counts and geometry types
    get_crs: Extract CRS WKT from spatial_ref_sys table
    get_subbasins: Read subbasin2d polygons as GeoDataFrame
    get_reaches: Read reach2d linestrings as GeoDataFrame
    get_outlets: Read outlet points as GeoDataFrame
    get_junctions: Read junction points as GeoDataFrame
    get_discretization: Read grid cells (large, opt-in)
    read_grid_database: Read all layers in one call
    discover_sqlite_files: Find .sqlite files in a project directory
    join_with_parameters: Merge geometry with basin parameter DataFrame

Dependencies:
    Required for geometry methods:
        - geopandas: Spatial data handling
        - (fiona/GDAL backend reads SpatiaLite natively)

    Not required for list_layers, get_crs, discover_sqlite_files:
        - Uses stdlib sqlite3 only

    Install with:
        pip install hms-commander[gis]
        # OR
        pip install geopandas

Example:
    >>> from hms_commander import HmsSqlite
    >>>
    >>> # List layers (no geopandas needed)
    >>> layers = HmsSqlite.list_layers("project.sqlite")
    >>> print(layers)
    >>>
    >>> # Read subbasin polygons
    >>> subs = HmsSqlite.get_subbasins("project.sqlite")
    >>> print(f"Found {len(subs)} subbasins")

Notes:
    - All methods are static (no instantiation required)
    - HEC-HMS 4.x gridded models store geometry in SpatiaLite format
    - The spatial_ref_sys table contains CRS as WKT (often custom, no EPSG)
    - Geometry is stored as WKB blobs in GEOMETRY columns
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd

from .LoggingConfig import get_logger
from .Decorators import log_call

logger = get_logger(__name__)

# Geometry type codes used in SpatiaLite geometry_columns table
_GEOM_TYPE_NAMES = {
    0: "Geometry",
    1: "Point",
    2: "LineString",
    3: "Polygon",
    4: "MultiPoint",
    5: "MultiLineString",
    6: "MultiPolygon",
    7: "GeometryCollection",
}

# Standard HMS SQLite layers and their expected geometry types
_HMS_LAYERS = {
    "subbasin2d": "Polygon",
    "reach2d": "LineString",
    "outlet": "Point",
    "junction": "Point",
    "subbasin": "Point",
    "reach": "LineString",
    "diversion": "Point",
    "reservoir": "Point",
    "reservoir2d": "Polygon",
    "sink": "Point",
    "source": "Point",
    "discretization": "Polygon",
}


class HmsSqlite:
    """
    Static class for HEC-HMS SQLite grid database operations.

    Provides methods for reading spatial geometry from SpatiaLite databases
    created by HEC-HMS 4.x for gridded models (Modified Clark, SCS Grid).

    All methods are static - do not instantiate this class.

    Example:
        >>> from hms_commander import HmsSqlite
        >>>
        >>> # Read subbasin polygons
        >>> subs = HmsSqlite.get_subbasins("Minimum_Facility.sqlite")
        >>> print(f"Found {len(subs)} subbasins")
        >>>
        >>> # Read all layers at once
        >>> layers = HmsSqlite.read_grid_database("Minimum_Facility.sqlite")
        >>> for name, gdf in layers.items():
        ...     print(f"  {name}: {len(gdf)} features")
    """

    @staticmethod
    def _check_gis_dependencies():
        """Check that geopandas is installed."""
        try:
            import geopandas
        except ImportError:
            raise ImportError(
                "geopandas is required for geometry operations.\n"
                "Install with: pip install hms-commander[gis]\n"
                "Or: pip install geopandas"
            )

    @staticmethod
    @log_call
    def list_layers(sqlite_path: Union[str, Path]) -> pd.DataFrame:
        """
        List all spatial layers in an HMS SQLite database.

        Uses stdlib sqlite3 only - no geopandas required.

        Parameters
        ----------
        sqlite_path : Union[str, Path]
            Path to the SQLite database file.

        Returns
        -------
        pd.DataFrame
            DataFrame with columns:
                - table_name: Name of the table
                - row_count: Number of rows
                - geometry_type: Geometry type name (Point, LineString, Polygon, etc.)
                - srid: Spatial reference ID

        Raises
        ------
        FileNotFoundError
            If sqlite_path does not exist.

        Example
        -------
        >>> layers = HmsSqlite.list_layers("Minimum_Facility.sqlite")
        >>> print(layers)
        """
        sqlite_path = Path(sqlite_path)
        if not sqlite_path.exists():
            raise FileNotFoundError(f"SQLite file not found: {sqlite_path}")

        conn = sqlite3.connect(str(sqlite_path))
        try:
            cursor = conn.cursor()

            # Read geometry_columns metadata
            geom_info = {}
            try:
                cursor.execute("SELECT f_table_name, geometry_type, srid FROM geometry_columns")
                for row in cursor.fetchall():
                    table_name = row[0]
                    geom_type_val = row[1]
                    srid = row[2]
                    # type can be int or string depending on SpatiaLite version
                    if isinstance(geom_type_val, int):
                        geom_type = _GEOM_TYPE_NAMES.get(geom_type_val, f"Unknown({geom_type_val})")
                    else:
                        geom_type = str(geom_type_val)
                    geom_info[table_name] = {"geometry_type": geom_type, "srid": srid}
            except sqlite3.OperationalError:
                logger.debug("No geometry_columns table found")

            # Get row counts for all spatial tables
            records = []
            for table_name in sorted(geom_info.keys()):
                try:
                    cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                    row_count = cursor.fetchone()[0]
                except sqlite3.OperationalError:
                    row_count = 0

                records.append({
                    "table_name": table_name,
                    "row_count": row_count,
                    "geometry_type": geom_info[table_name]["geometry_type"],
                    "srid": geom_info[table_name]["srid"],
                })

            logger.info(f"Found {len(records)} spatial layers in {sqlite_path.name}")
            return pd.DataFrame(records)
        finally:
            conn.close()

    @staticmethod
    @log_call
    def get_crs(sqlite_path: Union[str, Path]) -> Optional[str]:
        """
        Extract CRS as WKT string from the spatial_ref_sys table.

        Uses stdlib sqlite3 only - no geopandas required.

        Parameters
        ----------
        sqlite_path : Union[str, Path]
            Path to the SQLite database file.

        Returns
        -------
        Optional[str]
            WKT string of the coordinate reference system, or None if not found.

        Raises
        ------
        FileNotFoundError
            If sqlite_path does not exist.

        Example
        -------
        >>> wkt = HmsSqlite.get_crs("Minimum_Facility.sqlite")
        >>> print(wkt[:50])
        'PROJCS["NAD83 / UTM zone 16N",...'
        """
        sqlite_path = Path(sqlite_path)
        if not sqlite_path.exists():
            raise FileNotFoundError(f"SQLite file not found: {sqlite_path}")

        conn = sqlite3.connect(str(sqlite_path))
        try:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT srtext FROM spatial_ref_sys LIMIT 1")
                row = cursor.fetchone()
                if row and row[0]:
                    wkt = row[0].strip()
                    if wkt:
                        logger.info(f"CRS WKT found in {sqlite_path.name} ({len(wkt)} chars)")
                        return wkt
            except sqlite3.OperationalError:
                logger.debug(f"No spatial_ref_sys table in {sqlite_path.name}")

            return None
        finally:
            conn.close()

    @staticmethod
    @log_call
    def get_subbasins(sqlite_path: Union[str, Path]) -> 'gpd.GeoDataFrame':
        """
        Read subbasin polygons from the subbasin2d table.

        Parameters
        ----------
        sqlite_path : Union[str, Path]
            Path to the SQLite database file.

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with subbasin polygons. Columns depend on the HMS
            project configuration; always includes ``geometry`` (Polygon or
            MultiPolygon) and typically ``name``. May also include:
            ``area_sqkm``, ``centroid_x``, ``centroid_y``, ``latitude``,
            ``longitude`` (these are NULL in some projects).

        Raises
        ------
        FileNotFoundError
            If sqlite_path does not exist.
        ImportError
            If geopandas is not installed.
        ValueError
            If the subbasin2d table is not found.

        Example
        -------
        >>> subs = HmsSqlite.get_subbasins("Minimum_Facility.sqlite")
        >>> print(f"Found {len(subs)} subbasins")
        """
        return HmsSqlite._read_layer(sqlite_path, "subbasin2d")

    @staticmethod
    @log_call
    def get_reaches(sqlite_path: Union[str, Path]) -> 'gpd.GeoDataFrame':
        """
        Read reach linestrings from the reach2d table.

        Parameters
        ----------
        sqlite_path : Union[str, Path]
            Path to the SQLite database file.

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with reach linestrings and topology attributes including:
                - name: Reach name
                - linkno, dslinkno: Link numbers for topology
                - uslinkno1, uslinkno2: Upstream link numbers
                - strmorder: Stream order
                - length: Reach length
                - slope: Reach slope
                - geometry: LineString geometry

        Raises
        ------
        FileNotFoundError
            If sqlite_path does not exist.
        ImportError
            If geopandas is not installed.
        ValueError
            If the reach2d table is not found.

        Example
        -------
        >>> reaches = HmsSqlite.get_reaches("Minimum_Facility.sqlite")
        >>> print(f"Found {len(reaches)} reaches")
        """
        return HmsSqlite._read_layer(sqlite_path, "reach2d")

    @staticmethod
    @log_call
    def get_outlets(sqlite_path: Union[str, Path]) -> 'gpd.GeoDataFrame':
        """
        Read outlet points from the outlet table.

        Parameters
        ----------
        sqlite_path : Union[str, Path]
            Path to the SQLite database file.

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with outlet points and attributes including:
                - name: Outlet name
                - geometry: Point geometry

        Raises
        ------
        FileNotFoundError
            If sqlite_path does not exist.
        ImportError
            If geopandas is not installed.
        ValueError
            If the outlet table is not found.

        Example
        -------
        >>> outlets = HmsSqlite.get_outlets("Minimum_Facility.sqlite")
        >>> for _, row in outlets.iterrows():
        ...     print(f"  {row['name']}: ({row.geometry.x:.1f}, {row.geometry.y:.1f})")
        """
        return HmsSqlite._read_layer(sqlite_path, "outlet")

    @staticmethod
    @log_call
    def get_junctions(sqlite_path: Union[str, Path]) -> 'gpd.GeoDataFrame':
        """
        Read junction points from the junction table.

        Returns an empty GeoDataFrame if the junction table has no rows
        (common in gridded models where junctions are implicit).

        Parameters
        ----------
        sqlite_path : Union[str, Path]
            Path to the SQLite database file.

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with junction points (may be empty).

        Raises
        ------
        FileNotFoundError
            If sqlite_path does not exist.
        ImportError
            If geopandas is not installed.

        Example
        -------
        >>> junctions = HmsSqlite.get_junctions("Minimum_Facility.sqlite")
        >>> print(f"Found {len(junctions)} junctions")  # Often 0
        """
        return HmsSqlite._read_layer(sqlite_path, "junction")

    @staticmethod
    @log_call
    def get_discretization(sqlite_path: Union[str, Path]) -> 'gpd.GeoDataFrame':
        """
        Read grid cell discretization polygons.

        This layer can be very large (thousands to hundreds of thousands of cells).
        Use only when grid cell geometry is needed.

        Parameters
        ----------
        sqlite_path : Union[str, Path]
            Path to the SQLite database file.

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with discretization grid cell polygons.

        Raises
        ------
        FileNotFoundError
            If sqlite_path does not exist.
        ImportError
            If geopandas is not installed.

        Example
        -------
        >>> cells = HmsSqlite.get_discretization("Minimum_Facility.sqlite")
        >>> print(f"Found {len(cells)} grid cells")
        """
        return HmsSqlite._read_layer(sqlite_path, "discretization")

    @staticmethod
    @log_call
    def read_grid_database(
        sqlite_path: Union[str, Path],
        include_discretization: bool = False,
        skip_empty: bool = True
    ) -> Dict[str, 'gpd.GeoDataFrame']:
        """
        Read all spatial layers from an HMS SQLite database.

        Parameters
        ----------
        sqlite_path : Union[str, Path]
            Path to the SQLite database file.
        include_discretization : bool, default False
            If True, include the discretization grid cells (can be very large).
        skip_empty : bool, default True
            If True, omit layers with zero rows from the result.

        Returns
        -------
        Dict[str, gpd.GeoDataFrame]
            Dictionary mapping layer name to GeoDataFrame.

        Raises
        ------
        FileNotFoundError
            If sqlite_path does not exist.
        ImportError
            If geopandas is not installed.

        Example
        -------
        >>> layers = HmsSqlite.read_grid_database("Minimum_Facility.sqlite")
        >>> for name, gdf in layers.items():
        ...     print(f"  {name}: {len(gdf)} features")
        """
        HmsSqlite._check_gis_dependencies()
        sqlite_path = Path(sqlite_path)
        if not sqlite_path.exists():
            raise FileNotFoundError(f"SQLite file not found: {sqlite_path}")

        # Get layer info to know which have data
        layer_info = HmsSqlite.list_layers(sqlite_path)

        # Standard layers to read (order matters for logging)
        target_layers = ["subbasin2d", "reach2d", "outlet", "junction",
                         "subbasin", "reach", "diversion", "reservoir",
                         "reservoir2d", "sink", "source"]
        if include_discretization:
            target_layers.append("discretization")

        result = {}
        for layer_name in target_layers:
            # Check if layer exists in database
            layer_rows = layer_info[layer_info["table_name"] == layer_name]
            if layer_rows.empty:
                continue

            row_count = layer_rows.iloc[0]["row_count"]
            if skip_empty and row_count == 0:
                continue

            try:
                gdf = HmsSqlite._read_layer(sqlite_path, layer_name)
                result[layer_name] = gdf
            except ValueError as e:
                logger.warning(f"Could not read layer '{layer_name}': {e}")

        logger.info(
            f"Read {len(result)} layers from {sqlite_path.name}: "
            + ", ".join(f"{k}({len(v)})" for k, v in result.items())
        )
        return result

    @staticmethod
    @log_call
    def discover_sqlite_files(project_dir: Union[str, Path]) -> List[Path]:
        """
        Find all .sqlite files in an HMS project directory.

        Parameters
        ----------
        project_dir : Union[str, Path]
            Path to the HMS project directory.

        Returns
        -------
        List[Path]
            Sorted list of .sqlite file paths.

        Example
        -------
        >>> files = HmsSqlite.discover_sqlite_files("river_bend/")
        >>> print(f"Found {len(files)} SQLite files")
        """
        project_dir = Path(project_dir)
        if not project_dir.is_dir():
            logger.warning(f"Directory not found: {project_dir}")
            return []

        sqlite_files = sorted(project_dir.glob("*.sqlite"))
        logger.info(f"Found {len(sqlite_files)} .sqlite files in {project_dir}")
        return sqlite_files

    @staticmethod
    @log_call
    def join_with_parameters(
        sqlite_gdf: 'gpd.GeoDataFrame',
        subbasin_df: pd.DataFrame,
        join_column: str = "name"
    ) -> 'gpd.GeoDataFrame':
        """
        Merge SQLite geometry with basin parameter DataFrame.

        Joins on the specified column (default: 'name') to combine spatial
        geometry from the SQLite database with hydrologic parameters from
        basin file parsing.

        Parameters
        ----------
        sqlite_gdf : gpd.GeoDataFrame
            GeoDataFrame from get_subbasins() or similar.
        subbasin_df : pd.DataFrame
            DataFrame with subbasin parameters (e.g., from HmsPrj.subbasin_df
            or HmsBasin.get_subbasins()).
        join_column : str, default "name"
            Column name to join on (must exist in both DataFrames).

        Returns
        -------
        gpd.GeoDataFrame
            Merged GeoDataFrame with geometry and parameters.

        Raises
        ------
        ImportError
            If geopandas is not installed.
        ValueError
            If join_column is missing from either DataFrame.

        Example
        -------
        >>> subs_geo = HmsSqlite.get_subbasins("Minimum_Facility.sqlite")
        >>> from hms_commander import HmsBasin
        >>> subs_params = HmsBasin.get_subbasins("Minimum_Facility.basin")
        >>> merged = HmsSqlite.join_with_parameters(subs_geo, subs_params)
        >>> print(f"Merged: {len(merged)} rows with geometry + parameters")
        """
        HmsSqlite._check_gis_dependencies()
        import geopandas as gpd

        if join_column not in sqlite_gdf.columns:
            raise ValueError(
                f"Column '{join_column}' not found in geometry GeoDataFrame. "
                f"Available: {list(sqlite_gdf.columns)}"
            )
        if join_column not in subbasin_df.columns:
            raise ValueError(
                f"Column '{join_column}' not found in parameter DataFrame. "
                f"Available: {list(subbasin_df.columns)}"
            )

        # Determine columns to bring from subbasin_df (avoid duplicates)
        geo_cols = set(sqlite_gdf.columns)
        param_cols = [join_column] + [
            c for c in subbasin_df.columns
            if c not in geo_cols and c != join_column
        ]
        param_subset = subbasin_df[param_cols].copy()

        merged = sqlite_gdf.merge(param_subset, on=join_column, how="left")

        # Ensure result is GeoDataFrame
        if not isinstance(merged, gpd.GeoDataFrame):
            merged = gpd.GeoDataFrame(merged, geometry="geometry", crs=sqlite_gdf.crs)

        logger.info(
            f"Joined {len(sqlite_gdf)} geometries with {len(subbasin_df)} parameters "
            f"on '{join_column}' -> {len(merged)} rows"
        )
        return merged

    # =========================================================================
    # Internal helpers
    # =========================================================================

    @staticmethod
    def _read_layer(
        sqlite_path: Union[str, Path],
        layer_name: str
    ) -> 'gpd.GeoDataFrame':
        """
        Read a single spatial layer from an HMS SQLite database.

        Parameters
        ----------
        sqlite_path : Union[str, Path]
            Path to the SQLite database file.
        layer_name : str
            Name of the layer/table to read.

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with layer data.
        """
        HmsSqlite._check_gis_dependencies()
        import geopandas as gpd

        sqlite_path = Path(sqlite_path)
        if not sqlite_path.exists():
            raise FileNotFoundError(f"SQLite file not found: {sqlite_path}")

        # Verify the layer exists
        conn = sqlite3.connect(str(sqlite_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (layer_name,)
            )
            if cursor.fetchone() is None:
                raise ValueError(
                    f"Layer '{layer_name}' not found in {sqlite_path.name}"
                )

            # Check row count
            cursor.execute(f'SELECT COUNT(*) FROM "{layer_name}"')
            row_count = cursor.fetchone()[0]
        finally:
            conn.close()

        if row_count == 0:
            # Return empty GeoDataFrame with correct CRS
            wkt = HmsSqlite.get_crs(sqlite_path)
            crs = None
            if wkt:
                try:
                    from pyproj import CRS as PyprojCRS
                    crs = PyprojCRS.from_wkt(wkt)
                except (ImportError, Exception):
                    pass
            return gpd.GeoDataFrame(geometry=[], crs=crs)

        # Read using geopandas (fiona/GDAL handles SpatiaLite natively)
        gdf = gpd.read_file(str(sqlite_path), layer=layer_name)

        logger.debug(f"Read {len(gdf)} features from {sqlite_path.name}:{layer_name}")
        return gdf
