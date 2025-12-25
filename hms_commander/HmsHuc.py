"""
HmsHuc - HUC Watershed Operations for HMS Commander

Provides static methods for downloading and working with USGS Hydrologic Unit Code (HUC)
watersheds from the Watershed Boundary Dataset (WBD) via PyNHD.

This module enables automated download of standardized watershed boundaries for use in
AORC precipitation grid cell mapping and other spatial operations.

Classes:
    HmsHuc: Static class for HUC watershed operations

Key Functions:
    get_huc12_for_bounds: Download HUC12 watersheds within bounding box
    get_huc8_for_bounds: Download HUC8 watersheds within bounding box
    get_huc_by_ids: Download specific HUCs by ID
    get_available_levels: List available HUC levels

Dependencies:
    Required:
        - pygeohydro: HUC watershed download
        - geopandas: Spatial data handling
        - shapely: Geometry operations

    Install with:
        pip install hms-commander[gis]
        # OR
        pip install pygeohydro geopandas shapely

Example:
    >>> from hms_commander import HmsHuc
    >>>
    >>> # Download HUC12 watersheds for project area
    >>> bounds = (-77.71, 41.01, -77.25, 41.22)  # west, south, east, north
    >>> watersheds = HmsHuc.get_huc12_for_bounds(bounds)
    >>> print(f"Downloaded {len(watersheds)} HUC12 watersheds")
    >>>
    >>> # Access data
    >>> for idx, ws in watersheds.iterrows():
    ...     print(f"{ws['huc12']}: {ws['name']} ({ws['areasqkm']:.1f} km²)")

Notes:
    - All methods are static (no instantiation required)
    - Returns GeoPandas GeoDataFrames with WGS84 (EPSG:4326) CRS
    - HUC boundaries are standardized, peer-reviewed by USGS
    - Final WBD published January 2025 (static but authoritative)
"""

from pathlib import Path
from typing import List, Optional, Tuple, Union

from .LoggingConfig import get_logger
from .Decorators import log_call

logger = get_logger(__name__)


class HmsHuc:
    """
    Static class for HUC watershed operations.

    Provides methods for downloading USGS Hydrologic Unit Code (HUC) watersheds
    from the Watershed Boundary Dataset (WBD) using PyNHD.

    All methods are static - do not instantiate this class.

    HUC Levels:
        - HUC2: Regions (21 in CONUS)
        - HUC4: Subregions (222 in CONUS)
        - HUC6: Basins (378 in CONUS)
        - HUC8: Subbasins (2,264 in CONUS) - Good for regional HMS models
        - HUC10: Watersheds (18,000+ in CONUS)
        - HUC12: Subwatersheds (100,000+ in CONUS) - Good for detailed HMS models

    Example:
        >>> from hms_commander import HmsHuc
        >>>
        >>> # Download HUC12 watersheds
        >>> bounds = (-77.71, 41.01, -77.25, 41.22)
        >>> huc12s = HmsHuc.get_huc12_for_bounds(bounds)
        >>>
        >>> # Download specific HUC by ID
        >>> specific = HmsHuc.get_huc_by_ids("huc12", ["020502030404"])
    """

    @staticmethod
    def _check_dependencies():
        """Check that PyNHD and dependencies are installed."""
        try:
            import pygeohydro
            import geopandas
            import shapely
        except ImportError as e:
            missing_pkg = str(e).split("'")[1] if "'" in str(e) else "unknown"
            raise ImportError(
                f"Missing required package: {missing_pkg}\n"
                "Install with: pip install hms-commander[gis]\n"
                "Or: pip install pygeohydro geopandas shapely"
            )

    @staticmethod
    @log_call
    def get_huc12_for_bounds(
        bounds: Tuple[float, float, float, float],
        return_format: str = "geodataframe"
    ) -> 'gpd.GeoDataFrame':
        """
        Download HUC12 watersheds within bounding box.

        Parameters
        ----------
        bounds : Tuple[float, float, float, float]
            Bounding box as (west, south, east, north) in WGS84 decimal degrees.
            Example: (-77.71, 41.01, -77.25, 41.22)
        return_format : str, default "geodataframe"
            Return format:
                - "geodataframe": GeoPandas GeoDataFrame (default)
                - "shapefile": Save to shapefile and return path
                - "geojson": Save to GeoJSON and return path

        Returns
        -------
        gpd.GeoDataFrame or Path
            HUC12 watersheds as GeoDataFrame (if return_format="geodataframe")
            or Path to output file (if return_format="shapefile" or "geojson").

            GeoDataFrame columns include:
                - huc12: 12-digit HUC identifier
                - name: Watershed name
                - areasqkm: Area in square kilometers
                - states: State abbreviations
                - geometry: Polygon geometry (EPSG:4326)

        Raises
        ------
        ImportError
            If pygeohydro, geopandas, or shapely not installed
        ValueError
            If bounds are invalid or no HUCs found

        Examples
        --------
        >>> from hms_commander import HmsHuc
        >>>
        >>> # Download HUC12s for project area
        >>> bounds = (-77.71, 41.01, -77.25, 41.22)
        >>> watersheds = HmsHuc.get_huc12_for_bounds(bounds)
        >>> print(f"Found {len(watersheds)} HUC12 watersheds")
        >>>
        >>> # Inspect data
        >>> print(watersheds[['huc12', 'name', 'areasqkm']])
        >>>
        >>> # Save to file
        >>> path = HmsHuc.get_huc12_for_bounds(bounds, return_format="geojson")

        Notes
        -----
        - Returns watersheds that intersect the bounding box
        - CRS is always EPSG:4326 (WGS84)
        - Typical HUC12 size: 0.1-1 square mile (~10-100 km²)
        - May return 5-50+ HUC12s depending on area size
        """
        HmsHuc._check_dependencies()

        from pygeohydro import WBD
        from shapely.geometry import box
        import geopandas as gpd

        # Validate bounds
        west, south, east, north = bounds
        if west >= east:
            raise ValueError(f"Invalid bounds: west ({west}) must be < east ({east})")
        if south >= north:
            raise ValueError(f"Invalid bounds: south ({south}) must be < north ({north})")

        logger.info(f"Downloading HUC12 watersheds for bounds: {bounds}")

        # Create bounding box geometry
        bbox_geom = box(west, south, east, north)

        # Download HUC12 watersheds
        wbd = WBD("huc12")
        watersheds = wbd.bygeom(bbox_geom, geo_crs="EPSG:4326")

        if len(watersheds) == 0:
            raise ValueError(f"No HUC12 watersheds found within bounds {bounds}")

        logger.info(f"Downloaded {len(watersheds)} HUC12 watersheds")

        # Return based on format
        if return_format == "geodataframe":
            return watersheds
        elif return_format == "shapefile":
            output_path = Path("huc12_watersheds.shp")
            watersheds.to_file(output_path)
            logger.info(f"Saved to shapefile: {output_path}")
            return output_path
        elif return_format == "geojson":
            output_path = Path("huc12_watersheds.geojson")
            watersheds.to_file(output_path, driver="GeoJSON")
            logger.info(f"Saved to GeoJSON: {output_path}")
            return output_path
        else:
            raise ValueError(f"Invalid return_format: {return_format}. Use 'geodataframe', 'shapefile', or 'geojson'")

    @staticmethod
    @log_call
    def get_huc8_for_bounds(
        bounds: Tuple[float, float, float, float],
        return_format: str = "geodataframe"
    ) -> 'gpd.GeoDataFrame':
        """
        Download HUC8 watersheds within bounding box.

        Parameters
        ----------
        bounds : Tuple[float, float, float, float]
            Bounding box as (west, south, east, north) in WGS84 decimal degrees.
        return_format : str, default "geodataframe"
            Return format: "geodataframe", "shapefile", or "geojson"

        Returns
        -------
        gpd.GeoDataFrame or Path
            HUC8 watersheds as GeoDataFrame or path to output file.

            GeoDataFrame columns include:
                - huc8: 8-digit HUC identifier
                - name: Watershed name
                - areasqkm: Area in square kilometers
                - states: State abbreviations
                - geometry: Polygon geometry (EPSG:4326)

        Examples
        --------
        >>> from hms_commander import HmsHuc
        >>>
        >>> # Download HUC8s for regional model
        >>> bounds = (-77.71, 41.01, -77.25, 41.22)
        >>> watersheds = HmsHuc.get_huc8_for_bounds(bounds)
        >>> print(f"Found {len(watersheds)} HUC8 watersheds")

        Notes
        -----
        - HUC8 represents subbasins (typically 10-100 square miles)
        - Good for regional HMS models with multiple subbasins
        - Fewer watersheds than HUC12 (typically 1-5 per small area)
        """
        HmsHuc._check_dependencies()

        from pygeohydro import WBD
        from shapely.geometry import box

        # Validate bounds
        west, south, east, north = bounds
        if west >= east or south >= north:
            raise ValueError(f"Invalid bounds: {bounds}")

        logger.info(f"Downloading HUC8 watersheds for bounds: {bounds}")

        # Create bounding box geometry
        bbox_geom = box(west, south, east, north)

        # Download HUC8 watersheds
        wbd = WBD("huc8")
        watersheds = wbd.bygeom(bbox_geom, geo_crs="EPSG:4326")

        if len(watersheds) == 0:
            raise ValueError(f"No HUC8 watersheds found within bounds {bounds}")

        logger.info(f"Downloaded {len(watersheds)} HUC8 watersheds")

        # Return based on format
        if return_format == "geodataframe":
            return watersheds
        elif return_format == "shapefile":
            output_path = Path("huc8_watersheds.shp")
            watersheds.to_file(output_path)
            logger.info(f"Saved to shapefile: {output_path}")
            return output_path
        elif return_format == "geojson":
            output_path = Path("huc8_watersheds.geojson")
            watersheds.to_file(output_path, driver="GeoJSON")
            logger.info(f"Saved to GeoJSON: {output_path}")
            return output_path
        else:
            raise ValueError(f"Invalid return_format: {return_format}")

    @staticmethod
    @log_call
    def get_huc_by_ids(
        level: str,
        huc_ids: List[str],
        return_format: str = "geodataframe"
    ) -> 'gpd.GeoDataFrame':
        """
        Download specific HUC watersheds by ID.

        Parameters
        ----------
        level : str
            HUC level: "huc2", "huc4", "huc6", "huc8", "huc10", or "huc12"
        huc_ids : List[str]
            List of HUC identifiers to download.
            Example: ["020502030404", "020502030405"] for HUC12
        return_format : str, default "geodataframe"
            Return format: "geodataframe", "shapefile", or "geojson"

        Returns
        -------
        gpd.GeoDataFrame or Path
            Requested HUC watersheds

        Raises
        ------
        ValueError
            If invalid level or no HUCs found

        Examples
        --------
        >>> from hms_commander import HmsHuc
        >>>
        >>> # Download specific HUC12 watersheds
        >>> huc_ids = ["020502030404", "020502030405"]
        >>> watersheds = HmsHuc.get_huc_by_ids("huc12", huc_ids)
        >>>
        >>> # Download specific HUC8
        >>> watersheds = HmsHuc.get_huc_by_ids("huc8", ["02050203"])

        Notes
        -----
        - Useful when you know specific HUC IDs you need
        - Faster than bounding box query for specific watersheds
        - Can mix HUCs from different regions
        """
        HmsHuc._check_dependencies()

        from pygeohydro import WBD

        # Validate level
        valid_levels = ["huc2", "huc4", "huc6", "huc8", "huc10", "huc12"]
        if level not in valid_levels:
            raise ValueError(f"Invalid level: {level}. Must be one of {valid_levels}")

        if not huc_ids:
            raise ValueError("huc_ids list cannot be empty")

        logger.info(f"Downloading {len(huc_ids)} {level.upper()} watersheds")

        # Download by IDs
        wbd = WBD(level)
        watersheds = wbd.byids(level, huc_ids)

        if len(watersheds) == 0:
            raise ValueError(f"No {level.upper()} watersheds found for IDs: {huc_ids}")

        logger.info(f"Downloaded {len(watersheds)} watersheds")

        # Return based on format
        if return_format == "geodataframe":
            return watersheds
        elif return_format == "shapefile":
            output_path = Path(f"{level}_watersheds.shp")
            watersheds.to_file(output_path)
            logger.info(f"Saved to shapefile: {output_path}")
            return output_path
        elif return_format == "geojson":
            output_path = Path(f"{level}_watersheds.geojson")
            watersheds.to_file(output_path, driver="GeoJSON")
            logger.info(f"Saved to GeoJSON: {output_path}")
            return output_path
        else:
            raise ValueError(f"Invalid return_format: {return_format}")

    @staticmethod
    def get_available_levels() -> List[str]:
        """
        Get list of available HUC levels.

        Returns
        -------
        List[str]
            Available HUC levels: ["huc2", "huc4", "huc6", "huc8", "huc10", "huc12"]

        Examples
        --------
        >>> from hms_commander import HmsHuc
        >>>
        >>> levels = HmsHuc.get_available_levels()
        >>> print(f"Available HUC levels: {levels}")
        """
        return ["huc2", "huc4", "huc6", "huc8", "huc10", "huc12"]

    @staticmethod
    def get_huc_info() -> dict:
        """
        Get information about HUC levels and typical characteristics.

        Returns
        -------
        dict
            Information about each HUC level including typical size and count.

        Examples
        --------
        >>> from hms_commander import HmsHuc
        >>>
        >>> info = HmsHuc.get_huc_info()
        >>> for level, data in info.items():
        ...     print(f"{level}: {data['description']}")
        """
        return {
            "huc2": {
                "name": "Region",
                "description": "Major drainage basins",
                "typical_size": ">10,000 sq mi",
                "conus_count": 21,
                "example": "02 = Mid-Atlantic"
            },
            "huc4": {
                "name": "Subregion",
                "description": "Large watershed groups",
                "typical_size": "1,000-10,000 sq mi",
                "conus_count": 222,
                "example": "0205 = Upper Susquehanna"
            },
            "huc6": {
                "name": "Basin",
                "description": "Medium watersheds",
                "typical_size": "100-1,000 sq mi",
                "conus_count": 378,
                "example": "020502 = Bald Eagle-Penns"
            },
            "huc8": {
                "name": "Subbasin",
                "description": "Small watersheds (good for regional HMS)",
                "typical_size": "10-100 sq mi",
                "conus_count": 2264,
                "example": "02050203 = Bald Eagle Creek"
            },
            "huc10": {
                "name": "Watershed",
                "description": "Local drainage areas",
                "typical_size": "1-10 sq mi",
                "conus_count": "18,000+",
                "example": "0205020304 = Spring Creek"
            },
            "huc12": {
                "name": "Subwatershed",
                "description": "Catchments (good for detailed HMS)",
                "typical_size": "0.1-1 sq mi",
                "conus_count": "100,000+",
                "example": "020502030404 = Buffalo Run"
            }
        }
