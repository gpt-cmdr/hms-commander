"""
Terrain-oriented helpers for TauDEM preprocessing.

This module is intentionally small and delegates to `HmsHydrologyContext` so
the shared geometry logic stays in one place.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from .HmsGaugeStudy import HmsHydrologyContext
from .HmsWatershedVerification import HmsWatershedVerification


class HmsTerrain:
    """Static terrain helpers for TauDEM preprocessing handoff."""

    @staticmethod
    def geometry_bounds(feature_or_geometry: Any):
        """Return bounds for a GeoJSON payload."""
        return HmsHydrologyContext.geometry_bounds(feature_or_geometry)

    @staticmethod
    def recommend_dem_clip_extent(
        feature_or_geometry: Any,
        buffer_fraction: float = 0.05,
        min_buffer_degrees: float = 0.01,
    ) -> Dict[str, Any]:
        """Recommend a padded DEM clip envelope around a reference geometry."""
        return HmsHydrologyContext.recommend_dem_clip_extent(
            feature_or_geometry,
            buffer_fraction=buffer_fraction,
            min_buffer_degrees=min_buffer_degrees,
        )

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
        return HmsHydrologyContext.build_taudem_handoff(
            gauge_metadata=gauge_metadata,
            basin_boundary=basin_boundary,
            huc_context=huc_context,
            clip_geometry=clip_geometry,
            buffer_fraction=buffer_fraction,
            min_buffer_degrees=min_buffer_degrees,
        )

    @staticmethod
    def derive_boundary_outlet(
        reference_boundary_path,
        stream_network_path,
        *,
        output_path=None,
        seed_outlet_path=None,
        fallback_crs=None,
        study_name: Optional[str] = None,
        workspace_root=None,
        site_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Derive a downstream outlet where the main stem crosses the basin boundary."""
        return HmsWatershedVerification.derive_boundary_outlet(
            reference_boundary_path=reference_boundary_path,
            stream_network_path=stream_network_path,
            output_path=output_path,
            seed_outlet_path=seed_outlet_path,
            fallback_crs=fallback_crs,
            study_name=study_name,
            workspace_root=workspace_root,
            site_id=site_id,
        )

    @staticmethod
    def derive_taudem_boundary_outlet(
        stream_network_path,
        *,
        taudem_watershed_raster_path=None,
        taudem_boundary_path=None,
        output_path=None,
        seed_outlet_path=None,
        fallback_crs=None,
        study_name: Optional[str] = None,
        workspace_root=None,
        site_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Derive a handoff outlet where the TauDEM main stem crosses the TauDEM basin boundary."""
        return HmsWatershedVerification.derive_taudem_boundary_outlet(
            stream_network_path=stream_network_path,
            taudem_watershed_raster_path=taudem_watershed_raster_path,
            taudem_boundary_path=taudem_boundary_path,
            output_path=output_path,
            seed_outlet_path=seed_outlet_path,
            fallback_crs=fallback_crs,
            study_name=study_name,
            workspace_root=workspace_root,
            site_id=site_id,
        )
