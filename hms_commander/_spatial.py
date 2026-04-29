"""Private shared GIS helpers for TauDEM/HMS workflows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Union


def json_default(value: Any) -> Any:
    """Serialize pathlib and CRS-like values inside JSON payloads."""

    if isinstance(value, Path):
        return str(value)
    return str(value)


def write_json(path: Union[str, Path], payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Write JSON with stable formatting."""

    path = Path(path)
    existed = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=json_default) + "\n", encoding="utf-8")
    return {"status": "updated" if existed else "created", "bytes": path.stat().st_size}


def write_vector(path: Union[str, Path], gdf) -> Dict[str, Any]:
    """Write a vector dataset with stable overwrite behavior."""

    path = Path(path)
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


def resolve_crs(crs_value: Any, fallback_crs: Optional[Any] = None):
    """Resolve a CRS-like value, optionally falling back to a supplied CRS."""

    from pyproj import CRS

    if crs_value is None:
        return CRS.from_user_input(fallback_crs) if fallback_crs is not None else None
    try:
        resolved = CRS.from_user_input(crs_value)
    except Exception:
        return CRS.from_user_input(fallback_crs) if fallback_crs is not None else None

    if fallback_crs is not None and resolved.to_epsg() is None:
        return CRS.from_user_input(fallback_crs)
    return resolved


def load_vector(path: Union[str, Path], fallback_crs: Optional[Any] = None):
    """Read a vector file and apply fallback CRS when metadata is missing."""

    import geopandas as gpd

    path = Path(path)
    gdf = gpd.read_file(path)
    resolved_crs = resolve_crs(gdf.crs, fallback_crs)
    if resolved_crs is None:
        raise ValueError(f"Could not determine CRS for vector dataset: {path}")
    if gdf.crs is None:
        return gdf.set_crs(resolved_crs)
    return gdf.set_crs(resolved_crs, allow_override=True)


def single_geometry(gdf):
    """Dissolve a GeoDataFrame into one valid geometry."""

    from shapely.ops import unary_union

    geometry = unary_union([geom for geom in gdf.geometry if geom is not None and not geom.is_empty])
    if geometry.is_empty:
        raise ValueError("Dataset does not contain any non-empty geometries")
    if not geometry.is_valid:
        geometry = geometry.buffer(0)
    return geometry


def polygonize_watershed_raster(
    raster_path: Union[str, Path],
    fallback_crs: Optional[Any] = None,
    *,
    positive_only: bool = True,
):
    """Polygonize a watershed grid by dissolving all valid watershed cells."""

    import geopandas as gpd
    import numpy as np
    import rasterio
    from rasterio.features import shapes
    from shapely.geometry import shape
    from shapely.ops import unary_union

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
        resolved_crs = resolve_crs(src.crs, fallback_crs)
        if resolved_crs is None:
            raise ValueError(f"Could not determine CRS for raster dataset: {raster_path}")

    if not geometry.is_valid:
        geometry = geometry.buffer(0)
    return gpd.GeoDataFrame({"source": ["watershed_raster"]}, geometry=[geometry], crs=resolved_crs)


def polygonize_zone_raster(
    raster_path: Union[str, Path],
    *,
    zone_column: str = "wsno",
):
    """Polygonize integer raster zones and dissolve by zone value."""

    import geopandas as gpd
    import numpy as np
    import rasterio
    from rasterio.features import shapes
    from shapely.geometry import shape

    raster_path = Path(raster_path)
    with rasterio.open(raster_path) as src:
        array = src.read(1)
        nodata = src.nodata
        mask = np.ones(array.shape, dtype=bool)
        if nodata is not None:
            mask &= array != nodata
        if not mask.any():
            raise ValueError(f"No watershed zones were found in {raster_path}")

        records = [
            {zone_column: int(value), "geometry": shape(geom)}
            for geom, value in shapes(array.astype("int32"), mask=mask, transform=src.transform)
        ]
        resolved_crs = resolve_crs(src.crs)
        if resolved_crs is None:
            raise ValueError(f"Could not determine CRS for raster dataset: {raster_path}")

    zones = gpd.GeoDataFrame(records, crs=resolved_crs)
    zones = zones.dissolve(by=zone_column, as_index=False)
    zones["geometry"] = zones.geometry.buffer(0)
    zones[zone_column] = zones[zone_column].astype(int)
    return zones.sort_values(zone_column).reset_index(drop=True)
