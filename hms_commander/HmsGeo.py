"""
HmsGeo - Geospatial data extraction from HEC-HMS model files

This module provides functionality to extract GIS data from HEC-HMS model files
and export them to standard geospatial formats (GeoJSON, Shapefile, etc.).

All methods in this class are static and designed to be used without instantiation.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Union

from .LoggingConfig import get_logger
from .Decorators import log_call

logger = get_logger(__name__)


class HmsGeo:
    """
    A class for extracting geospatial data from HEC-HMS model files.

    Supports extraction from:
    - .basin files: Subbasins, junctions, reaches with attributes
    - .geo files: Coordinate data for model elements
    - .map files: Detailed boundary polygons and river polylines

    All methods in this class are static and designed to be used without instantiation.
    """

    # TODO: Audit all files referencing EPSG:2278 (HmsGrid.py, HmsAorc.py, etc.)
    # to make them CRS-agnostic. See _detect_crs() in HmsPrj for auto-detection.

    @staticmethod
    def parse_geo_file(geo_path: Union[str, Path]) -> Dict[str, Dict[str, float]]:
        """
        Parse HEC-HMS .geo file to extract subbasin coordinates.

        Args:
            geo_path: Path to the .geo file

        Returns:
            Dictionary mapping subbasin names to {x, y} coordinates

        Example:
            >>> coords = HmsGeo.parse_geo_file("model.geo")
            >>> print(coords["A100A"])
            {'x': 3084918.3, 'y': 13771479.6}
        """
        geo_path = Path(geo_path)
        logger.info(f"Parsing GEO file: {geo_path}")

        coordinates = {}
        current_subbasin = None

        with open(geo_path, 'r') as f:
            for line in f:
                line = line.strip()

                if line.startswith('Subbasin:'):
                    current_subbasin = line.split(':', 1)[1].strip()
                    coordinates[current_subbasin] = {}

                elif line.startswith('Canvas X:') and current_subbasin:
                    x_value = line.split(':', 1)[1].strip()
                    coordinates[current_subbasin]['x'] = float(x_value)

                elif line.startswith('Canvas Y:') and current_subbasin:
                    y_value = line.split(':', 1)[1].strip()
                    coordinates[current_subbasin]['y'] = float(y_value)

                elif line.startswith('End:'):
                    current_subbasin = None

        logger.info(f"Found {len(coordinates)} subbasins in GEO file")
        return coordinates

    @staticmethod
    @log_call
    def get_project_bounds(geo_path: Union[str, Path],
                          crs_epsg: str = "EPSG:2278") -> Tuple[float, float, float, float]:
        """
        Get project bounding box from .geo file coordinates.

        Args:
            geo_path: Path to the .geo file
            crs_epsg: CRS of the coordinates (e.g. "EPSG:2278")

        Returns:
            Tuple of (minx, miny, maxx, maxy) in project CRS

        Example:
            >>> bounds = HmsGeo.get_project_bounds("model.geo")
            >>> minx, miny, maxx, maxy = bounds
            >>> print(f"Extent: {maxx - minx:.1f} x {maxy - miny:.1f} feet")
        """
        geo_path = Path(geo_path)

        # Parse coordinates from .geo file
        coordinates = HmsGeo.parse_geo_file(geo_path)

        if not coordinates:
            raise ValueError(f"No coordinates found in {geo_path}")

        # Calculate bounding box
        x_coords = [coord['x'] for coord in coordinates.values() if 'x' in coord]
        y_coords = [coord['y'] for coord in coordinates.values() if 'y' in coord]

        if not x_coords or not y_coords:
            raise ValueError(f"No valid coordinates found in {geo_path}")

        minx = min(x_coords)
        maxx = max(x_coords)
        miny = min(y_coords)
        maxy = max(y_coords)

        logger.info(f"Project bounds: ({minx:.1f}, {miny:.1f}) to ({maxx:.1f}, {maxy:.1f})")
        logger.info(f"  Extent: {maxx - minx:.1f} x {maxy - miny:.1f} feet")

        return (minx, miny, maxx, maxy)

    @staticmethod
    @log_call
    def get_project_centroid_latlon(geo_path: Union[str, Path],
                                    crs_epsg: str = "EPSG:2278") -> Tuple[float, float]:
        """
        Get project centroid in WGS84 lat/lon coordinates.

        This follows the ras-commander pattern of get_project_bounds_latlon(),
        calculating the geographic center of the project for use with web services
        like NOAA Atlas 14 API.

        Args:
            geo_path: Path to the .geo file
            crs_epsg: CRS of the coordinates (e.g. "EPSG:2278")

        Returns:
            Tuple of (latitude, longitude) in decimal degrees (WGS84, EPSG:4326)

        Raises:
            ImportError: If pyproj is not installed
            ValueError: If no coordinates found or transformation fails

        Example:
            >>> lat, lon = HmsGeo.get_project_centroid_latlon("model.geo")
            >>> print(f"Project center: {lat:.4f}°N, {abs(lon):.4f}°W")
        """
        try:
            from pyproj import Transformer
        except ImportError:
            raise ImportError(
                "pyproj is required for coordinate transformation. "
                "Install with: pip install pyproj"
            )

        geo_path = Path(geo_path)

        # Get project bounds in project CRS
        minx, miny, maxx, maxy = HmsGeo.get_project_bounds(geo_path, crs_epsg)

        # Calculate centroid in project CRS
        centroid_x = (minx + maxx) / 2.0
        centroid_y = (miny + maxy) / 2.0

        logger.info(f"Project centroid (project CRS): ({centroid_x:.1f}, {centroid_y:.1f})")

        # Transform to WGS84 (EPSG:4326)
        transformer = Transformer.from_crs(crs_epsg, "EPSG:4326", always_xy=True)
        lon, lat = transformer.transform(centroid_x, centroid_y)

        logger.info(f"Project centroid (WGS84): {lat:.6f}°N, {abs(lon):.6f}°W")

        return (lat, lon)

    @staticmethod
    @log_call
    def get_subbasin_centroid(map_path: Union[str, Path],
                              subbasin_index: int,
                              crs_epsg: str) -> Tuple[float, float]:
        """
        Get the geometric centroid of a single boundary polygon in project CRS.

        Parses the .map file and builds a shapely Polygon from the boundary
        at the given index, then returns its centroid coordinates.

        Args:
            map_path: Path to the .map file
            subbasin_index: Index into the boundaries list from parse_map_file()
            crs_epsg: Project CRS (for documentation/logging; coords returned in native CRS)

        Returns:
            Tuple of (x, y) in project CRS

        Raises:
            ImportError: If shapely is not installed
            IndexError: If subbasin_index is out of range
            ValueError: If boundary has insufficient coordinates

        Example:
            >>> x, y = HmsGeo.get_subbasin_centroid("model.map", 0, "EPSG:2278")
            >>> print(f"Centroid: ({x:.1f}, {y:.1f})")
        """
        try:
            from shapely.geometry import Polygon
        except ImportError:
            raise ImportError(
                "shapely is required for centroid calculations. "
                "Install with: pip install shapely"
            )

        map_path = Path(map_path)
        logger.info(f"Computing centroid for boundary index {subbasin_index} from {map_path}")

        map_data = HmsGeo.parse_map_file(map_path)
        boundaries = map_data['boundaries']

        if subbasin_index < 0 or subbasin_index >= len(boundaries):
            raise IndexError(
                f"subbasin_index {subbasin_index} out of range "
                f"(0-{len(boundaries) - 1})"
            )

        coords = boundaries[subbasin_index]['coordinates']
        if len(coords) < 3:
            raise ValueError(
                f"Boundary {subbasin_index} has only {len(coords)} coordinates "
                f"(need at least 3 for a polygon)"
            )

        poly = Polygon(coords)
        centroid = poly.centroid
        x, y = centroid.x, centroid.y

        logger.info(f"Boundary {subbasin_index} centroid ({crs_epsg}): ({x:.1f}, {y:.1f})")
        return (x, y)

    @staticmethod
    @log_call
    def get_subbasin_centroids_latlon(map_path: Union[str, Path],
                                      crs_epsg: str) -> Dict[int, Tuple[float, float]]:
        """
        Get centroids of all boundary polygons, transformed to WGS84.

        Parses the .map file, builds a shapely Polygon for each boundary,
        computes centroids, and transforms them from the project CRS to
        EPSG:4326 (WGS84 lat/lon).

        Args:
            map_path: Path to the .map file
            crs_epsg: Source CRS for transformation (e.g. "EPSG:2278")

        Returns:
            Dictionary mapping boundary index to (lat, lon) in decimal degrees

        Raises:
            ImportError: If shapely or pyproj is not installed
            ValueError: If no boundaries found

        Example:
            >>> centroids = HmsGeo.get_subbasin_centroids_latlon("model.map", "EPSG:2278")
            >>> for idx, (lat, lon) in centroids.items():
            ...     print(f"Boundary {idx}: {lat:.6f}, {lon:.6f}")
        """
        try:
            from shapely.geometry import Polygon
        except ImportError:
            raise ImportError(
                "shapely is required for centroid calculations. "
                "Install with: pip install shapely"
            )
        try:
            from pyproj import Transformer
        except ImportError:
            raise ImportError(
                "pyproj is required for coordinate transformation. "
                "Install with: pip install pyproj"
            )

        map_path = Path(map_path)
        logger.info(f"Computing all boundary centroids from {map_path} (CRS: {crs_epsg})")

        map_data = HmsGeo.parse_map_file(map_path)
        boundaries = map_data['boundaries']

        if not boundaries:
            raise ValueError(f"No boundaries found in {map_path}")

        transformer = Transformer.from_crs(crs_epsg, "EPSG:4326", always_xy=True)
        centroids = {}

        for idx, boundary in enumerate(boundaries):
            coords = boundary['coordinates']
            if len(coords) < 3:
                logger.warning(f"Skipping boundary {idx} - only {len(coords)} coordinates")
                continue

            poly = Polygon(coords)
            c = poly.centroid
            lon, lat = transformer.transform(c.x, c.y)
            centroids[idx] = (lat, lon)

        logger.info(f"Computed {len(centroids)} boundary centroids in WGS84")
        return centroids

    @staticmethod
    @log_call
    def get_combined_centroid_latlon(map_path: Union[str, Path],
                                     crs_epsg: str) -> Tuple[float, float]:
        """
        Get the centroid of the union of all boundary polygons in WGS84.

        Unions all boundary polygons into a single geometry, computes its
        centroid, and transforms from the project CRS to EPSG:4326.

        Args:
            map_path: Path to the .map file
            crs_epsg: Source CRS for transformation (e.g. "EPSG:2278")

        Returns:
            Tuple of (lat, lon) in decimal degrees (WGS84)

        Raises:
            ImportError: If shapely or pyproj is not installed
            ValueError: If no valid boundaries found

        Example:
            >>> lat, lon = HmsGeo.get_combined_centroid_latlon("model.map", "EPSG:2278")
            >>> print(f"Combined center: {lat:.6f}, {lon:.6f}")
        """
        try:
            from shapely.geometry import Polygon
            from shapely.ops import unary_union
        except ImportError:
            raise ImportError(
                "shapely is required for centroid calculations. "
                "Install with: pip install shapely"
            )
        try:
            from pyproj import Transformer
        except ImportError:
            raise ImportError(
                "pyproj is required for coordinate transformation. "
                "Install with: pip install pyproj"
            )

        map_path = Path(map_path)
        logger.info(f"Computing combined centroid from {map_path} (CRS: {crs_epsg})")

        map_data = HmsGeo.parse_map_file(map_path)
        boundaries = map_data['boundaries']

        if not boundaries:
            raise ValueError(f"No boundaries found in {map_path}")

        polygons = []
        for idx, boundary in enumerate(boundaries):
            coords = boundary['coordinates']
            if len(coords) < 3:
                logger.warning(f"Skipping boundary {idx} - only {len(coords)} coordinates")
                continue
            polygons.append(Polygon(coords))

        if not polygons:
            raise ValueError(f"No valid polygons (3+ coordinates) found in {map_path}")

        combined = unary_union(polygons)
        centroid = combined.centroid

        transformer = Transformer.from_crs(crs_epsg, "EPSG:4326", always_xy=True)
        lon, lat = transformer.transform(centroid.x, centroid.y)

        logger.info(f"Combined centroid (WGS84): {lat:.6f}°N, {abs(lon):.6f}°W")
        return (lat, lon)

    @staticmethod
    def parse_basin_file(basin_path: Union[str, Path]) -> Tuple[Dict[str, Dict[str, Any]],
                                                                  Dict[str, Dict[str, Any]],
                                                                  Dict[str, Dict[str, Any]]]:
        """
        Parse HEC-HMS .basin file to extract all model elements.

        Args:
            basin_path: Path to the .basin file

        Returns:
            Tuple of (subbasins, junctions, reaches) dictionaries

        Example:
            >>> subs, juncs, reachs = HmsGeo.parse_basin_file("model.basin")
            >>> print(f"Found {len(subs)} subbasins")
        """
        basin_path = Path(basin_path)
        logger.info(f"Parsing basin file: {basin_path}")

        subbasins = {}
        junctions = {}
        reaches = {}

        current_element = None
        current_type = None

        with open(basin_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()

                # Identify element type
                if line.startswith('Subbasin:'):
                    current_element = line.split(':', 1)[1].strip()
                    current_type = 'subbasin'
                    subbasins[current_element] = {'type': 'Subbasin'}

                elif line.startswith('Junction:'):
                    current_element = line.split(':', 1)[1].strip()
                    current_type = 'junction'
                    junctions[current_element] = {'type': 'Junction'}

                elif line.startswith('Reach:'):
                    current_element = line.split(':', 1)[1].strip()
                    current_type = 'reach'
                    reaches[current_element] = {'type': 'Reach'}

                # Parse attributes based on element type
                elif current_element and current_type:
                    data_dict = None
                    if current_type == 'subbasin':
                        data_dict = subbasins[current_element]
                    elif current_type == 'junction':
                        data_dict = junctions[current_element]
                    elif current_type == 'reach':
                        data_dict = reaches[current_element]

                    if data_dict is not None:
                        HmsGeo._parse_element_attributes(line, data_dict)

                    if line.startswith('End:') and not line.startswith('End '):
                        current_element = None
                        current_type = None

        logger.info(f"Found {len(subbasins)} subbasins, {len(junctions)} junctions, "
                   f"{len(reaches)} reaches")
        return subbasins, junctions, reaches

    @staticmethod
    def _parse_element_attributes(line: str, data_dict: Dict[str, Any]) -> None:
        """
        Parse attribute line from basin file into data dictionary.

        Args:
            line: Line from basin file
            data_dict: Dictionary to store parsed attributes
        """
        if line.startswith('Canvas X:'):
            x_value = line.split(':', 1)[1].strip()
            data_dict['x'] = float(x_value)

        elif line.startswith('Canvas Y:'):
            y_value = line.split(':', 1)[1].strip()
            data_dict['y'] = float(y_value)

        elif line.startswith('From Canvas X:'):
            from_x = line.split(':', 1)[1].strip()
            data_dict['from_x'] = float(from_x)

        elif line.startswith('From Canvas Y:'):
            from_y = line.split(':', 1)[1].strip()
            data_dict['from_y'] = float(from_y)

        elif line.startswith('Area:'):
            area = line.split(':', 1)[1].strip()
            data_dict['area'] = float(area)

        elif line.startswith('Downstream:'):
            downstream = line.split(':', 1)[1].strip()
            data_dict['downstream'] = downstream

        elif line.startswith('Percent Impervious Area:'):
            impervious = line.split(':', 1)[1].strip()
            data_dict['percent_impervious'] = float(impervious)

        elif line.startswith('Time of Concentration:'):
            tc = line.split(':', 1)[1].strip()
            data_dict['time_of_concentration'] = float(tc)

        elif line.startswith('Description:'):
            desc = line.split(':', 1)[1].strip()
            data_dict['description'] = desc

    @staticmethod
    def parse_map_file(map_path: Union[str, Path]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse HEC-HMS .map file to extract boundary polygons and river polylines.

        Args:
            map_path: Path to the .map file

        Returns:
            Dictionary with 'boundaries' and 'rivers' lists of features

        Example:
            >>> data = HmsGeo.parse_map_file("model.map")
            >>> print(f"Boundaries: {len(data['boundaries'])}")
            >>> print(f"Rivers: {len(data['rivers'])}")
        """
        map_path = Path(map_path)
        logger.info(f"Parsing MAP file: {map_path}")

        boundaries = []
        rivers = []

        current_map_type = None
        current_segment_type = None
        current_coordinates = []

        with open(map_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()

                if not line:
                    continue

                # Identify map type
                if line.startswith('MapGeo:'):
                    map_type = line.split(':', 1)[1].strip()
                    current_map_type = map_type
                    logger.debug(f"Processing {map_type}...")
                    continue

                # Identify segment type (closed=polygon, open=polyline)
                if line.startswith('MapSegment:'):
                    # Save previous segment if it exists
                    if current_coordinates and current_map_type:
                        feature = {
                            'coordinates': current_coordinates.copy(),
                            'segment_type': current_segment_type,
                            'map_type': current_map_type
                        }

                        if current_map_type == 'BoundaryMap':
                            boundaries.append(feature)
                        elif current_map_type == 'RiverMap':
                            rivers.append(feature)

                    # Start new segment
                    segment_type = line.split(':', 1)[1].strip()
                    current_segment_type = segment_type
                    current_coordinates = []
                    continue

                # Parse coordinate pairs
                if ',' in line:
                    try:
                        parts = line.split(',')
                        if len(parts) == 2:
                            x = float(parts[0].strip())
                            y = float(parts[1].strip())
                            current_coordinates.append([x, y])
                    except (ValueError, IndexError):
                        # Skip invalid coordinate lines (common in HMS map files)
                        continue

        # Don't forget the last segment
        if current_coordinates and current_map_type:
            feature = {
                'coordinates': current_coordinates.copy(),
                'segment_type': current_segment_type,
                'map_type': current_map_type
            }

            if current_map_type == 'BoundaryMap':
                boundaries.append(feature)
            elif current_map_type == 'RiverMap':
                rivers.append(feature)

        logger.info(f"Found {len(boundaries)} boundaries, {len(rivers)} rivers")
        return {
            'boundaries': boundaries,
            'rivers': rivers
        }

    @staticmethod
    def create_geojson_subbasins(subbasins: Dict[str, Dict[str, Any]],
                                 output_path: Union[str, Path],
                                 crs_epsg: Optional[str] = None) -> None:
        """
        Create GeoJSON file from subbasin point data.

        Args:
            subbasins: Dictionary of subbasin data
            output_path: Path to output GeoJSON file
            crs_epsg: Optional CRS EPSG code (defaults to EPSG:2278)

        Example:
            >>> subs, _, _ = HmsGeo.parse_basin_file("model.basin")
            >>> HmsGeo.create_geojson_subbasins(subs, "subbasins.geojson")
        """
        output_path = Path(output_path)
        if not crs_epsg:
            raise ValueError("crs_epsg is required (e.g. 'EPSG:2278'). Use HmsPrj.crs_epsg for auto-detected CRS.")

        features = []

        for name, attrs in subbasins.items():
            if 'x' not in attrs or 'y' not in attrs:
                logger.warning(f"Skipping {name} - missing coordinates")
                continue

            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [attrs['x'], attrs['y']]
                },
                "properties": {
                    "name": name,
                    "area": attrs.get('area'),
                    "downstream": attrs.get('downstream'),
                    "percent_impervious": attrs.get('percent_impervious'),
                    "time_of_concentration": attrs.get('time_of_concentration')
                }
            }
            features.append(feature)

        geojson = HmsGeo._create_geojson_structure(features, crs_epsg)

        with open(output_path, 'w') as f:
            json.dump(geojson, f, indent=2)

        logger.info(f"Created subbasins GeoJSON with {len(features)} features at: {output_path}")

    @staticmethod
    def create_geojson_junctions(junctions: Dict[str, Dict[str, Any]],
                                 output_path: Union[str, Path],
                                 crs_epsg: Optional[str] = None) -> None:
        """
        Create GeoJSON file from junction point data.

        Args:
            junctions: Dictionary of junction data
            output_path: Path to output GeoJSON file
            crs_epsg: Optional CRS EPSG code (defaults to EPSG:2278)
        """
        output_path = Path(output_path)
        if not crs_epsg:
            raise ValueError("crs_epsg is required (e.g. 'EPSG:2278'). Use HmsPrj.crs_epsg for auto-detected CRS.")

        features = []

        for name, attrs in junctions.items():
            if 'x' not in attrs or 'y' not in attrs:
                continue

            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [attrs['x'], attrs['y']]
                },
                "properties": {
                    "name": name,
                    "type": attrs.get('type'),
                    "downstream": attrs.get('downstream')
                }
            }
            features.append(feature)

        geojson = HmsGeo._create_geojson_structure(features, crs_epsg)

        with open(output_path, 'w') as f:
            json.dump(geojson, f, indent=2)

        logger.info(f"Created junctions GeoJSON with {len(features)} features at: {output_path}")

    @staticmethod
    def create_geojson_reaches(reaches: Dict[str, Dict[str, Any]],
                              output_path: Union[str, Path],
                              crs_epsg: Optional[str] = None) -> None:
        """
        Create GeoJSON file from reach line data.

        Args:
            reaches: Dictionary of reach data
            output_path: Path to output GeoJSON file
            crs_epsg: Optional CRS EPSG code (defaults to EPSG:2278)
        """
        output_path = Path(output_path)
        if not crs_epsg:
            raise ValueError("crs_epsg is required (e.g. 'EPSG:2278'). Use HmsPrj.crs_epsg for auto-detected CRS.")

        features = []

        for name, attrs in reaches.items():
            if 'from_x' not in attrs or 'from_y' not in attrs:
                continue
            if 'x' not in attrs or 'y' not in attrs:
                continue

            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [attrs['from_x'], attrs['from_y']],
                        [attrs['x'], attrs['y']]
                    ]
                },
                "properties": {
                    "name": name,
                    "type": attrs.get('type'),
                    "downstream": attrs.get('downstream'),
                    "description": attrs.get('description')
                }
            }
            features.append(feature)

        geojson = HmsGeo._create_geojson_structure(features, crs_epsg)

        with open(output_path, 'w') as f:
            json.dump(geojson, f, indent=2)

        logger.info(f"Created reaches GeoJSON with {len(features)} features at: {output_path}")

    @staticmethod
    def create_geojson_boundaries(boundaries: List[Dict[str, Any]],
                                 output_path: Union[str, Path],
                                 crs_epsg: Optional[str] = None) -> None:
        """
        Create GeoJSON file from boundary polygon data.

        Args:
            boundaries: List of boundary features from parse_map_file
            output_path: Path to output GeoJSON file
            crs_epsg: Optional CRS EPSG code (defaults to EPSG:2278)
        """
        output_path = Path(output_path)
        if not crs_epsg:
            raise ValueError("crs_epsg is required (e.g. 'EPSG:2278'). Use HmsPrj.crs_epsg for auto-detected CRS.")

        features = []

        for idx, boundary in enumerate(boundaries):
            coords = boundary['coordinates']
            segment_type = boundary['segment_type']

            # For closed polygons, ensure the last coordinate matches the first
            if segment_type == 'closed':
                if coords[0] != coords[-1]:
                    coords.append(coords[0])

                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [coords]
                    },
                    "properties": {
                        "id": idx,
                        "segment_type": segment_type,
                        "num_vertices": len(coords)
                    }
                }
            else:
                # Open segments in boundary map
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coords
                    },
                    "properties": {
                        "id": idx,
                        "segment_type": segment_type,
                        "num_vertices": len(coords)
                    }
                }

            features.append(feature)

        geojson = HmsGeo._create_geojson_structure(features, crs_epsg)

        with open(output_path, 'w') as f:
            json.dump(geojson, f, indent=2)

        logger.info(f"Created boundaries GeoJSON with {len(features)} features at: {output_path}")

    @staticmethod
    def create_geojson_rivers(rivers: List[Dict[str, Any]],
                             output_path: Union[str, Path],
                             crs_epsg: Optional[str] = None) -> None:
        """
        Create GeoJSON file from river/stream polyline data.

        Args:
            rivers: List of river features from parse_map_file
            output_path: Path to output GeoJSON file
            crs_epsg: Optional CRS EPSG code (defaults to EPSG:2278)
        """
        output_path = Path(output_path)
        if not crs_epsg:
            raise ValueError("crs_epsg is required (e.g. 'EPSG:2278'). Use HmsPrj.crs_epsg for auto-detected CRS.")

        features = []

        for idx, river in enumerate(rivers):
            coords = river['coordinates']
            segment_type = river['segment_type']

            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords
                },
                "properties": {
                    "id": idx,
                    "segment_type": segment_type,
                    "num_vertices": len(coords),
                    "length_2d_ft": HmsGeo._calculate_2d_length(coords)
                }
            }

            features.append(feature)

        geojson = HmsGeo._create_geojson_structure(features, crs_epsg)

        with open(output_path, 'w') as f:
            json.dump(geojson, f, indent=2)

        logger.info(f"Created rivers GeoJSON with {len(features)} features at: {output_path}")

    @staticmethod
    def _create_geojson_structure(features: List[Dict[str, Any]],
                                 crs_epsg: str) -> Dict[str, Any]:
        """
        Create standard GeoJSON structure with features and CRS.

        Args:
            features: List of GeoJSON features
            crs_epsg: CRS EPSG URN string

        Returns:
            Complete GeoJSON structure
        """
        return {
            "type": "FeatureCollection",
            "crs": {
                "type": "name",
                "properties": {
                    "name": crs_epsg
                }
            },
            "features": features
        }

    @staticmethod
    def _calculate_2d_length(coords: List[List[float]]) -> float:
        """
        Calculate 2D length of a polyline in feet.

        Args:
            coords: List of [x, y] coordinate pairs

        Returns:
            Length in feet
        """
        length = 0.0
        for i in range(len(coords) - 1):
            dx = coords[i+1][0] - coords[i][0]
            dy = coords[i+1][1] - coords[i][1]
            length += (dx**2 + dy**2)**0.5
        return round(length, 2)

    @staticmethod
    def create_geojson_diversions(diversions: Dict[str, Dict[str, Any]],
                                  output_path: Union[str, Path],
                                  crs_epsg: Optional[str] = None) -> None:
        """
        Create GeoJSON file from diversion point data.

        Diversions are HMS elements that split flow between two downstream
        paths. They are critical for accurate upstream drainage area analysis.

        Args:
            diversions: Dictionary of diversion data (name -> attributes)
            output_path: Path to output GeoJSON file
            crs_epsg: Optional CRS EPSG code (defaults to EPSG:2278)

        Example:
            >>> diversions = HmsGeo._parse_diversions("model.basin")
            >>> HmsGeo.create_geojson_diversions(diversions, "hms_diversions.geojson")
        """
        output_path = Path(output_path)
        if not crs_epsg:
            raise ValueError("crs_epsg is required (e.g. 'EPSG:2278'). Use HmsPrj.crs_epsg for auto-detected CRS.")

        features = []

        for name, attrs in diversions.items():
            x = attrs.get('x') or attrs.get('canvas_x')
            y = attrs.get('y') or attrs.get('canvas_y')

            if x is None or y is None:
                continue

            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [x, y]
                },
                "properties": {
                    "name": name,
                    "downstream": attrs.get('downstream'),
                    "divert_to": attrs.get('divert_to'),
                    "description": attrs.get('description', '')
                }
            }
            features.append(feature)

        geojson = HmsGeo._create_geojson_structure(features, crs_epsg)

        with open(output_path, 'w') as f:
            json.dump(geojson, f, indent=2)

        logger.info(f"Created diversions GeoJSON with {len(features)} features at: {output_path}")

    @staticmethod
    @log_call
    def detect_model_type(project_dir: Union[str, Path]) -> str:
        """
        Detect whether an HMS project uses gridded or lumped model structure.

        Checks for the presence of .sqlite files in the project directory.
        Gridded models (Modified Clark, SCS Grid) store spatial geometry in
        SQLite databases, while lumped models use .geo/.map text files.

        Args:
            project_dir: Path to the HMS project directory.

        Returns:
            'gridded' if .sqlite files are found, 'lumped' otherwise.

        Example:
            >>> model_type = HmsGeo.detect_model_type("HMS_Tickfaw/")
            >>> print(f"Model type: {model_type}")
            'gridded'
        """
        project_dir = Path(project_dir)
        if not project_dir.is_dir():
            raise FileNotFoundError(f"Project directory not found: {project_dir}")
        sqlite_files = list(project_dir.glob("*.sqlite"))
        model_type = "gridded" if sqlite_files else "lumped"
        logger.info(
            f"Model type: {model_type} "
            f"({len(sqlite_files)} .sqlite files in {project_dir.name})"
        )
        return model_type

    @staticmethod
    def _parse_diversions(basin_path: Union[str, Path]) -> Dict[str, Dict[str, Any]]:
        """
        Parse diversion elements from basin file for GIS extraction.

        Internal helper used by extract_all_gis(). Returns dict format
        compatible with create_geojson_diversions().

        Args:
            basin_path: Path to .basin file

        Returns:
            Dict mapping diversion names to their attributes
        """
        import re as _re

        basin_path = Path(basin_path)

        try:
            with open(basin_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(basin_path, 'r', encoding='latin-1') as f:
                content = f.read()

        diversions = {}
        pattern = r'Diversion:\s*(.+?)\n(.*?)End:'
        matches = _re.findall(pattern, content, _re.DOTALL | _re.IGNORECASE)

        for match in matches:
            name = match[0].strip()
            block = match[1]
            attrs = {}

            for line in block.splitlines():
                line = line.strip()
                if ':' in line and line != 'End:':
                    key, value = line.split(':', 1)
                    attrs[key.strip()] = value.strip()

            diversion_data = {
                'downstream': attrs.get('Downstream', ''),
                'divert_to': attrs.get('Divert To', ''),
                'description': attrs.get('Description', ''),
            }

            # Parse coordinates
            try:
                diversion_data['x'] = float(attrs.get('Canvas X', ''))
                diversion_data['y'] = float(attrs.get('Canvas Y', ''))
            except (ValueError, TypeError):
                pass

            try:
                diversion_data['canvas_x'] = float(attrs.get('Canvas X', ''))
                diversion_data['canvas_y'] = float(attrs.get('Canvas Y', ''))
            except (ValueError, TypeError):
                pass

            diversions[name] = diversion_data

        return diversions

    @staticmethod
    @log_call
    def extract_all_gis(basin_path: Union[str, Path],
                       geo_path: Optional[Union[str, Path]] = None,
                       map_path: Optional[Union[str, Path]] = None,
                       output_dir: Optional[Union[str, Path]] = None,
                       crs_epsg: Optional[str] = None,
                       include_diversions: bool = True) -> Dict[str, Path]:
        """
        Extract all GIS data from HEC-HMS model files to GeoJSON.

        This is a convenience method that extracts all available data from
        the provided files and creates GeoJSON outputs.

        Args:
            basin_path: Path to .basin file (required)
            geo_path: Path to .geo file (optional)
            map_path: Path to .map file (optional)
            output_dir: Directory for output files (defaults to basin file directory)
            crs_epsg: Optional CRS EPSG code (defaults to EPSG:2278)
            include_diversions: If True, extract diversion elements to GeoJSON
                (default True). Diversions are critical for upstream area analysis.

        Returns:
            Dictionary mapping output type to file path.
            When include_diversions=True, includes 'diversions' key.

        Example:
            >>> outputs = HmsGeo.extract_all_gis(
            ...     "model.basin",
            ...     geo_path="model.geo",
            ...     map_path="model.map",
            ...     include_diversions=True
            ... )
            >>> print(outputs.keys())
            dict_keys(['subbasins', 'junctions', 'reaches', 'diversions', 'boundaries', 'rivers'])
        """
        basin_path = Path(basin_path)
        output_dir = Path(output_dir) if output_dir else basin_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        if not crs_epsg:
            raise ValueError("crs_epsg is required (e.g. 'EPSG:2278'). Use HmsPrj.crs_epsg for auto-detected CRS.")

        logger.info("=" * 70)
        logger.info("HEC-HMS GIS Extraction")
        logger.info("=" * 70)

        outputs = {}

        # Parse basin file
        subbasins, junctions, reaches = HmsGeo.parse_basin_file(basin_path)

        # Merge coordinates from .geo file if provided
        if geo_path:
            geo_coords = HmsGeo.parse_geo_file(geo_path)
            for name, coords in geo_coords.items():
                if name in subbasins:
                    if 'x' not in subbasins[name]:
                        subbasins[name]['x'] = coords['x']
                    if 'y' not in subbasins[name]:
                        subbasins[name]['y'] = coords['y']

        # Create GeoJSON outputs
        output_subbasins = output_dir / "hms_subbasins.geojson"
        HmsGeo.create_geojson_subbasins(subbasins, output_subbasins, crs_epsg)
        outputs['subbasins'] = output_subbasins

        output_junctions = output_dir / "hms_junctions.geojson"
        HmsGeo.create_geojson_junctions(junctions, output_junctions, crs_epsg)
        outputs['junctions'] = output_junctions

        output_reaches = output_dir / "hms_reaches.geojson"
        HmsGeo.create_geojson_reaches(reaches, output_reaches, crs_epsg)
        outputs['reaches'] = output_reaches

        # Extract diversions if requested
        if include_diversions:
            diversions = HmsGeo._parse_diversions(basin_path)
            if diversions:
                output_diversions = output_dir / "hms_diversions.geojson"
                HmsGeo.create_geojson_diversions(diversions, output_diversions, crs_epsg)
                outputs['diversions'] = output_diversions
                logger.info(f"Extracted {len(diversions)} diversions")
            else:
                logger.info("No diversions found in basin file")

        # Parse and export map file if provided
        if map_path:
            map_data = HmsGeo.parse_map_file(map_path)

            output_boundaries = output_dir / "hms_boundaries.geojson"
            HmsGeo.create_geojson_boundaries(map_data['boundaries'],
                                            output_boundaries, crs_epsg)
            outputs['boundaries'] = output_boundaries

            output_rivers = output_dir / "hms_rivers.geojson"
            HmsGeo.create_geojson_rivers(map_data['rivers'],
                                        output_rivers, crs_epsg)
            outputs['rivers'] = output_rivers

        logger.info("=" * 70)
        logger.info("Extraction Complete!")
        logger.info("=" * 70)
        for key, path in outputs.items():
            logger.info(f"  {key}: {path}")

        return outputs
