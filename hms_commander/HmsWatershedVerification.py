"""
TauDEM watershed verification helpers.

This module compares TauDEM-derived watershed outputs against an official
reference boundary, writes a durable verification artifact, and can generate
review figures suitable for downstream workflows such as `ras-agent`.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Union

from .Decorators import log_call
from .LoggingConfig import get_logger

logger = get_logger(__name__)

try:
    PACKAGE_VERSION = version("hms-commander")
except PackageNotFoundError:  # pragma: no cover - fallback for source-only runs
    PACKAGE_VERSION = "0.2.1"


class HmsWatershedVerification:
    """Static helpers for TauDEM boundary verification and QA figures."""

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
    def _write_json(path: Path, payload: Mapping[str, Any]) -> Dict[str, Any]:
        """Write JSON with stable formatting."""
        existed = path.exists()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, default=HmsWatershedVerification._json_default) + "\n",
            encoding="utf-8",
        )
        return {"status": "updated" if existed else "created", "bytes": path.stat().st_size}

    @staticmethod
    def _write_vector(path: Path, gdf) -> Dict[str, Any]:
        """Write a vector dataset with stable overwrite behavior."""
        suffix = path.suffix.lower()
        driver_by_suffix = {
            ".geojson": "GeoJSON",
            ".json": "GeoJSON",
            ".shp": "ESRI Shapefile",
            ".gpkg": "GPKG",
        }
        if suffix not in driver_by_suffix:
            raise ValueError(f"Unsupported vector output format for {path}")

        existed = path.exists()
        path.parent.mkdir(parents=True, exist_ok=True)
        if suffix == ".shp":
            for sidecar_suffix in (".shp", ".shx", ".dbf", ".prj", ".cpg", ".qpj"):
                sidecar = path.with_suffix(sidecar_suffix)
                if sidecar.exists():
                    sidecar.unlink()
        elif path.exists():
            path.unlink()

        gdf.to_file(path, driver=driver_by_suffix[suffix])
        return {"status": "updated" if existed else "created", "bytes": path.stat().st_size}

    @staticmethod
    def _check_dependencies():
        """Import GIS dependencies only when verification is actually invoked."""
        try:
            import geopandas as gpd
            import numpy as np
            import rasterio
            from pyproj import CRS
            from rasterio.enums import Resampling
            from rasterio.features import shapes
            from shapely.geometry import MultiPolygon, Point, box, shape
            from shapely.ops import nearest_points, unary_union
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
            "Resampling": Resampling,
            "shapes": shapes,
            "shape": shape,
            "Point": Point,
            "MultiPolygon": MultiPolygon,
            "box": box,
            "nearest_points": nearest_points,
            "unary_union": unary_union,
        }

    @staticmethod
    def _check_plotting_dependencies():
        """Import plotting dependencies only when figure generation is invoked."""
        deps = HmsWatershedVerification._check_dependencies()
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from matplotlib.colors import ListedColormap
            from matplotlib.lines import Line2D
            from matplotlib.patches import Patch
        except ImportError as exc:  # pragma: no cover - exercised only in missing-deps env
            missing_pkg = str(exc).split("'")[1] if "'" in str(exc) else "matplotlib"
            raise ImportError(
                f"Missing required plotting package: {missing_pkg}\n"
                "Install with: pip install matplotlib"
            ) from exc

        deps.update(
            {
                "matplotlib": matplotlib,
                "plt": plt,
                "ListedColormap": ListedColormap,
                "Line2D": Line2D,
                "Patch": Patch,
            }
        )
        return deps

    @staticmethod
    def _resolve_crs(crs_value: Any, fallback_crs: Optional[Any] = None):
        """Resolve a CRS-like value, optionally falling back to a supplied CRS."""
        deps = HmsWatershedVerification._check_dependencies()
        CRS = deps["CRS"]
        if crs_value is None:
            return CRS.from_user_input(fallback_crs) if fallback_crs is not None else None
        try:
            resolved = CRS.from_user_input(crs_value)
        except Exception:
            return CRS.from_user_input(fallback_crs) if fallback_crs is not None else None

        if fallback_crs is not None and resolved.to_epsg() is None:
            return CRS.from_user_input(fallback_crs)
        return resolved

    @staticmethod
    def _load_vector(path: Union[str, Path], fallback_crs: Optional[Any] = None):
        """Read a vector file and apply fallback CRS when metadata is missing."""
        deps = HmsWatershedVerification._check_dependencies()
        gpd = deps["gpd"]

        path = Path(path)
        gdf = gpd.read_file(path)
        resolved_crs = HmsWatershedVerification._resolve_crs(gdf.crs, fallback_crs)
        if resolved_crs is None:
            raise ValueError(f"Could not determine CRS for vector dataset: {path}")
        if gdf.crs is None:
            gdf = gdf.set_crs(resolved_crs)
        else:
            gdf = gdf.set_crs(resolved_crs, allow_override=True)
        return gdf

    @staticmethod
    def _single_geometry(gdf):
        """Dissolve a GeoDataFrame into one valid geometry."""
        deps = HmsWatershedVerification._check_dependencies()
        unary_union = deps["unary_union"]

        geometry = unary_union([geom for geom in gdf.geometry if geom is not None and not geom.is_empty])
        if geometry.is_empty:
            raise ValueError("Dataset does not contain any non-empty geometries")
        if not geometry.is_valid:
            geometry = geometry.buffer(0)
        return geometry

    @staticmethod
    def _polygonize_watershed_raster(
        raster_path: Union[str, Path],
        fallback_crs: Optional[Any] = None,
        *,
        positive_only: bool = True,
    ):
        """Polygonize a TauDEM watershed grid by dissolving all valid watershed cells."""
        deps = HmsWatershedVerification._check_dependencies()
        gpd = deps["gpd"]
        np = deps["np"]
        rasterio = deps["rasterio"]
        shapes = deps["shapes"]
        shape = deps["shape"]
        unary_union = deps["unary_union"]

        raster_path = Path(raster_path)
        with rasterio.open(raster_path) as src:
            array = src.read(1)
            nodata = src.nodata
            mask = np.ones(array.shape, dtype=bool)
            if nodata is not None:
                mask &= array != nodata
            if positive_only:
                mask &= array > 0
            if not mask.any():
                raise ValueError(f"No watershed cells were found in {raster_path}")

            polygon_geometries = [
                shape(geom)
                for geom, _ in shapes(array.astype("int32"), mask=mask, transform=src.transform)
            ]
            geometry = unary_union(polygon_geometries)
            resolved_crs = HmsWatershedVerification._resolve_crs(src.crs, fallback_crs)
            if resolved_crs is None:
                raise ValueError(f"Could not determine CRS for raster dataset: {raster_path}")

        if not geometry.is_valid:
            geometry = geometry.buffer(0)
        return gpd.GeoDataFrame({"source": ["watershed_raster"]}, geometry=[geometry], crs=resolved_crs)

    @staticmethod
    def _stream_network_summary(streams_gdf, verification_crs) -> Dict[str, Any]:
        """Summarize stream-network counts, lengths, and order distribution."""
        if streams_gdf is None or len(streams_gdf) == 0:
            return {
                "feature_count": 0,
                "total_length_m": 0.0,
                "total_length_km": 0.0,
                "max_stream_order": None,
                "stream_order_counts": {},
            }

        streams_projected = streams_gdf.to_crs(verification_crs)
        feature_count = int(len(streams_projected))
        total_length_m = float(streams_projected.geometry.length.sum())
        order_column = None
        for candidate in ("strmOrder", "stream_order", "order", "ORD"):
            if candidate in streams_projected.columns:
                order_column = candidate
                break

        order_counts: Dict[str, int] = {}
        max_stream_order = None
        if order_column is not None:
            counts = streams_projected[order_column].dropna().astype(int).value_counts().sort_index()
            order_counts = {str(index): int(value) for index, value in counts.items()}
            if not counts.empty:
                max_stream_order = int(counts.index.max())

        return {
            "feature_count": feature_count,
            "total_length_m": round(total_length_m, 3),
            "total_length_km": round(total_length_m / 1000.0, 3),
            "max_stream_order": max_stream_order,
            "stream_order_counts": order_counts,
        }

    @staticmethod
    def _point_metrics(original_outlet_gdf, snapped_outlet_gdf, reference_geometry, taudem_geometry, verification_crs):
        """Compute outlet movement and containment metrics."""
        original_metrics = None
        snapped_metrics = None
        snap_distance_m = None
        original_point = None

        if original_outlet_gdf is not None and len(original_outlet_gdf) > 0:
            original_point = original_outlet_gdf.to_crs(verification_crs).geometry.iloc[0]
            original_metrics = {
                "x": round(float(original_point.x), 3),
                "y": round(float(original_point.y), 3),
                "inside_reference_boundary": bool(reference_geometry.covers(original_point)),
                "inside_taudem_boundary": bool(taudem_geometry.covers(original_point)),
            }
        if snapped_outlet_gdf is not None and len(snapped_outlet_gdf) > 0:
            snapped_point = snapped_outlet_gdf.to_crs(verification_crs).geometry.iloc[0]
            snapped_metrics = {
                "x": round(float(snapped_point.x), 3),
                "y": round(float(snapped_point.y), 3),
                "inside_reference_boundary": bool(reference_geometry.covers(snapped_point)),
                "inside_taudem_boundary": bool(taudem_geometry.covers(snapped_point)),
            }
            if original_metrics is not None and original_point is not None:
                snap_distance_m = round(float(original_point.distance(snapped_point)), 3)
            elif "Dist_moved" in snapped_outlet_gdf.columns:
                moved_value = snapped_outlet_gdf["Dist_moved"].iloc[0]
                if moved_value is not None and float(moved_value) >= 0:
                    snap_distance_m = round(float(moved_value), 3)

        return {
            "original_outlet": original_metrics,
            "snapped_outlet": snapped_metrics,
            "snap_distance_m": snap_distance_m,
        }

    @staticmethod
    def _rounded_bounds(bounds) -> list[float]:
        """Round a bounds tuple to stable JSON-friendly floats."""
        return [round(float(value), 3) for value in bounds]

    @staticmethod
    def _crs_label(crs_value: Any, fallback_crs: Optional[Any] = None) -> Optional[str]:
        """Return a compact CRS label, preferring EPSG codes when available."""
        resolved = HmsWatershedVerification._resolve_crs(crs_value, fallback_crs)
        if resolved is None:
            return None
        epsg = resolved.to_epsg()
        return f"EPSG:{epsg}" if epsg is not None else str(resolved)

    @staticmethod
    def _vector_dataset_summary(path: Path, resolved_gdf, verification_crs) -> Dict[str, Any]:
        """Summarize declared and resolved CRS details for a vector dataset."""
        deps = HmsWatershedVerification._check_dependencies()
        gpd = deps["gpd"]

        raw_gdf = gpd.read_file(path)
        projected = resolved_gdf.to_crs(verification_crs)
        summary: Dict[str, Any] = {
            "path": str(path),
            "dataset_kind": "vector",
            "declared_crs": HmsWatershedVerification._crs_label(raw_gdf.crs),
            "resolved_crs": HmsWatershedVerification._crs_label(resolved_gdf.crs, verification_crs),
            "feature_count": int(len(resolved_gdf)),
            "bounds_in_verification_crs": (
                HmsWatershedVerification._rounded_bounds(projected.total_bounds)
                if len(projected) > 0
                else None
            ),
        }
        if len(projected) > 0 and projected.geometry.iloc[0] is not None:
            point_geom = projected.geometry.iloc[0]
            if point_geom.geom_type == "Point":
                point_wgs84 = resolved_gdf.to_crs("EPSG:4326").geometry.iloc[0]
                summary["first_point_in_verification_crs"] = {
                    "x": round(float(point_geom.x), 3),
                    "y": round(float(point_geom.y), 3),
                }
                summary["first_point_in_wgs84"] = {
                    "lon": round(float(point_wgs84.x), 6),
                    "lat": round(float(point_wgs84.y), 6),
                }
        return summary

    @staticmethod
    def _raster_dataset_summary(
        path: Path,
        verification_crs,
        *,
        fallback_crs: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Summarize declared and resolved CRS details for a raster dataset."""
        deps = HmsWatershedVerification._check_dependencies()
        gpd = deps["gpd"]
        rasterio = deps["rasterio"]
        box = deps["box"]

        with rasterio.open(path) as src:
            resolved_crs = HmsWatershedVerification._resolve_crs(src.crs, fallback_crs or verification_crs)
            if resolved_crs is None:
                raise ValueError(f"Could not determine CRS for raster dataset: {path}")
            bounds_geometry = gpd.GeoDataFrame(
                {"id": [1]},
                geometry=[box(*src.bounds)],
                crs=resolved_crs,
            ).to_crs(verification_crs)
            return {
                "path": str(path),
                "dataset_kind": "raster",
                "declared_crs": HmsWatershedVerification._crs_label(src.crs),
                "resolved_crs": HmsWatershedVerification._crs_label(resolved_crs, verification_crs),
                "width": int(src.width),
                "height": int(src.height),
                "bounds_in_verification_crs": HmsWatershedVerification._rounded_bounds(
                    bounds_geometry.geometry.iloc[0].bounds
                ),
            }

    @staticmethod
    def _build_verification_context(
        reference_boundary_path: Union[str, Path],
        *,
        taudem_watershed_raster_path: Optional[Union[str, Path]] = None,
        taudem_boundary_path: Optional[Union[str, Path]] = None,
        original_outlet_path: Optional[Union[str, Path]] = None,
        snapped_outlet_path: Optional[Union[str, Path]] = None,
        stream_network_path: Optional[Union[str, Path]] = None,
        fallback_crs: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Load all datasets required for verification and figure generation."""
        if taudem_watershed_raster_path is None and taudem_boundary_path is None:
            raise ValueError("Provide either taudem_watershed_raster_path or taudem_boundary_path")

        reference_boundary_path = Path(reference_boundary_path)
        reference_gdf = HmsWatershedVerification._load_vector(reference_boundary_path, fallback_crs=fallback_crs)
        verification_crs = HmsWatershedVerification._resolve_crs(reference_gdf.crs, fallback_crs)
        if verification_crs is None:
            raise ValueError("Could not determine a projected CRS for verification")

        reference_geometry = HmsWatershedVerification._single_geometry(reference_gdf.to_crs(verification_crs))

        if taudem_watershed_raster_path is not None:
            taudem_watershed_raster_path = Path(taudem_watershed_raster_path)
            taudem_gdf = HmsWatershedVerification._polygonize_watershed_raster(
                taudem_watershed_raster_path,
                fallback_crs=verification_crs,
            )
            taudem_source_path = taudem_watershed_raster_path
            taudem_source_type = "watershed_raster"
        else:
            taudem_boundary_path = Path(taudem_boundary_path)
            taudem_gdf = HmsWatershedVerification._load_vector(
                taudem_boundary_path,
                fallback_crs=verification_crs,
            )
            taudem_source_path = taudem_boundary_path
            taudem_source_type = "boundary_vector"

        taudem_geometry = HmsWatershedVerification._single_geometry(taudem_gdf.to_crs(verification_crs))

        original_outlet_path = Path(original_outlet_path) if original_outlet_path else None
        snapped_outlet_path = Path(snapped_outlet_path) if snapped_outlet_path else None
        stream_network_path = Path(stream_network_path) if stream_network_path else None

        original_outlet_gdf = (
            HmsWatershedVerification._load_vector(original_outlet_path, fallback_crs=verification_crs)
            if original_outlet_path
            else None
        )
        snapped_outlet_gdf = (
            HmsWatershedVerification._load_vector(snapped_outlet_path, fallback_crs=verification_crs)
            if snapped_outlet_path
            else None
        )
        streams_gdf = (
            HmsWatershedVerification._load_vector(stream_network_path, fallback_crs=verification_crs)
            if stream_network_path
            else None
        )

        return {
            "reference_boundary_path": reference_boundary_path,
            "reference_gdf": reference_gdf,
            "reference_geometry": reference_geometry,
            "taudem_source_path": taudem_source_path,
            "taudem_source_type": taudem_source_type,
            "taudem_watershed_raster_path": (
                Path(taudem_watershed_raster_path) if taudem_watershed_raster_path is not None else None
            ),
            "taudem_boundary_path": Path(taudem_boundary_path) if taudem_boundary_path is not None else None,
            "taudem_gdf": taudem_gdf,
            "taudem_geometry": taudem_geometry,
            "original_outlet_path": original_outlet_path,
            "original_outlet_gdf": original_outlet_gdf,
            "snapped_outlet_path": snapped_outlet_path,
            "snapped_outlet_gdf": snapped_outlet_gdf,
            "stream_network_path": stream_network_path,
            "streams_gdf": streams_gdf,
            "verification_crs": verification_crs,
        }

    @staticmethod
    def _collect_point_geometries(geometry) -> list[Any]:
        """Flatten a geometry into a list of point candidates."""
        deps = HmsWatershedVerification._check_dependencies()
        Point = deps["Point"]

        if geometry is None or geometry.is_empty:
            return []

        geom_type = geometry.geom_type
        if geom_type == "Point":
            return [geometry]
        if geom_type == "MultiPoint":
            return [geom for geom in geometry.geoms if not geom.is_empty]
        if geom_type in ("LineString", "LinearRing"):
            coords = list(geometry.coords)
            if not coords:
                return []
            points = [Point(coords[0])]
            if coords[-1] != coords[0]:
                points.append(Point(coords[-1]))
            return points
        if geom_type in ("MultiLineString", "GeometryCollection", "MultiPolygon"):
            points = []
            for subgeom in geometry.geoms:
                points.extend(HmsWatershedVerification._collect_point_geometries(subgeom))
            return points
        return []

    @staticmethod
    def _dedupe_points(points, precision: int = 6):
        """Deduplicate point candidates by rounded coordinate key."""
        unique_points = []
        seen = set()
        for point in points:
            key = (round(float(point.x), precision), round(float(point.y), precision))
            if key not in seen:
                seen.add(key)
                unique_points.append(point)
        return unique_points

    @staticmethod
    def _boundary_outlet_candidates(boundary_geometry, streams_gdf, verification_crs):
        """Collect unique stream-boundary intersection point candidates."""
        if streams_gdf is None or len(streams_gdf) == 0:
            return []

        candidates = []
        for geometry in streams_gdf.to_crs(verification_crs).geometry:
            intersection = geometry.intersection(boundary_geometry)
            candidates.extend(HmsWatershedVerification._collect_point_geometries(intersection))
        return HmsWatershedVerification._dedupe_points(candidates)

    @staticmethod
    def _stream_order_column(streams_gdf) -> Optional[str]:
        """Return the first recognized stream-order column name."""
        for candidate in ("strmOrder", "stream_order", "order", "ORD"):
            if candidate in streams_gdf.columns:
                return candidate
        return None

    @staticmethod
    def _compute_metrics(context: Mapping[str, Any]) -> Dict[str, Any]:
        """Compute watershed verification metrics from a loaded context."""
        reference_geometry = context["reference_geometry"]
        taudem_geometry = context["taudem_geometry"]
        verification_crs = context["verification_crs"]

        reference_area_m2 = float(reference_geometry.area)
        taudem_area_m2 = float(taudem_geometry.area)
        absolute_difference_m2 = abs(taudem_area_m2 - reference_area_m2)
        signed_difference_m2 = taudem_area_m2 - reference_area_m2
        percent_difference = (signed_difference_m2 / reference_area_m2 * 100.0) if reference_area_m2 else None
        absolute_percent_difference = abs(percent_difference) if percent_difference is not None else None

        intersection = reference_geometry.intersection(taudem_geometry)
        union = reference_geometry.union(taudem_geometry)
        false_negative = reference_geometry.difference(taudem_geometry)
        false_positive = taudem_geometry.difference(reference_geometry)
        intersection_area_m2 = float(intersection.area)
        union_area_m2 = float(union.area)

        outlet_metrics = HmsWatershedVerification._point_metrics(
            context["original_outlet_gdf"],
            context["snapped_outlet_gdf"],
            reference_geometry,
            taudem_geometry,
            verification_crs,
        )
        stream_metrics = HmsWatershedVerification._stream_network_summary(
            context["streams_gdf"],
            verification_crs,
        )

        return {
            "reference_basin_area_m2": round(reference_area_m2, 3),
            "reference_basin_area_sqkm": round(reference_area_m2 / 1_000_000.0, 6),
            "reference_basin_area_sqmi": round(reference_area_m2 / 2_589_988.110336, 6),
            "taudem_basin_area_m2": round(taudem_area_m2, 3),
            "taudem_basin_area_sqkm": round(taudem_area_m2 / 1_000_000.0, 6),
            "taudem_basin_area_sqmi": round(taudem_area_m2 / 2_589_988.110336, 6),
            "signed_area_difference_m2": round(signed_difference_m2, 3),
            "absolute_area_difference_m2": round(absolute_difference_m2, 3),
            "absolute_area_difference_sqkm": round(absolute_difference_m2 / 1_000_000.0, 6),
            "percent_area_difference": round(percent_difference, 6) if percent_difference is not None else None,
            "absolute_percent_area_difference": (
                round(absolute_percent_difference, 6) if absolute_percent_difference is not None else None
            ),
            "polygon_overlap": {
                "intersection_area_m2": round(intersection_area_m2, 3),
                "intersection_area_sqkm": round(intersection_area_m2 / 1_000_000.0, 6),
                "union_area_m2": round(union_area_m2, 3),
                "union_area_sqkm": round(union_area_m2 / 1_000_000.0, 6),
                "intersection_over_union": round(intersection_area_m2 / union_area_m2, 6) if union_area_m2 else None,
                "reference_coverage_ratio": (
                    round(intersection_area_m2 / reference_area_m2, 6) if reference_area_m2 else None
                ),
                "taudem_coverage_ratio": (
                    round(intersection_area_m2 / taudem_area_m2, 6) if taudem_area_m2 else None
                ),
                "false_negative_area_sqkm": round(float(false_negative.area) / 1_000_000.0, 6),
                "false_positive_area_sqkm": round(float(false_positive.area) / 1_000_000.0, 6),
            },
            "outlet": outlet_metrics,
            "stream_network": stream_metrics,
        }

    @staticmethod
    def _select_boundary_outlet(boundary_geometry, streams_projected, verification_crs, seed_point=None) -> Dict[str, Any]:
        """Select a candidate outlet where the main stem crosses a supplied boundary."""
        deps = HmsWatershedVerification._check_dependencies()
        Point = deps["Point"]

        order_column = HmsWatershedVerification._stream_order_column(streams_projected)
        selected_stream_order = None
        candidate_streams = streams_projected
        if order_column is not None and len(streams_projected) > 0:
            selected_stream_order = int(streams_projected[order_column].dropna().astype(int).max())
            candidate_streams = streams_projected[streams_projected[order_column].astype(float) == selected_stream_order]

        candidates = HmsWatershedVerification._boundary_outlet_candidates(
            boundary_geometry,
            candidate_streams,
            verification_crs,
        )
        if not candidates:
            raise ValueError(
                "No stream/boundary crossing points were found for the selected main-stem stream network."
            )

        candidate_records = []
        for index, point in enumerate(candidates, start=1):
            distance_to_seed = float(point.distance(seed_point)) if seed_point is not None else None
            candidate_records.append(
                {
                    "candidate_index": index,
                    "x": round(float(point.x), 3),
                    "y": round(float(point.y), 3),
                    "distance_to_seed_m": round(distance_to_seed, 3) if distance_to_seed is not None else None,
                }
            )

        if seed_point is not None:
            selected_record = min(
                candidate_records,
                key=lambda record: (
                    record["distance_to_seed_m"] is None,
                    record["distance_to_seed_m"] if record["distance_to_seed_m"] is not None else float("inf"),
                    record["candidate_index"],
                ),
            )
            selection_method = "nearest_seed_outlet"
        elif len(candidate_records) == 1:
            selected_record = candidate_records[0]
            selection_method = "single_candidate"
        else:
            boundary_centroid = boundary_geometry.centroid
            selected_record = max(
                candidate_records,
                key=lambda record: Point(record["x"], record["y"]).distance(boundary_centroid),
            )
            selection_method = "farthest_from_boundary_centroid"

        selected_point = Point(selected_record["x"], selected_record["y"])
        return {
            "selection_method": selection_method,
            "stream_order_field": order_column,
            "selected_stream_order": selected_stream_order,
            "candidate_streams": candidate_streams,
            "candidate_records": candidate_records,
            "selected_record": selected_record,
            "selected_point": selected_point,
        }

    @staticmethod
    @log_call
    def derive_boundary_outlet(
        reference_boundary_path: Union[str, Path],
        stream_network_path: Union[str, Path],
        *,
        output_path: Optional[Union[str, Path]] = None,
        seed_outlet_path: Optional[Union[str, Path]] = None,
        fallback_crs: Optional[Any] = None,
        study_name: Optional[str] = None,
        workspace_root: Optional[Union[str, Path]] = None,
        site_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Select the main-stem basin-boundary crossing as a candidate outlet."""
        deps = HmsWatershedVerification._check_dependencies()
        gpd = deps["gpd"]

        reference_gdf = HmsWatershedVerification._load_vector(reference_boundary_path, fallback_crs=fallback_crs)
        verification_crs = HmsWatershedVerification._resolve_crs(reference_gdf.crs, fallback_crs)
        if verification_crs is None:
            raise ValueError("Could not determine a projected CRS for outlet derivation")

        reference_geometry = HmsWatershedVerification._single_geometry(reference_gdf.to_crs(verification_crs))
        boundary_geometry = reference_geometry.boundary
        streams_gdf = HmsWatershedVerification._load_vector(stream_network_path, fallback_crs=verification_crs)
        streams_projected = streams_gdf.to_crs(verification_crs)

        order_column = HmsWatershedVerification._stream_order_column(streams_projected)
        selected_stream_order = None
        candidate_streams = streams_projected
        if order_column is not None and len(streams_projected) > 0:
            selected_stream_order = int(streams_projected[order_column].dropna().astype(int).max())
            candidate_streams = streams_projected[streams_projected[order_column].astype(float) == selected_stream_order]

        seed_point = None
        if seed_outlet_path is not None:
            seed_gdf = HmsWatershedVerification._load_vector(seed_outlet_path, fallback_crs=verification_crs)
            seed_point = HmsWatershedVerification._first_projected_point(seed_gdf, verification_crs)

        selection = HmsWatershedVerification._select_boundary_outlet(
            boundary_geometry,
            streams_projected,
            verification_crs,
            seed_point=seed_point,
        )
        selection_method = selection["selection_method"]
        order_column = selection["stream_order_field"]
        selected_stream_order = selection["selected_stream_order"]
        candidate_streams = selection["candidate_streams"]
        candidate_records = selection["candidate_records"]
        selected_record = selection["selected_record"]
        selected_point = selection["selected_point"]

        outlet_gdf = gpd.GeoDataFrame(
            {
                "id": [1],
                "sel_method": [selection_method],
                "str_order": [selected_stream_order],
                "cand_count": [len(candidate_records)],
            },
            geometry=[selected_point],
            crs=verification_crs,
        )

        payload = {
            "schema_version": "1.0",
            "study_type": "boundary_outlet_selection",
            "generated_at": HmsWatershedVerification._utc_now(),
            "status": "completed",
            "study_name": study_name,
            "site_id": site_id,
            "workspace_root": str(Path(workspace_root)) if workspace_root is not None else None,
            "verification_crs": str(verification_crs),
            "inputs": {
                "reference_boundary_path": str(Path(reference_boundary_path)),
                "stream_network_path": str(Path(stream_network_path)),
                "seed_outlet_path": str(Path(seed_outlet_path)) if seed_outlet_path is not None else None,
            },
            "selection": {
                "selection_method": selection_method,
                "stream_order_field": order_column,
                "selected_stream_order": selected_stream_order,
                "mainstem_feature_count": int(len(candidate_streams)),
                "boundary_crossing_count": len(candidate_records),
                "selected_outlet": {
                    "x": selected_record["x"],
                    "y": selected_record["y"],
                    "distance_to_seed_m": selected_record["distance_to_seed_m"],
                },
                "candidate_crossings": candidate_records,
            },
            "builder": {
                "package": "hms-commander",
                "class": "HmsWatershedVerification",
                "method": "derive_boundary_outlet",
                "version": PACKAGE_VERSION,
            },
        }

        if output_path is not None:
            output_path = Path(output_path)
            write_result = HmsWatershedVerification._write_vector(output_path, outlet_gdf)
            payload["artifact"] = {
                "path": str(output_path),
                "status": write_result["status"],
                "bytes": write_result["bytes"],
            }

        return payload

    @staticmethod
    @log_call
    def derive_taudem_boundary_outlet(
        stream_network_path: Union[str, Path],
        *,
        taudem_watershed_raster_path: Optional[Union[str, Path]] = None,
        taudem_boundary_path: Optional[Union[str, Path]] = None,
        output_path: Optional[Union[str, Path]] = None,
        seed_outlet_path: Optional[Union[str, Path]] = None,
        fallback_crs: Optional[Any] = None,
        study_name: Optional[str] = None,
        workspace_root: Optional[Union[str, Path]] = None,
        site_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Select the main-stem crossing of the TauDEM-derived basin boundary."""
        deps = HmsWatershedVerification._check_dependencies()
        gpd = deps["gpd"]

        if taudem_watershed_raster_path is None and taudem_boundary_path is None:
            raise ValueError("Provide either taudem_watershed_raster_path or taudem_boundary_path")

        derived_fallback_crs = fallback_crs
        if derived_fallback_crs is None and seed_outlet_path is not None:
            seed_raw_gdf = gpd.read_file(seed_outlet_path)
            derived_fallback_crs = HmsWatershedVerification._resolve_crs(seed_raw_gdf.crs)
        if derived_fallback_crs is None:
            stream_raw_gdf = gpd.read_file(stream_network_path)
            derived_fallback_crs = HmsWatershedVerification._resolve_crs(stream_raw_gdf.crs)

        if taudem_watershed_raster_path is not None:
            taudem_watershed_raster_path = Path(taudem_watershed_raster_path)
            taudem_gdf = HmsWatershedVerification._polygonize_watershed_raster(
                taudem_watershed_raster_path,
                fallback_crs=derived_fallback_crs,
            )
            taudem_source_path = taudem_watershed_raster_path
            taudem_source_type = "watershed_raster"
        else:
            taudem_boundary_path = Path(taudem_boundary_path)
            taudem_gdf = HmsWatershedVerification._load_vector(
                taudem_boundary_path,
                fallback_crs=derived_fallback_crs,
            )
            taudem_source_path = taudem_boundary_path
            taudem_source_type = "boundary_vector"

        verification_crs = HmsWatershedVerification._resolve_crs(taudem_gdf.crs, derived_fallback_crs)
        if verification_crs is None:
            raise ValueError("Could not determine a projected CRS for TauDEM boundary outlet derivation")

        taudem_geometry = HmsWatershedVerification._single_geometry(taudem_gdf.to_crs(verification_crs))
        boundary_geometry = taudem_geometry.boundary
        streams_gdf = HmsWatershedVerification._load_vector(stream_network_path, fallback_crs=verification_crs)
        streams_projected = streams_gdf.to_crs(verification_crs)

        seed_point = None
        if seed_outlet_path is not None:
            seed_gdf = HmsWatershedVerification._load_vector(seed_outlet_path, fallback_crs=verification_crs)
            seed_point = HmsWatershedVerification._first_projected_point(seed_gdf, verification_crs)

        selection = HmsWatershedVerification._select_boundary_outlet(
            boundary_geometry,
            streams_projected,
            verification_crs,
            seed_point=seed_point,
        )
        selection_method = selection["selection_method"]
        order_column = selection["stream_order_field"]
        selected_stream_order = selection["selected_stream_order"]
        candidate_streams = selection["candidate_streams"]
        candidate_records = selection["candidate_records"]
        selected_record = selection["selected_record"]
        selected_point = selection["selected_point"]

        outlet_gdf = gpd.GeoDataFrame(
            {
                "id": [1],
                "sel_method": [selection_method],
                "str_order": [selected_stream_order],
                "cand_count": [len(candidate_records)],
            },
            geometry=[selected_point],
            crs=verification_crs,
        )

        payload = {
            "schema_version": "1.0",
            "study_type": "taudem_boundary_outlet_selection",
            "generated_at": HmsWatershedVerification._utc_now(),
            "status": "completed",
            "study_name": study_name,
            "site_id": site_id,
            "workspace_root": str(Path(workspace_root)) if workspace_root is not None else None,
            "verification_crs": str(verification_crs),
            "inputs": {
                "taudem_source_path": str(taudem_source_path),
                "taudem_source_type": taudem_source_type,
                "stream_network_path": str(Path(stream_network_path)),
                "seed_outlet_path": str(Path(seed_outlet_path)) if seed_outlet_path is not None else None,
            },
            "selection": {
                "selection_method": selection_method,
                "stream_order_field": order_column,
                "selected_stream_order": selected_stream_order,
                "mainstem_feature_count": int(len(candidate_streams)),
                "boundary_crossing_count": len(candidate_records),
                "selected_outlet": {
                    "x": selected_record["x"],
                    "y": selected_record["y"],
                    "distance_to_seed_m": selected_record["distance_to_seed_m"],
                },
                "candidate_crossings": candidate_records,
            },
            "builder": {
                "package": "hms-commander",
                "class": "HmsWatershedVerification",
                "method": "derive_taudem_boundary_outlet",
                "version": PACKAGE_VERSION,
            },
        }

        if output_path is not None:
            output_path = Path(output_path)
            write_result = HmsWatershedVerification._write_vector(output_path, outlet_gdf)
            payload["artifact"] = {
                "path": str(output_path),
                "status": write_result["status"],
                "bytes": write_result["bytes"],
            }

        return payload

    @staticmethod
    def _first_projected_point(gdf, verification_crs):
        """Return the first point geometry in the verification CRS."""
        if gdf is None or len(gdf) == 0:
            return None
        return gdf.to_crs(verification_crs).geometry.iloc[0]

    @staticmethod
    def _merge_bounds(*bounds_candidates) -> Optional[tuple[float, float, float, float]]:
        """Merge one or more bounds tuples, skipping missing entries."""
        valid_bounds = [bounds for bounds in bounds_candidates if bounds is not None]
        if not valid_bounds:
            return None
        minx = min(bounds[0] for bounds in valid_bounds)
        miny = min(bounds[1] for bounds in valid_bounds)
        maxx = max(bounds[2] for bounds in valid_bounds)
        maxy = max(bounds[3] for bounds in valid_bounds)
        return (minx, miny, maxx, maxy)

    @staticmethod
    def _bounds_from_point(point) -> Optional[tuple[float, float, float, float]]:
        """Return point bounds for a single shapely point."""
        if point is None or point.is_empty:
            return None
        return point.bounds

    @staticmethod
    def _point_extent_bounds(point, extra_points=None):
        """Create a padded plot extent around one point and optional helper points."""
        extra_points = extra_points or []
        bounds = HmsWatershedVerification._merge_bounds(
            HmsWatershedVerification._bounds_from_point(point),
            *[HmsWatershedVerification._bounds_from_point(extra_point) for extra_point in extra_points],
        )
        if bounds is None:
            return None
        minx, miny, maxx, maxy = bounds
        span_x = max(maxx - minx, 1.0)
        span_y = max(maxy - miny, 1.0)
        pad_x = max(span_x * 0.35, 2000.0)
        pad_y = max(span_y * 0.35, 2000.0)
        return (minx - pad_x, miny - pad_y, maxx + pad_x, maxy + pad_y)

    @staticmethod
    def _apply_plot_extent(ax, bounds, *, padding_ratio: float = 0.05, min_padding: float = 500.0):
        """Apply a padded extent to a Matplotlib axis."""
        if bounds is None:
            return
        minx, miny, maxx, maxy = bounds
        width = max(maxx - minx, 1.0)
        height = max(maxy - miny, 1.0)
        pad_x = max(width * padding_ratio, min_padding)
        pad_y = max(height * padding_ratio, min_padding)
        ax.set_xlim(minx - pad_x, maxx + pad_x)
        ax.set_ylim(miny - pad_y, maxy + pad_y)
        ax.set_aspect("equal")

    @staticmethod
    def _style_axis(ax, title: str):
        """Apply consistent cartographic styling to an axis."""
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.set_xlabel("Easting (m)")
        ax.set_ylabel("Northing (m)")
        ax.grid(color="#d0d7de", linewidth=0.6, alpha=0.35)
        for spine in ax.spines.values():
            spine.set_color("#88929d")
            spine.set_linewidth(0.8)

    @staticmethod
    def _copy_cmap(plt, cmap_name: str):
        """Return a mutable colormap copy with transparent masked pixels."""
        cmap = plt.get_cmap(cmap_name).copy()
        cmap.set_bad((1.0, 1.0, 1.0, 0.0))
        return cmap

    @staticmethod
    def _read_raster_for_plot(
        raster_path: Union[str, Path],
        *,
        max_dimension: int = 1400,
        log_transform: bool = False,
        positive_only: bool = False,
        discrete: bool = False,
    ) -> Dict[str, Any]:
        """Read a downsampled raster suitable for figure generation."""
        deps = HmsWatershedVerification._check_dependencies()
        np = deps["np"]
        rasterio = deps["rasterio"]
        Resampling = deps["Resampling"]

        raster_path = Path(raster_path)
        with rasterio.open(raster_path) as src:
            scale = max(src.width / max_dimension, src.height / max_dimension, 1.0)
            out_width = max(1, int(round(src.width / scale)))
            out_height = max(1, int(round(src.height / scale)))
            resampling = Resampling.nearest if discrete else Resampling.average
            data = src.read(
                1,
                masked=True,
                out_shape=(out_height, out_width),
                resampling=resampling,
            )
            bounds = src.bounds

        mask = np.ma.getmaskarray(data)
        array = np.asarray(data, dtype="float64")
        if positive_only or log_transform:
            mask = mask | (array <= 0)
        array[mask] = np.nan
        if log_transform:
            with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
                array = np.log1p(array)

        return {
            "array": array,
            "extent": (bounds.left, bounds.right, bounds.bottom, bounds.top),
        }

    @staticmethod
    def _plot_reference_layers(ax, context: Mapping[str, Any], *, include_streams: bool = True):
        """Plot reference and TauDEM basin outlines plus optional stream network."""
        reference_gdf = context["reference_gdf"].to_crs(context["verification_crs"])
        taudem_gdf = context["taudem_gdf"].to_crs(context["verification_crs"])

        reference_gdf.boundary.plot(
            ax=ax,
            color="#1f1f1f",
            linewidth=1.6,
            label="Reference basin",
            zorder=5,
        )
        taudem_gdf.boundary.plot(
            ax=ax,
            color="#cc5500",
            linewidth=1.4,
            linestyle="--",
            label="TauDEM basin",
            zorder=6,
        )

        streams_gdf = context["streams_gdf"]
        if include_streams and streams_gdf is not None and len(streams_gdf) > 0:
            streams_gdf.to_crs(context["verification_crs"]).plot(
                ax=ax,
                color="#0b6e8e",
                linewidth=0.7,
                alpha=0.8,
                label="TauDEM streams",
                zorder=4,
            )

    @staticmethod
    def _plot_dem_bounds(ax, dem_bounds_geometry, verification_crs):
        """Plot DEM bounds as a buffered terrain extent overlay."""
        if dem_bounds_geometry is None:
            return

        deps = HmsWatershedVerification._check_dependencies()
        gpd = deps["gpd"]
        dem_gdf = gpd.GeoDataFrame(
            {"name": ["DEM extent"]},
            geometry=[dem_bounds_geometry],
            crs=verification_crs,
        )
        dem_gdf.plot(
            ax=ax,
            facecolor="#bfdbfe",
            edgecolor="#2563eb",
            alpha=0.16,
            linewidth=1.2,
            label="Buffered DEM extent",
            zorder=1,
        )
        dem_gdf.boundary.plot(
            ax=ax,
            color="#2563eb",
            linewidth=1.3,
            alpha=0.9,
            zorder=2,
        )

    @staticmethod
    def _plot_gauge_point(ax, gauge_point):
        """Plot a gauge point on the active axis."""
        if gauge_point is None or gauge_point.is_empty:
            return

        ax.scatter(
            [gauge_point.x],
            [gauge_point.y],
            s=130,
            marker="^",
            facecolor="#2f9e44",
            edgecolor="#0b3d20",
            linewidth=1.2,
            label="Gauge point",
            zorder=10,
        )

    @staticmethod
    def _plot_outlets(
        ax,
        context: Mapping[str, Any],
        *,
        original_label: str = "Original outlet",
        snapped_label: str = "Snapped outlet",
    ):
        """Plot original and snapped outlet points."""
        verification_crs = context["verification_crs"]
        original_point = HmsWatershedVerification._first_projected_point(
            context["original_outlet_gdf"],
            verification_crs,
        )
        snapped_point = HmsWatershedVerification._first_projected_point(
            context["snapped_outlet_gdf"],
            verification_crs,
        )

        if original_point is not None:
            ax.scatter(
                [original_point.x],
                [original_point.y],
                s=120,
                marker="o",
                facecolor="#ffd166",
                edgecolor="#1f1f1f",
                linewidth=1.4,
                label=original_label,
                zorder=8,
            )
        if snapped_point is not None:
            ax.scatter(
                [snapped_point.x],
                [snapped_point.y],
                s=130,
                marker="x",
                color="#c1121f",
                linewidths=2.0,
                label=snapped_label,
                zorder=9,
            )

        return {"original_point": original_point, "snapped_point": snapped_point}

    @staticmethod
    def _plot_point_to_point_connector(ax, point_a, point_b, color: str, label: str):
        """Plot a connector between two points and annotate the distance."""
        if point_a is None or point_b is None:
            return None

        ax.plot(
            [point_a.x, point_b.x],
            [point_a.y, point_b.y],
            color=color,
            linestyle="-.",
            linewidth=1.8,
            alpha=0.95,
            zorder=7,
        )
        distance_m = float(point_a.distance(point_b))
        midpoint_x = (point_a.x + point_b.x) / 2.0
        midpoint_y = (point_a.y + point_b.y) / 2.0
        ax.annotate(
            f"{label}: {distance_m / 1000.0:.2f} km",
            (midpoint_x, midpoint_y),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=9,
            color=color,
            bbox={"boxstyle": "round,pad=0.2", "facecolor": "white", "edgecolor": color, "alpha": 0.85},
            zorder=10,
        )
        return distance_m

    @staticmethod
    def _plot_distance_connector(ax, point, geometry, color: str, label: str):
        """Plot the nearest distance from an outlet point to a basin boundary."""
        deps = HmsWatershedVerification._check_dependencies()
        nearest_points = deps["nearest_points"]

        nearest_on_boundary = nearest_points(point, geometry.boundary)[1]
        ax.plot(
            [point.x, nearest_on_boundary.x],
            [point.y, nearest_on_boundary.y],
            color=color,
            linestyle=":",
            linewidth=1.6,
            alpha=0.95,
            zorder=7,
        )
        distance_m = float(point.distance(nearest_on_boundary))
        midpoint_x = (point.x + nearest_on_boundary.x) / 2.0
        midpoint_y = (point.y + nearest_on_boundary.y) / 2.0
        ax.annotate(
            f"{label}: {distance_m / 1000.0:.2f} km",
            (midpoint_x, midpoint_y),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=9,
            color=color,
            bbox={"boxstyle": "round,pad=0.2", "facecolor": "white", "edgecolor": color, "alpha": 0.85},
            zorder=10,
        )
        return nearest_on_boundary

    @staticmethod
    def _save_figure(fig, output_path: Path) -> Dict[str, Any]:
        """Save a Matplotlib figure with stable settings."""
        existed = output_path.exists()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=200, bbox_inches="tight", facecolor="white")
        return {"status": "updated" if existed else "created", "bytes": output_path.stat().st_size}

    @staticmethod
    def _build_outlet_summary_text(metrics: Mapping[str, Any]) -> str:
        """Create a concise multiline outlet summary for the mismatch figure."""
        outlet = metrics["outlet"]
        original = outlet["original_outlet"] or {}
        snapped = outlet["snapped_outlet"] or {}
        overlap = metrics["polygon_overlap"]

        return "\n".join(
            [
                f"Area diff: {metrics['absolute_percent_area_difference']:.2f}%"
                if metrics["absolute_percent_area_difference"] is not None
                else "Area diff: n/a",
                f"IoU: {overlap['intersection_over_union']:.4f}"
                if overlap["intersection_over_union"] is not None
                else "IoU: n/a",
                (
                    "Original outlet in ref/TauDEM: "
                    f"{original.get('inside_reference_boundary', 'n/a')}/"
                    f"{original.get('inside_taudem_boundary', 'n/a')}"
                ),
                (
                    "Snapped outlet in ref/TauDEM: "
                    f"{snapped.get('inside_reference_boundary', 'n/a')}/"
                    f"{snapped.get('inside_taudem_boundary', 'n/a')}"
                ),
                f"Snap distance: {outlet['snap_distance_m']:.1f} m"
                if outlet["snap_distance_m"] is not None
                else "Snap distance: n/a",
            ]
        )

    @staticmethod
    def _build_crs_alignment_summary_text(
        audit_payload: Mapping[str, Any],
        *,
        reference_geometry,
        dem_bounds_geometry=None,
        gauge_point=None,
        outlet_point=None,
        outlet_label: str = "current outlet",
    ) -> str:
        """Create a concise multiline summary for the CRS alignment context figure."""
        comparisons = audit_payload.get("comparisons", {})
        lines = []

        if dem_bounds_geometry is not None and reference_geometry is not None:
            lines.append(f"DEM covers reference basin: {bool(dem_bounds_geometry.covers(reference_geometry))}")
        if gauge_point is not None and reference_geometry is not None:
            lines.append(f"Gauge inside reference basin: {bool(reference_geometry.covers(gauge_point))}")
        if outlet_point is not None and dem_bounds_geometry is not None:
            lines.append(f"Outlet inside DEM extent: {bool(dem_bounds_geometry.covers(outlet_point))}")

        outlet_vs_dem = comparisons.get("original_outlet_vs_dem_bounds")
        if outlet_vs_dem is not None:
            lines.append(f"Outlet to DEM edge: {outlet_vs_dem['distance_to_dem_bounds_m'] / 1000.0:.2f} km")

        outlet_vs_ref = comparisons.get("original_outlet_vs_reference_boundary")
        if outlet_vs_ref is not None:
            lines.append(
                f"Outlet to reference basin edge: {outlet_vs_ref['distance_to_reference_boundary_m'] / 1000.0:.2f} km"
            )

        outlet_vs_taudem = comparisons.get("original_outlet_vs_taudem_boundary")
        if outlet_vs_taudem is not None:
            lines.append(f"Outlet to TauDEM edge: {outlet_vs_taudem['distance_to_taudem_boundary_m'] / 1000.0:.2f} km")

        outlet_vs_gauge = comparisons.get("original_outlet_vs_gauge_point")
        if outlet_vs_gauge is not None:
            lines.append(f"Gauge to {outlet_label}: {outlet_vs_gauge['distance_m'] / 1000.0:.2f} km")

        return "\n".join(lines)

    @staticmethod
    def _create_outlet_mismatch_figure(
        context: Mapping[str, Any],
        metrics: Mapping[str, Any],
        *,
        output_path: Path,
        study_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a figure showing outlet placement relative to basin boundaries."""
        deps = HmsWatershedVerification._check_plotting_dependencies()
        plt = deps["plt"]

        fig, axes = plt.subplots(1, 2, figsize=(15.5, 7.5), constrained_layout=True)
        fig.suptitle(
            study_name or "TauDEM outlet and basin verification",
            fontsize=16,
            fontweight="bold",
        )

        full_bounds = HmsWatershedVerification._merge_bounds(
            context["reference_geometry"].bounds,
            context["taudem_geometry"].bounds,
            HmsWatershedVerification._bounds_from_point(
                HmsWatershedVerification._first_projected_point(
                    context["original_outlet_gdf"],
                    context["verification_crs"],
                )
            ),
            HmsWatershedVerification._bounds_from_point(
                HmsWatershedVerification._first_projected_point(
                    context["snapped_outlet_gdf"],
                    context["verification_crs"],
                )
            ),
        )

        plotted_points = []
        for axis in axes:
            HmsWatershedVerification._plot_reference_layers(axis, context, include_streams=True)
            point_layers = HmsWatershedVerification._plot_outlets(axis, context)
            plotted_points.append(point_layers)

        HmsWatershedVerification._apply_plot_extent(axes[0], full_bounds, padding_ratio=0.05, min_padding=1500.0)
        HmsWatershedVerification._style_axis(axes[0], "Full basin context")
        axes[0].legend(loc="lower left", frameon=True, framealpha=0.95)
        axes[0].text(
            0.02,
            0.98,
            HmsWatershedVerification._build_outlet_summary_text(metrics),
            transform=axes[0].transAxes,
            va="top",
            ha="left",
            fontsize=9,
            bbox={"boxstyle": "round,pad=0.4", "facecolor": "white", "edgecolor": "#88929d", "alpha": 0.92},
        )

        primary_point = plotted_points[1]["snapped_point"] or plotted_points[1]["original_point"]
        helper_points = []
        if primary_point is not None:
            if not context["reference_geometry"].covers(primary_point):
                helper_points.append(
                    HmsWatershedVerification._plot_distance_connector(
                        axes[1],
                        primary_point,
                        context["reference_geometry"],
                        "#1f1f1f",
                        "To reference basin",
                    )
                )
            if not context["taudem_geometry"].covers(primary_point):
                helper_points.append(
                    HmsWatershedVerification._plot_distance_connector(
                        axes[1],
                        primary_point,
                        context["taudem_geometry"],
                        "#cc5500",
                        "To TauDEM basin",
                    )
                )

        zoom_bounds = HmsWatershedVerification._point_extent_bounds(primary_point, helper_points)
        if zoom_bounds is None:
            zoom_bounds = full_bounds
        HmsWatershedVerification._apply_plot_extent(axes[1], zoom_bounds, padding_ratio=0.08, min_padding=750.0)
        HmsWatershedVerification._style_axis(axes[1], "Outlet vicinity and nearest basin edge")

        write_result = HmsWatershedVerification._save_figure(fig, output_path)
        plt.close(fig)

        return {
            "title": "Outlet placement mismatch",
            "description": (
                "Reference basin, TauDEM basin, stream network, and original/snapped outlets with nearest "
                "boundary distance callouts."
            ),
            "path": str(output_path),
            "status": write_result["status"],
            "bytes": write_result["bytes"],
        }

    @staticmethod
    def _plot_raster_panel(
        ax,
        title: str,
        raster_path: Optional[Path],
        *,
        cmap_name: str,
        log_transform: bool = False,
        positive_only: bool = False,
        discrete: bool = False,
        context: Mapping[str, Any],
        add_colorbar: bool = False,
        colorbar_label: Optional[str] = None,
        fig=None,
    ):
        """Plot one TauDEM raster panel with common overlays."""
        deps = HmsWatershedVerification._check_plotting_dependencies()
        plt = deps["plt"]

        if raster_path is None or not Path(raster_path).exists():
            ax.text(
                0.5,
                0.5,
                "Not available",
                transform=ax.transAxes,
                ha="center",
                va="center",
                fontsize=11,
                color="#57606a",
            )
            HmsWatershedVerification._plot_reference_layers(ax, context, include_streams=True)
            HmsWatershedVerification._plot_outlets(ax, context)
            HmsWatershedVerification._style_axis(ax, title)
            return

        raster_display = HmsWatershedVerification._read_raster_for_plot(
            raster_path,
            log_transform=log_transform,
            positive_only=positive_only,
            discrete=discrete,
        )
        image = ax.imshow(
            raster_display["array"],
            extent=raster_display["extent"],
            origin="upper",
            cmap=HmsWatershedVerification._copy_cmap(plt, cmap_name),
            interpolation="nearest",
            zorder=1,
        )
        HmsWatershedVerification._plot_reference_layers(ax, context, include_streams=True)
        HmsWatershedVerification._plot_outlets(ax, context)
        HmsWatershedVerification._style_axis(ax, title)
        if add_colorbar and fig is not None:
            colorbar = fig.colorbar(image, ax=ax, shrink=0.82, pad=0.01)
            if colorbar_label:
                colorbar.set_label(colorbar_label)

    @staticmethod
    def _create_taudem_outputs_overview_figure(
        context: Mapping[str, Any],
        metrics: Mapping[str, Any],
        *,
        output_path: Path,
        fel_raster_path: Optional[Union[str, Path]] = None,
        ad8_raster_path: Optional[Union[str, Path]] = None,
        src_raster_path: Optional[Union[str, Path]] = None,
        study_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a multi-panel figure showing core TauDEM raster outputs."""
        deps = HmsWatershedVerification._check_plotting_dependencies()
        plt = deps["plt"]

        watershed_raster_path = context["taudem_watershed_raster_path"]
        fig, axes = plt.subplots(2, 2, figsize=(15.5, 13), constrained_layout=True)
        fig.suptitle(
            (study_name or "TauDEM outputs overview") + " - TauDEM rasters",
            fontsize=16,
            fontweight="bold",
        )

        HmsWatershedVerification._plot_raster_panel(
            axes[0, 0],
            "Filled DEM (fel.tif)",
            Path(fel_raster_path) if fel_raster_path else None,
            cmap_name="terrain",
            positive_only=False,
            discrete=False,
            context=context,
            add_colorbar=True,
            colorbar_label="Elevation",
            fig=fig,
        )
        HmsWatershedVerification._plot_raster_panel(
            axes[0, 1],
            "Contributing area log1p(ad8.tif)",
            Path(ad8_raster_path) if ad8_raster_path else None,
            cmap_name="viridis",
            log_transform=True,
            positive_only=True,
            discrete=False,
            context=context,
            add_colorbar=True,
            colorbar_label="log1p(cells)",
            fig=fig,
        )
        HmsWatershedVerification._plot_raster_panel(
            axes[1, 0],
            "Stream raster (src.tif)",
            Path(src_raster_path) if src_raster_path else None,
            cmap_name="Blues",
            positive_only=True,
            discrete=True,
            context=context,
            add_colorbar=False,
            fig=fig,
        )
        HmsWatershedVerification._plot_raster_panel(
            axes[1, 1],
            "Watershed raster (w.tif)",
            watershed_raster_path,
            cmap_name="Oranges",
            positive_only=True,
            discrete=True,
            context=context,
            add_colorbar=False,
            fig=fig,
        )

        basin_bounds = HmsWatershedVerification._merge_bounds(
            context["reference_geometry"].bounds,
            context["taudem_geometry"].bounds,
        )
        for axis in axes.flat:
            HmsWatershedVerification._apply_plot_extent(
                axis,
                basin_bounds,
                padding_ratio=0.04,
                min_padding=1000.0,
            )

        stream_metrics = metrics["stream_network"]
        fig.text(
            0.02,
            0.015,
            (
                "Reference basin: "
                f"{metrics['reference_basin_area_sqmi']:.2f} sq mi | "
                "TauDEM basin: "
                f"{metrics['taudem_basin_area_sqmi']:.2f} sq mi | "
                "Area diff: "
                f"{metrics['absolute_percent_area_difference']:.2f}% | "
                "Streams: "
                f"{stream_metrics['feature_count']} features, "
                f"max order {stream_metrics['max_stream_order']}"
            ),
            fontsize=10,
            color="#24292f",
        )

        write_result = HmsWatershedVerification._save_figure(fig, output_path)
        plt.close(fig)

        return {
            "title": "TauDEM outputs overview",
            "description": (
                "Four-panel summary of filled DEM, contributing area, stream raster, and watershed raster "
                "with basin, outlet, and stream overlays."
            ),
            "path": str(output_path),
            "status": write_result["status"],
            "bytes": write_result["bytes"],
        }

    @staticmethod
    def _create_crs_alignment_context_figure(
        context: Mapping[str, Any],
        audit_payload: Mapping[str, Any],
        *,
        output_path: Path,
        dem_bounds_geometry=None,
        gauge_point=None,
        study_name: Optional[str] = None,
        outlet_label: str = "current outlet",
    ) -> Dict[str, Any]:
        """Create a figure showing DEM extent, basin context, gauge, and current outlet."""
        deps = HmsWatershedVerification._check_plotting_dependencies()
        plt = deps["plt"]

        verification_crs = context["verification_crs"]
        original_point = HmsWatershedVerification._first_projected_point(context["original_outlet_gdf"], verification_crs)
        snapped_point = HmsWatershedVerification._first_projected_point(context["snapped_outlet_gdf"], verification_crs)

        fig, axes = plt.subplots(1, 2, figsize=(16, 8), constrained_layout=True)
        fig.suptitle(
            study_name or "Gauge, outlet, and DEM extent context",
            fontsize=16,
            fontweight="bold",
        )

        full_bounds = HmsWatershedVerification._merge_bounds(
            context["reference_geometry"].bounds,
            context["taudem_geometry"].bounds,
            dem_bounds_geometry.bounds if dem_bounds_geometry is not None else None,
            HmsWatershedVerification._bounds_from_point(gauge_point),
            HmsWatershedVerification._bounds_from_point(original_point),
            HmsWatershedVerification._bounds_from_point(snapped_point),
        )

        helper_points = []
        for axis in axes:
            HmsWatershedVerification._plot_dem_bounds(axis, dem_bounds_geometry, verification_crs)
            HmsWatershedVerification._plot_reference_layers(axis, context, include_streams=True)
            HmsWatershedVerification._plot_gauge_point(axis, gauge_point)
            point_layers = HmsWatershedVerification._plot_outlets(
                axis,
                context,
                original_label=outlet_label.title(),
                snapped_label="Snapped outlet",
            )
            helper_points.append(point_layers)

        HmsWatershedVerification._plot_point_to_point_connector(
            axes[0],
            gauge_point,
            original_point,
            "#7c3aed",
            f"Gauge to {outlet_label}",
        )
        HmsWatershedVerification._apply_plot_extent(axes[0], full_bounds, padding_ratio=0.04, min_padding=1000.0)
        HmsWatershedVerification._style_axis(axes[0], "Full buffered terrain and basin context")
        Patch = deps["Patch"]
        Line2D = deps["Line2D"]
        axes[0].legend(
            handles=[
                Patch(facecolor="#bfdbfe", edgecolor="#2563eb", alpha=0.35, label="Buffered DEM extent"),
                Line2D([0], [0], color="#1f1f1f", linewidth=1.6, label="Reference basin"),
                Line2D([0], [0], color="#cc5500", linewidth=1.4, linestyle="--", label="TauDEM basin"),
                Line2D([0], [0], color="#0b6e8e", linewidth=0.9, label="TauDEM streams"),
                Line2D(
                    [0],
                    [0],
                    marker="^",
                    color="#0b3d20",
                    markerfacecolor="#2f9e44",
                    markeredgecolor="#0b3d20",
                    linestyle="None",
                    markersize=8,
                    label="Gauge point",
                ),
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="#1f1f1f",
                    markerfacecolor="#ffd166",
                    markeredgecolor="#1f1f1f",
                    linestyle="None",
                    markersize=8,
                    label=outlet_label.title(),
                ),
                Line2D(
                    [0],
                    [0],
                    marker="x",
                    color="#c1121f",
                    linestyle="None",
                    markersize=8,
                    markeredgewidth=2.0,
                    label="Snapped outlet",
                ),
            ],
            loc="lower left",
            frameon=True,
            framealpha=0.95,
        )
        axes[0].text(
            0.02,
            0.98,
            HmsWatershedVerification._build_crs_alignment_summary_text(
                audit_payload,
                reference_geometry=context["reference_geometry"],
                dem_bounds_geometry=dem_bounds_geometry,
                gauge_point=gauge_point,
                outlet_point=original_point,
                outlet_label=outlet_label,
            ),
            transform=axes[0].transAxes,
            va="top",
            ha="left",
            fontsize=9,
            bbox={"boxstyle": "round,pad=0.4", "facecolor": "white", "edgecolor": "#88929d", "alpha": 0.92},
        )

        primary_point = helper_points[1]["snapped_point"] or helper_points[1]["original_point"]
        zoom_helpers = []
        if primary_point is not None and dem_bounds_geometry is not None and not dem_bounds_geometry.covers(primary_point):
            zoom_helpers.append(
                HmsWatershedVerification._plot_distance_connector(
                    axes[1],
                    primary_point,
                    dem_bounds_geometry,
                    "#2563eb",
                    "To DEM extent",
                )
            )
        if primary_point is not None and not context["reference_geometry"].covers(primary_point):
            zoom_helpers.append(
                HmsWatershedVerification._plot_distance_connector(
                    axes[1],
                    primary_point,
                    context["reference_geometry"],
                    "#1f1f1f",
                    "To reference basin",
                )
            )
        if primary_point is not None and not context["taudem_geometry"].covers(primary_point):
            zoom_helpers.append(
                HmsWatershedVerification._plot_distance_connector(
                    axes[1],
                    primary_point,
                    context["taudem_geometry"],
                    "#cc5500",
                    "To TauDEM basin",
                )
            )

        zoom_bounds = HmsWatershedVerification._point_extent_bounds(primary_point, zoom_helpers)
        if zoom_bounds is None:
            zoom_bounds = full_bounds
        HmsWatershedVerification._apply_plot_extent(axes[1], zoom_bounds, padding_ratio=0.08, min_padding=750.0)
        HmsWatershedVerification._style_axis(axes[1], "Outlet relative to DEM and basin edges")

        write_result = HmsWatershedVerification._save_figure(fig, output_path)
        plt.close(fig)

        return {
            "title": "Gauge, outlet, and DEM extent context",
            "description": (
                "Two-panel context figure showing the buffered DEM extent, reference basin, TauDEM basin, "
                "stream network, gauge location, and current TauDEM outlet."
            ),
            "path": str(output_path),
            "status": write_result["status"],
            "bytes": write_result["bytes"],
        }

    @staticmethod
    @log_call
    def verify_boundary(
        reference_boundary_path: Union[str, Path],
        *,
        taudem_watershed_raster_path: Optional[Union[str, Path]] = None,
        taudem_boundary_path: Optional[Union[str, Path]] = None,
        output_path: Optional[Union[str, Path]] = None,
        original_outlet_path: Optional[Union[str, Path]] = None,
        snapped_outlet_path: Optional[Union[str, Path]] = None,
        stream_network_path: Optional[Union[str, Path]] = None,
        fallback_crs: Optional[Any] = None,
        study_name: Optional[str] = None,
        workspace_root: Optional[Union[str, Path]] = None,
        site_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compare a TauDEM basin against an official reference boundary."""
        context = HmsWatershedVerification._build_verification_context(
            reference_boundary_path=reference_boundary_path,
            taudem_watershed_raster_path=taudem_watershed_raster_path,
            taudem_boundary_path=taudem_boundary_path,
            original_outlet_path=original_outlet_path,
            snapped_outlet_path=snapped_outlet_path,
            stream_network_path=stream_network_path,
            fallback_crs=fallback_crs,
        )
        metrics = HmsWatershedVerification._compute_metrics(context)

        payload = {
            "schema_version": "1.0",
            "study_type": "taudem_boundary_verification",
            "generated_at": HmsWatershedVerification._utc_now(),
            "status": "completed",
            "study_name": study_name,
            "site_id": site_id,
            "workspace_root": str(Path(workspace_root)) if workspace_root is not None else None,
            "verification_crs": str(context["verification_crs"]),
            "inputs": {
                "reference_boundary_path": str(context["reference_boundary_path"]),
                "taudem_source_path": str(context["taudem_source_path"]),
                "taudem_source_type": context["taudem_source_type"],
                "original_outlet_path": (
                    str(context["original_outlet_path"]) if context["original_outlet_path"] else None
                ),
                "snapped_outlet_path": (
                    str(context["snapped_outlet_path"]) if context["snapped_outlet_path"] else None
                ),
                "stream_network_path": (
                    str(context["stream_network_path"]) if context["stream_network_path"] else None
                ),
            },
            "metrics": metrics,
            "builder": {
                "package": "hms-commander",
                "class": "HmsWatershedVerification",
                "version": PACKAGE_VERSION,
            },
        }

        if output_path is not None:
            output_path = Path(output_path)
            write_result = HmsWatershedVerification._write_json(output_path, payload)
            payload["artifact"] = {
                "path": str(output_path),
                "status": write_result["status"],
                "bytes": write_result["bytes"],
            }

        return payload

    @staticmethod
    @log_call
    def verify_taudem_run(
        run_root: Union[str, Path],
        reference_boundary_path: Union[str, Path],
        *,
        output_path: Optional[Union[str, Path]] = None,
        watershed_path: Optional[Union[str, Path]] = None,
        original_outlet_path: Optional[Union[str, Path]] = None,
        snapped_outlet_path: Optional[Union[str, Path]] = None,
        stream_network_path: Optional[Union[str, Path]] = None,
        fallback_crs: Optional[Any] = None,
        study_name: Optional[str] = None,
        workspace_root: Optional[Union[str, Path]] = None,
        site_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Verify a TauDEM run folder using the standard output names when not overridden."""
        run_root = Path(run_root)
        if output_path is None:
            output_path = run_root / "boundary_verification.json"
        watershed_path = Path(watershed_path) if watershed_path else run_root / "w.tif"
        original_outlet_path = (
            Path(original_outlet_path)
            if original_outlet_path
            else (run_root / "outlet.shp" if (run_root / "outlet.shp").exists() else None)
        )
        snapped_outlet_path = (
            Path(snapped_outlet_path)
            if snapped_outlet_path
            else (run_root / "outlet_snapped.shp" if (run_root / "outlet_snapped.shp").exists() else None)
        )
        stream_network_path = (
            Path(stream_network_path)
            if stream_network_path
            else (run_root / "net.shp" if (run_root / "net.shp").exists() else None)
        )

        return HmsWatershedVerification.verify_boundary(
            reference_boundary_path=reference_boundary_path,
            taudem_watershed_raster_path=watershed_path,
            output_path=output_path,
            original_outlet_path=original_outlet_path,
            snapped_outlet_path=snapped_outlet_path,
            stream_network_path=stream_network_path,
            fallback_crs=fallback_crs,
            study_name=study_name,
            workspace_root=workspace_root or run_root.parent,
            site_id=site_id,
        )

    @staticmethod
    @log_call
    def audit_crs_alignment(
        reference_boundary_path: Union[str, Path],
        *,
        output_path: Optional[Union[str, Path]] = None,
        dem_path: Optional[Union[str, Path]] = None,
        taudem_watershed_raster_path: Optional[Union[str, Path]] = None,
        taudem_boundary_path: Optional[Union[str, Path]] = None,
        original_outlet_path: Optional[Union[str, Path]] = None,
        snapped_outlet_path: Optional[Union[str, Path]] = None,
        stream_network_path: Optional[Union[str, Path]] = None,
        gauge_point_path: Optional[Union[str, Path]] = None,
        fallback_crs: Optional[Any] = None,
        study_name: Optional[str] = None,
        workspace_root: Optional[Union[str, Path]] = None,
        site_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Write a durable CRS audit for basin, terrain, outlet, and stream datasets."""
        deps = HmsWatershedVerification._check_dependencies()
        gpd = deps["gpd"]
        rasterio = deps["rasterio"]
        box = deps["box"]

        reference_boundary_path = Path(reference_boundary_path)
        reference_gdf = HmsWatershedVerification._load_vector(reference_boundary_path, fallback_crs=fallback_crs)
        verification_crs = HmsWatershedVerification._resolve_crs(reference_gdf.crs, fallback_crs)
        if verification_crs is None:
            raise ValueError("Could not determine a projected CRS for CRS audit")

        reference_geometry = HmsWatershedVerification._single_geometry(reference_gdf.to_crs(verification_crs))
        reference_geometry_wgs84 = HmsWatershedVerification._single_geometry(reference_gdf.to_crs("EPSG:4326"))

        datasets: Dict[str, Any] = {
            "reference_boundary": HmsWatershedVerification._vector_dataset_summary(
                reference_boundary_path,
                reference_gdf,
                verification_crs,
            )
        }
        inputs: Dict[str, Optional[str]] = {
            "reference_boundary_path": str(reference_boundary_path),
            "dem_path": str(Path(dem_path)) if dem_path is not None else None,
            "taudem_watershed_raster_path": (
                str(Path(taudem_watershed_raster_path)) if taudem_watershed_raster_path is not None else None
            ),
            "taudem_boundary_path": str(Path(taudem_boundary_path)) if taudem_boundary_path is not None else None,
            "original_outlet_path": str(Path(original_outlet_path)) if original_outlet_path is not None else None,
            "snapped_outlet_path": str(Path(snapped_outlet_path)) if snapped_outlet_path is not None else None,
            "stream_network_path": str(Path(stream_network_path)) if stream_network_path is not None else None,
            "gauge_point_path": str(Path(gauge_point_path)) if gauge_point_path is not None else None,
        }

        taudem_geometry = None
        taudem_geometry_wgs84 = None
        if taudem_watershed_raster_path is not None:
            taudem_watershed_raster_path = Path(taudem_watershed_raster_path)
            taudem_gdf = HmsWatershedVerification._polygonize_watershed_raster(
                taudem_watershed_raster_path,
                fallback_crs=verification_crs,
            )
            taudem_geometry = HmsWatershedVerification._single_geometry(taudem_gdf.to_crs(verification_crs))
            taudem_geometry_wgs84 = HmsWatershedVerification._single_geometry(taudem_gdf.to_crs("EPSG:4326"))
            datasets["taudem_watershed"] = HmsWatershedVerification._raster_dataset_summary(
                taudem_watershed_raster_path,
                verification_crs,
                fallback_crs=verification_crs,
            )
        elif taudem_boundary_path is not None:
            taudem_boundary_path = Path(taudem_boundary_path)
            taudem_gdf = HmsWatershedVerification._load_vector(
                taudem_boundary_path,
                fallback_crs=verification_crs,
            )
            taudem_geometry = HmsWatershedVerification._single_geometry(taudem_gdf.to_crs(verification_crs))
            taudem_geometry_wgs84 = HmsWatershedVerification._single_geometry(taudem_gdf.to_crs("EPSG:4326"))
            datasets["taudem_boundary"] = HmsWatershedVerification._vector_dataset_summary(
                taudem_boundary_path,
                taudem_gdf,
                verification_crs,
            )

        dem_bounds_geometry = None
        dem_bounds_geometry_wgs84 = None
        if dem_path is not None:
            dem_path = Path(dem_path)
            datasets["dem"] = HmsWatershedVerification._raster_dataset_summary(
                dem_path,
                verification_crs,
                fallback_crs=verification_crs,
            )
            with rasterio.open(dem_path) as src:
                dem_crs = HmsWatershedVerification._resolve_crs(src.crs, verification_crs)
                dem_bounds_gdf = gpd.GeoDataFrame(
                    {"id": [1]},
                    geometry=[box(*src.bounds)],
                    crs=dem_crs,
                )
            dem_bounds_geometry = dem_bounds_gdf.to_crs(verification_crs).geometry.iloc[0]
            dem_bounds_geometry_wgs84 = dem_bounds_gdf.to_crs("EPSG:4326").geometry.iloc[0]

        original_outlet_gdf = None
        snapped_outlet_gdf = None
        gauge_point_gdf = None

        if original_outlet_path is not None:
            original_outlet_path = Path(original_outlet_path)
            original_outlet_gdf = HmsWatershedVerification._load_vector(
                original_outlet_path,
                fallback_crs=verification_crs,
            )
            datasets["original_outlet"] = HmsWatershedVerification._vector_dataset_summary(
                original_outlet_path,
                original_outlet_gdf,
                verification_crs,
            )
        if snapped_outlet_path is not None:
            snapped_outlet_path = Path(snapped_outlet_path)
            snapped_outlet_gdf = HmsWatershedVerification._load_vector(
                snapped_outlet_path,
                fallback_crs=verification_crs,
            )
            datasets["snapped_outlet"] = HmsWatershedVerification._vector_dataset_summary(
                snapped_outlet_path,
                snapped_outlet_gdf,
                verification_crs,
            )
        if stream_network_path is not None:
            stream_network_path = Path(stream_network_path)
            streams_gdf = HmsWatershedVerification._load_vector(
                stream_network_path,
                fallback_crs=verification_crs,
            )
            datasets["stream_network"] = HmsWatershedVerification._vector_dataset_summary(
                stream_network_path,
                streams_gdf,
                verification_crs,
            )
        if gauge_point_path is not None:
            gauge_point_path = Path(gauge_point_path)
            gauge_point_gdf = HmsWatershedVerification._load_vector(
                gauge_point_path,
                fallback_crs=verification_crs,
            )
            datasets["gauge_point"] = HmsWatershedVerification._vector_dataset_summary(
                gauge_point_path,
                gauge_point_gdf,
                verification_crs,
            )

        comparisons: Dict[str, Any] = {}
        original_point = None
        original_point_wgs84 = None
        snapped_point = None
        gauge_point = None

        if original_outlet_gdf is not None and len(original_outlet_gdf) > 0:
            original_point = original_outlet_gdf.to_crs(verification_crs).geometry.iloc[0]
            original_point_wgs84 = original_outlet_gdf.to_crs("EPSG:4326").geometry.iloc[0]
            comparisons["original_outlet_vs_reference_boundary"] = {
                "inside_reference_boundary_verification_crs": bool(reference_geometry.covers(original_point)),
                "inside_reference_boundary_wgs84": bool(reference_geometry_wgs84.covers(original_point_wgs84)),
                "distance_to_reference_boundary_m": round(float(reference_geometry.distance(original_point)), 3),
            }
            if taudem_geometry is not None and taudem_geometry_wgs84 is not None:
                comparisons["original_outlet_vs_taudem_boundary"] = {
                    "inside_taudem_boundary_verification_crs": bool(taudem_geometry.covers(original_point)),
                    "inside_taudem_boundary_wgs84": bool(taudem_geometry_wgs84.covers(original_point_wgs84)),
                    "distance_to_taudem_boundary_m": round(float(taudem_geometry.distance(original_point)), 3),
                }
            if dem_bounds_geometry is not None and dem_bounds_geometry_wgs84 is not None:
                comparisons["original_outlet_vs_dem_bounds"] = {
                    "inside_dem_bounds_verification_crs": bool(dem_bounds_geometry.covers(original_point)),
                    "inside_dem_bounds_wgs84": bool(dem_bounds_geometry_wgs84.covers(original_point_wgs84)),
                    "distance_to_dem_bounds_m": round(float(dem_bounds_geometry.distance(original_point)), 3),
                }

        if snapped_outlet_gdf is not None and len(snapped_outlet_gdf) > 0:
            snapped_point = snapped_outlet_gdf.to_crs(verification_crs).geometry.iloc[0]
        if gauge_point_gdf is not None and len(gauge_point_gdf) > 0:
            gauge_point = gauge_point_gdf.to_crs(verification_crs).geometry.iloc[0]

        if original_point is not None and snapped_point is not None:
            comparisons["original_vs_snapped_outlet"] = {
                "distance_m": round(float(original_point.distance(snapped_point)), 3),
            }
        if original_point is not None and gauge_point is not None:
            comparisons["original_outlet_vs_gauge_point"] = {
                "distance_m": round(float(original_point.distance(gauge_point)), 3),
            }

        payload = {
            "schema_version": "1.0",
            "study_type": "taudem_crs_alignment_audit",
            "generated_at": HmsWatershedVerification._utc_now(),
            "status": "completed",
            "study_name": study_name,
            "site_id": site_id,
            "workspace_root": str(Path(workspace_root)) if workspace_root is not None else None,
            "verification_crs": str(verification_crs),
            "inputs": inputs,
            "datasets": datasets,
            "comparisons": comparisons,
            "builder": {
                "package": "hms-commander",
                "class": "HmsWatershedVerification",
                "version": PACKAGE_VERSION,
            },
        }

        if output_path is not None:
            output_path = Path(output_path)
            write_result = HmsWatershedVerification._write_json(output_path, payload)
            payload["artifact"] = {
                "path": str(output_path),
                "status": write_result["status"],
                "bytes": write_result["bytes"],
            }

        return payload

    @staticmethod
    @log_call
    def create_crs_alignment_figure(
        reference_boundary_path: Union[str, Path],
        *,
        output_path: Union[str, Path],
        manifest_path: Optional[Union[str, Path]] = None,
        dem_path: Optional[Union[str, Path]] = None,
        taudem_watershed_raster_path: Optional[Union[str, Path]] = None,
        taudem_boundary_path: Optional[Union[str, Path]] = None,
        original_outlet_path: Optional[Union[str, Path]] = None,
        snapped_outlet_path: Optional[Union[str, Path]] = None,
        stream_network_path: Optional[Union[str, Path]] = None,
        gauge_point_path: Optional[Union[str, Path]] = None,
        fallback_crs: Optional[Any] = None,
        study_name: Optional[str] = None,
        outlet_label: str = "current outlet",
        workspace_root: Optional[Union[str, Path]] = None,
        site_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a context figure for gauge, outlet, basin, and DEM extent alignment."""
        audit_payload = HmsWatershedVerification.audit_crs_alignment(
            reference_boundary_path=reference_boundary_path,
            dem_path=dem_path,
            taudem_watershed_raster_path=taudem_watershed_raster_path,
            taudem_boundary_path=taudem_boundary_path,
            original_outlet_path=original_outlet_path,
            snapped_outlet_path=snapped_outlet_path,
            stream_network_path=stream_network_path,
            gauge_point_path=gauge_point_path,
            fallback_crs=fallback_crs,
            study_name=study_name,
            workspace_root=workspace_root,
            site_id=site_id,
        )
        context = HmsWatershedVerification._build_verification_context(
            reference_boundary_path=reference_boundary_path,
            taudem_watershed_raster_path=taudem_watershed_raster_path,
            taudem_boundary_path=taudem_boundary_path,
            original_outlet_path=original_outlet_path,
            snapped_outlet_path=snapped_outlet_path,
            stream_network_path=stream_network_path,
            fallback_crs=fallback_crs,
        )

        deps = HmsWatershedVerification._check_dependencies()
        gpd = deps["gpd"]
        rasterio = deps["rasterio"]
        box = deps["box"]

        verification_crs = context["verification_crs"]
        gauge_point = None
        if gauge_point_path is not None:
            gauge_gdf = HmsWatershedVerification._load_vector(gauge_point_path, fallback_crs=verification_crs)
            gauge_point = gauge_gdf.to_crs(verification_crs).geometry.iloc[0]

        dem_bounds_geometry = None
        if dem_path is not None:
            with rasterio.open(dem_path) as src:
                dem_crs = HmsWatershedVerification._resolve_crs(src.crs, verification_crs)
                dem_bounds_gdf = gpd.GeoDataFrame(
                    {"id": [1]},
                    geometry=[box(*src.bounds)],
                    crs=dem_crs,
                )
            dem_bounds_geometry = dem_bounds_gdf.to_crs(verification_crs).geometry.iloc[0]

        output_path = Path(output_path)
        figure_artifact = HmsWatershedVerification._create_crs_alignment_context_figure(
            context,
            audit_payload,
            output_path=output_path,
            dem_bounds_geometry=dem_bounds_geometry,
            gauge_point=gauge_point,
            study_name=study_name,
            outlet_label=outlet_label,
        )

        payload = {
            "schema_version": "1.0",
            "study_type": "taudem_crs_alignment_figure",
            "generated_at": HmsWatershedVerification._utc_now(),
            "status": "completed",
            "study_name": study_name,
            "site_id": site_id,
            "workspace_root": str(Path(workspace_root)) if workspace_root is not None else None,
            "verification_crs": str(verification_crs),
            "inputs": audit_payload["inputs"],
            "summary": audit_payload.get("comparisons", {}),
            "figure": figure_artifact,
            "builder": {
                "package": "hms-commander",
                "class": "HmsWatershedVerification",
                "version": PACKAGE_VERSION,
            },
        }

        if manifest_path is not None:
            manifest_path = Path(manifest_path)
            write_result = HmsWatershedVerification._write_json(manifest_path, payload)
            payload["artifact"] = {
                "path": str(manifest_path),
                "status": write_result["status"],
                "bytes": write_result["bytes"],
            }

        return payload

    @staticmethod
    @log_call
    def create_verification_figures(
        reference_boundary_path: Union[str, Path],
        *,
        output_dir: Union[str, Path],
        manifest_path: Optional[Union[str, Path]] = None,
        taudem_watershed_raster_path: Optional[Union[str, Path]] = None,
        taudem_boundary_path: Optional[Union[str, Path]] = None,
        original_outlet_path: Optional[Union[str, Path]] = None,
        snapped_outlet_path: Optional[Union[str, Path]] = None,
        stream_network_path: Optional[Union[str, Path]] = None,
        fel_raster_path: Optional[Union[str, Path]] = None,
        ad8_raster_path: Optional[Union[str, Path]] = None,
        src_raster_path: Optional[Union[str, Path]] = None,
        fallback_crs: Optional[Any] = None,
        study_name: Optional[str] = None,
        workspace_root: Optional[Union[str, Path]] = None,
        site_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate durable QA figures for a TauDEM verification dataset."""
        context = HmsWatershedVerification._build_verification_context(
            reference_boundary_path=reference_boundary_path,
            taudem_watershed_raster_path=taudem_watershed_raster_path,
            taudem_boundary_path=taudem_boundary_path,
            original_outlet_path=original_outlet_path,
            snapped_outlet_path=snapped_outlet_path,
            stream_network_path=stream_network_path,
            fallback_crs=fallback_crs,
        )
        metrics = HmsWatershedVerification._compute_metrics(context)

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        if manifest_path is None:
            manifest_path = output_dir / "figure_manifest.json"
        else:
            manifest_path = Path(manifest_path)

        outlet_figure_path = output_dir / "outlet_boundary_mismatch.png"
        overview_figure_path = output_dir / "taudem_outputs_overview.png"

        outlet_figure = HmsWatershedVerification._create_outlet_mismatch_figure(
            context,
            metrics,
            output_path=outlet_figure_path,
            study_name=study_name,
        )
        overview_figure = HmsWatershedVerification._create_taudem_outputs_overview_figure(
            context,
            metrics,
            output_path=overview_figure_path,
            fel_raster_path=fel_raster_path,
            ad8_raster_path=ad8_raster_path,
            src_raster_path=src_raster_path,
            study_name=study_name,
        )

        payload = {
            "schema_version": "1.0",
            "study_type": "taudem_verification_figures",
            "generated_at": HmsWatershedVerification._utc_now(),
            "status": "completed",
            "study_name": study_name,
            "site_id": site_id,
            "workspace_root": str(Path(workspace_root)) if workspace_root is not None else None,
            "verification_crs": str(context["verification_crs"]),
            "inputs": {
                "reference_boundary_path": str(context["reference_boundary_path"]),
                "taudem_source_path": str(context["taudem_source_path"]),
                "taudem_source_type": context["taudem_source_type"],
                "fel_raster_path": str(Path(fel_raster_path)) if fel_raster_path else None,
                "ad8_raster_path": str(Path(ad8_raster_path)) if ad8_raster_path else None,
                "src_raster_path": str(Path(src_raster_path)) if src_raster_path else None,
                "original_outlet_path": (
                    str(context["original_outlet_path"]) if context["original_outlet_path"] else None
                ),
                "snapped_outlet_path": (
                    str(context["snapped_outlet_path"]) if context["snapped_outlet_path"] else None
                ),
                "stream_network_path": (
                    str(context["stream_network_path"]) if context["stream_network_path"] else None
                ),
            },
            "metrics_summary": {
                "reference_basin_area_sqmi": metrics["reference_basin_area_sqmi"],
                "taudem_basin_area_sqmi": metrics["taudem_basin_area_sqmi"],
                "absolute_percent_area_difference": metrics["absolute_percent_area_difference"],
                "intersection_over_union": metrics["polygon_overlap"]["intersection_over_union"],
                "snap_distance_m": metrics["outlet"]["snap_distance_m"],
                "stream_feature_count": metrics["stream_network"]["feature_count"],
                "max_stream_order": metrics["stream_network"]["max_stream_order"],
            },
            "figures": {
                "outlet_boundary_mismatch": outlet_figure,
                "taudem_outputs_overview": overview_figure,
            },
            "builder": {
                "package": "hms-commander",
                "class": "HmsWatershedVerification",
                "version": PACKAGE_VERSION,
            },
        }

        write_result = HmsWatershedVerification._write_json(Path(manifest_path), payload)
        payload["artifact"] = {
            "path": str(manifest_path),
            "status": write_result["status"],
            "bytes": write_result["bytes"],
        }

        return payload

    @staticmethod
    @log_call
    def create_taudem_run_figures(
        run_root: Union[str, Path],
        reference_boundary_path: Union[str, Path],
        *,
        output_dir: Optional[Union[str, Path]] = None,
        manifest_path: Optional[Union[str, Path]] = None,
        watershed_path: Optional[Union[str, Path]] = None,
        original_outlet_path: Optional[Union[str, Path]] = None,
        snapped_outlet_path: Optional[Union[str, Path]] = None,
        stream_network_path: Optional[Union[str, Path]] = None,
        fel_raster_path: Optional[Union[str, Path]] = None,
        ad8_raster_path: Optional[Union[str, Path]] = None,
        src_raster_path: Optional[Union[str, Path]] = None,
        fallback_crs: Optional[Any] = None,
        study_name: Optional[str] = None,
        workspace_root: Optional[Union[str, Path]] = None,
        site_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create standard TauDEM verification figures from a TauDEM run folder."""
        run_root = Path(run_root)
        if output_dir is None:
            output_dir = run_root / "figures"
        output_dir = Path(output_dir)
        if manifest_path is None:
            manifest_path = output_dir / "figure_manifest.json"

        watershed_path = Path(watershed_path) if watershed_path else run_root / "w.tif"
        original_outlet_path = (
            Path(original_outlet_path)
            if original_outlet_path
            else (run_root / "outlet.shp" if (run_root / "outlet.shp").exists() else None)
        )
        snapped_outlet_path = (
            Path(snapped_outlet_path)
            if snapped_outlet_path
            else (run_root / "outlet_snapped.shp" if (run_root / "outlet_snapped.shp").exists() else None)
        )
        stream_network_path = (
            Path(stream_network_path)
            if stream_network_path
            else (run_root / "net.shp" if (run_root / "net.shp").exists() else None)
        )
        fel_raster_path = (
            Path(fel_raster_path)
            if fel_raster_path
            else (run_root / "fel.tif" if (run_root / "fel.tif").exists() else None)
        )
        ad8_raster_path = (
            Path(ad8_raster_path)
            if ad8_raster_path
            else (run_root / "ad8.tif" if (run_root / "ad8.tif").exists() else None)
        )
        src_raster_path = (
            Path(src_raster_path)
            if src_raster_path
            else (run_root / "src.tif" if (run_root / "src.tif").exists() else None)
        )

        return HmsWatershedVerification.create_verification_figures(
            reference_boundary_path=reference_boundary_path,
            output_dir=output_dir,
            manifest_path=manifest_path,
            taudem_watershed_raster_path=watershed_path,
            original_outlet_path=original_outlet_path,
            snapped_outlet_path=snapped_outlet_path,
            stream_network_path=stream_network_path,
            fel_raster_path=fel_raster_path,
            ad8_raster_path=ad8_raster_path,
            src_raster_path=src_raster_path,
            fallback_crs=fallback_crs,
            study_name=study_name,
            workspace_root=workspace_root or run_root.parent,
            site_id=site_id,
        )
