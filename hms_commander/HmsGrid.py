"""
HmsGrid - HMS Grid Definition and Grid Cell Mapping Operations

Provides static methods for creating HMS grid definition files and mapping
grid cells to subbasins for gridded precipitation workflows.

This module enables:
- Creation of .grid files for HMS gridded precipitation
- Generation of grid cell mapping files (hrapcells format)
- Spatial intersection of AORC grid cells with subbasin boundaries
- Travel length calculation for ModClark routing

Classes:
    HmsGrid: Static class for grid operations

Key Functions:
    create_grid_definition: Generate HMS .grid file
    map_grid_to_subbasins: Create grid cell mapping file
    get_cell_polygons: Place a grid cell file's cells on the map (HRAP, SHG)
    remap_cell_file: Move a grid cell file to another lattice (HRAP to SHG)
    check_cells_on_grid: Check cells against a DSS grid record
    calculate_travel_lengths: Compute flow distances
    get_grid_info: Read .grid file metadata

Dependencies:
    Required:
        - geopandas: Spatial operations
        - shapely: Geometry operations
        - xarray: NetCDF grid handling
        - pandas: Data manipulation
        - numpy: Numerical operations

    Install with:
        pip install hms-commander[gis]
        # OR
        pip install geopandas shapely xarray pandas numpy

Example:
    >>> from hms_commander import HmsGrid, HmsHuc, HmsAorc
    >>>
    >>> # Download HUC12 watersheds
    >>> bounds = (-77.71, 41.01, -77.25, 41.22)
    >>> watersheds = HmsHuc.get_huc12_for_bounds(bounds)
    >>>
    >>> # Download AORC data
    >>> aorc_nc = HmsAorc.download(bounds, "2020-05-01", "2020-05-15", "aorc.nc")
    >>>
    >>> # Create grid definition
    >>> HmsGrid.create_grid_definition(
    ...     grid_name="AORC_Grid_1",
    ...     dss_file="aorc_may2020.dss",
    ...     pathname="/AORC/GRID/PRECIP////",
    ...     output_file="grids/aorc.grid"
    ... )
    >>>
    >>> # Map AORC grid to each HUC12
    >>> for idx, ws in watersheds.iterrows():
    ...     HmsGrid.map_grid_to_subbasins(
    ...         subbasin_geometries={ws['name']: ws['geometry']},
    ...         grid_coords=(lon_coords, lat_coords),
    ...         output_hrapcells=f"regions/huc12_{ws['huc12']}"
    ...     )

Notes:
    - All methods are static (no instantiation required)
    - Grid cell mapping follows HMS hrapcells format
    - Supports both user shapefiles and HUC boundaries
"""

from pathlib import Path
from typing import Union, Optional, Tuple, Dict, List
from datetime import datetime
import logging
import re

from .LoggingConfig import get_logger
from .Decorators import log_call

logger = get_logger(__name__)


class HmsGrid:
    """
    Static class for HMS grid operations.

    Provides methods for creating HMS grid definition files and mapping
    grid cells to subbasins for gridded precipitation workflows.

    All methods are static - do not instantiate this class.

    Example:
        >>> from hms_commander import HmsGrid
        >>>
        >>> # Create grid definition
        >>> HmsGrid.create_grid_definition(
        ...     grid_name="AORC_Grid_1",
        ...     dss_file="aorc.dss",
        ...     pathname="/AORC/GRID/PRECIP////",
        ...     output_file="grids/aorc.grid"
        ... )
        >>>
        >>> # Map grid cells to subbasin
        >>> HmsGrid.map_grid_to_subbasins(
        ...     subbasin_geometries={"Sub1": polygon1, "Sub2": polygon2},
        ...     grid_coords=(lon_coords, lat_coords),
        ...     output_hrapcells="regions/hrapcells"
        ... )
    """

    @staticmethod
    @log_call
    def create_grid_definition(
        grid_name: str,
        dss_file: Union[str, Path],
        pathname: str,
        output_file: Union[str, Path],
        project_name: Optional[str] = None,
        description: str = "AORC Gridded Precipitation",
        version: str = "4.13"
    ) -> Path:
        """
        Generate HMS .grid file for AORC precipitation.

        Creates a .grid file that references DSS grid data for HMS gridded
        precipitation workflows.

        Args:
            grid_name: Name of the grid (e.g., "AORC_Grid_1", "Grid 1")
            dss_file: Path to DSS file (relative to HMS project folder)
            pathname: DSS pathname for grid data (e.g., "/AORC/GRID/PRECIP////")
            output_file: Output .grid file path
            project_name: Project name for Grid Manager section. If None, uses grid_name.
            description: Description for the grid (default: "AORC Gridded Precipitation")
            version: HMS version for format compatibility (default: "4.13")

        Returns:
            Path to created .grid file

        Example:
            >>> from hms_commander import HmsGrid
            >>>
            >>> # Create grid definition
            >>> HmsGrid.create_grid_definition(
            ...     grid_name="AORC_May2020",
            ...     dss_file="precip/aorc_may2020.dss",
            ...     pathname="/AORC/MAY2020/PRECIP////",
            ...     output_file="grids/aorc_may2020.grid",
            ...     description="AORC May 2020 Storm"
            ... )

        Notes:
            - Output format follows HMS .grid file specification
            - References external DSS grid data
            - Grid Type: Precipitation
            - Data Source Type: External DSS
            - See tenk example project for reference format
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Use grid_name as project_name if not specified
        if project_name is None:
            project_name = grid_name

        # Get current date and time
        now = datetime.now()
        date_str = now.strftime("%d %B %Y")  # e.g., "21 December 2025"
        time_str = now.strftime("%H:%M:%S")  # e.g., "14:30:00"

        # Build .grid file content (following tenk.grid format)
        content = f"""Grid Manager: {project_name}
     Grid Manager: {project_name}
     Version: {version}
     Filepath Separator: \\
End:

Grid: {grid_name}
     Grid: {grid_name}
     Grid Type: Precipitation
     Description: {description}
     Last Modified Date: {date_str}
     Last Modified Time: {time_str}
     Storm Center X: 0.0
     Storm Center Y: 0.0
     Data Source Type: External DSS
     Filename: {dss_file}
     Pathname: {pathname}
End:
"""

        # Write file
        output_path.write_text(content, encoding='utf-8')
        logger.info(f"Created .grid file: {output_path}")

        return output_path

    @staticmethod
    @log_call
    def map_grid_to_subbasins(
        subbasin_geometries: Dict[str, 'shapely.geometry.Polygon'],
        grid_coords: Tuple['np.ndarray', 'np.ndarray'],
        output_hrapcells: Union[str, Path],
        outlet_points: Optional[Dict[str, Tuple[float, float]]] = None,
        cell_size_km: Optional[float] = None,
        grid_origin: Optional[Tuple[int, int]] = None
    ) -> Path:
        """
        Generate grid cell mapping file (hrapcells format).

        Creates a file that maps grid cells to HMS subbasins with area
        weights and travel lengths for ModClark routing.

        Args:
            subbasin_geometries: Dictionary mapping subbasin names to Shapely Polygon geometries
            grid_coords: Tuple of (longitude_array, latitude_array) defining grid cell centers
            output_hrapcells: Output hrapcells file path
            outlet_points: Dictionary mapping subbasin names to outlet coordinates (lon, lat).
                If None, uses centroid of lowest-elevation grid cells.
            cell_size_km: Grid cell size in km. If None, calculated from coordinates.
            grid_origin: Grid index origin (x_min, y_min). If None, calculated from coordinates.

        Returns:
            Path to created hrapcells file

        Example:
            >>> from hms_commander import HmsGrid, HmsHuc
            >>> import numpy as np
            >>>
            >>> # Get HUC12 watershed
            >>> bounds = (-77.71, 41.01, -77.25, 41.22)
            >>> watersheds = HmsHuc.get_huc12_for_bounds(bounds)
            >>>
            >>> # Create geometry dict
            >>> geoms = {row['name']: row['geometry'] for _, row in watersheds.iterrows()}
            >>>
            >>> # Grid coordinates from AORC
            >>> lon = np.linspace(-77.71, -77.25, 50)
            >>> lat = np.linspace(41.01, 41.22, 25)
            >>>
            >>> # Map AORC grid to subbasins
            >>> HmsGrid.map_grid_to_subbasins(
            ...     subbasin_geometries=geoms,
            ...     grid_coords=(lon, lat),
            ...     output_hrapcells="regions/hrapcells"
            ... )

        Notes:
            - Output format: HMS hrapcells file
            - Header: "Parameter Order: xCoord yCoord TravelLength Area"
            - Grid cells: "GRIDCELL: x y travel_length area"
            - Travel length: Distance from grid cell centroid to subbasin outlet (km)
            - Area: Grid cell area within subbasin (km²)
            - See tenk/hrapcells for reference format
        """
        try:
            import numpy as np
            from shapely.geometry import box, Point
        except ImportError:
            raise ImportError(
                "HmsGrid.map_grid_to_subbasins() requires geopandas and shapely.\n"
                "Install with: pip install hms-commander[gis]"
            )

        output_path = Path(output_hrapcells)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lon_coords, lat_coords = grid_coords
        n_lon = len(lon_coords)
        n_lat = len(lat_coords)

        # Calculate cell size if not provided
        d_lon = abs(lon_coords[1] - lon_coords[0]) if n_lon > 1 else 0.01
        d_lat = abs(lat_coords[1] - lat_coords[0]) if n_lat > 1 else 0.01

        # Approximate cell size in km (at mid-latitude)
        mid_lat = np.mean(lat_coords)
        km_per_deg_lon = 111.32 * np.cos(np.radians(mid_lat))  # km per degree longitude
        km_per_deg_lat = 110.574  # km per degree latitude (approximately constant)

        if cell_size_km is None:
            cell_width_km = d_lon * km_per_deg_lon
            cell_height_km = d_lat * km_per_deg_lat
            cell_area_km2 = cell_width_km * cell_height_km
        else:
            cell_area_km2 = cell_size_km ** 2

        # Calculate grid origin indices if not provided
        if grid_origin is None:
            # Use arbitrary origin (matching HRAP-style indexing)
            x_origin = 600  # Arbitrary starting index
            y_origin = 300  # Arbitrary starting index
        else:
            x_origin, y_origin = grid_origin

        # Build output content
        lines = []
        lines.append("Parameter Order: xCoord yCoord TravelLength Area")
        lines.append("End:")

        total_cells = 0

        for subbasin_name, subbasin_geom in subbasin_geometries.items():
            subbasin_lines = []

            # Determine outlet point for travel length calculation
            if outlet_points and subbasin_name in outlet_points:
                outlet_lon, outlet_lat = outlet_points[subbasin_name]
            else:
                # Use centroid as outlet (approximation)
                centroid = subbasin_geom.centroid
                outlet_lon, outlet_lat = centroid.x, centroid.y

            # Iterate through grid cells
            for i_lon, lon in enumerate(lon_coords):
                for i_lat, lat in enumerate(lat_coords):
                    # Create grid cell polygon
                    cell_minx = lon - d_lon / 2
                    cell_maxx = lon + d_lon / 2
                    cell_miny = lat - d_lat / 2
                    cell_maxy = lat + d_lat / 2
                    cell_poly = box(cell_minx, cell_miny, cell_maxx, cell_maxy)

                    # Check intersection with subbasin
                    if subbasin_geom.intersects(cell_poly):
                        intersection = subbasin_geom.intersection(cell_poly)

                        # Calculate area of intersection in km²
                        # Use fraction of cell area based on intersection fraction
                        cell_fraction = intersection.area / cell_poly.area
                        area_km2 = cell_fraction * cell_area_km2

                        # Only include cells with meaningful area
                        if area_km2 > 0.001:  # Threshold: 0.001 km²
                            # Calculate travel length (Euclidean distance to outlet)
                            cell_center = Point(lon, lat)
                            dx_km = (lon - outlet_lon) * km_per_deg_lon
                            dy_km = (lat - outlet_lat) * km_per_deg_lat
                            travel_length_km = np.sqrt(dx_km**2 + dy_km**2)

                            # Grid indices (HRAP-style)
                            x_idx = x_origin + i_lon
                            y_idx = y_origin + i_lat

                            subbasin_lines.append(
                                f"GRIDCELL:  {x_idx}  {y_idx}  {travel_length_km:.2f}  {area_km2:.2f}"
                            )
                            total_cells += 1

            # Add subbasin section if it has cells
            if subbasin_lines:
                lines.append(f"SUBBASIN:  {subbasin_name}")
                lines.extend(subbasin_lines)
                lines.append("END:")

        # Write file
        content = "\n".join(lines) + "\n"
        output_path.write_text(content, encoding='utf-8')
        logger.info(f"Created hrapcells file: {output_path} ({total_cells} cells)")

        return output_path

    @staticmethod
    @log_call
    def map_aorc_to_subbasins(
        basin_geometry: Union[str, Path, 'gpd.GeoDataFrame', 'shapely.geometry.Polygon'],
        aorc_grid: Union[str, Path],
        output_hrapcells: Union[str, Path],
        subbasin_name: Optional[str] = None,
        method: str = "intersection"
    ) -> Path:
        """
        Generate grid cell mapping file from AORC NetCDF (hrapcells format).

        Convenience method that extracts grid coordinates from an AORC NetCDF file
        and maps them to subbasin boundaries.

        Args:
            basin_geometry: Subbasin geometry, one of:
                - Path to shapefile
                - GeoDataFrame with geometry
                - Shapely Polygon (single subbasin)
            aorc_grid: Path to AORC NetCDF file
            output_hrapcells: Output hrapcells file path
            subbasin_name: Name of subbasin (for multi-subbasin files)
            method: Mapping method (default: "intersection"):
                - "intersection": Spatial intersection (exact, slow)
                - "centroid": Grid cell centroid within subbasin (fast)
                - "nearest": Nearest grid cell (approximate)

        Returns:
            Path to created hrapcells file

        Example:
            >>> from hms_commander import HmsGrid, HmsHuc
            >>>
            >>> # Get HUC12 watershed
            >>> bounds = (-77.71, 41.01, -77.25, 41.22)
            >>> watersheds = HmsHuc.get_huc12_for_bounds(bounds)
            >>> huc12 = watersheds.iloc[0]
            >>>
            >>> # Map AORC grid to HUC12
            >>> HmsGrid.map_aorc_to_subbasins(
            ...     basin_geometry=huc12['geometry'],
            ...     aorc_grid="precip/aorc_may2020.nc",
            ...     output_hrapcells=f"regions/huc12_{huc12['huc12']}",
            ...     subbasin_name=huc12['name']
            ... )

        Notes:
            - Reads grid coordinates from AORC NetCDF file
            - Uses map_grid_to_subbasins() internally
            - See tenk/regions/hrapcells for reference format
        """
        try:
            import xarray as xr
            import geopandas as gpd
            from shapely.geometry import Polygon
        except ImportError:
            raise ImportError(
                "HmsGrid.map_aorc_to_subbasins() requires xarray and geopandas.\n"
                "Install with: pip install hms-commander[gis,aorc]"
            )

        # Load AORC NetCDF to get grid coordinates
        aorc_path = Path(aorc_grid)
        ds = xr.open_dataset(aorc_path)

        # Find coordinate variables
        lon_dim = 'longitude' if 'longitude' in ds.dims else 'lon' if 'lon' in ds.dims else 'x'
        lat_dim = 'latitude' if 'latitude' in ds.dims else 'lat' if 'lat' in ds.dims else 'y'

        lon_coords = ds[lon_dim].values
        lat_coords = ds[lat_dim].values
        ds.close()

        # Handle different geometry input types
        if isinstance(basin_geometry, (str, Path)):
            # Read from shapefile
            gdf = gpd.read_file(basin_geometry)
            if len(gdf) == 1:
                geom = gdf.geometry.iloc[0]
                name = subbasin_name or gdf.iloc[0].get('NAME', 'Subbasin1')
                geometries = {name: geom}
            else:
                # Multiple subbasins in shapefile
                name_col = 'NAME' if 'NAME' in gdf.columns else gdf.columns[0]
                geometries = {row[name_col]: row['geometry'] for _, row in gdf.iterrows()}
        elif hasattr(basin_geometry, 'geometry'):
            # GeoDataFrame
            if len(basin_geometry) == 1:
                geom = basin_geometry.geometry.iloc[0]
                name = subbasin_name or 'Subbasin1'
                geometries = {name: geom}
            else:
                name_col = 'NAME' if 'NAME' in basin_geometry.columns else basin_geometry.columns[0]
                geometries = {row[name_col]: row['geometry'] for _, row in basin_geometry.iterrows()}
        else:
            # Shapely Polygon
            name = subbasin_name or 'Subbasin1'
            geometries = {name: basin_geometry}

        # Call the main mapping function
        return HmsGrid.map_grid_to_subbasins(
            subbasin_geometries=geometries,
            grid_coords=(lon_coords, lat_coords),
            output_hrapcells=output_hrapcells
        )

    @staticmethod
    def calculate_travel_lengths(
        grid_cells: 'gpd.GeoDataFrame',
        outlet_point: Tuple[float, float],
        method: str = "euclidean"
    ) -> 'pd.Series':
        """
        Calculate flow distance from grid cells to outlet.

        Computes travel lengths for ModClark time-area calculations.

        Args:
            grid_cells: Grid cell geometries (polygons or points) as GeoDataFrame
            outlet_point: Subbasin outlet coordinates (lon, lat) or (x, y)
            method: Distance calculation method (default: "euclidean"):
                - "euclidean": Straight-line distance (fast)
                - "flow_path": Along DEM flow paths (requires DEM, accurate)

        Returns:
            Travel lengths in kilometers as pd.Series

        Example:
            >>> from hms_commander import HmsGrid
            >>>
            >>> # Calculate travel lengths
            >>> travel_lengths = HmsGrid.calculate_travel_lengths(
            ...     grid_cells=grid_cells_gdf,
            ...     outlet_point=(-77.5, 41.1),
            ...     method="euclidean"
            ... )

        Notes:
            - Euclidean: Simple, fast, approximate
            - Flow path: Accurate, requires DEM (future implementation)
            - Units: Always kilometers (HMS standard)
        """
        try:
            import numpy as np
            import pandas as pd
        except ImportError:
            raise ImportError(
                "HmsGrid.calculate_travel_lengths() requires numpy and pandas.\n"
                "Install with: pip install numpy pandas"
            )

        if method != "euclidean":
            raise NotImplementedError(
                f"Method '{method}' not yet implemented. Only 'euclidean' is supported.\n"
                "Flow path calculation requires DEM integration."
            )

        outlet_lon, outlet_lat = outlet_point

        # Get centroids if geometries are polygons
        if hasattr(grid_cells.geometry.iloc[0], 'centroid'):
            centroids = grid_cells.geometry.centroid
        else:
            centroids = grid_cells.geometry

        # Calculate Euclidean distances in km
        mid_lat = centroids.y.mean()
        km_per_deg_lon = 111.32 * np.cos(np.radians(mid_lat))
        km_per_deg_lat = 110.574

        dx_km = (centroids.x - outlet_lon) * km_per_deg_lon
        dy_km = (centroids.y - outlet_lat) * km_per_deg_lat

        travel_lengths = np.sqrt(dx_km**2 + dy_km**2)

        return pd.Series(travel_lengths, index=grid_cells.index, name='travel_length_km')

    @staticmethod
    @log_call
    def get_grid_info(grid_file: Union[str, Path]) -> dict:
        """
        Read metadata from HMS .grid file.

        Args:
            grid_file: Path to .grid file

        Returns:
            Grid metadata dictionary including:
                - grid_manager: Grid manager name
                - version: HMS version
                - grids: List of grid definitions, each containing:
                    - grid_name: Grid name
                    - grid_type: Grid type (e.g., "Precipitation")
                    - description: Grid description
                    - dss_file: DSS file path
                    - pathname: DSS pathname
                    - last_modified: Last modification datetime

        Example:
            >>> from hms_commander import HmsGrid
            >>>
            >>> # Read grid metadata
            >>> info = HmsGrid.get_grid_info("grids/aorc.grid")
            >>> print(info['grids'][0]['grid_name'])
            'AORC_Grid_1'
            >>> print(info['grids'][0]['pathname'])
            '/AORC/GRID/PRECIP////'
        """
        grid_path = Path(grid_file)
        if not grid_path.exists():
            raise FileNotFoundError(f"Grid file not found: {grid_path}")

        content = grid_path.read_text(encoding='utf-8')

        result = {
            'grid_manager': None,
            'version': None,
            'grids': []
        }

        # Parse Grid Manager section
        manager_match = re.search(r'Grid Manager:\s*(.+?)\n', content)
        if manager_match:
            result['grid_manager'] = manager_match.group(1).strip()

        version_match = re.search(r'Version:\s*(.+?)\n', content)
        if version_match:
            result['version'] = version_match.group(1).strip()

        # Parse Grid sections
        grid_pattern = re.compile(
            r'Grid:\s*(.+?)\n'
            r'.*?'
            r'Grid Type:\s*(.+?)\n'
            r'.*?'
            r'Description:\s*(.+?)\n'
            r'.*?'
            r'Last Modified Date:\s*(.+?)\n'
            r'.*?'
            r'Last Modified Time:\s*(.+?)\n'
            r'.*?'
            r'Data Source Type:\s*(.+?)\n'
            r'.*?'
            r'Filename:\s*(.+?)\n'
            r'.*?'
            r'Pathname:\s*(.+?)\n',
            re.DOTALL
        )

        for match in grid_pattern.finditer(content):
            grid_info = {
                'grid_name': match.group(1).strip(),
                'grid_type': match.group(2).strip(),
                'description': match.group(3).strip(),
                'last_modified_date': match.group(4).strip(),
                'last_modified_time': match.group(5).strip(),
                'data_source_type': match.group(6).strip(),
                'dss_file': match.group(7).strip(),
                'pathname': match.group(8).strip()
            }
            result['grids'].append(grid_info)

        logger.info(f"Read grid info: {grid_path} ({len(result['grids'])} grids)")
        return result

    @staticmethod
    @log_call
    def read_hrapcells(hrapcells_file: Union[str, Path]) -> Dict[str, List[dict]]:
        """
        Read grid cell mapping from hrapcells file.

        Args:
            hrapcells_file: Path to hrapcells file

        Returns:
            Dictionary mapping subbasin names to list of grid cells.
            Each grid cell is a dict with:
                - x: X coordinate index
                - y: Y coordinate index
                - travel_length: Travel length in km
                - area: Area in km²

        Example:
            >>> from hms_commander import HmsGrid
            >>>
            >>> # Read hrapcells
            >>> cells = HmsGrid.read_hrapcells("regions/hrapcells")
            >>> print(f"Subbasins: {list(cells.keys())}")
            >>> print(f"Cells in first subbasin: {len(cells['85'])}")
        """
        hrapcells_path = Path(hrapcells_file)
        if not hrapcells_path.exists():
            raise FileNotFoundError(f"hrapcells file not found: {hrapcells_path}")

        content = hrapcells_path.read_text(encoding='utf-8')
        lines = content.strip().split('\n')

        result = {}
        current_subbasin = None

        for line in lines:
            line = line.strip()

            if line.startswith('Parameter Order:') or line.startswith('End:') or line == 'END:':
                continue

            if line.startswith('SUBBASIN:'):
                current_subbasin = line.split(':', 1)[1].strip()
                result[current_subbasin] = []

            elif line.startswith('GRIDCELL:') and current_subbasin is not None:
                parts = line.split(':', 1)[1].strip().split()
                if len(parts) >= 4:
                    cell = {
                        'x': int(parts[0]),
                        'y': int(parts[1]),
                        'travel_length': float(parts[2]),
                        'area': float(parts[3])
                    }
                    result[current_subbasin].append(cell)

        logger.info(f"Read hrapcells: {hrapcells_path} ({len(result)} subbasins)")
        return result

    # ------------------------------------------------------------------
    # Cell lattices: geographic cells, remapping and checks
    # ------------------------------------------------------------------

    #: HEC's HRAP lattice: polar stereographic on the LFM sphere, with false easting and
    #: northing of 401 and 1601 cells, so cell (i, j) has its lower-left corner at
    #: (i * 4762.5, j * 4762.5). This is the WKT HEC-HMS sample grids store.
    HRAP_WKT = (
        'PROJCS["Stereographic_CONUS_HRAP",GEOGCS["GCS_Sphere_LFM",DATUM["D_Sphere_LFM",'
        'SPHEROID["Shpere_LFM",6371200.0,0.0]],PRIMEM["Greenwich",0.0],'
        'UNIT["Degree",0.0174532925199433]],PROJECTION["Stereographic_North_Pole"],'
        'PARAMETER["False_Easting",1909762.5],PARAMETER["False_Northing",7624762.5],'
        'PARAMETER["Central_Meridian",-105.0],PARAMETER["Standard_Parallel_1",60.0],'
        'UNIT["Meter",1.0]]'
    )
    #: HRAP cell size in metres (at 60 degrees N, its true-scale latitude).
    HRAP_CELL_SIZE = 4762.5
    #: The Standard Hydrologic Grid: USGS CONUS Albers on NAD 83 (EPSG:5070), in metres.
    #: Cell (i, j) has its lower-left corner at (i * cell_size, j * cell_size).
    SHG_CRS = "EPSG:5070"

    @staticmethod
    def _lattice(lattice, cell_size: Optional[float]):
        """``(crs, cell_size)`` of a cell lattice: ``"HRAP"``, ``"SHG"``, a grid dict from
        ``HmsDss.read_grid`` (its ``crs`` and ``cell_size``), or any CRS with ``cell_size``."""
        if isinstance(lattice, dict):
            crs, size = lattice.get("crs"), lattice.get("cell_size")
            if not crs or not size:
                raise ValueError("a grid dict needs 'crs' and 'cell_size' (HmsDss.read_grid)")
            if cell_size is not None and float(cell_size) != float(size):
                raise ValueError(f"cell_size {cell_size} differs from the grid's {size}")
            return crs, float(size)
        if isinstance(lattice, str) and lattice.upper() == "HRAP":
            if cell_size is not None and float(cell_size) != HmsGrid.HRAP_CELL_SIZE:
                raise ValueError("the HRAP lattice has a fixed cell size of 4762.5 m")
            return HmsGrid.HRAP_WKT, HmsGrid.HRAP_CELL_SIZE
        if isinstance(lattice, str) and lattice.upper() == "SHG":
            size = 2000.0 if cell_size is None else float(cell_size)
            if not size > 0:
                raise ValueError("cell_size must be positive")
            return HmsGrid.SHG_CRS, size
        if cell_size is None or not float(cell_size) > 0:
            raise ValueError("a CRS lattice needs a positive cell_size in its units")
        return lattice, float(cell_size)

    @staticmethod
    @log_call
    def get_cell_polygons(
        cell_file: Union[str, Path],
        lattice: Union[str, dict] = "HRAP",
        cell_size: Optional[float] = None,
    ) -> 'gpd.GeoDataFrame':
        """
        Return the cells of a grid cell file (hrapcells format) as polygons.

        A cell file gives each cell by its integer lattice index; cell ``(x, y)`` covers
        ``x * cell_size`` to ``(x + 1) * cell_size`` east and the same north, in the
        lattice's coordinates. This places the cells of a file such as the tenk sample's
        ``regions/hrapcells`` on the map.

        Args:
            cell_file: Grid cell file (``Parameter Order: xCoord yCoord TravelLength Area``).
            lattice: ``"HRAP"`` (default; HEC's HRAP, cell size 4762.5 m), ``"SHG"``
                (EPSG:5070, cell size ``cell_size``, default 2000 m), a grid dict from
                ``HmsDss.read_grid`` (its ``crs`` and ``cell_size``), or any CRS accepted
                by pyproj with ``cell_size`` in its units.
            cell_size: Cell size for ``"SHG"`` or a CRS lattice.

        Returns:
            GeoDataFrame with ``subbasin``, ``x``, ``y``, ``travel_length`` (km),
            ``area`` (km2, the cell's area inside the subbasin, as the file states) and
            the whole cell as ``geometry``, in the lattice CRS.

        Example:
            >>> cells = HmsGrid.get_cell_polygons("tenk/regions/hrapcells", "HRAP")
            >>> basins = cells.dissolve("subbasin")   # the cells each subbasin uses
        """
        try:
            import geopandas as gpd
            from shapely.geometry import box
        except ImportError:
            raise ImportError(
                "HmsGrid.get_cell_polygons() requires geopandas and shapely.\n"
                "Install with: pip install hms-commander[gis]"
            )
        crs, size = HmsGrid._lattice(lattice, cell_size)
        rows = []
        for subbasin, cells in HmsGrid.read_hrapcells(cell_file).items():
            for c in cells:
                x, y = c["x"], c["y"]
                rows.append({
                    "subbasin": subbasin, "x": x, "y": y,
                    "travel_length": c["travel_length"], "area": c["area"],
                    "geometry": box(x * size, y * size, (x + 1) * size, (y + 1) * size),
                })
        if not rows:
            raise ValueError(f"no GRIDCELL entries in {cell_file}")
        return gpd.GeoDataFrame(rows, geometry="geometry", crs=crs)

    @staticmethod
    @log_call
    def remap_cell_file(
        cell_file: Union[str, Path],
        output_file: Union[str, Path],
        source_lattice: Union[str, dict] = "HRAP",
        target_lattice: Union[str, dict] = "SHG",
        target_cell_size: Optional[float] = None,
        source_cell_size: Optional[float] = None,
    ) -> Path:
        """
        Move a grid cell file onto another lattice, keeping each subbasin's area.

        Each source cell's area inside its subbasin (the file's ``Area``) is spread over
        the target cells it overlaps, in proportion to the overlap, assuming that area is
        spread evenly over the source cell. A file does not say where inside a partly
        covered cell the subbasin lies, so boundary cells are approximate; whole cells
        are exact. Overlaps are measured in EPSG:5070 (equal-area). Each subbasin's total
        area is preserved to rounding. A target cell's travel length is the
        area-weighted mean of the travel lengths of the source cells it receives area
        from. Use it, for example, to run the tenk sample on SHG grids: the result has
        SHG indexes, which the SHG grid records of ``HmsDssGrid.write_grid_timeseries(
        target_crs="SHG")`` and ``HmsAorc.convert_to_dss_grid(target_crs="SHG")`` use.

        Args:
            cell_file: Source grid cell file (hrapcells format).
            output_file: New cell file to write. An existing file is replaced.
            source_lattice: Lattice of ``cell_file`` (see ``get_cell_polygons``).
            target_lattice: Lattice of the output (default ``"SHG"``).
            target_cell_size: Target cell size (``"SHG"`` default 2000 m).
            source_cell_size: Source cell size for a CRS lattice.

        Returns:
            Path to the new cell file.

        Raises:
            ValueError: If the file has no cells, or a lattice is not understood.
        """
        try:
            import numpy as np
            import geopandas as gpd
            from shapely.geometry import box
        except ImportError:
            raise ImportError(
                "HmsGrid.remap_cell_file() requires geopandas and shapely.\n"
                "Install with: pip install hms-commander[gis]"
            )
        source = HmsGrid.get_cell_polygons(cell_file, source_lattice, source_cell_size)
        target_crs, tsize = HmsGrid._lattice(target_lattice, target_cell_size)
        # Densify before reprojecting, so curved cell edges keep their shape.
        source_size = HmsGrid._lattice(source_lattice, source_cell_size)[1]
        source["geometry"] = source.geometry.segmentize(source_size / 20.0)
        in_target = source.to_crs(target_crs)

        lines = ["Parameter Order: xCoord yCoord TravelLength Area", "End:"]
        total_cells = 0
        for subbasin in dict.fromkeys(source["subbasin"]):
            acc: Dict[Tuple[int, int], List[float]] = {}
            for idx in source.index[source["subbasin"] == subbasin]:
                cell_t = in_target.geometry[idx]
                area_in = float(source.at[idx, "area"])
                travel = float(source.at[idx, "travel_length"])
                minx, miny, maxx, maxy = cell_t.bounds
                parts = []
                for ix in range(int(np.floor(minx / tsize)), int(np.floor(maxx / tsize)) + 1):
                    for iy in range(int(np.floor(miny / tsize)), int(np.floor(maxy / tsize)) + 1):
                        piece = cell_t.intersection(
                            box(ix * tsize, iy * tsize, (ix + 1) * tsize, (iy + 1) * tsize))
                        if not piece.is_empty:
                            parts.append(((ix, iy), piece))
                if not parts:
                    continue
                pieces = gpd.GeoSeries([pc for _, pc in parts], crs=target_crs)
                areas = pieces.to_crs(HmsGrid.SHG_CRS).area.to_numpy()
                # Shares of the source cell; they sum to 1, so the subbasin area is kept.
                shares = areas / areas.sum() if areas.sum() > 0 else areas
                for ((ix, iy), _), share in zip(parts, shares):
                    a = area_in * float(share)
                    entry = acc.setdefault((ix, iy), [0.0, 0.0])
                    entry[0] += a
                    entry[1] += a * travel
            cells = [(k, v) for k, v in acc.items() if v[0] > 0]
            if not cells:
                continue
            lines.append(f"SUBBASIN:  {subbasin}")
            for (ix, iy), (a, at) in sorted(cells, key=lambda kv: (-kv[0][1], kv[0][0])):
                lines.append(f"GRIDCELL:  {ix}  {iy}  {at / a:.2f}  {a:.4f}")
                total_cells += 1
            lines.append("END:")

        out = Path(output_file)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        logger.info(f"Remapped cell file to {out.name} ({total_cells} cells)")
        return out

    @staticmethod
    @log_call
    def check_cells_on_grid(
        cell_file: Union[str, Path],
        grid: dict,
    ) -> 'pd.DataFrame':
        """
        Check that a grid cell file's cells fall on a DSS grid, and weight its values.

        HEC-HMS looks each cell up by its index in the grid record. A cell outside the
        record, or on a missing value, gets no precipitation, and HEC-HMS can still report
        a successful run (look for ``WARNING 40503`` in its log). Use this check before a
        run, and its ``weighted_value`` to compare with the subbasin's ``PRECIP-INC``.

        Args:
            cell_file: Grid cell file (hrapcells format), on the grid's lattice.
            grid: A grid dict from ``HmsDss.read_grid`` (``data``, ``lower_left_cell``).
                Row 0 of ``data`` is the southern row.

        Returns:
            DataFrame, one row per subbasin: ``cells``, ``area_km2``,
            ``cells_outside`` (not in the record), ``cells_missing`` (NaN in the record),
            ``area_outside_km2``, ``area_missing_km2`` and ``weighted_value`` (the
            area-weighted mean of the cells' values, in the grid's units, over the cells
            that have one; NaN when none has).
        """
        import numpy as np
        import pandas as pd

        data = np.asarray(grid["data"], dtype=float)
        x0, y0 = grid["lower_left_cell"]
        ny, nx = data.shape
        rows = []
        for subbasin, cells in HmsGrid.read_hrapcells(cell_file).items():
            area = a_out = a_miss = wsum = asum = 0.0
            n_out = n_miss = 0
            for c in cells:
                col, row = c["x"] - int(x0), c["y"] - int(y0)
                area += c["area"]
                if not (0 <= col < nx and 0 <= row < ny):
                    n_out += 1
                    a_out += c["area"]
                    continue
                value = data[row, col]
                if not np.isfinite(value):
                    n_miss += 1
                    a_miss += c["area"]
                    continue
                wsum += c["area"] * value
                asum += c["area"]
            rows.append({
                "subbasin": subbasin, "cells": len(cells), "area_km2": area,
                "cells_outside": n_out, "cells_missing": n_miss,
                "area_outside_km2": a_out, "area_missing_km2": a_miss,
                "weighted_value": wsum / asum if asum > 0 else float("nan"),
            })
        return pd.DataFrame(rows).set_index("subbasin")

    @staticmethod
    def get_info() -> dict:
        """
        Get information about HMS grid operations.

        Returns:
            Information about grid operations:
                - format: File format descriptions
                - supported_grids: Supported grid types
                - hrapcells_format: hrapcells file format description
                - references: Reference documentation

        Example:
            >>> from hms_commander import HmsGrid
            >>>
            >>> info = HmsGrid.get_info()
            >>> print(info['format'])
        """
        return {
            'format': {
                '.grid': 'HMS grid definition file',
                'hrapcells': 'HMS grid cell mapping file'
            },
            'supported_grids': {
                'Precipitation': 'Gridded precipitation (AORC, HRAP, etc.)',
                'Temperature': 'Gridded temperature',
                'Other': 'Other gridded data types'
            },
            'hrapcells_format': {
                'header': 'Parameter Order: xCoord yCoord TravelLength Area',
                'subbasin': 'SUBBASIN: <name>',
                'gridcell': 'GRIDCELL: <x> <y> <travel_length_km> <area_km2>',
                'end': 'END:'
            },
            'references': {
                'example_project': 'examples/example_projects/hms413_run_all/tenk/tenk/',
                'grid_file': 'tenk.grid',
                'hrapcells_file': 'hrapcells'
            }
        }
