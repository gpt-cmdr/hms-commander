"""
Gauge-first hydrology primitives.

This is a thin compatibility facade over `HmsHydrologyContext` so older code
can keep importing `HmsGaugeData` while the actual implementation lives in the
study module.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence

from .HmsGaugeStudy import HmsHydrologyContext


class HmsGaugeData:
    """Primitive-first USGS/NLDI gauge and gauge-driven context helpers."""

    @staticmethod
    def normalize_site_id(site_id: Any) -> str:
        """Normalize a USGS site id."""
        return HmsHydrologyContext.normalize_site_id(site_id)

    @staticmethod
    def get_nldi_feature_id(site_id: Any) -> str:
        """Return the NLDI feature id for a site."""
        return HmsHydrologyContext.get_nldi_feature_id(site_id)

    @staticmethod
    def get_usgs_gauge_metadata(site_id: Any, session: Optional[Any] = None) -> Dict[str, Any]:
        """Fetch combined NLDI and NWIS metadata for a gauge."""
        return HmsHydrologyContext.get_usgs_gauge_metadata(site_id, session=session)

    @staticmethod
    def get_usgs_gauge_point_feature(
        site_id: Optional[Any] = None,
        gauge_metadata: Optional[Mapping[str, Any]] = None,
        session: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Build a point FeatureCollection for a gauge site."""
        return HmsHydrologyContext.get_usgs_gauge_point_feature(
            site_id=site_id,
            gauge_metadata=gauge_metadata,
            session=session,
        )

    @staticmethod
    def get_nldi_basin_from_gauge(site_id: Any, session: Optional[Any] = None) -> Dict[str, Any]:
        """Fetch the NLDI basin for a gauge."""
        return HmsHydrologyContext.get_nldi_basin_from_gauge(site_id, session=session)

    @staticmethod
    def get_nhdplus_upstream_flowlines_from_gauge(
        site_id: Any,
        distance_km: float = 25.0,
        session: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Fetch upstream flowlines for a gauge."""
        return HmsHydrologyContext.get_nhdplus_upstream_flowlines_from_gauge(
            site_id,
            distance_km=distance_km,
            session=session,
        )

    @staticmethod
    def get_nhd_huc_boundary_from_gauge(
        site_id: Any,
        huc_level: str = "huc12",
        session: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Fetch the containing HUC boundary for a gauge location."""
        return HmsHydrologyContext.get_nhd_huc_boundary_from_gauge(
            site_id,
            huc_level=huc_level,
            session=session,
        )

    @staticmethod
    def get_nhd_huc8_boundary_from_gauge(site_id: Any, session: Optional[Any] = None) -> Dict[str, Any]:
        """Convenience wrapper for HUC8 context."""
        return HmsHydrologyContext.get_nhd_huc8_boundary_from_gauge(site_id, session=session)

    @staticmethod
    def get_nhd_huc12_boundary_from_gauge(site_id: Any, session: Optional[Any] = None) -> Dict[str, Any]:
        """Convenience wrapper for HUC12 context."""
        return HmsHydrologyContext.get_nhd_huc12_boundary_from_gauge(site_id, session=session)

    @staticmethod
    def build_pour_point_feature(
        coordinates: Optional[Sequence[float]] = None,
        gauge_metadata: Optional[Mapping[str, Any]] = None,
        properties: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a TauDEM-style pour point FeatureCollection."""
        return HmsHydrologyContext.build_pour_point_feature(
            coordinates=coordinates,
            gauge_metadata=gauge_metadata,
            properties=properties,
        )
