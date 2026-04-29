"""
TauDEM-to-HMS basin assembly helpers.

This module assembles a durable, geometry-first HMS handoff package from
verified TauDEM outputs. The first slice focuses on topology and geometry
only; hydrologic parameter estimation is intentionally deferred.
"""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Union

import pandas as pd

from .Decorators import log_call
from .HmsWatershedVerification import HmsWatershedVerification
from .LoggingConfig import get_logger
from ._parsing import HmsFileParser
from ._project_registry import (
    build_project_registry_block,
    register_project_block,
    rewrite_project_block,
)
from ._spatial import (
    load_vector,
    polygonize_zone_raster,
    resolve_crs,
    single_geometry,
    write_json,
    write_vector,
)

logger = get_logger(__name__)

try:
    PACKAGE_VERSION = version("hms-commander")
except PackageNotFoundError:  # pragma: no cover - fallback for source-only runs
    PACKAGE_VERSION = "0.2.1"


class HmsBasinBuilder:
    """Static helpers for assembling TauDEM-derived HMS topology packages."""

    DEFAULT_TAUDEM_RUN_RELATIVE_PATH = Path("04_terrain") / "taudem_work"
    DEFAULT_VERIFICATION_RELATIVE_PATH = Path("09_taudem_verification")
    BOUNDARY_HANDOFF_OUTLET_NAME = "taudem_boundary_handoff_outlet.geojson"
    SUPPORTED_OUTLET_MODES = {"boundary_handoff", "snapped", "original"}
    SUPPORTED_TERMINAL_NODE_MODES = {"sink", "junction"}
    SUPPORTED_HMS_VERSION_PROFILES = {"4.13"}
    SUPPORTED_UNIT_SYSTEMS = {
        "english": "English",
        "imperial": "English",
        "us customary": "English",
        "us customary units": "English",
        "si": "SI",
        "metric": "SI",
    }
    FREQUENCY_STORM_MET_VERSION = "3.3"

    @staticmethod
    def _utc_now() -> str:
        """Return a compact UTC timestamp."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def _json_default(value: Any) -> Any:
        """Serialize pathlib and CRS-like values inside JSON payloads."""
        if isinstance(value, Path):
            return str(value)
        return str(value)

    @staticmethod
    def _check_dependencies():
        """Import GIS dependencies only when assembly is invoked."""
        try:
            import geopandas as gpd
            import numpy as np
            import rasterio
            from pyproj import CRS
            from rasterio.features import shapes
            from shapely.geometry import LineString, Point, mapping, shape
            from shapely.ops import linemerge, unary_union
        except ImportError as exc:  # pragma: no cover - exercised only in missing-deps env
            missing_pkg = str(exc).split("'")[1] if "'" in str(exc) else "unknown"
            raise ImportError(
                f"Missing required GIS package: {missing_pkg}\n"
                "Install with: pip install hms-commander[gis]\n"
                "Or install geopandas, shapely, rasterio, and pyproj."
            ) from exc

        return {
            "gpd": gpd,
            "np": np,
            "rasterio": rasterio,
            "CRS": CRS,
            "shapes": shapes,
            "shape": shape,
            "mapping": mapping,
            "Point": Point,
            "LineString": LineString,
            "linemerge": linemerge,
            "unary_union": unary_union,
        }

    @staticmethod
    def _write_json(path: Path, payload: Mapping[str, Any]) -> Dict[str, Any]:
        """Write JSON with stable formatting."""
        return write_json(path, payload)

    @staticmethod
    def _write_vector(path: Path, gdf) -> Dict[str, Any]:
        """Write a vector dataset with stable overwrite behavior."""
        return write_vector(path, gdf)

    @staticmethod
    def _write_csv(path: Path, frame: pd.DataFrame) -> Dict[str, Any]:
        """Write CSV with stable overwrite behavior."""
        existed = path.exists()
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
        return {"status": "updated" if existed else "created", "bytes": path.stat().st_size}

    @staticmethod
    def _as_int(value: Any, default: int = 0) -> int:
        """Coerce a numeric-like value to int, treating nulls as defaults."""
        if value is None:
            return default
        try:
            if pd.isna(value):
                return default
        except TypeError:
            pass
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _as_float(value: Any, default: Optional[float] = None) -> Optional[float]:
        """Coerce a numeric-like value to float, treating nulls as defaults."""
        if value is None:
            return default
        try:
            if pd.isna(value):
                return default
        except TypeError:
            pass
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _resolve_taudem_run_dir(
        workspace_root: Union[str, Path],
        taudem_run_dir: Optional[Union[str, Path]] = None,
    ) -> Path:
        """Resolve the TauDEM output directory for a workspace."""
        workspace_root = Path(workspace_root)
        if taudem_run_dir is not None:
            resolved = Path(taudem_run_dir)
            if not resolved.exists():
                raise FileNotFoundError(f"TauDEM run directory not found: {resolved}")
            return resolved

        candidate_dirs = [
            workspace_root / "net.shp",
            workspace_root / HmsBasinBuilder.DEFAULT_TAUDEM_RUN_RELATIVE_PATH / "net.shp",
            workspace_root / "taudem_work" / "net.shp",
        ]
        for candidate in candidate_dirs:
            if candidate.exists():
                return candidate.parent

        raise FileNotFoundError(
            "Could not resolve TauDEM run directory. "
            "Provide taudem_run_dir explicitly or use a workspace with "
            "`04_terrain/taudem_work`."
        )

    @staticmethod
    def _resolve_verification_dir(
        workspace_root: Union[str, Path],
        verification_dir: Optional[Union[str, Path]] = None,
    ) -> Path:
        """Resolve the verification artifact directory for a workspace."""
        workspace_root = Path(workspace_root)
        if verification_dir is not None:
            return Path(verification_dir)
        return workspace_root / HmsBasinBuilder.DEFAULT_VERIFICATION_RELATIVE_PATH

    @staticmethod
    def _resolve_source_paths(
        workspace_root: Union[str, Path],
        taudem_run_dir: Optional[Union[str, Path]] = None,
        verification_dir: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Path]:
        """Resolve the standard source paths needed for assembly."""
        workspace_root = Path(workspace_root)
        run_root = HmsBasinBuilder._resolve_taudem_run_dir(workspace_root, taudem_run_dir)
        verification_root = HmsBasinBuilder._resolve_verification_dir(workspace_root, verification_dir)

        net_path = run_root / "net.shp"
        watershed_path = run_root / "w.tif"
        if not net_path.exists():
            raise FileNotFoundError(f"TauDEM stream network not found: {net_path}")
        if not watershed_path.exists():
            raise FileNotFoundError(f"TauDEM watershed raster not found: {watershed_path}")

        return {
            "workspace_root": workspace_root,
            "taudem_run_dir": run_root,
            "verification_dir": verification_root,
            "net_path": net_path,
            "watershed_path": watershed_path,
            "original_outlet_path": run_root / "outlet.shp",
            "snapped_outlet_path": run_root / "outlet_snapped.shp",
            "boundary_handoff_outlet_path": verification_root / HmsBasinBuilder.BOUNDARY_HANDOFF_OUTLET_NAME,
        }

    @staticmethod
    def _resolve_linear_units(crs) -> Dict[str, Any]:
        """Resolve linear-unit metadata for the active projected CRS."""
        axis_info = getattr(crs, "axis_info", None) or []
        if axis_info:
            unit_name = axis_info[0].unit_name or "unknown"
            unit_to_meters = float(axis_info[0].unit_conversion_factor or 1.0)
        else:
            unit_name = "unknown"
            unit_to_meters = 1.0

        unit_name_normalized = unit_name.lower()
        has_planar_units = bool(axis_info) and "degree" not in unit_name_normalized

        epsg = crs.to_epsg()
        return {
            "native": str(crs),
            "epsg": f"EPSG:{epsg}" if epsg else None,
            "is_projected": bool(getattr(crs, "is_projected", False)) or has_planar_units,
            "linear_unit_name": unit_name,
            "linear_unit_to_meters": unit_to_meters,
        }

    @staticmethod
    def _resolve_best_crs(primary_crs: Any, source_paths: Mapping[str, Path]):
        """Choose the most useful projected CRS from available source metadata."""
        deps = HmsBasinBuilder._check_dependencies()
        gpd = deps["gpd"]

        candidates = []
        primary_resolved = resolve_crs(primary_crs)
        if primary_resolved is not None:
            candidates.append(primary_resolved)

        for candidate_path in (
            source_paths["boundary_handoff_outlet_path"],
            source_paths["snapped_outlet_path"],
            source_paths["original_outlet_path"],
            source_paths["net_path"],
        ):
            if not candidate_path.exists():
                continue
            try:
                raw_gdf = gpd.read_file(candidate_path)
            except Exception:
                continue
            candidate_crs = resolve_crs(raw_gdf.crs)
            if candidate_crs is not None:
                candidates.append(candidate_crs)

        if not candidates:
            return None

        def score(candidate_crs) -> tuple[int, int, int]:
            info = HmsBasinBuilder._resolve_linear_units(candidate_crs)
            return (
                1 if info["epsg"] else 0,
                1 if info["is_projected"] else 0,
                1 if "degree" not in info["linear_unit_name"].lower() else 0,
            )

        return max(candidates, key=score)

    @staticmethod
    def _length_metrics(length_native: float, unit_to_meters: float) -> Dict[str, float]:
        """Build a consistent set of length metrics."""
        length_m = float(length_native) * unit_to_meters
        length_ft = length_m / 0.3048
        return {
            "length_native": float(length_native),
            "length_m": length_m,
            "length_km": length_m / 1000.0,
            "length_ft": length_ft,
            "length_mi": length_ft / 5280.0,
        }

    @staticmethod
    def _area_metrics(area_native: float, unit_to_meters: float) -> Dict[str, float]:
        """Build a consistent set of area metrics."""
        area_m2 = float(area_native) * (unit_to_meters ** 2)
        area_ft2 = area_m2 / (0.3048 ** 2)
        return {
            "area_native": float(area_native),
            "area_m2": area_m2,
            "area_sqkm": area_m2 / 1_000_000.0,
            "area_sqmi": area_m2 / 2_589_988.110336,
            "area_ft2": area_ft2,
            "area_acres": area_ft2 / 43_560.0,
        }

    @staticmethod
    def _normalize_line(geometry):
        """Normalize any line-like geometry into a single LineString."""
        deps = HmsBasinBuilder._check_dependencies()
        LineString = deps["LineString"]
        linemerge = deps["linemerge"]

        if geometry is None or geometry.is_empty:
            raise ValueError("Reach geometry is missing or empty")
        if geometry.geom_type == "LineString":
            line = geometry
        elif geometry.geom_type == "MultiLineString":
            merged = linemerge(geometry)
            if merged.geom_type == "LineString":
                line = merged
            else:
                line = max(list(merged.geoms), key=lambda item: item.length)
        else:
            raise ValueError(f"Unsupported reach geometry type: {geometry.geom_type}")

        if not isinstance(line, LineString):
            raise ValueError("Could not normalize reach geometry into a LineString")
        return line

    @staticmethod
    def _polygonize_wsno_raster(raster_path: Union[str, Path]):
        """Polygonize TauDEM subbasin zones from a watershed grid."""
        return polygonize_zone_raster(raster_path, zone_column="wsno")

    @staticmethod
    def _boundary_geometry_from_zones(zones_gdf):
        """Return the dissolved TauDEM basin geometry for all zones."""
        return single_geometry(zones_gdf)

    @staticmethod
    def _build_outlet_item(
        source_paths: Mapping[str, Path],
        verification_crs,
        outlet_mode: str,
    ) -> Dict[str, Any]:
        """Resolve the sink point for the assembled HMS handoff package."""
        deps = HmsBasinBuilder._check_dependencies()
        gpd = deps["gpd"]
        Point = deps["Point"]
        mapping = deps["mapping"]

        if outlet_mode not in HmsBasinBuilder.SUPPORTED_OUTLET_MODES:
            raise ValueError(
                f"Unsupported outlet_mode '{outlet_mode}'. "
                f"Choose from {sorted(HmsBasinBuilder.SUPPORTED_OUTLET_MODES)}."
            )

        outlet_path = None
        outlet_gdf = None
        outlet_source = None
        selection_payload = None

        if outlet_mode == "boundary_handoff":
            outlet_path = source_paths["boundary_handoff_outlet_path"]
            if outlet_path.exists():
                outlet_gdf = load_vector(outlet_path, fallback_crs=verification_crs)
                outlet_source = "artifact"
            else:
                seed_outlet_path = source_paths["snapped_outlet_path"]
                if not seed_outlet_path.exists():
                    seed_outlet_path = source_paths["original_outlet_path"]
                    if not seed_outlet_path.exists():
                        seed_outlet_path = None

                selection_payload = HmsWatershedVerification.derive_taudem_boundary_outlet(
                    stream_network_path=source_paths["net_path"],
                    taudem_watershed_raster_path=source_paths["watershed_path"],
                    seed_outlet_path=seed_outlet_path,
                    fallback_crs=verification_crs,
                    workspace_root=source_paths["workspace_root"],
                    study_name=Path(source_paths["workspace_root"]).name,
                )
                selection_crs = resolve_crs(
                    selection_payload["verification_crs"],
                    verification_crs,
                )
                outlet_gdf = gpd.GeoDataFrame(
                    {"id": [1]},
                    geometry=[
                        Point(
                            selection_payload["selection"]["selected_outlet"]["x"],
                            selection_payload["selection"]["selected_outlet"]["y"],
                        )
                    ],
                    crs=selection_crs,
                )
                outlet_source = "derived"
        elif outlet_mode == "snapped":
            outlet_path = source_paths["snapped_outlet_path"]
            if not outlet_path.exists():
                raise FileNotFoundError(f"Snapped outlet dataset not found: {outlet_path}")
            outlet_gdf = load_vector(outlet_path, fallback_crs=verification_crs)
            outlet_source = "snapped_outlet"
        else:
            outlet_path = source_paths["original_outlet_path"]
            if not outlet_path.exists():
                raise FileNotFoundError(f"Original outlet dataset not found: {outlet_path}")
            outlet_gdf = load_vector(outlet_path, fallback_crs=verification_crs)
            outlet_source = "original_outlet"

        outlet_projected = outlet_gdf.to_crs(verification_crs)
        outlet_point = outlet_projected.geometry.iloc[0]
        return {
            "name": "Sink_001",
            "type": "Sink",
            "mode": outlet_mode,
            "source": outlet_source,
            "source_path": str(outlet_path) if outlet_path is not None else None,
            "x": float(outlet_point.x),
            "y": float(outlet_point.y),
            "geometry": mapping(outlet_point),
            "selection": selection_payload,
        }

    @staticmethod
    def _resolved_junction_id(downstream_link: int, downstream_node_id: int) -> int:
        """Resolve a stable junction token from TauDEM identifiers."""
        if downstream_node_id > 0:
            return downstream_node_id
        return downstream_link

    @staticmethod
    def _sanitize_export_value(value: Any) -> Any:
        """Convert nested export values into flat, serializable properties."""
        if isinstance(value, (list, dict)):
            return json.dumps(value, sort_keys=True)
        return value

    @staticmethod
    def _records_to_frame(records: Sequence[Mapping[str, Any]]) -> pd.DataFrame:
        """Convert spec records to a flat table suitable for CSV export."""
        flat_rows: List[Dict[str, Any]] = []
        for record in records:
            flat_row = {
                key: HmsBasinBuilder._sanitize_export_value(value)
                for key, value in record.items()
                if key != "geometry"
            }
            flat_rows.append(flat_row)
        return pd.DataFrame(flat_rows)

    @staticmethod
    def _records_to_gdf(records: Sequence[Mapping[str, Any]], crs_value: str):
        """Convert spec records to a GeoDataFrame suitable for vector export."""
        deps = HmsBasinBuilder._check_dependencies()
        gpd = deps["gpd"]
        shape = deps["shape"]

        geometries = [shape(record["geometry"]) for record in records]
        frame = HmsBasinBuilder._records_to_frame(records)
        return gpd.GeoDataFrame(frame, geometry=geometries, crs=crs_value)

    @staticmethod
    def _geometry_start_end_points(line):
        """Return the start and end points for a normalized line geometry."""
        deps = HmsBasinBuilder._check_dependencies()
        Point = deps["Point"]

        coords = list(line.coords)
        return Point(coords[0]), Point(coords[-1])

    @staticmethod
    @log_call
    def build_taudem_hms_spec(
        workspace_root: Union[str, Path],
        taudem_run_dir: Optional[Union[str, Path]] = None,
        verification_dir: Optional[Union[str, Path]] = None,
        outlet_mode: str = "boundary_handoff",
        unit_system: str = "English",
    ) -> Dict[str, Any]:
        """Build an in-memory TauDEM-to-HMS topology and geometry spec."""
        unit_system = HmsBasinBuilder._normalize_unit_system(unit_system)
        deps = HmsBasinBuilder._check_dependencies()
        gpd = deps["gpd"]
        mapping = deps["mapping"]

        source_paths = HmsBasinBuilder._resolve_source_paths(
            workspace_root=workspace_root,
            taudem_run_dir=taudem_run_dir,
            verification_dir=verification_dir,
        )

        zones_gdf = HmsBasinBuilder._polygonize_wsno_raster(source_paths["watershed_path"])
        verification_crs = HmsBasinBuilder._resolve_best_crs(zones_gdf.crs, source_paths)
        if verification_crs is None:
            raise ValueError("Could not determine projected CRS for TauDEM HMS assembly")

        crs_info = HmsBasinBuilder._resolve_linear_units(verification_crs)
        if not crs_info["is_projected"]:
            raise ValueError(
                "TauDEM HMS assembly requires a projected CRS so geometry metrics are meaningful."
            )

        unit_to_meters = crs_info["linear_unit_to_meters"]
        net_gdf = load_vector(
            source_paths["net_path"],
            fallback_crs=verification_crs,
        ).to_crs(verification_crs)
        net_gdf = net_gdf.copy()
        net_gdf["LINKNO"] = net_gdf["LINKNO"].astype(int)
        net_gdf["WSNO"] = net_gdf["WSNO"].astype(int)
        net_gdf = net_gdf.sort_values("LINKNO").reset_index(drop=True)
        net_gdf["geometry"] = net_gdf.geometry.apply(HmsBasinBuilder._normalize_line)

        boundary_geometry = HmsBasinBuilder._boundary_geometry_from_zones(zones_gdf)
        outlet_item = HmsBasinBuilder._build_outlet_item(
            source_paths=source_paths,
            verification_crs=verification_crs,
            outlet_mode=outlet_mode,
        )

        zone_by_wsno = {int(row.wsno): row.geometry for row in zones_gdf.itertuples(index=False)}
        reach_rows_by_linkno = {
            int(row.LINKNO): row
            for row in net_gdf.itertuples(index=False)
        }
        upstream_map: Dict[int, List[int]] = {}
        for row in net_gdf.itertuples(index=False):
            downstream_link = HmsBasinBuilder._as_int(row.DSLINKNO)
            if downstream_link > 0:
                upstream_map.setdefault(downstream_link, []).append(int(row.LINKNO))

        valid_junction_targets = sorted(
            downstream_link
            for downstream_link in upstream_map
            if downstream_link in reach_rows_by_linkno
        )
        junction_name_by_downstream_link: Dict[int, str] = {}
        junction_records: List[Dict[str, Any]] = []
        for downstream_link in valid_junction_targets:
            downstream_row = reach_rows_by_linkno[downstream_link]
            downstream_node_id = HmsBasinBuilder._as_int(getattr(downstream_row, "DSNODEID", None), default=-1)
            resolved_node_id = HmsBasinBuilder._resolved_junction_id(downstream_link, downstream_node_id)
            junction_name = f"J_{resolved_node_id}"
            junction_name_by_downstream_link[downstream_link] = junction_name

            downstream_line = downstream_row.geometry
            junction_point, _ = HmsBasinBuilder._geometry_start_end_points(downstream_line)
            upstream_reaches = sorted(
                f"R_{link_id}" for link_id in upstream_map.get(downstream_link, [])
            )

            junction_records.append(
                {
                    "name": junction_name,
                    "type": "Junction",
                    "source_ids": {
                        "resolved_node_id": resolved_node_id,
                        "downstream_linkno": downstream_link,
                        "downstream_node_id": downstream_node_id if downstream_node_id > 0 else None,
                    },
                    "downstream": f"R_{downstream_link}",
                    "upstream_reaches": upstream_reaches,
                    "x": float(junction_point.x),
                    "y": float(junction_point.y),
                    "canvas_x": float(junction_point.x),
                    "canvas_y": float(junction_point.y),
                    "geometry": mapping(junction_point),
                }
            )

        reach_records: List[Dict[str, Any]] = []
        invalid_downstream_links = set()
        disconnected_upstream_refs = set()
        missing_subbasin_wsno = set()
        for row in net_gdf.itertuples(index=False):
            linkno = int(row.LINKNO)
            wsno = int(row.WSNO)
            downstream_link = HmsBasinBuilder._as_int(row.DSLINKNO)
            upstream_links_raw = [
                HmsBasinBuilder._as_int(getattr(row, "USLINKNO1", 0)),
                HmsBasinBuilder._as_int(getattr(row, "USLINKNO2", 0)),
            ]
            upstream_reach_names: List[str] = []
            missing_upstream_refs: List[int] = []
            for upstream_link in upstream_links_raw:
                if upstream_link <= 0:
                    continue
                if upstream_link in reach_rows_by_linkno:
                    upstream_reach_names.append(f"R_{upstream_link}")
                else:
                    missing_upstream_refs.append(upstream_link)
                    disconnected_upstream_refs.add(upstream_link)

            if downstream_link <= 0:
                downstream_name = outlet_item["name"]
            elif downstream_link in junction_name_by_downstream_link:
                downstream_name = junction_name_by_downstream_link[downstream_link]
            else:
                downstream_name = None
                invalid_downstream_links.add(downstream_link)

            line = row.geometry
            upstream_point, downstream_point = HmsBasinBuilder._geometry_start_end_points(line)
            line_length_metrics = HmsBasinBuilder._length_metrics(line.length, unit_to_meters)
            straight_length = upstream_point.distance(downstream_point)
            straight_length_metrics = HmsBasinBuilder._length_metrics(straight_length, unit_to_meters)
            strm_order = HmsBasinBuilder._as_int(getattr(row, "strmOrder", None), default=0)
            slope_value = HmsBasinBuilder._as_float(getattr(row, "Slope", None))

            if wsno not in zone_by_wsno:
                missing_subbasin_wsno.add(wsno)

            reach_records.append(
                {
                    "name": f"R_{linkno}",
                    "type": "Reach",
                    "source_ids": {
                        "linkno": linkno,
                        "wsno": wsno,
                        "downstream_linkno": downstream_link if downstream_link > 0 else None,
                    },
                    "downstream": downstream_name,
                    "upstream_reaches": sorted(upstream_reach_names),
                    "missing_upstream_link_refs": sorted(missing_upstream_refs),
                    "wsno": wsno,
                    "stream_order": strm_order if strm_order > 0 else None,
                    "slope": slope_value,
                    "from_x": float(upstream_point.x),
                    "from_y": float(upstream_point.y),
                    "x": float(downstream_point.x),
                    "y": float(downstream_point.y),
                    "canvas_x": float(downstream_point.x),
                    "canvas_y": float(downstream_point.y),
                    "from_canvas_x": float(upstream_point.x),
                    "from_canvas_y": float(upstream_point.y),
                    **line_length_metrics,
                    "straight_length_native": straight_length_metrics["length_native"],
                    "straight_length_m": straight_length_metrics["length_m"],
                    "straight_length_ft": straight_length_metrics["length_ft"],
                    "straight_length_mi": straight_length_metrics["length_mi"],
                    "geometry": mapping(line),
                }
            )

        subbasin_records: List[Dict[str, Any]] = []
        missing_reach_wsno = set()
        linkno_by_wsno = {
            HmsBasinBuilder._as_int(getattr(row, "WSNO", None)): HmsBasinBuilder._as_int(getattr(row, "LINKNO", None))
            for row in net_gdf.itertuples(index=False)
        }
        for row in zones_gdf.itertuples(index=False):
            wsno = int(row.wsno)
            geometry = row.geometry
            if not geometry.is_valid:
                geometry = geometry.buffer(0)
            centroid = geometry.centroid
            area_metrics = HmsBasinBuilder._area_metrics(geometry.area, unit_to_meters)
            linkno = linkno_by_wsno.get(wsno)
            if linkno is None:
                downstream_name = None
                missing_reach_wsno.add(wsno)
            else:
                downstream_name = f"R_{linkno}"

            subbasin_records.append(
                {
                    "name": f"SB_{wsno}",
                    "type": "Subbasin",
                    "source_ids": {
                        "wsno": wsno,
                        "linkno": linkno,
                    },
                    "downstream": downstream_name,
                    "wsno": wsno,
                    "linkno": linkno,
                    "centroid_x": float(centroid.x),
                    "centroid_y": float(centroid.y),
                    "canvas_x": float(centroid.x),
                    "canvas_y": float(centroid.y),
                    **area_metrics,
                    "geometry": mapping(geometry),
                }
            )

        terminal_reaches = sorted(
            record["name"]
            for record in reach_records
            if record["downstream"] == outlet_item["name"]
        )
        sink_record = {
            "name": outlet_item["name"],
            "type": "Sink",
            "mode": outlet_item["mode"],
            "source": outlet_item["source"],
            "source_path": outlet_item["source_path"],
            "downstream": None,
            "upstream_reaches": terminal_reaches,
            "x": outlet_item["x"],
            "y": outlet_item["y"],
            "canvas_x": outlet_item["x"],
            "canvas_y": outlet_item["y"],
            "geometry": outlet_item["geometry"],
        }

        basin_area_metrics = HmsBasinBuilder._area_metrics(boundary_geometry.area, unit_to_meters)
        subbasin_area_sum_m2 = float(sum(record["area_m2"] for record in subbasin_records))
        area_closure_error_m2 = subbasin_area_sum_m2 - basin_area_metrics["area_m2"]
        area_closure_error_pct = (
            (area_closure_error_m2 / basin_area_metrics["area_m2"]) * 100.0
            if basin_area_metrics["area_m2"] > 0
            else 0.0
        )

        reach_wsno_values = {record["wsno"] for record in reach_records}
        subbasin_wsno_values = {record["wsno"] for record in subbasin_records}
        junction_fallback_count = sum(
            1
            for record in junction_records
            if record["source_ids"]["downstream_node_id"] is None
        )

        spec = {
            "schema_version": "1.0",
            "study_type": "taudem_hms_spec",
            "generated_at": HmsBasinBuilder._utc_now(),
            "study_name": Path(source_paths["workspace_root"]).name,
            "workspace_root": str(Path(source_paths["workspace_root"]).resolve()),
            "unit_system": unit_system,
            "outlet_mode": outlet_mode,
            "crs": crs_info,
            "source_paths": {
                "workspace_root": str(Path(source_paths["workspace_root"]).resolve()),
                "taudem_run_dir": str(Path(source_paths["taudem_run_dir"]).resolve()),
                "verification_dir": str(Path(source_paths["verification_dir"]).resolve()),
                "net_path": str(Path(source_paths["net_path"]).resolve()),
                "watershed_path": str(Path(source_paths["watershed_path"]).resolve()),
                "boundary_handoff_outlet_path": str(Path(source_paths["boundary_handoff_outlet_path"]).resolve()),
            },
            "outlet": {
                "name": sink_record["name"],
                "mode": sink_record["mode"],
                "source": sink_record["source"],
                "source_path": sink_record["source_path"],
                "x": sink_record["x"],
                "y": sink_record["y"],
                "geometry": sink_record["geometry"],
            },
            "counts": {
                "subbasins": len(subbasin_records),
                "reaches": len(reach_records),
                "junctions": len(junction_records),
                "sinks": 1,
            },
            "network_checks": {
                "reach_wsno_count": len(reach_wsno_values),
                "subbasin_wsno_count": len(subbasin_wsno_values),
                "matched_wsno_count": len(reach_wsno_values & subbasin_wsno_values),
                "missing_wsno_in_reaches": sorted(subbasin_wsno_values - reach_wsno_values),
                "missing_wsno_in_subbasins": sorted(reach_wsno_values - subbasin_wsno_values),
                "missing_subbasin_for_reaches": sorted(missing_subbasin_wsno),
                "missing_reach_for_subbasins": sorted(missing_reach_wsno),
                "invalid_downstream_links": sorted(invalid_downstream_links),
                "disconnected_upstream_link_refs": sorted(disconnected_upstream_refs),
                "terminal_link_count": len(terminal_reaches),
                "terminal_link_names": terminal_reaches,
                "junction_fallback_count": junction_fallback_count,
                "taudem_basin_area_m2": basin_area_metrics["area_m2"],
                "subbasin_area_sum_m2": subbasin_area_sum_m2,
                "area_closure_error_m2": area_closure_error_m2,
                "area_closure_error_pct": area_closure_error_pct,
            },
            "subbasins": subbasin_records,
            "reaches": reach_records,
            "junctions": junction_records,
            "sink": sink_record,
            "builder": {
                "package": "hms-commander",
                "class": "HmsBasinBuilder",
                "method": "build_taudem_hms_spec",
                "version": PACKAGE_VERSION,
            },
        }

        return spec

    @staticmethod
    @log_call
    def export_taudem_hms_spec(
        spec: Mapping[str, Any],
        output_dir: Union[str, Path],
    ) -> Dict[str, Path]:
        """Write the durable TauDEM-to-HMS handoff package for a spec."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        crs_value = spec["crs"].get("native") or spec["crs"].get("epsg")
        if not crs_value:
            raise ValueError("Spec is missing CRS metadata")

        paths = {
            "spec": output_dir / "taudem_hms_spec.json",
            "subbasins_geojson": output_dir / "subbasins.geojson",
            "subbasins_csv": output_dir / "subbasins.csv",
            "reaches_geojson": output_dir / "reaches.geojson",
            "reaches_csv": output_dir / "reaches.csv",
            "junctions_geojson": output_dir / "junctions.geojson",
            "sink_geojson": output_dir / "sink.geojson",
            "assembly_report": output_dir / "assembly_report.json",
        }

        artifacts: Dict[str, Dict[str, Any]] = {}
        artifacts["spec"] = HmsBasinBuilder._write_json(paths["spec"], spec)

        subbasins_gdf = HmsBasinBuilder._records_to_gdf(spec["subbasins"], crs_value)
        reaches_gdf = HmsBasinBuilder._records_to_gdf(spec["reaches"], crs_value)
        junctions_gdf = HmsBasinBuilder._records_to_gdf(spec["junctions"], crs_value)
        sink_gdf = HmsBasinBuilder._records_to_gdf([spec["sink"]], crs_value)

        artifacts["subbasins_geojson"] = HmsBasinBuilder._write_vector(paths["subbasins_geojson"], subbasins_gdf)
        artifacts["reaches_geojson"] = HmsBasinBuilder._write_vector(paths["reaches_geojson"], reaches_gdf)
        artifacts["junctions_geojson"] = HmsBasinBuilder._write_vector(paths["junctions_geojson"], junctions_gdf)
        artifacts["sink_geojson"] = HmsBasinBuilder._write_vector(paths["sink_geojson"], sink_gdf)

        artifacts["subbasins_csv"] = HmsBasinBuilder._write_csv(
            paths["subbasins_csv"],
            HmsBasinBuilder._records_to_frame(spec["subbasins"]),
        )
        artifacts["reaches_csv"] = HmsBasinBuilder._write_csv(
            paths["reaches_csv"],
            HmsBasinBuilder._records_to_frame(spec["reaches"]),
        )

        assembly_report = {
            "schema_version": "1.0",
            "study_type": "taudem_hms_assembly_report",
            "generated_at": HmsBasinBuilder._utc_now(),
            "study_name": spec.get("study_name"),
            "workspace_root": spec.get("workspace_root"),
            "output_dir": str(output_dir.resolve()),
            "counts": spec.get("counts", {}),
            "network_checks": spec.get("network_checks", {}),
            "outlet": spec.get("outlet", {}),
            "source_paths": spec.get("source_paths", {}),
            "artifacts": {
                key: {
                    "path": str(path.resolve()),
                    "status": artifacts[key]["status"],
                    "bytes": artifacts[key]["bytes"],
                }
                for key, path in paths.items()
                if key != "assembly_report"
            },
            "builder": {
                "package": "hms-commander",
                "class": "HmsBasinBuilder",
                "method": "export_taudem_hms_spec",
                "version": PACKAGE_VERSION,
            },
        }
        artifacts["assembly_report"] = HmsBasinBuilder._write_json(paths["assembly_report"], assembly_report)

        return paths

    @staticmethod
    def _validate_supported_hms_profile(hms_version_profile: str) -> str:
        """Restrict v1 writers to the known HMS 4.13 saved shape."""
        profile = str(hms_version_profile).strip()
        if profile not in HmsBasinBuilder.SUPPORTED_HMS_VERSION_PROFILES:
            raise ValueError(
                "TauDEM-to-HMS writers currently support only the HMS 4.13 profile. "
                f"Received: {hms_version_profile!r}"
            )
        return profile

    @staticmethod
    def _validate_terminal_node_mode(terminal_node_mode: str) -> str:
        """Validate the terminal node mode for basin scaffold writing."""
        mode = str(terminal_node_mode).strip().lower()
        if mode not in HmsBasinBuilder.SUPPORTED_TERMINAL_NODE_MODES:
            raise ValueError(
                f"Unsupported terminal_node_mode {terminal_node_mode!r}; "
                f"expected one of {sorted(HmsBasinBuilder.SUPPORTED_TERMINAL_NODE_MODES)}"
            )
        return mode

    @staticmethod
    def _normalize_unit_system(unit_system: str) -> str:
        """Canonicalize supported HMS unit system values."""
        normalized = re.sub(r"[\s_\-]+", " ", str(unit_system).strip().lower())
        if normalized not in HmsBasinBuilder.SUPPORTED_UNIT_SYSTEMS:
            raise ValueError(
                f"Unsupported unit_system {unit_system!r}; "
                f"expected one of {sorted(set(HmsBasinBuilder.SUPPORTED_UNIT_SYSTEMS.values()))}"
            )
        return HmsBasinBuilder.SUPPORTED_UNIT_SYSTEMS[normalized]

    @staticmethod
    def _local_hms_timestamp() -> Dict[str, str]:
        """Return HMS-style local date/time strings."""
        now = datetime.now()
        return {
            "date": f"{now.day} {now.strftime('%B %Y')}",
            "time": now.strftime("%H:%M:%S"),
        }

    @staticmethod
    def _format_hms_datetime(value: datetime) -> Dict[str, str]:
        """Format an arbitrary datetime using HMS date/time strings."""
        return {
            "date": f"{value.day} {value.strftime('%B %Y')}",
            "time": value.strftime("%H:%M"),
        }

    @staticmethod
    def _format_hms_scalar(value: Union[int, float]) -> str:
        """Format a numeric scalar using compact HMS-friendly text."""
        numeric = float(value)
        if numeric.is_integer():
            return str(int(numeric))
        return f"{numeric:.6f}".rstrip("0").rstrip(".")

    @staticmethod
    def _format_hms_depth(value: float) -> str:
        """Format a cumulative depth value for a Frequency Based Hypothetical met file."""
        depth_value = max(float(value), 0.0001)
        return f"{depth_value:.4f}".rstrip("0").rstrip(".")

    @staticmethod
    def _sanitize_file_stem(name: str) -> str:
        """Build a filesystem-safe file stem while preserving readable HMS names."""
        sanitized = re.sub(r"[^A-Za-z0-9._+\-]+", "_", str(name).strip())
        sanitized = re.sub(r"_+", "_", sanitized).strip("._")
        if not sanitized:
            raise ValueError(f"Could not build a file stem from {name!r}")
        return sanitized

    @staticmethod
    def _read_text_with_fallback(path: Path) -> str:
        """Read a text file using the common HMS encodings."""
        return HmsFileParser.read_file(path)

    @staticmethod
    def _write_text(path: Path, content: str) -> Path:
        """Write UTF-8 text content with parent creation."""
        path.parent.mkdir(parents=True, exist_ok=True)
        HmsFileParser.write_file(path, content)
        return path

    @staticmethod
    def _resolve_spec_crs(spec: Mapping[str, Any]):
        """Resolve a pyproj CRS object from a TauDEM HMS spec."""
        deps = HmsBasinBuilder._check_dependencies()
        CRS = deps["CRS"]

        crs_section = spec.get("crs", {})
        crs_value = crs_section.get("native") or crs_section.get("epsg")
        if not crs_value:
            raise ValueError("Spec is missing CRS metadata")
        return CRS.from_user_input(crs_value)

    @staticmethod
    def _point_to_latlon(x: float, y: float, crs) -> Dict[str, float]:
        """Convert a projected point into latitude/longitude."""
        deps = HmsBasinBuilder._check_dependencies()
        gpd = deps["gpd"]
        Point = deps["Point"]

        point_series = gpd.GeoSeries([Point(float(x), float(y))], crs=crs).to_crs("EPSG:4326")
        point = point_series.iloc[0]
        return {"latitude": float(point.y), "longitude": float(point.x)}

    @staticmethod
    def _spec_bounds(spec: Mapping[str, Any], crs_value: str) -> Dict[str, float]:
        """Compute combined geometry bounds for a TauDEM HMS spec."""
        all_records: List[Mapping[str, Any]] = []
        for key in ("subbasins", "reaches", "junctions"):
            all_records.extend(spec.get(key, []))
        all_records.append(spec["sink"])
        gdf = HmsBasinBuilder._records_to_gdf(all_records, crs_value)
        west, south, east, north = gdf.total_bounds
        return {
            "west": float(west),
            "south": float(south),
            "east": float(east),
            "north": float(north),
        }

    @staticmethod
    def _append_block(lines: List[str], header: str, fields: Sequence[tuple[str, Any]]) -> None:
        """Append a simple HMS block to a list of lines."""
        lines.append(header)
        for key, value in fields:
            if value is None:
                continue
            lines.append(f"     {key}: {value}")
        lines.extend(["End:", ""])

    @staticmethod
    def _terminal_junction_record(spec: Mapping[str, Any]) -> Dict[str, Any]:
        """Build a terminal junction record from the spec sink for control variants."""
        sink = dict(spec["sink"])
        return {
            "name": sink["name"],
            "type": "Junction",
            "source_ids": {"derived_from_sink": True},
            "downstream": None,
            "upstream_reaches": list(sink.get("upstream_reaches", [])),
            "x": sink["x"],
            "y": sink["y"],
            "canvas_x": sink["canvas_x"],
            "canvas_y": sink["canvas_y"],
            "geometry": sink["geometry"],
        }

    @staticmethod
    def _normalize_project_block_geometry_columns(sqlite_path: Path) -> None:
        """Force SQLite layer metadata to the same geometry types used by HMS examples."""
        geometry_type_by_table = {
            "subbasin": 1,
            "reach": 2,
            "junction": 1,
            "sink": 1,
            "subbasin2d": 6,
            "reach2d": 2,
        }
        conn = sqlite3.connect(str(sqlite_path))
        try:
            cursor = conn.cursor()
            for table_name, geometry_type in geometry_type_by_table.items():
                cursor.execute(
                    """
                    UPDATE geometry_columns
                       SET geometry_type = ?, coord_dimension = 2, geometry_format = 'WKB'
                     WHERE f_table_name = ?
                    """,
                    (geometry_type, table_name),
                )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _build_project_registry_block(
        block_type: str,
        logical_name: str,
        filename: str,
        description: str = "",
    ) -> str:
        """Build a real HMS registry block for the .hms project file."""
        return build_project_registry_block(
            block_type=block_type,
            logical_name=logical_name,
            filename=filename,
            description=description,
        )

    @staticmethod
    def _register_project_block(
        hms_path: Union[str, Path],
        block_type: str,
        logical_name: str,
        filename: str,
        description: str = "",
    ) -> Path:
        """Register a Basin/Precipitation/Control block in a real HMS project file."""
        return register_project_block(
            hms_path,
            entry_type=block_type,
            logical_name=logical_name,
            filename=filename,
            description=description,
            allow_existing=False,
        )

    @staticmethod
    def _rewrite_project_block(
        hms_path: Union[str, Path],
        block_type: str,
        logical_name: str,
        filename: str,
        description: str = "",
    ) -> Path:
        """Rewrite an existing Basin/Precipitation/Control block in a .hms file."""
        return rewrite_project_block(
            hms_path,
            entry_type=block_type,
            logical_name=logical_name,
            filename=filename,
            description=description,
        )

    @staticmethod
    def _clone_placeholder_met(
        template_met_path: Path,
        met_path: Path,
        met_name: str,
        basin_name: str,
    ) -> Path:
        """Clone a met file and wire it to the new basin as a non-production placeholder."""
        content = HmsBasinBuilder._read_text_with_fallback(template_met_path)
        content = re.sub(r"^Meteorology:\s*.*$", f"Meteorology: {met_name}", content, flags=re.MULTILINE)

        met_block_match = re.search(
            r"^(Meteorology:\s*.*?\n)(.*?)(^End:\s*$)",
            content,
            flags=re.MULTILINE | re.DOTALL,
        )
        if not met_block_match:
            raise ValueError(f"Could not find Meteorology block in {template_met_path.name}")

        body = met_block_match.group(2)
        description_line = "     Description: TauDEM import placeholder; non-production scaffold"
        if re.search(r"^\s+Description:", body, flags=re.MULTILINE):
            body = re.sub(r"^\s+Description:.*$", description_line, body, flags=re.MULTILINE)
        else:
            body = description_line + "\n" + body

        basin_model_pattern = rf"^\s+Use Basin Model:\s*{re.escape(basin_name)}\s*$"
        if not re.search(basin_model_pattern, body, flags=re.MULTILINE):
            body = body.rstrip() + f"\n     Use Basin Model: {basin_name}\n"

        content = content[:met_block_match.start(2)] + body + content[met_block_match.end(2):]
        content = content.replace("Depth: 0.0\n", "Depth: 0.0001\n")
        return HmsBasinBuilder._write_text(met_path, content)

    @staticmethod
    def _clone_placeholder_control(
        template_control_path: Path,
        control_path: Path,
        control_name: str,
    ) -> Path:
        """Clone a control file and rename it for TauDEM import scaffolding."""
        content = HmsBasinBuilder._read_text_with_fallback(template_control_path)
        content = re.sub(r"^Control:\s*.*$", f"Control: {control_name}", content, flags=re.MULTILINE)
        description_line = "     Description: TauDEM import placeholder; non-production scaffold"
        if re.search(r"^\s+Description:", content, flags=re.MULTILINE):
            content = re.sub(r"^\s+Description:.*$", description_line, content, flags=re.MULTILINE)
        else:
            content = re.sub(
                r"^(Control:\s*.*\n)",
                rf"\1{description_line}\n",
                content,
                count=1,
                flags=re.MULTILINE,
            )
        return HmsBasinBuilder._write_text(control_path, content)

    @staticmethod
    def _write_run_block(
        run_path: Path,
        run_name: str,
        basin_name: str,
        met_name: str,
        control_name: str,
        dss_file: str,
        log_file: str,
        description: str = "TauDEM import scaffold; topology/geometry validation only",
    ) -> Path:
        """Upsert an HMS run block into the project run file used by HEC-HMS."""
        timestamp = HmsBasinBuilder._local_hms_timestamp()
        lines = [
            f"Run: {run_name}",
            "     Default Description: No",
            f"     Description: {description}",
            f"     Log File: {log_file}",
            f"     DSS File: {dss_file}",
            "     Is Save Spatial Results: No",
            f"     Last Modified Date: {timestamp['date']}",
            f"     Last Modified Time: {timestamp['time']}",
            f"     Basin: {basin_name}",
            f"     Precip: {met_name}",
            f"     Control: {control_name}",
            "     Save State Type: None",
            "     Time-Series Output: Save All",
            "     Time Series Results Manager Start:",
            "     Time Series Results Manager End:",
            "End:",
            "",
        ]
        block = "\n".join(lines).strip() + "\n"

        if run_path.exists():
            content = HmsBasinBuilder._read_text_with_fallback(run_path)
        else:
            content = ""

        pattern = re.compile(
            rf"(^Run:\s*{re.escape(run_name)}\s*$.*?^End:\s*$\n?)",
            flags=re.MULTILINE | re.DOTALL,
        )
        if pattern.search(content):
            new_content = pattern.sub(block, content, count=1)
        elif content.strip():
            new_content = content.rstrip() + "\n\n" + block
        else:
            new_content = block

        return HmsBasinBuilder._write_text(run_path, new_content)

    @staticmethod
    def _resolve_atlas14_query_point(
        spec: Mapping[str, Any],
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Resolve the NOAA Atlas 14 query point for a TauDEM HMS spec."""
        if (latitude is None) ^ (longitude is None):
            raise ValueError("atlas14_latitude and atlas14_longitude must be provided together")

        if latitude is not None and longitude is not None:
            return {
                "source": "user_supplied",
                "latitude": float(latitude),
                "longitude": float(longitude),
                "x": None,
                "y": None,
            }

        deps = HmsBasinBuilder._check_dependencies()
        shape = deps["shape"]
        unary_union = deps["unary_union"]
        basin_geometry = unary_union([shape(record["geometry"]) for record in spec["subbasins"]])
        centroid = basin_geometry.centroid
        crs = HmsBasinBuilder._resolve_spec_crs(spec)
        latlon = HmsBasinBuilder._point_to_latlon(float(centroid.x), float(centroid.y), crs)
        return {
            "source": "basin_centroid",
            "latitude": latlon["latitude"],
            "longitude": latlon["longitude"],
            "x": float(centroid.x),
            "y": float(centroid.y),
        }

    @staticmethod
    @log_call
    def write_atlas14_frequency_met_file(
        met_path: Union[str, Path],
        met_name: str,
        basin_name: str,
        subbasin_names: Sequence[str],
        depths_inches: Sequence[float],
        ari_years: int = 100,
        total_duration_minutes: int = 1440,
        time_interval_minutes: int = 5,
        peak_position_percent: int = 67,
        unit_system: str = "English",
        description: Optional[str] = None,
    ) -> Path:
        """Write a compute-ready Atlas 14 Frequency Based Hypothetical .met file."""
        unit_system = HmsBasinBuilder._normalize_unit_system(unit_system)
        met_path = Path(met_path)
        met_path.parent.mkdir(parents=True, exist_ok=True)

        if ari_years <= 0:
            raise ValueError("ari_years must be positive")
        if total_duration_minutes <= 0:
            raise ValueError("total_duration_minutes must be positive")
        if time_interval_minutes <= 0:
            raise ValueError("time_interval_minutes must be positive")
        if total_duration_minutes % time_interval_minutes != 0:
            raise ValueError("total_duration_minutes must be divisible by time_interval_minutes")
        if not depths_inches:
            raise ValueError("depths_inches must contain at least one cumulative depth value")
        if not subbasin_names:
            raise ValueError("subbasin_names must contain at least one subbasin")

        exceedance_frequency_pct = 100.0 / float(ari_years)
        storm_size = exceedance_frequency_pct / 100.0
        timestamp = HmsBasinBuilder._local_hms_timestamp()
        if description is None:
            description = (
                f"Atlas 14 frequency storm ({ari_years}-year, "
                f"{int(round(total_duration_minutes / 60.0))}-hour)"
            )

        lines: List[str] = [
            f"Meteorology: {met_name}",
            f"     Description: {description}",
            f"     Last Modified Date: {timestamp['date']}",
            f"     Last Modified Time: {timestamp['time']}",
            f"     Version: {HmsBasinBuilder.FREQUENCY_STORM_MET_VERSION}",
            f"     Unit System: {unit_system}",
            "     Precipitation Method: Frequency Based Hypothetical",
            "     Snowmelt Method: None",
            f"     Use Basin Model: {basin_name}",
            "End:",
            "",
            "Precip Method Parameters: Frequency Based Hypothetical",
            f"     Exceedence Frequency: {HmsBasinBuilder._format_hms_scalar(exceedance_frequency_pct)}",
            "     Single Hypothetical Storm Size: Yes",
            "     Convert From Annual Series: No",
            "     Convert to Annual Series: Yes",
            f"     Storm Size: {HmsBasinBuilder._format_hms_scalar(storm_size)}",
            f"     Total Duration: {int(total_duration_minutes)}",
            f"     Time Interval: {int(time_interval_minutes)}",
            f"     Percent of Duration Before Peak Rainfall: {int(peak_position_percent)}",
        ]
        lines.extend(
            f"     Depth: {HmsBasinBuilder._format_hms_depth(depth)}"
            for depth in depths_inches
        )
        lines.extend(["End:", ""])

        for subbasin_name in subbasin_names:
            lines.extend([f"Subbasin: {subbasin_name}", "End:", ""])

        return HmsBasinBuilder._write_text(met_path, "\n".join(lines))

    @staticmethod
    def _write_atlas14_control_file(
        control_path: Union[str, Path],
        control_name: str,
        total_duration_minutes: int = 1440,
        time_interval_minutes: int = 5,
        tail_duration_minutes: int = 1440,
        start_datetime: Optional[datetime] = None,
        hms_version_profile: str = "4.13",
    ) -> Path:
        """Write a minimal HMS 4.13 control file for Atlas 14 compute testing."""
        HmsBasinBuilder._validate_supported_hms_profile(hms_version_profile)
        if total_duration_minutes <= 0:
            raise ValueError("total_duration_minutes must be positive")
        if time_interval_minutes <= 0:
            raise ValueError("time_interval_minutes must be positive")
        if tail_duration_minutes < 0:
            raise ValueError("tail_duration_minutes must be non-negative")

        control_path = Path(control_path)
        control_path.parent.mkdir(parents=True, exist_ok=True)
        if start_datetime is None:
            start_datetime = datetime(2000, 1, 1, 0, 0)
        end_datetime = start_datetime + timedelta(
            minutes=int(total_duration_minutes + tail_duration_minutes)
        )
        timestamp = HmsBasinBuilder._local_hms_timestamp()
        start_text = HmsBasinBuilder._format_hms_datetime(start_datetime)
        end_text = HmsBasinBuilder._format_hms_datetime(end_datetime)
        lines = [
            f"Control: {control_name}",
            f"     Last Modified Date: {timestamp['date']}",
            f"     Last Modified Time: {timestamp['time']}",
            f"     Version: {hms_version_profile}",
            f"     Start Date: {start_text['date']}",
            f"     Start Time: {start_text['time']}",
            f"     End Date: {end_text['date']}",
            f"     End Time: {end_text['time']}",
            f"     Time Interval: {int(time_interval_minutes)}",
            "End:",
            "",
        ]
        return HmsBasinBuilder._write_text(control_path, "\n".join(lines))

    @staticmethod
    @log_call
    def write_basin_scaffold(
        spec: Mapping[str, Any],
        basin_path: Union[str, Path],
        basin_name: str,
        hms_version_profile: str = "4.13",
        terminal_node_mode: str = "sink",
    ) -> Path:
        """Write an HMS 4.13-style basin scaffold from a TauDEM HMS spec."""
        HmsBasinBuilder._validate_supported_hms_profile(hms_version_profile)
        terminal_mode = HmsBasinBuilder._validate_terminal_node_mode(terminal_node_mode)

        deps = HmsBasinBuilder._check_dependencies()
        shape = deps["shape"]

        basin_path = Path(basin_path)
        basin_path.parent.mkdir(parents=True, exist_ok=True)

        crs = HmsBasinBuilder._resolve_spec_crs(spec)
        crs_value = spec["crs"].get("native") or spec["crs"].get("epsg") or str(crs)
        crs_wkt = crs.to_wkt()
        timestamp = HmsBasinBuilder._local_hms_timestamp()
        bounds = HmsBasinBuilder._spec_bounds(spec, crs_value)
        sqlite_name = basin_path.with_suffix(".sqlite").name
        unit_system = HmsBasinBuilder._normalize_unit_system(spec.get("unit_system", "English"))

        lines: List[str] = [
            f"Basin: {basin_name}",
            f"     Last Modified Date: {timestamp['date']}",
            f"     Last Modified Time: {timestamp['time']}",
            f"     Version: {hms_version_profile}",
            "     Filepath Separator: \\",
            f"     Unit System: {unit_system}",
            "     Missing Flow To Zero: No",
            "     Enable Flow Ratio: No",
            "     Compute Local Flow At Junctions: No",
            "     Unregulated Output Required: No",
            "",
            "     Enable Sediment Routing: No",
            "End:",
            "",
        ]

        for record in spec["subbasins"]:
            latlon = HmsBasinBuilder._point_to_latlon(record["centroid_x"], record["centroid_y"], crs)
            area_value = record["area_sqmi"] if unit_system == "English" else record["area_sqkm"]
            lag_minutes = max(5.0, round(max(record.get("area_sqmi", 0.1), 0.1) * 30.0, 3))
            fields = [
                ("Last Modified Date", timestamp["date"]),
                ("Last Modified Time", timestamp["time"]),
                ("Latitude Degrees", f"{latlon['latitude']:.12f}"),
                ("Longitude Degrees", f"{latlon['longitude']:.12f}"),
                ("Canvas X", record["canvas_x"]),
                ("Canvas Y", record["canvas_y"]),
                ("Area", round(area_value, 6)),
                ("Downstream", record["downstream"]),
                ("Discretization", "None"),
                ("File", sqlite_name),
                ("Canopy", "None"),
                ("Allow Simultaneous Precip Et", "No"),
                ("Plant Uptake Method", "Simple"),
                ("Surface", "None"),
                ("LossRate", "Deficit Constant"),
                ("Percent Impervious Area", 0),
                ("Initial Deficit", 0),
                ("Maximum Deficit", 0.5 if unit_system == "English" else 12.7),
                ("Percolation Rate", 0.02 if unit_system == "English" else 0.508),
                ("Recovery Factor", 1.0),
                ("Transform", "SCS"),
                ("Lag", lag_minutes),
                ("Unitgraph Type", "STANDARD"),
                ("Baseflow", "None"),
            ]
            HmsBasinBuilder._append_block(lines, f"Subbasin: {record['name']}", fields)

        for record in spec["reaches"]:
            line = shape(record["geometry"])
            midpoint = line.interpolate(0.5, normalized=True)
            routing_k = max(1.0, round(max(record.get("length_mi", 0.1), 0.1) * 2.0, 3))
            fields = [
                ("Last Modified Date", timestamp["date"]),
                ("Last Modified Time", timestamp["time"]),
                ("Canvas X", record["canvas_x"]),
                ("Canvas Y", record["canvas_y"]),
                ("From Canvas X", record["from_canvas_x"]),
                ("From Canvas Y", record["from_canvas_y"]),
                ("Label X", midpoint.x),
                ("Label Y", midpoint.y),
                ("Downstream", record["downstream"]),
                ("Route", "Muskingum"),
                ("Initial Variable", "Combined Inflow"),
                ("Muskingum K", routing_k),
                ("Muskingum x", 0.2),
                ("Muskingum Steps", 5),
                ("Channel Loss", "None"),
            ]
            HmsBasinBuilder._append_block(lines, f"Reach: {record['name']}", fields)

        junction_records = list(spec["junctions"])
        if terminal_mode == "junction":
            junction_records.append(HmsBasinBuilder._terminal_junction_record(spec))

        for record in junction_records:
            fields = [
                ("Last Modified Date", timestamp["date"]),
                ("Last Modified Time", timestamp["time"]),
                ("Canvas X", record["canvas_x"]),
                ("Canvas Y", record["canvas_y"]),
                ("Downstream", record.get("downstream")),
            ]
            HmsBasinBuilder._append_block(lines, f"Junction: {record['name']}", fields)

        if terminal_mode == "sink":
            sink = spec["sink"]
            sink_fields = [
                ("Last Modified Date", timestamp["date"]),
                ("Last Modified Time", timestamp["time"]),
                ("Canvas X", sink["canvas_x"]),
                ("Canvas Y", sink["canvas_y"]),
            ]
            HmsBasinBuilder._append_block(lines, f"Sink: {sink['name']}", sink_fields)

        lines.extend(
            [
                "Basin Layer Properties:",
                "     Element Layer:",
                "          Name: Icons",
                "          Layer shown: Yes",
                "     End Layer:",
                "     Element Layer:",
                "          Name: Subbasins",
                "          Layer shown: Yes",
                "     End Layer:",
                "     Discretization Layer:",
                "          Layer shown: Yes",
                "     End Layer:",
                "     2D Connection Layer:",
                "          Layer shown: Yes",
                "     End Layer:",
                "End:",
                "",
                "Basin Spatial Properties:",
                f"     Coordinate System: {crs_wkt}",
                "End:",
                "",
                "Basin Schematic Properties:",
                f"     Coordinate System: {crs_wkt}",
                f"     Last View N: {bounds['north']}",
                f"     Last View S: {bounds['south']}",
                f"     Last View W: {bounds['west']}",
                f"     Last View E: {bounds['east']}",
                f"     Maximum View N: {bounds['north']}",
                f"     Maximum View S: {bounds['south']}",
                f"     Maximum View W: {bounds['west']}",
                f"     Maximum View E: {bounds['east']}",
                "     Extent Method: Elements",
                "     Buffer: 0",
                "     Draw Icons: Yes",
                "     Draw Icon Labels: Name",
                "     Draw Map Objects: Yes",
                "     Draw Gridlines: No",
                "     Draw Flow Direction: No",
                "     Draw HillShade Layer: Yes",
                "     Draw Elevation Layer: Yes",
                "     Elevation Layer Color Palette: Default",
                "     Ignore Elevation Color Ramp Scale: No",
                "     Use Interpolated Color Ramp for Elevation Layer: Yes",
                "     Color Ramp Opacity Level for Elevation Layer: 33.0",
                "     Fix Element Locations: No",
                "     Fix Hydrologic Order: No",
                "End:",
                "",
            ]
        )

        return HmsBasinBuilder._write_text(basin_path, "\n".join(lines))

    @staticmethod
    @log_call
    def write_sqlite_geometry(
        spec: Mapping[str, Any],
        sqlite_path: Union[str, Path],
        include_empty_compat_layers: bool = True,
        terminal_node_mode: str = "sink",
    ) -> Path:
        """Write a TauDEM HMS geometry package using the HMS SQLite layer contract."""
        deps = HmsBasinBuilder._check_dependencies()
        gpd = deps["gpd"]
        Point = deps["Point"]
        terminal_mode = HmsBasinBuilder._validate_terminal_node_mode(terminal_node_mode)

        sqlite_path = Path(sqlite_path)
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        if sqlite_path.exists():
            sqlite_path.unlink()

        crs = HmsBasinBuilder._resolve_spec_crs(spec)
        crs_value = spec["crs"].get("native") or spec["crs"].get("epsg") or str(crs)

        subbasins_2d = HmsBasinBuilder._records_to_gdf(spec["subbasins"], crs_value).copy()
        subbasin_centroids = gpd.GeoSeries(
            [geometry.centroid for geometry in subbasins_2d.geometry],
            crs=crs,
        ).to_crs("EPSG:4326")
        subbasins_2d["latitude"] = subbasin_centroids.y.astype(float)
        subbasins_2d["longitude"] = subbasin_centroids.x.astype(float)
        subbasins_2d = subbasins_2d[
            ["name", "centroid_x", "centroid_y", "area_sqkm", "latitude", "longitude", "geometry"]
        ]

        subbasin_points = gpd.GeoDataFrame(
            {"name": subbasins_2d["name"].tolist()},
            geometry=[Point(xy) for xy in zip(subbasins_2d["centroid_x"], subbasins_2d["centroid_y"])],
            crs=crs,
        )

        reaches_2d = HmsBasinBuilder._records_to_gdf(spec["reaches"], crs_value).copy()
        reaches_2d["linkno"] = reaches_2d["source_ids"].apply(lambda value: json.loads(value)["linkno"])
        reaches_2d["dslinkno"] = reaches_2d["source_ids"].apply(
            lambda value: json.loads(value).get("downstream_linkno")
        )
        reaches_2d["wsno"] = reaches_2d["source_ids"].apply(lambda value: json.loads(value)["wsno"])
        reaches_2d["strmorder"] = reaches_2d["stream_order"]
        reaches_2d["length"] = reaches_2d["length_m"]
        reaches_2d = reaches_2d[
            ["name", "linkno", "dslinkno", "wsno", "strmorder", "length", "slope", "geometry"]
        ]

        reach_lines = reaches_2d[["name", "geometry"]].copy()
        empty_point_layer = gpd.GeoDataFrame({"name": []}, geometry=[], crs=crs)
        empty_line_layer = gpd.GeoDataFrame({"name": []}, geometry=[], crs=crs)

        junction_records = list(spec["junctions"])
        sink_records: List[Mapping[str, Any]] = []
        if terminal_mode == "junction":
            junction_records.append(HmsBasinBuilder._terminal_junction_record(spec))
        else:
            sink_records = [spec["sink"]]

        junctions = (
            HmsBasinBuilder._records_to_gdf(junction_records, crs_value)[["name", "geometry"]].copy()
            if junction_records
            else empty_point_layer.copy()
        )
        sink = (
            HmsBasinBuilder._records_to_gdf(sink_records, crs_value)[["name", "geometry"]].copy()
            if sink_records
            else empty_point_layer.copy()
        )

        layers = [
            ("subbasin2d", subbasins_2d),
            ("reach2d", reaches_2d),
        ]
        if include_empty_compat_layers:
            layers.extend(
                [
                    ("subbasin", subbasin_points),
                    ("reach", reach_lines),
                    ("junction", junctions if len(junctions) else empty_point_layer),
                    ("sink", sink if len(sink) else empty_point_layer),
                ]
            )

        for layer_name, layer_gdf in layers:
            layer_gdf.to_file(sqlite_path, driver="SQLite", layer=layer_name)

        HmsBasinBuilder._normalize_project_block_geometry_columns(sqlite_path)
        return sqlite_path

    @staticmethod
    @log_call
    def bootstrap_taudem_project(
        spec: Mapping[str, Any],
        template_project_dir: Union[str, Path],
        output_dir: Union[str, Path],
        basin_name: str,
        met_name: str,
        control_name: str,
        run_name: str,
        hms_version_profile: str = "4.13",
        terminal_node_mode: str = "sink",
    ) -> Dict[str, Path]:
        """Clone a real HMS project shell and stage a TauDEM import into it."""
        from .HmsPrj import HmsPrj

        HmsBasinBuilder._validate_supported_hms_profile(hms_version_profile)
        HmsBasinBuilder._validate_terminal_node_mode(terminal_node_mode)

        template_project_dir = Path(template_project_dir)
        output_dir = Path(output_dir)
        if not template_project_dir.is_dir():
            raise FileNotFoundError(f"Template project directory not found: {template_project_dir}")
        if output_dir.exists():
            raise FileExistsError(f"Output project directory already exists: {output_dir}")

        shutil.copytree(template_project_dir, output_dir)
        project = HmsPrj().initialize(output_dir)
        if project.project_file is None:
            raise FileNotFoundError(f"No .hms project file found in cloned directory: {output_dir}")
        if project.met_df.empty:
            raise ValueError(f"Template project has no meteorology models: {template_project_dir}")
        if project.control_df.empty:
            raise ValueError(f"Template project has no control specifications: {template_project_dir}")

        basin_stem = HmsBasinBuilder._sanitize_file_stem(basin_name)
        met_stem = HmsBasinBuilder._sanitize_file_stem(met_name)
        control_stem = HmsBasinBuilder._sanitize_file_stem(control_name)
        run_stem = HmsBasinBuilder._sanitize_file_stem(run_name)
        basin_path = output_dir / f"{basin_stem}.basin"
        sqlite_path = output_dir / f"{basin_stem}.sqlite"
        met_path = output_dir / f"{met_stem}.met"
        control_path = output_dir / f"{control_stem}.control"
        run_path = project.project_file.with_suffix(".run")

        HmsBasinBuilder.write_basin_scaffold(
            spec=spec,
            basin_path=basin_path,
            basin_name=basin_name,
            hms_version_profile=hms_version_profile,
            terminal_node_mode=terminal_node_mode,
        )
        HmsBasinBuilder.write_sqlite_geometry(
            spec=spec,
            sqlite_path=sqlite_path,
            include_empty_compat_layers=True,
            terminal_node_mode=terminal_node_mode,
        )

        template_met_path = Path(project.met_df.iloc[0]["full_path"])
        template_control_path = Path(project.control_df.iloc[0]["full_path"])
        HmsBasinBuilder._clone_placeholder_met(template_met_path, met_path, met_name, basin_name)
        HmsBasinBuilder._clone_placeholder_control(template_control_path, control_path, control_name)

        HmsBasinBuilder._register_project_block(
            hms_path=project.project_file,
            block_type="Basin",
            logical_name=basin_name,
            filename=basin_path.name,
            description="TauDEM import scaffold; topology/geometry validation only",
        )
        HmsBasinBuilder._register_project_block(
            hms_path=project.project_file,
            block_type="Precipitation",
            logical_name=met_name,
            filename=met_path.name,
            description="TauDEM import placeholder met; non-production scaffold",
        )
        HmsBasinBuilder._register_project_block(
            hms_path=project.project_file,
            block_type="Control",
            logical_name=control_name,
            filename=control_path.name,
            description="TauDEM import placeholder control; non-production scaffold",
        )

        HmsBasinBuilder._write_run_block(
            run_path=run_path,
            run_name=run_name,
            basin_name=basin_name,
            met_name=met_name,
            control_name=control_name,
            dss_file=f"{run_stem}.dss",
            log_file=f"{run_stem}.log",
        )

        report_path = output_dir / "taudem_bootstrap_report.json"
        report_payload = {
            "schema_version": "1.0",
            "study_type": "taudem_hms_bootstrap_report",
            "generated_at": HmsBasinBuilder._utc_now(),
            "template_project_dir": str(template_project_dir.resolve()),
            "output_dir": str(output_dir.resolve()),
            "hms_project_file": str(project.project_file.resolve()),
            "terminal_node_mode": terminal_node_mode,
            "hms_version_profile": hms_version_profile,
            "names": {
                "basin": basin_name,
                "met": met_name,
                "control": control_name,
                "run": run_name,
            },
            "files": {
                "basin": str(basin_path.resolve()),
                "sqlite": str(sqlite_path.resolve()),
                "met": str(met_path.resolve()),
                "control": str(control_path.resolve()),
                "run": str(run_path.resolve()),
            },
            "counts": spec.get("counts", {}),
            "builder": {
                "package": "hms-commander",
                "class": "HmsBasinBuilder",
                "method": "bootstrap_taudem_project",
                "version": PACKAGE_VERSION,
            },
        }
        HmsBasinBuilder._write_json(report_path, report_payload)

        return {
            "project_dir": output_dir,
            "project_file": project.project_file,
            "basin": basin_path,
            "sqlite": sqlite_path,
            "met": met_path,
            "control": control_path,
            "run": run_path,
            "bootstrap_report": report_path,
        }

    @staticmethod
    @log_call
    def bootstrap_taudem_atlas14_project(
        spec: Mapping[str, Any],
        template_project_dir: Union[str, Path],
        output_dir: Union[str, Path],
        basin_name: str,
        met_name: str,
        control_name: str,
        run_name: str,
        ari_years: int = 100,
        total_duration_minutes: int = 1440,
        time_interval_minutes: int = 5,
        peak_position_percent: int = 67,
        atlas14_latitude: Optional[float] = None,
        atlas14_longitude: Optional[float] = None,
        atlas14_series: str = "pds",
        atlas14_units: str = "english",
        atlas14_depths: Optional[Sequence[float]] = None,
        atlas14_depth_table: Optional[Union[pd.DataFrame, Sequence[Mapping[str, Any]]]] = None,
        atlas14_cache_dir: Optional[Union[str, Path]] = None,
        tail_duration_minutes: int = 1440,
        hms_version_profile: str = "4.13",
        terminal_node_mode: str = "sink",
    ) -> Dict[str, Path]:
        """Bootstrap a compute-ready TauDEM HMS project with an Atlas 14 frequency storm."""
        from .Atlas14Storm import Atlas14Storm

        project_paths = HmsBasinBuilder.bootstrap_taudem_project(
            spec=spec,
            template_project_dir=template_project_dir,
            output_dir=output_dir,
            basin_name=basin_name,
            met_name=met_name,
            control_name=control_name,
            run_name=run_name,
            hms_version_profile=hms_version_profile,
            terminal_node_mode=terminal_node_mode,
        )

        unit_system = HmsBasinBuilder._normalize_unit_system(spec.get("unit_system", "English"))
        query_point = HmsBasinBuilder._resolve_atlas14_query_point(
            spec,
            latitude=atlas14_latitude,
            longitude=atlas14_longitude,
        )
        durations_min = list(Atlas14Storm.FREQUENCY_STORM_DURATIONS_MIN)
        if durations_min[-1] != int(total_duration_minutes):
            raise ValueError(
                "Current Atlas 14 TauDEM bootstrap expects the final frequency-storm duration "
                f"to match total_duration_minutes ({durations_min[-1]} != {total_duration_minutes})."
            )

        depth_duration_table_df: Optional[pd.DataFrame] = None
        atlas14_point_frequency: Optional[Dict[str, Any]] = None
        native_units = Atlas14Storm.normalize_depth_units(atlas14_units)
        if atlas14_depths is not None:
            if atlas14_depth_table is not None:
                depth_duration_table_df = pd.DataFrame(atlas14_depth_table).copy()
            resolved_depths_native_units = [float(value) for value in atlas14_depths]
            resolved_depths = Atlas14Storm.convert_depths_to_inches(
                resolved_depths_native_units,
                units=native_units,
            )
        elif atlas14_depth_table is not None:
            depth_duration_table_df = pd.DataFrame(atlas14_depth_table).copy()
            resolved_depths_native_units = Atlas14Storm.build_frequency_storm_depths(
                depth_table=depth_duration_table_df,
                ari_years=ari_years,
                durations_min=durations_min,
            )
            resolved_depths = Atlas14Storm.convert_depths_to_inches(
                resolved_depths_native_units,
                units=native_units,
            )
        else:
            atlas14_result = Atlas14Storm.get_frequency_storm_depths(
                latitude=query_point["latitude"],
                longitude=query_point["longitude"],
                ari_years=ari_years,
                series=atlas14_series,
                units=native_units,
                durations_min=durations_min,
                cache_dir=Path(atlas14_cache_dir) if atlas14_cache_dir is not None else None,
            )
            resolved_depths = atlas14_result["depths_inches"]
            resolved_depths_native_units = atlas14_result["depths_native_units"]
            native_units = atlas14_result["native_units"]
            depth_duration_table_df = atlas14_result["depth_duration_table"].copy()
            atlas14_point_frequency = atlas14_result["point_frequency"]

        if len(resolved_depths) != len(durations_min):
            raise ValueError(
                f"Expected {len(durations_min)} Atlas 14 cumulative depths for the HMS "
                f"frequency storm, received {len(resolved_depths)}"
            )

        met_description = (
            f"Atlas 14 NOAA PFDS {ari_years}-year frequency storm; "
            f"query=({query_point['latitude']:.6f}, {query_point['longitude']:.6f}) "
            f"source={query_point['source']}"
        )
        basin_registry_description = "TauDEM-derived basin scaffold for Atlas 14 compute testing"
        met_registry_description = "Atlas 14 frequency storm meteorology scaffold"
        control_registry_description = "Atlas 14 control specification scaffold"
        run_description = "TauDEM Atlas 14 frequency-storm compute scaffold"

        HmsBasinBuilder.write_atlas14_frequency_met_file(
            met_path=project_paths["met"],
            met_name=met_name,
            basin_name=basin_name,
            subbasin_names=[record["name"] for record in spec["subbasins"]],
            depths_inches=resolved_depths,
            ari_years=ari_years,
            total_duration_minutes=total_duration_minutes,
            time_interval_minutes=time_interval_minutes,
            peak_position_percent=peak_position_percent,
            unit_system=unit_system,
            description=met_description,
        )
        HmsBasinBuilder._write_atlas14_control_file(
            control_path=project_paths["control"],
            control_name=control_name,
            total_duration_minutes=total_duration_minutes,
            time_interval_minutes=time_interval_minutes,
            tail_duration_minutes=tail_duration_minutes,
            hms_version_profile=hms_version_profile,
        )
        HmsBasinBuilder._write_run_block(
            run_path=project_paths["run"],
            run_name=run_name,
            basin_name=basin_name,
            met_name=met_name,
            control_name=control_name,
            dss_file=f"{HmsBasinBuilder._sanitize_file_stem(run_name)}.dss",
            log_file=f"{HmsBasinBuilder._sanitize_file_stem(run_name)}.log",
            description=run_description,
        )

        HmsBasinBuilder._rewrite_project_block(
            hms_path=project_paths["project_file"],
            block_type="Basin",
            logical_name=basin_name,
            filename=project_paths["basin"].name,
            description=basin_registry_description,
        )
        HmsBasinBuilder._rewrite_project_block(
            hms_path=project_paths["project_file"],
            block_type="Precipitation",
            logical_name=met_name,
            filename=project_paths["met"].name,
            description=met_registry_description,
        )
        HmsBasinBuilder._rewrite_project_block(
            hms_path=project_paths["project_file"],
            block_type="Control",
            logical_name=control_name,
            filename=project_paths["control"].name,
            description=control_registry_description,
        )

        atlas14_report_path = Path(output_dir) / "atlas14_storm_report.json"
        atlas14_report = {
            "schema_version": "1.0",
            "study_type": "taudem_hms_atlas14_frequency_storm",
            "generated_at": HmsBasinBuilder._utc_now(),
            "project_dir": str(Path(output_dir).resolve()),
            "hms_version_profile": hms_version_profile,
            "terminal_node_mode": terminal_node_mode,
            "names": {
                "basin": basin_name,
                "met": met_name,
                "control": control_name,
                "run": run_name,
            },
            "query_point": query_point,
            "atlas14": {
                "series": atlas14_series,
                "units": native_units,
                "requested_units": atlas14_units,
                "ari_years": int(ari_years),
                "exceedance_frequency_pct": 100.0 / float(ari_years),
                "total_duration_minutes": int(total_duration_minutes),
                "time_interval_minutes": int(time_interval_minutes),
                "peak_position_percent": int(peak_position_percent),
                "durations_min": durations_min,
                "depths_inches": resolved_depths,
                "depths_native_units": resolved_depths_native_units,
                "native_units": native_units,
                "depth_duration_table": (
                    depth_duration_table_df.to_dict(orient="records")
                    if depth_duration_table_df is not None
                    else None
                ),
                "point_frequency": (
                    {
                        key: value
                        for key, value in atlas14_point_frequency.items()
                        if key not in {"depth_duration_table"}
                    }
                    if atlas14_point_frequency is not None
                    else None
                ),
            },
            "files": {
                "project_file": str(Path(project_paths["project_file"]).resolve()),
                "basin": str(Path(project_paths["basin"]).resolve()),
                "sqlite": str(Path(project_paths["sqlite"]).resolve()),
                "met": str(Path(project_paths["met"]).resolve()),
                "control": str(Path(project_paths["control"]).resolve()),
                "run": str(Path(project_paths["run"]).resolve()),
            },
            "counts": spec.get("counts", {}),
            "builder": {
                "package": "hms-commander",
                "class": "HmsBasinBuilder",
                "method": "bootstrap_taudem_atlas14_project",
                "version": PACKAGE_VERSION,
            },
        }
        HmsBasinBuilder._write_json(atlas14_report_path, atlas14_report)
        project_paths["atlas14_report"] = atlas14_report_path
        return project_paths
