"""
Gauge-first hydrology study and TauDEM input-pack helpers.

This module restores the lightweight TauDEM preprocessing surface used by the
Illinois-first `ras-agent` work. The scope is intentionally narrow:

- fetch gauge-first hydrology context from USGS NLDI/NWIS services
- package a durable study workspace with manifest/report/data-gap artifacts
- build a TauDEM handoff pack with pour point, basin boundary, HUC references,
  and a recommended DEM clip extent

The implementation stays within the repository's static-class pattern and uses
plain GeoJSON dictionaries so the core workflow does not require optional GIS
dependencies.
"""

from __future__ import annotations

import json
import urllib.parse
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

import requests

from .Decorators import log_call
from .HmsHuc import HmsHuc
from .LoggingConfig import get_logger

logger = get_logger(__name__)

DEFAULT_TIMEOUT = 60
DEFAULT_HUC_LEVELS: Tuple[str, ...] = ("huc8", "huc12")
NLDI_SITE_URL = "https://api.water.usgs.gov/nldi/linked-data/nwissite/{feature_id}"
NLDI_FLOWLINES_URL = (
    "https://api.water.usgs.gov/nldi/linked-data/nwissite/{feature_id}/navigation/UT/flowlines"
)
NWIS_SITE_URL = "https://waterservices.usgs.gov/nwis/site/"
FABRIC_COLLECTION_URL = (
    "https://api.water.usgs.gov/fabric/pygeoapi/collections/{collection}/items"
)

try:
    PACKAGE_VERSION = version("hms-commander")
except PackageNotFoundError:  # pragma: no cover - fallback for non-installed source runs
    PACKAGE_VERSION = "0.2.1"

_STUDY_ARTIFACT_SPECS: Tuple[Dict[str, Any], ...] = (
    {
        "id": "gauge_metadata",
        "artifact_type": "metadata",
        "format": "json",
        "description": "Combined NLDI and NWIS gauge metadata.",
        "path": "metadata/gauge_metadata.json",
    },
    {
        "id": "nldi_basin",
        "artifact_type": "vector",
        "format": "geojson",
        "description": "NLDI upstream basin outline.",
        "path": "context/nldi_basin.geojson",
    },
    {
        "id": "upstream_hydrography",
        "artifact_type": "vector",
        "format": "geojson",
        "description": "NLDI upstream tributary flowline context.",
        "path": "context/upstream_hydrography.geojson",
    },
    {
        "id": "provenance",
        "artifact_type": "report",
        "format": "json",
        "description": "Service and library provenance for generated artifacts.",
        "path": "metadata/provenance.json",
    },
    {
        "id": "manifest",
        "artifact_type": "report",
        "format": "json",
        "description": "Study manifest for downstream orchestration.",
        "path": "metadata/study_manifest.json",
    },
    {
        "id": "study_report",
        "artifact_type": "report",
        "format": "json",
        "description": "High-level study status summary.",
        "path": "reports/study_report.json",
    },
    {
        "id": "data_gap_analysis",
        "artifact_type": "report",
        "format": "json",
        "description": "Structured data gap analysis.",
        "path": "reports/data_gap_analysis.json",
    },
    {
        "id": "huc8_context",
        "artifact_type": "vector",
        "format": "geojson",
        "description": "HUC8 watershed context.",
        "path": "context/huc8_context.geojson",
    },
    {
        "id": "huc12_context",
        "artifact_type": "vector",
        "format": "geojson",
        "description": "HUC12 watershed context.",
        "path": "context/huc12_context.geojson",
    },
)

_PACK_ARTIFACT_SPECS: Tuple[Dict[str, Any], ...] = (
    {
        "id": "taudem_pour_point",
        "artifact_type": "vector",
        "format": "geojson",
        "description": "TauDEM pour point derived from gauge metadata.",
        "path": "raw/taudem_input_pack/pour_point.geojson",
    },
    {
        "id": "taudem_basin_boundary",
        "artifact_type": "vector",
        "format": "geojson",
        "description": "Basin boundary prepared for TauDEM context.",
        "path": "raw/taudem_input_pack/basin_boundary.geojson",
    },
    {
        "id": "taudem_huc_context_reference",
        "artifact_type": "reference",
        "format": "json",
        "description": "References to HUC context artifacts in the study workspace.",
        "path": "raw/taudem_input_pack/huc_context_reference.json",
    },
    {
        "id": "taudem_dem_clip_extent",
        "artifact_type": "metadata",
        "format": "json",
        "description": "Recommended DEM clip extent metadata for TauDEM preprocessing.",
        "path": "raw/taudem_input_pack/recommended_dem_clip_extent.json",
    },
    {
        "id": "taudem_pack_provenance",
        "artifact_type": "report",
        "format": "json",
        "description": "Provenance for TauDEM input-pack artifacts.",
        "path": "raw/taudem_input_pack/provenance.json",
    },
    {
        "id": "taudem_pack_manifest",
        "artifact_type": "report",
        "format": "json",
        "description": "Machine-readable manifest for the TauDEM input pack.",
        "path": "raw/taudem_input_pack/taudem_input_pack_manifest.json",
    },
    {
        "id": "taudem_pack_report",
        "artifact_type": "report",
        "format": "json",
        "description": "High-level status summary for the TauDEM input pack.",
        "path": "raw/taudem_input_pack/report.json",
    },
    {
        "id": "taudem_pack_data_gap_analysis",
        "artifact_type": "report",
        "format": "json",
        "description": "Structured data gap analysis for the TauDEM input pack.",
        "path": "raw/taudem_input_pack/data_gap_analysis.json",
    },
)


def _utc_now() -> str:
    """Return a compact UTC timestamp with a trailing Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_site_id(site_id: Any) -> str:
    """Normalize a USGS site id while preserving leading zeros when provided."""
    if site_id is None:
        raise ValueError("site_id is required")
    normalized = str(site_id).strip()
    if normalized.upper().startswith("USGS-"):
        normalized = normalized.split("-", 1)[1]
    if not normalized:
        raise ValueError("site_id cannot be empty")
    return normalized


def _nldi_feature_id(site_id: Any) -> str:
    """Build the NLDI feature id used by the USGS API."""
    return f"USGS-{_normalize_site_id(site_id)}"


def _json_default(value: Any) -> Any:
    """Serialize pathlib objects inside JSON payloads."""
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _write_json(path: Path, payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Write JSON with stable indentation and return artifact write metadata."""
    existed = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=_json_default) + "\n", encoding="utf-8")
    return {
        "status": "updated" if existed else "created",
        "bytes": path.stat().st_size,
    }


def _load_json(path: Path) -> Dict[str, Any]:
    """Read JSON from disk."""
    return json.loads(path.read_text(encoding="utf-8"))


def _build_request_url(url: str, params: Optional[Mapping[str, Any]] = None) -> str:
    """Build a stable request url string for provenance records."""
    if not params:
        return url
    return f"{url}?{urllib.parse.urlencode(params, doseq=True)}"


def _request_json(
    url: str,
    params: Optional[Mapping[str, Any]] = None,
    session: Optional[Any] = None,
    *,
    artifact_id: str,
    source_name: str,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """GET a JSON endpoint and return both payload and provenance record."""
    client = session or requests
    response = client.get(url, params=params, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    record = {
        "retrieved_at": _utc_now(),
        "source_name": source_name,
        "method": "GET",
        "request_url": _build_request_url(url, params),
        "status_code": getattr(response, "status_code", None),
        "artifact_id": artifact_id,
        "notes": None,
    }
    return response.json(), record


def _request_text(
    url: str,
    params: Optional[Mapping[str, Any]] = None,
    session: Optional[Any] = None,
    *,
    artifact_id: str,
    source_name: str,
) -> Tuple[str, Dict[str, Any]]:
    """GET a text endpoint and return both payload and provenance record."""
    client = session or requests
    response = client.get(url, params=params, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    record = {
        "retrieved_at": _utc_now(),
        "source_name": source_name,
        "method": "GET",
        "request_url": _build_request_url(url, params),
        "status_code": getattr(response, "status_code", None),
        "artifact_id": artifact_id,
        "notes": None,
    }
    return response.text, record


def _first_feature(feature_or_collection: Mapping[str, Any]) -> Dict[str, Any]:
    """Extract the first feature from a FeatureCollection or Feature payload."""
    payload_type = feature_or_collection.get("type")
    if payload_type == "Feature":
        return dict(feature_or_collection)
    if payload_type != "FeatureCollection":
        raise ValueError("Expected a Feature or FeatureCollection GeoJSON payload")
    features = feature_or_collection.get("features") or []
    if not features:
        raise ValueError("FeatureCollection does not contain any features")
    return dict(features[0])


def _extract_coordinates(gauge_feature: Mapping[str, Any]) -> Tuple[float, float]:
    """Extract longitude/latitude from an NLDI point feature."""
    geometry = gauge_feature.get("geometry") or {}
    coordinates = geometry.get("coordinates") or []
    if len(coordinates) < 2:
        raise ValueError("Gauge feature is missing point coordinates")
    return float(coordinates[0]), float(coordinates[1])


def _parse_nwis_rdb(rdb_text: str) -> Dict[str, str]:
    """Parse the first data row from the NWIS RDB site service."""
    data_lines = [
        line
        for line in rdb_text.splitlines()
        if line.strip() and not line.startswith("#")
    ]
    if len(data_lines) < 3:
        return {}
    headers = data_lines[0].split("\t")
    values = data_lines[2].split("\t")
    row = dict(zip(headers, values))
    return {key: value for key, value in row.items() if value != ""}


def _normalize_huc_level(level: str) -> Tuple[str, str, str]:
    """Normalize a HUC level name to artifact id, collection name, and property key."""
    normalized = str(level).lower().replace("_", "").replace("-", "")
    mapping = {
        "huc8": ("huc8_context", "nhdplusv2-huc08", "huc_8"),
        "huc12": ("huc12_context", "nhdplusv2-huc12", "huc_12"),
    }
    if normalized not in mapping:
        raise ValueError(f"Unsupported HUC level: {level}")
    return mapping[normalized]


def _features_from_geometry(feature_or_geometry: Any) -> List[Tuple[float, float]]:
    """Collect all xy pairs from common GeoJSON payload types."""
    points: List[Tuple[float, float]] = []

    def walk(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, Mapping):
            value_type = value.get("type")
            if value_type == "FeatureCollection":
                for feature in value.get("features", []):
                    walk(feature)
                return
            if value_type == "Feature":
                walk(value.get("geometry"))
                return
            if value_type == "GeometryCollection":
                for geometry in value.get("geometries", []):
                    walk(geometry)
                return
            if "coordinates" in value:
                walk(value.get("coordinates"))
                return
            return
        if isinstance(value, (list, tuple)):
            if len(value) >= 2 and all(isinstance(component, (int, float)) for component in value[:2]):
                points.append((float(value[0]), float(value[1])))
                return
            for item in value:
                walk(item)

    walk(feature_or_geometry)
    return points


def _geometry_bounds(feature_or_geometry: Any) -> Tuple[float, float, float, float]:
    """Compute bounds from GeoJSON without requiring shapely."""
    points = _features_from_geometry(feature_or_geometry)
    if not points:
        raise ValueError("No coordinates were found in the supplied geometry")
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return (min(xs), min(ys), max(xs), max(ys))


def _bounds_polygon(bounds: Sequence[float]) -> Dict[str, Any]:
    """Convert bounds into a simple bounding-box polygon."""
    west, south, east, north = bounds
    return {
        "type": "Polygon",
        "coordinates": [[
            [west, south],
            [east, south],
            [east, north],
            [west, north],
            [west, south],
        ]],
    }


def _recommend_dem_clip_extent(
    feature_or_geometry: Any,
    *,
    buffer_fraction: float = 0.05,
    min_buffer_degrees: float = 0.01,
) -> Dict[str, Any]:
    """Recommend a slightly padded DEM clip envelope around a reference geometry."""
    west, south, east, north = _geometry_bounds(feature_or_geometry)
    x_buffer = round(max((east - west) * buffer_fraction, min_buffer_degrees), 12)
    y_buffer = round(max((north - south) * buffer_fraction, min_buffer_degrees), 12)
    return {
        "source_bounds": [round(west, 12), round(south, 12), round(east, 12), round(north, 12)],
        "recommended_bounds": [
            round(west - x_buffer, 12),
            round(south - y_buffer, 12),
            round(east + x_buffer, 12),
            round(north + y_buffer, 12),
        ],
        "buffer_fraction": buffer_fraction,
        "minimum_buffer_degrees": min_buffer_degrees,
        "applied_buffer_degrees": {"x": x_buffer, "y": y_buffer},
    }


def _artifact_catalog(
    specs: Sequence[Mapping[str, Any]],
    workspace_root: Path,
    artifact_state: Optional[Mapping[str, Mapping[str, Any]]] = None,
    *,
    status_overrides: Optional[Mapping[str, str]] = None,
    omit_bytes_for: Optional[Iterable[str]] = None,
) -> List[Dict[str, Any]]:
    """Build a manifest-style artifact catalog from filesystem state and writes."""
    state = artifact_state or {}
    overrides = status_overrides or {}
    omit_bytes = set(omit_bytes_for or [])
    artifacts: List[Dict[str, Any]] = []

    for spec in specs:
        artifact_id = spec["id"]
        absolute_path = workspace_root / spec["path"]
        known_state = dict(state.get(artifact_id, {}))
        status = overrides.get(artifact_id)
        if status is None:
            if known_state.get("status"):
                status = str(known_state["status"])
            elif absolute_path.exists():
                status = "created"
            else:
                status = "planned"

        entry = dict(spec)
        entry["status"] = status
        byte_count = known_state.get("bytes")
        if byte_count is None and absolute_path.exists():
            byte_count = absolute_path.stat().st_size
        if status != "planned" and byte_count is not None and artifact_id not in omit_bytes:
            entry["bytes"] = byte_count
        artifacts.append(entry)

    return artifacts


def _artifact_rows(
    artifact_catalog: Sequence[Mapping[str, Any]],
    *,
    status_overrides: Optional[Mapping[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Build the compact artifact rows used by reports."""
    overrides = status_overrides or {}
    rows: List[Dict[str, Any]] = []
    for artifact in artifact_catalog:
        rows.append(
            {
                "id": artifact["id"],
                "path": artifact["path"],
                "status": overrides.get(str(artifact["id"]), artifact["status"]),
            }
        )
    return rows


def _provenance_record(
    *,
    source_name: str,
    method: str,
    request_url: Union[str, Path],
    artifact_id: str,
    notes: Optional[str] = None,
    status_code: Optional[int] = None,
) -> Dict[str, Any]:
    """Create a provenance record for derived artifacts."""
    return {
        "retrieved_at": _utc_now(),
        "source_name": source_name,
        "method": method,
        "request_url": str(request_url),
        "status_code": status_code,
        "artifact_id": artifact_id,
        "notes": notes,
    }


def _feature_collection_from_geodataframe(gdf: Any) -> Dict[str, Any]:
    """Convert a GeoDataFrame-like object into a GeoJSON dict."""
    if hasattr(gdf, "to_json"):
        return json.loads(gdf.to_json())
    raise TypeError("HUC result could not be converted to GeoJSON")


def _fetch_gauge_metadata_payload(
    site_id: Any,
    session: Optional[Any] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Fetch combined NLDI and NWIS metadata for a USGS gauge site."""
    normalized_site_id = _normalize_site_id(site_id)
    feature_id = _nldi_feature_id(normalized_site_id)
    retrieved_at = _utc_now()

    feature_payload, nldi_record = _request_json(
        NLDI_SITE_URL.format(feature_id=feature_id),
        params={"f": "json"},
        session=session,
        artifact_id="gauge_metadata",
        source_name="USGS NLDI",
    )
    nwis_text, nwis_record = _request_text(
        NWIS_SITE_URL,
        params={
            "format": "rdb",
            "sites": normalized_site_id,
            "siteOutput": "expanded",
        },
        session=session,
        artifact_id="gauge_metadata",
        source_name="USGS NWIS Site Service",
    )

    feature = _first_feature(feature_payload)
    properties = feature.get("properties") or {}
    longitude, latitude = _extract_coordinates(feature)

    metadata = {
        "site_id": normalized_site_id,
        "nldi_feature_id": feature_id,
        "retrieved_at": retrieved_at,
        "name": properties.get("name"),
        "coordinates": {
            "longitude": longitude,
            "latitude": latitude,
        },
        "nldi": {
            "source": properties.get("source"),
            "source_name": properties.get("sourceName"),
            "comid": properties.get("comid"),
            "reachcode": properties.get("reachcode"),
            "measure": properties.get("measure"),
            "navigation_url": properties.get("navigation"),
            "uri": properties.get("uri"),
            "mainstem": properties.get("mainstem"),
            "type": properties.get("type"),
        },
        "nwis_site": _parse_nwis_rdb(nwis_text),
    }
    return metadata, [nldi_record, nwis_record]


def _fetch_nldi_basin_payload(
    site_id: Any,
    session: Optional[Any] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Fetch the NLDI upstream basin for a gauge site."""
    feature_id = _nldi_feature_id(site_id)
    basin_payload, record = _request_json(
        f"{NLDI_SITE_URL.format(feature_id=feature_id)}/basin",
        params={"f": "json"},
        session=session,
        artifact_id="nldi_basin",
        source_name="USGS NLDI",
    )
    return basin_payload, record


def _fetch_upstream_flowlines_payload(
    site_id: Any,
    session: Optional[Any] = None,
    *,
    distance_km: float = 25.0,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Fetch upstream hydrography from NLDI."""
    feature_id = _nldi_feature_id(site_id)
    flowlines_payload, record = _request_json(
        NLDI_FLOWLINES_URL.format(feature_id=feature_id),
        params={"distance": distance_km, "f": "json"},
        session=session,
        artifact_id="upstream_hydrography",
        source_name="USGS NLDI",
    )
    return flowlines_payload, record


def _fetch_huc_context_from_fabric(
    bounds: Sequence[float],
    huc_levels: Sequence[str],
    session: Optional[Any] = None,
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """Fetch HUC context directly from the public Fabric API."""
    bbox = ",".join(str(value) for value in bounds)
    context: Dict[str, Dict[str, Any]] = {}
    records: List[Dict[str, Any]] = []

    for level in huc_levels:
        artifact_id, collection_name, _ = _normalize_huc_level(level)
        payload, record = _request_json(
            FABRIC_COLLECTION_URL.format(collection=collection_name),
            params={"bbox": bbox, "f": "json"},
            session=session,
            artifact_id=artifact_id,
            source_name="USGS Fabric pygeoapi",
        )
        context[artifact_id] = payload
        records.append(record)

    return context, records


def _fetch_huc_context_payload(
    bounds: Sequence[float],
    huc_levels: Optional[Sequence[str]] = None,
    session: Optional[Any] = None,
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """Fetch HUC context using HmsHuc when available, then fall back to Fabric."""
    requested_levels = tuple(huc_levels or DEFAULT_HUC_LEVELS)

    try:
        context: Dict[str, Dict[str, Any]] = {}
        for level in requested_levels:
            artifact_id, _, _ = _normalize_huc_level(level)
            if artifact_id == "huc8_context":
                payload = _feature_collection_from_geodataframe(HmsHuc.get_huc8_for_bounds(tuple(bounds)))
            elif artifact_id == "huc12_context":
                payload = _feature_collection_from_geodataframe(HmsHuc.get_huc12_for_bounds(tuple(bounds)))
            else:  # pragma: no cover - currently not reachable
                raise ValueError(f"Unsupported HUC artifact id: {artifact_id}")
            context[artifact_id] = payload
        return context, []
    except Exception as exc:
        logger.info("Falling back to Fabric API for HUC context after HmsHuc failure: %s", exc)
        return _fetch_huc_context_from_fabric(bounds, requested_levels, session=session)


class HmsHydrologyContext:
    """
    Primitive-first USGS/NLDI gauge and geometry helpers.

    The methods in this class intentionally return plain dictionaries so they
    can be used in lightweight preprocessing steps without optional GIS
    dependencies.
    """

    @staticmethod
    def normalize_site_id(site_id: Any) -> str:
        """Normalize a USGS site id."""
        return _normalize_site_id(site_id)

    @staticmethod
    def get_nldi_feature_id(site_id: Any) -> str:
        """Return the NLDI feature id for a site."""
        return _nldi_feature_id(site_id)

    @staticmethod
    def get_usgs_gauge_metadata(site_id: Any, session: Optional[Any] = None) -> Dict[str, Any]:
        """Fetch combined NLDI and NWIS metadata for a gauge."""
        metadata, _ = _fetch_gauge_metadata_payload(site_id, session=session)
        return metadata

    @staticmethod
    def get_usgs_gauge_point_feature(
        site_id: Optional[Any] = None,
        gauge_metadata: Optional[Mapping[str, Any]] = None,
        session: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Build a point FeatureCollection for a gauge site."""
        metadata = dict(gauge_metadata or {})
        if not metadata:
            if site_id is None:
                raise ValueError("Either site_id or gauge_metadata is required")
            metadata = HmsHydrologyContext.get_usgs_gauge_metadata(site_id, session=session)

        coordinates = metadata.get("coordinates") or {}
        longitude = coordinates.get("longitude")
        latitude = coordinates.get("latitude")
        if longitude is None or latitude is None:
            raise ValueError("Gauge metadata is missing longitude/latitude values")

        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(longitude), float(latitude)],
                    },
                    "properties": {
                        "site_id": metadata.get("site_id") or _normalize_site_id(site_id),
                        "nldi_feature_id": metadata.get("nldi_feature_id") or _nldi_feature_id(site_id),
                        "name": metadata.get("name"),
                    },
                }
            ],
        }

    @staticmethod
    def get_nldi_basin_from_gauge(site_id: Any, session: Optional[Any] = None) -> Dict[str, Any]:
        """Fetch the NLDI basin for a gauge."""
        basin, _ = _fetch_nldi_basin_payload(site_id, session=session)
        return basin

    @staticmethod
    def get_nhdplus_upstream_flowlines_from_gauge(
        site_id: Any,
        distance_km: float = 25.0,
        session: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Fetch upstream NHDPlus flowlines for a gauge."""
        flowlines, _ = _fetch_upstream_flowlines_payload(
            site_id,
            session=session,
            distance_km=distance_km,
        )
        return flowlines

    @staticmethod
    def get_nhd_huc_context_for_bounds(
        bounds: Sequence[float],
        huc_levels: Optional[Sequence[str]] = None,
        session: Optional[Any] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Fetch HUC context for a bounding box."""
        context, _ = _fetch_huc_context_payload(bounds, huc_levels=huc_levels, session=session)
        return context

    @staticmethod
    def get_nhd_huc_context_for_geometry(
        feature_or_geometry: Any,
        huc_levels: Optional[Sequence[str]] = None,
        session: Optional[Any] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Fetch HUC context for a geometry by first deriving its bounds."""
        bounds = HmsHydrologyContext.geometry_bounds(feature_or_geometry)
        return HmsHydrologyContext.get_nhd_huc_context_for_bounds(
            bounds,
            huc_levels=huc_levels,
            session=session,
        )

    @staticmethod
    def get_nhd_huc_boundary_from_gauge(
        site_id: Any,
        huc_level: str = "huc12",
        session: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Fetch the containing HUC boundary for a gauge location."""
        point_feature = HmsHydrologyContext.get_usgs_gauge_point_feature(site_id=site_id, session=session)
        context = HmsHydrologyContext.get_nhd_huc_context_for_geometry(
            point_feature,
            huc_levels=[huc_level],
            session=session,
        )
        artifact_id, _, _ = _normalize_huc_level(huc_level)
        return context[artifact_id]

    @staticmethod
    def get_nhd_huc8_boundary_from_gauge(site_id: Any, session: Optional[Any] = None) -> Dict[str, Any]:
        """Convenience wrapper for HUC8 context."""
        return HmsHydrologyContext.get_nhd_huc_boundary_from_gauge(
            site_id,
            huc_level="huc8",
            session=session,
        )

    @staticmethod
    def get_nhd_huc12_boundary_from_gauge(site_id: Any, session: Optional[Any] = None) -> Dict[str, Any]:
        """Convenience wrapper for HUC12 context."""
        return HmsHydrologyContext.get_nhd_huc_boundary_from_gauge(
            site_id,
            huc_level="huc12",
            session=session,
        )

    @staticmethod
    def get_gauge_metadata(site_id: Any, session: Optional[Any] = None) -> Dict[str, Any]:
        """Compatibility alias for get_usgs_gauge_metadata."""
        return HmsHydrologyContext.get_usgs_gauge_metadata(site_id, session=session)

    @staticmethod
    def get_gauge_point_feature(
        site_id: Optional[Any] = None,
        gauge_metadata: Optional[Mapping[str, Any]] = None,
        session: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Compatibility alias for get_usgs_gauge_point_feature."""
        return HmsHydrologyContext.get_usgs_gauge_point_feature(
            site_id=site_id,
            gauge_metadata=gauge_metadata,
            session=session,
        )

    @staticmethod
    def get_huc_context_for_bounds(
        bounds: Sequence[float],
        huc_levels: Optional[Sequence[str]] = None,
        session: Optional[Any] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Compatibility alias for get_nhd_huc_context_for_bounds."""
        return HmsHydrologyContext.get_nhd_huc_context_for_bounds(
            bounds,
            huc_levels=huc_levels,
            session=session,
        )

    @staticmethod
    def get_huc_context_for_geometry(
        feature_or_geometry: Any,
        huc_levels: Optional[Sequence[str]] = None,
        session: Optional[Any] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Compatibility alias for get_nhd_huc_context_for_geometry."""
        return HmsHydrologyContext.get_nhd_huc_context_for_geometry(
            feature_or_geometry,
            huc_levels=huc_levels,
            session=session,
        )

    @staticmethod
    def get_upstream_flowlines_from_gauge(
        site_id: Any,
        distance_km: float = 25.0,
        session: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Compatibility alias for get_nhdplus_upstream_flowlines_from_gauge."""
        return HmsHydrologyContext.get_nhdplus_upstream_flowlines_from_gauge(
            site_id,
            distance_km=distance_km,
            session=session,
        )

    @staticmethod
    def get_watershed_boundary_from_gauge(site_id: Any, session: Optional[Any] = None) -> Dict[str, Any]:
        """Compatibility alias for the NLDI watershed boundary."""
        return HmsHydrologyContext.get_nldi_basin_from_gauge(site_id, session=session)

    @staticmethod
    def geometry_bounds(feature_or_geometry: Any) -> Tuple[float, float, float, float]:
        """Return GeoJSON bounds as (west, south, east, north)."""
        return _geometry_bounds(feature_or_geometry)

    @staticmethod
    def recommend_dem_clip_extent(
        feature_or_geometry: Any,
        buffer_fraction: float = 0.05,
        min_buffer_degrees: float = 0.01,
    ) -> Dict[str, Any]:
        """Recommend a padded DEM clipping extent around a reference geometry."""
        return _recommend_dem_clip_extent(
            feature_or_geometry,
            buffer_fraction=buffer_fraction,
            min_buffer_degrees=min_buffer_degrees,
        )

    @staticmethod
    def build_pour_point_feature(
        coordinates: Optional[Sequence[float]] = None,
        gauge_metadata: Optional[Mapping[str, Any]] = None,
        properties: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a TauDEM-style pour point FeatureCollection."""
        metadata = dict(gauge_metadata or {})
        if coordinates is None:
            metadata_coordinates = metadata.get("coordinates") or {}
            longitude = metadata_coordinates.get("longitude")
            latitude = metadata_coordinates.get("latitude")
            if longitude is None or latitude is None:
                raise ValueError("coordinates or gauge_metadata with longitude/latitude is required")
            coordinates = [float(longitude), float(latitude)]
        point_properties = {
            "site_id": metadata.get("site_id"),
            "nldi_feature_id": metadata.get("nldi_feature_id"),
            "name": metadata.get("name"),
        }
        if properties:
            point_properties.update(dict(properties))
        point_properties = {key: value for key, value in point_properties.items() if value is not None}
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [float(coordinates[0]), float(coordinates[1])]},
                    "properties": point_properties,
                }
            ],
        }

    @staticmethod
    def build_taudem_handoff(
        gauge_metadata: Optional[Mapping[str, Any]] = None,
        basin_boundary: Optional[Mapping[str, Any]] = None,
        huc_context: Optional[Mapping[str, Any]] = None,
        clip_geometry: Optional[Any] = None,
        buffer_fraction: float = 0.05,
        min_buffer_degrees: float = 0.01,
    ) -> Dict[str, Any]:
        """Build an in-memory TauDEM handoff bundle."""
        pour_point = None
        if gauge_metadata:
            try:
                pour_point = HmsHydrologyContext.build_pour_point_feature(gauge_metadata=gauge_metadata)
            except ValueError:
                pour_point = None

        clip_source = clip_geometry or basin_boundary
        recommended_extent = None
        if clip_source is not None:
            recommended_extent = HmsHydrologyContext.recommend_dem_clip_extent(
                clip_source,
                buffer_fraction=buffer_fraction,
                min_buffer_degrees=min_buffer_degrees,
            )

        return {
            "pour_point": pour_point,
            "basin_boundary": basin_boundary,
            "huc_context": dict(huc_context or {}),
            "recommended_dem_clip_extent": recommended_extent,
        }


class HmsGaugeStudy:
    """Static class for gauge-first study packaging and TauDEM handoff artifacts."""

    @staticmethod
    def normalize_site_id(site_id: Any) -> str:
        """Normalize a USGS site id."""
        return HmsHydrologyContext.normalize_site_id(site_id)

    @staticmethod
    def get_nldi_feature_id(site_id: Any) -> str:
        """Return the NLDI feature id for a site."""
        return HmsHydrologyContext.get_nldi_feature_id(site_id)

    @staticmethod
    def create_workspace(workspace_root: Union[str, Path]) -> Dict[str, Path]:
        """Create the standard gauge-study workspace layout."""
        root = Path(workspace_root)
        workspace = {
            "root": root,
            "metadata": root / "metadata",
            "context": root / "context",
            "reports": root / "reports",
            "raw": root / "raw",
        }
        for path in workspace.values():
            path.mkdir(parents=True, exist_ok=True)
        return workspace

    @staticmethod
    def fetch_gauge_metadata(site_id: Any, session: Optional[Any] = None) -> Dict[str, Any]:
        """Fetch combined gauge metadata."""
        return HmsHydrologyContext.get_usgs_gauge_metadata(site_id, session=session)

    @staticmethod
    def fetch_nldi_basin(site_id: Any, session: Optional[Any] = None) -> Dict[str, Any]:
        """Fetch the NLDI basin for a site."""
        return HmsHydrologyContext.get_nldi_basin_from_gauge(site_id, session=session)

    @staticmethod
    def fetch_upstream_hydrography(
        site_id: Any,
        distance_km: float = 25.0,
        session: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Fetch upstream hydrography for a site."""
        return HmsHydrologyContext.get_nhdplus_upstream_flowlines_from_gauge(
            site_id,
            distance_km=distance_km,
            session=session,
        )

    @staticmethod
    def fetch_huc_context(
        bounds: Sequence[float],
        huc_levels: Optional[Sequence[str]] = None,
        session: Optional[Any] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Fetch HUC context for bounds."""
        return HmsHydrologyContext.get_nhd_huc_context_for_bounds(
            bounds,
            huc_levels=huc_levels,
            session=session,
        )

    @staticmethod
    @log_call
    def build_from_usgs_site(
        site_id: Any,
        workspace_root: Union[str, Path],
        upstream_distance_km: float = 25.0,
        huc_levels: Optional[Sequence[str]] = None,
        session: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Build a gauge-first study workspace from USGS services."""
        normalized_site_id = HmsGaugeStudy.normalize_site_id(site_id)
        workspace = HmsGaugeStudy.create_workspace(workspace_root)
        artifact_state: Dict[str, Dict[str, Any]] = {}

        gauge_metadata, gauge_records = _fetch_gauge_metadata_payload(normalized_site_id, session=session)
        basin_boundary, basin_record = _fetch_nldi_basin_payload(normalized_site_id, session=session)
        provenance_records: List[Dict[str, Any]] = [*gauge_records, basin_record]

        context_payloads: Dict[str, Optional[Dict[str, Any]]] = {
            "nldi_basin": basin_boundary,
            "upstream_hydrography": None,
            "huc8_context": None,
            "huc12_context": None,
        }

        basin_bounds = HmsHydrologyContext.geometry_bounds(basin_boundary)

        try:
            huc_context, huc_records = _fetch_huc_context_payload(
                basin_bounds,
                huc_levels=huc_levels,
                session=session,
            )
            provenance_records.extend(huc_records)
            for artifact_id, payload in huc_context.items():
                context_payloads[artifact_id] = payload
        except Exception as exc:
            logger.warning("HUC context lookup failed for %s: %s", normalized_site_id, exc)

        try:
            flowlines_payload, flowlines_record = _fetch_upstream_flowlines_payload(
                normalized_site_id,
                session=session,
                distance_km=upstream_distance_km,
            )
            provenance_records.append(flowlines_record)
            context_payloads["upstream_hydrography"] = flowlines_payload
        except Exception as exc:
            logger.warning("Upstream hydrography lookup failed for %s: %s", normalized_site_id, exc)

        artifact_state["gauge_metadata"] = _write_json(
            workspace["metadata"] / "gauge_metadata.json",
            gauge_metadata,
        )
        artifact_state["nldi_basin"] = _write_json(
            workspace["context"] / "nldi_basin.geojson",
            basin_boundary,
        )
        if context_payloads["upstream_hydrography"] is not None:
            artifact_state["upstream_hydrography"] = _write_json(
                workspace["context"] / "upstream_hydrography.geojson",
                context_payloads["upstream_hydrography"],
            )
        for artifact_id in ("huc8_context", "huc12_context"):
            payload = context_payloads.get(artifact_id)
            if payload is not None:
                artifact_state[artifact_id] = _write_json(
                    workspace["context"] / Path(f"{artifact_id}.geojson"),
                    payload,
                )

        provenance = {
            "study_type": "gauge_first_watershed",
            "site_id": normalized_site_id,
            "generated_at": _utc_now(),
            "records": provenance_records,
        }
        artifact_state["provenance"] = _write_json(
            workspace["metadata"] / "provenance.json",
            provenance,
        )

        gaps: List[Dict[str, Any]] = []
        if context_payloads["huc8_context"] is None:
            gaps.append(
                {
                    "id": "missing_huc8_context",
                    "category": "hydrology_context",
                    "severity": "warning",
                    "status": "open",
                    "description": "HUC8 context could not be generated.",
                    "affected_artifact": "huc8_context",
                    "owner_repo": "hms-commander",
                    "issue_url": None,
                    "blocking_for": ["regional_context"],
                    "recommended_action": (
                        "Retry the HUC lookup with GIS dependencies installed or validate public Fabric API availability."
                    ),
                }
            )
        if context_payloads["huc12_context"] is None:
            gaps.append(
                {
                    "id": "missing_huc12_context",
                    "category": "hydrology_context",
                    "severity": "warning",
                    "status": "open",
                    "description": "HUC12 context could not be generated.",
                    "affected_artifact": "huc12_context",
                    "owner_repo": "hms-commander",
                    "issue_url": None,
                    "blocking_for": [],
                    "recommended_action": (
                        "Retry the HUC lookup with GIS dependencies installed or validate public Fabric API availability."
                    ),
                }
            )
        if context_payloads["upstream_hydrography"] is None:
            gaps.append(
                {
                    "id": "missing_upstream_hydrography",
                    "category": "hydrology_context",
                    "severity": "warning",
                    "status": "open",
                    "description": "Upstream hydrography context could not be generated.",
                    "affected_artifact": "upstream_hydrography",
                    "owner_repo": "hms-commander",
                    "issue_url": None,
                    "blocking_for": [],
                    "recommended_action": (
                        "Retry the NLDI navigation request or capture upstream flowlines from an alternate hydrography source."
                    ),
                }
            )

        data_gap_analysis = {
            "study_type": "gauge_first_watershed",
            "site_id": normalized_site_id,
            "generated_at": _utc_now(),
            "gap_count": len(gaps),
            "gaps": gaps,
        }
        artifact_state["data_gap_analysis"] = _write_json(
            workspace["reports"] / "data_gap_analysis.json",
            data_gap_analysis,
        )

        study_catalog_for_report = _artifact_catalog(_STUDY_ARTIFACT_SPECS, workspace["root"], artifact_state)
        available_context = sorted(
            artifact_id
            for artifact_id in ("nldi_basin", "huc8_context", "huc12_context", "upstream_hydrography")
            if context_payloads.get(artifact_id) is not None
        )
        missing_context = sorted(
            artifact_id
            for artifact_id in ("nldi_basin", "huc8_context", "huc12_context", "upstream_hydrography")
            if context_payloads.get(artifact_id) is None
        )
        study_report = {
            "study_type": "gauge_first_watershed",
            "site_id": normalized_site_id,
            "generated_at": _utc_now(),
            "gauge_name": gauge_metadata.get("name"),
            "coordinates": gauge_metadata.get("coordinates"),
            "available_context": available_context,
            "missing_context": missing_context,
            "artifact_count": len(_STUDY_ARTIFACT_SPECS),
            "data_gap_count": len(gaps),
            "blocking_gap_count": sum(1 for gap in gaps if gap.get("blocking_for")),
            "gap_affected_artifacts": sorted({gap["affected_artifact"] for gap in gaps}),
            "artifacts": _artifact_rows(
                study_catalog_for_report,
                status_overrides={"manifest": "planned", "study_report": "planned"},
            ),
        }
        artifact_state["study_report"] = _write_json(
            workspace["reports"] / "study_report.json",
            study_report,
        )

        study_catalog_for_manifest = _artifact_catalog(
            _STUDY_ARTIFACT_SPECS,
            workspace["root"],
            artifact_state,
            status_overrides={"manifest": "created"},
            omit_bytes_for={"manifest"},
        )
        manifest = {
            "schema_version": "1.0",
            "study_type": "gauge_first_watershed",
            "site_id": normalized_site_id,
            "nldi_feature_id": gauge_metadata.get("nldi_feature_id"),
            "generated_at": _utc_now(),
            "builder": {
                "package": "hms-commander",
                "class": "HmsGaugeStudy",
                "version": PACKAGE_VERSION,
            },
            "workspace": {
                "root": workspace["root"],
                "directories": {
                    "metadata": "metadata",
                    "context": "context",
                    "reports": "reports",
                    "raw": "raw",
                },
            },
            "artifacts": study_catalog_for_manifest,
        }
        artifact_state["manifest"] = _write_json(
            workspace["metadata"] / "study_manifest.json",
            manifest,
        )

        final_catalog = _artifact_catalog(_STUDY_ARTIFACT_SPECS, workspace["root"], artifact_state)
        final_manifest = dict(manifest)
        final_manifest["artifacts"] = _artifact_catalog(
            _STUDY_ARTIFACT_SPECS,
            workspace["root"],
            artifact_state,
            omit_bytes_for={"manifest"},
        )
        _write_json(workspace["metadata"] / "study_manifest.json", final_manifest)

        return {
            "site_id": normalized_site_id,
            "workspace_root": workspace["root"],
            "workspace": workspace,
            "gauge_metadata": gauge_metadata,
            "provenance": provenance,
            "manifest": final_manifest,
            "study_report": study_report,
            "data_gap_analysis": data_gap_analysis,
            "artifacts": final_catalog,
        }

    @staticmethod
    @log_call
    def build_taudem_input_pack(
        workspace_root: Union[str, Path],
        pack_name: str = "taudem_input_pack",
        dem_buffer_fraction: float = 0.05,
        min_dem_buffer_degrees: float = 0.01,
    ) -> Dict[str, Any]:
        """Build a TauDEM-ready input pack from a saved study workspace."""
        workspace_root = Path(workspace_root)
        HmsGaugeStudy.create_workspace(workspace_root)
        pack_root = workspace_root / "raw" / pack_name
        pack_root.mkdir(parents=True, exist_ok=True)

        artifact_state: Dict[str, Dict[str, Any]] = {}
        provenance_records: List[Dict[str, Any]] = []

        gauge_metadata_path = workspace_root / "metadata" / "gauge_metadata.json"
        basin_path = workspace_root / "context" / "nldi_basin.geojson"
        huc8_path = workspace_root / "context" / "huc8_context.geojson"
        huc12_path = workspace_root / "context" / "huc12_context.geojson"

        gauge_metadata = _load_json(gauge_metadata_path) if gauge_metadata_path.exists() else None
        basin_boundary = _load_json(basin_path) if basin_path.exists() else None
        site_id = (
            (gauge_metadata or {}).get("site_id")
            or (_load_json(workspace_root / "metadata" / "study_manifest.json").get("site_id")
                if (workspace_root / "metadata" / "study_manifest.json").exists() else None)
            or "unknown"
        )

        if gauge_metadata and (gauge_metadata.get("coordinates") or {}).get("longitude") is not None:
            pour_point = HmsHydrologyContext.build_pour_point_feature(
                gauge_metadata=gauge_metadata,
                properties={"source_artifact": "metadata/gauge_metadata.json"},
            )
            artifact_state["taudem_pour_point"] = _write_json(pack_root / "pour_point.geojson", pour_point)
            provenance_records.append(
                _provenance_record(
                    source_name="study_workspace",
                    method="DERIVED",
                    request_url=gauge_metadata_path,
                    artifact_id="taudem_pour_point",
                    notes="Derived from saved gauge metadata coordinates.",
                )
            )
        else:
            pour_point = None

        if basin_boundary is not None:
            artifact_state["taudem_basin_boundary"] = _write_json(pack_root / "basin_boundary.geojson", basin_boundary)
            provenance_records.append(
                _provenance_record(
                    source_name="study_workspace",
                    method="DERIVED",
                    request_url=basin_path,
                    artifact_id="taudem_basin_boundary",
                    notes="Copied from saved study basin boundary.",
                )
            )
        huc_reference_entries: List[Dict[str, Any]] = []
        for artifact_id, level, path in (
            ("huc8_context", "huc8", huc8_path),
            ("huc12_context", "huc12", huc12_path),
        ):
            if path.exists():
                payload = _load_json(path)
                huc_reference_entries.append(
                    {
                        "artifact_id": artifact_id,
                        "level": level,
                        "path": f"context/{path.name}",
                        "feature_count": len(payload.get("features") or []),
                        "bounds": list(HmsHydrologyContext.geometry_bounds(payload)),
                    }
                )

        huc_context_reference = {
            "study_type": "taudem_input_pack",
            "site_id": site_id,
            "generated_at": _utc_now(),
            "primary_reference": huc_reference_entries[0]["artifact_id"] if huc_reference_entries else None,
            "references": huc_reference_entries,
        }
        artifact_state["taudem_huc_context_reference"] = _write_json(
            pack_root / "huc_context_reference.json",
            huc_context_reference,
        )
        provenance_records.append(
            _provenance_record(
                source_name="study_workspace",
                method="DERIVED",
                request_url=workspace_root / "context",
                artifact_id="taudem_huc_context_reference",
                notes="References existing HUC context artifacts from the workspace.",
            )
        )

        recommended_extent = None
        if basin_boundary is not None:
            dem_extent_core = HmsHydrologyContext.recommend_dem_clip_extent(
                basin_boundary,
                buffer_fraction=dem_buffer_fraction,
                min_buffer_degrees=min_dem_buffer_degrees,
            )
            recommended_extent = {
                "study_type": "taudem_input_pack",
                "site_id": site_id,
                "generated_at": _utc_now(),
                "source_artifact": "taudem_basin_boundary",
                "source_bounds": dem_extent_core["source_bounds"],
                "recommended_bounds": dem_extent_core["recommended_bounds"],
                "buffer_fraction": dem_extent_core["buffer_fraction"],
                "min_buffer_degrees": dem_extent_core["minimum_buffer_degrees"],
                "applied_buffer_degrees": dem_extent_core["applied_buffer_degrees"],
                "recommended_clip_geometry": _bounds_polygon(dem_extent_core["recommended_bounds"]),
            }
            artifact_state["taudem_dem_clip_extent"] = _write_json(
                pack_root / "recommended_dem_clip_extent.json",
                recommended_extent,
            )
            provenance_records.append(
                _provenance_record(
                    source_name="study_workspace",
                    method="DERIVED",
                    request_url=pack_root,
                    artifact_id="taudem_dem_clip_extent",
                    notes="Derived from taudem_basin_boundary bounds with configured padding.",
                )
            )

        provenance = {
            "study_type": "taudem_input_pack",
            "site_id": site_id,
            "generated_at": _utc_now(),
            "records": provenance_records,
        }
        artifact_state["taudem_pack_provenance"] = _write_json(pack_root / "provenance.json", provenance)

        gaps: List[Dict[str, Any]] = []
        if pour_point is None:
            gaps.append(
                {
                    "id": "missing_gauge_metadata_for_taudem_pack",
                    "category": "taudem_pack",
                    "severity": "error",
                    "status": "open",
                    "description": "Gauge metadata is missing, so a TauDEM pour point cannot be derived.",
                    "affected_artifact": "taudem_pour_point",
                    "owner_repo": "hms-commander",
                    "issue_url": None,
                    "blocking_for": ["taudem_pour_point", "taudem_watershed_delineation"],
                    "recommended_action": (
                        "Build the gauge-first workspace first or provide a compatible gauge_metadata.json source file."
                    ),
                }
            )
        if not huc_reference_entries:
            gaps.append(
                {
                    "id": "missing_huc_context_for_taudem_pack",
                    "category": "taudem_pack",
                    "severity": "warning",
                    "status": "open",
                    "description": "No HUC context artifacts were available to reference in the TauDEM pack.",
                    "affected_artifact": "taudem_huc_context_reference",
                    "owner_repo": "hms-commander",
                    "issue_url": None,
                    "blocking_for": [],
                    "recommended_action": (
                        "Add at least one HUC context layer to improve review and DEM clipping context."
                    ),
                }
            )

        data_gap_analysis = {
            "study_type": "taudem_input_pack",
            "site_id": site_id,
            "generated_at": _utc_now(),
            "gap_count": len(gaps),
            "gaps": gaps,
        }
        artifact_state["taudem_pack_data_gap_analysis"] = _write_json(
            pack_root / "data_gap_analysis.json",
            data_gap_analysis,
        )

        available_components = sorted(
            artifact_id
            for artifact_id, is_available in (
                ("taudem_pour_point", pour_point is not None),
                ("taudem_basin_boundary", basin_boundary is not None),
                ("taudem_huc_context_reference", bool(huc_reference_entries)),
                ("taudem_dem_clip_extent", recommended_extent is not None),
            )
            if is_available
        )
        missing_components = sorted(
            artifact_id
            for artifact_id, is_available in (
                ("taudem_pour_point", pour_point is not None),
                ("taudem_basin_boundary", basin_boundary is not None),
                ("taudem_huc_context_reference", bool(huc_reference_entries)),
                ("taudem_dem_clip_extent", recommended_extent is not None),
            )
            if not is_available
        )
        pack_catalog_for_report = _artifact_catalog(_PACK_ARTIFACT_SPECS, workspace_root, artifact_state)
        study_report = {
            "study_type": "taudem_input_pack",
            "site_id": site_id,
            "generated_at": _utc_now(),
            "available_components": available_components,
            "missing_components": missing_components,
            "artifact_count": len(_PACK_ARTIFACT_SPECS),
            "data_gap_count": len(gaps),
            "blocking_gap_count": sum(1 for gap in gaps if gap.get("blocking_for")),
            "artifacts": _artifact_rows(
                pack_catalog_for_report,
                status_overrides={
                    "taudem_pack_manifest": "planned",
                    "taudem_pack_report": "planned",
                },
            ),
        }
        artifact_state["taudem_pack_report"] = _write_json(pack_root / "report.json", study_report)

        pack_catalog_for_manifest = _artifact_catalog(
            _PACK_ARTIFACT_SPECS,
            workspace_root,
            artifact_state,
            status_overrides={"taudem_pack_manifest": "created"},
            omit_bytes_for={"taudem_pack_manifest"},
        )
        manifest = {
            "schema_version": "1.0",
            "study_type": "taudem_input_pack",
            "site_id": site_id,
            "generated_at": _utc_now(),
            "builder": {
                "package": "hms-commander",
                "class": "HmsGaugeStudy",
                "method": "build_taudem_input_pack",
                "version": PACKAGE_VERSION,
            },
            "workspace_root": workspace_root,
            "pack_root": f"raw/{pack_name}",
            "artifacts": pack_catalog_for_manifest,
        }
        artifact_state["taudem_pack_manifest"] = _write_json(
            pack_root / "taudem_input_pack_manifest.json",
            manifest,
        )

        final_catalog = _artifact_catalog(_PACK_ARTIFACT_SPECS, workspace_root, artifact_state)
        final_manifest = dict(manifest)
        final_manifest["artifacts"] = _artifact_catalog(
            _PACK_ARTIFACT_SPECS,
            workspace_root,
            artifact_state,
            omit_bytes_for={"taudem_pack_manifest"},
        )
        _write_json(pack_root / "taudem_input_pack_manifest.json", final_manifest)

        return {
            "site_id": site_id,
            "workspace_root": workspace_root,
            "pack_root": pack_root,
            "artifacts": final_catalog,
            "provenance": provenance,
            "manifest": final_manifest,
            "study_report": study_report,
            "data_gap_analysis": data_gap_analysis,
        }
