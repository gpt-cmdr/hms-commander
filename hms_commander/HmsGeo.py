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

    # Constants
    CRS_EPSG_2278 = "urn:ogc:def:crs:EPSG::2278"
    CRS_NAME_2278 = "NAD83 / Texas South Central (ftUS)"

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
            crs_epsg: CRS of the coordinates (default: EPSG:2278 - Texas South Central)

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
            crs_epsg: CRS of the coordinates (default: EPSG:2278 - Texas South Central)

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
        crs_epsg = crs_epsg or HmsGeo.CRS_EPSG_2278

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
        crs_epsg = crs_epsg or HmsGeo.CRS_EPSG_2278

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
        crs_epsg = crs_epsg or HmsGeo.CRS_EPSG_2278

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
        crs_epsg = crs_epsg or HmsGeo.CRS_EPSG_2278

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
        crs_epsg = crs_epsg or HmsGeo.CRS_EPSG_2278

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
    def extract_all_gis(basin_path: Union[str, Path],
                       geo_path: Optional[Union[str, Path]] = None,
                       map_path: Optional[Union[str, Path]] = None,
                       output_dir: Optional[Union[str, Path]] = None,
                       crs_epsg: Optional[str] = None) -> Dict[str, Path]:
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

        Returns:
            Dictionary mapping output type to file path

        Example:
            >>> outputs = HmsGeo.extract_all_gis(
            ...     "model.basin",
            ...     geo_path="model.geo",
            ...     map_path="model.map"
            ... )
            >>> print(outputs.keys())
            dict_keys(['subbasins', 'junctions', 'reaches', 'boundaries', 'rivers'])
        """
        basin_path = Path(basin_path)
        output_dir = Path(output_dir) if output_dir else basin_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        crs_epsg = crs_epsg or HmsGeo.CRS_EPSG_2278

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
