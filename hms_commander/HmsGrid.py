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

        Parameters
        ----------
        grid_name : str
            Name of the grid (e.g., "AORC_Grid_1", "Grid 1")
        dss_file : str or Path
            Path to DSS file (relative to HMS project folder)
        pathname : str
            DSS pathname for grid data (e.g., "/AORC/GRID/PRECIP////")
        output_file : str or Path
            Output .grid file path
        project_name : str, optional
            Project name for Grid Manager section. If None, uses grid_name.
        description : str, default "AORC Gridded Precipitation"
            Description for the grid
        version : str, default "4.13"
            HMS version for format compatibility

        Returns
        -------
        Path
            Path to created .grid file

        Examples
        --------
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

        Notes
        -----
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

        Parameters
        ----------
        subbasin_geometries : Dict[str, Polygon]
            Dictionary mapping subbasin names to Shapely Polygon geometries
        grid_coords : Tuple[np.ndarray, np.ndarray]
            Tuple of (longitude_array, latitude_array) defining grid cell centers
        output_hrapcells : str or Path
            Output hrapcells file path
        outlet_points : Dict[str, Tuple[float, float]], optional
            Dictionary mapping subbasin names to outlet coordinates (lon, lat).
            If None, uses centroid of lowest-elevation grid cells.
        cell_size_km : float, optional
            Grid cell size in km. If None, calculated from coordinates.
        grid_origin : Tuple[int, int], optional
            Grid index origin (x_min, y_min). If None, calculated from coordinates.

        Returns
        -------
        Path
            Path to created hrapcells file

        Examples
        --------
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

        Notes
        -----
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

        Parameters
        ----------
        basin_geometry : str, Path, GeoDataFrame, or Polygon
            Subbasin geometry, one of:
                - Path to shapefile
                - GeoDataFrame with geometry
                - Shapely Polygon (single subbasin)
        aorc_grid : str or Path
            Path to AORC NetCDF file
        output_hrapcells : str or Path
            Output hrapcells file path
        subbasin_name : str, optional
            Name of subbasin (for multi-subbasin files)
        method : str, default "intersection"
            Mapping method:
                - "intersection": Spatial intersection (exact, slow)
                - "centroid": Grid cell centroid within subbasin (fast)
                - "nearest": Nearest grid cell (approximate)

        Returns
        -------
        Path
            Path to created hrapcells file

        Examples
        --------
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

        Notes
        -----
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

        Parameters
        ----------
        grid_cells : GeoDataFrame
            Grid cell geometries (polygons or points)
        outlet_point : Tuple[float, float]
            Subbasin outlet coordinates (lon, lat) or (x, y)
        method : str, default "euclidean"
            Distance calculation method:
                - "euclidean": Straight-line distance (fast)
                - "flow_path": Along DEM flow paths (requires DEM, accurate)

        Returns
        -------
        pd.Series
            Travel lengths in kilometers

        Examples
        --------
        >>> from hms_commander import HmsGrid
        >>>
        >>> # Calculate travel lengths
        >>> travel_lengths = HmsGrid.calculate_travel_lengths(
        ...     grid_cells=grid_cells_gdf,
        ...     outlet_point=(-77.5, 41.1),
        ...     method="euclidean"
        ... )

        Notes
        -----
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

        Parameters
        ----------
        grid_file : str or Path
            Path to .grid file

        Returns
        -------
        dict
            Grid metadata including:
                - grid_manager: Grid manager name
                - version: HMS version
                - grids: List of grid definitions, each containing:
                    - grid_name: Grid name
                    - grid_type: Grid type (e.g., "Precipitation")
                    - description: Grid description
                    - dss_file: DSS file path
                    - pathname: DSS pathname
                    - last_modified: Last modification datetime

        Examples
        --------
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

        Parameters
        ----------
        hrapcells_file : str or Path
            Path to hrapcells file

        Returns
        -------
        Dict[str, List[dict]]
            Dictionary mapping subbasin names to list of grid cells.
            Each grid cell is a dict with:
                - x: X coordinate index
                - y: Y coordinate index
                - travel_length: Travel length in km
                - area: Area in km²

        Examples
        --------
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

    @staticmethod
    def get_info() -> dict:
        """
        Get information about HMS grid operations.

        Returns
        -------
        dict
            Information about grid operations:
                - format: File format descriptions
                - supported_grids: Supported grid types
                - hrapcells_format: hrapcells file format description
                - references: Reference documentation

        Examples
        --------
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
