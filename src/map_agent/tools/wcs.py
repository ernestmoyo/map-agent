"""Raster fetch via WCS — modelled surfaces from MAP geoserver.

Fetches prevalence, incidence, mortality, interventions, vectors,
blood disorders, and accessibility rasters. Supports clipping by
country or admin1 bounding box.
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from map_agent.core.cache import cache_path_for, get_cached_path
from map_agent.core.config import settings
from map_agent.core.geoserver import get_wcs_client
from map_agent.tools.admin import resolve_country, get_boundaries

logger = logging.getLogger(__name__)


def _bbox_for_area(
    country: str | None = None,
    admin1: str | None = None,
    bbox: list[float] | None = None,
) -> tuple[float, float, float, float] | None:
    """Resolve a bounding box from country/admin1 name or explicit bbox.

    Returns (west, south, east, north) or None for global extent.
    """
    if bbox and len(bbox) == 4:
        return (bbox[0], bbox[1], bbox[2], bbox[3])

    if country:
        iso3 = resolve_country(country)
        level = 1 if admin1 else 0
        result = get_boundaries(iso3, level, name_filter=admin1)
        if "bbox" in result:
            b = result["bbox"]
            return (b[0], b[1], b[2], b[3])

    return None


def _safe_filename(layer_id: str, country: str | None, year: int | None) -> str:
    """Generate a filesystem-safe filename from layer parameters."""
    parts = [layer_id.replace(":", "_").replace("__", "_")]
    if country:
        parts.append(country.upper()[:3])
    if year:
        parts.append(str(year))
    return "_".join(parts) + ".tif"


def fetch_raster(
    layer_id: str,
    country: str | None = None,
    admin1: str | None = None,
    bbox: list[float] | None = None,
    year: int | None = None,
) -> dict:
    """Download a raster layer from MAP's WCS service.

    Clips to the specified geographic area. Returns the path to the
    downloaded GeoTIFF file.

    Args:
        layer_id: Full WCS layer ID (e.g., "Malaria__202508_Global_Pf_Parasite_Rate").
        country: Optional country name or ISO3 to clip to.
        admin1: Optional admin1 name to clip to (requires country).
        bbox: Optional explicit bounding box [west, south, east, north].
        year: Optional year (for time-aware layers; reserved for future use).

    Returns:
        Dict with: tif_path, layer_id, bbox, shape info.
    """
    area_bbox = _bbox_for_area(country, admin1, bbox)

    # Check cache
    cache_params = {
        "layer": layer_id,
        "bbox": area_bbox,
        "year": year,
    }
    cached = get_cached_path("raster", suffix=".tif", **cache_params)
    if cached is not None:
        return {
            "tif_path": str(cached.resolve()),
            "layer_id": layer_id,
            "bbox": list(area_bbox) if area_bbox else None,
            "cached": True,
        }

    # Fetch from WCS
    wcs = get_wcs_client()

    if layer_id not in wcs.contents:
        available = [c for c in wcs.contents if any(
            tok in c.lower() for tok in layer_id.lower().split("_") if len(tok) > 2
        )][:10]
        return {
            "error": f"Layer '{layer_id}' not found in WCS catalog.",
            "similar_layers": available,
            "suggestion": "Use catalog_search to find the correct layer ID.",
        }

    kwargs: dict = {
        "identifier": [layer_id],
        "format": "image/tiff",
    }
    if area_bbox:
        kwargs["subsets"] = [
            ("Long", area_bbox[0], area_bbox[2]),
            ("Lat", area_bbox[1], area_bbox[3]),
        ]

    logger.info("Fetching raster %s (bbox=%s)", layer_id, area_bbox)
    response = wcs.getCoverage(**kwargs)
    data = response.read()

    # Save to output dir
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    iso3 = None
    if country:
        try:
            iso3 = resolve_country(country)
        except ValueError:
            iso3 = country[:3].upper()

    filename = _safe_filename(layer_id, iso3, year)
    out_path = settings.output_dir / filename
    out_path.write_bytes(data)

    # Also cache it
    cache_out = cache_path_for("raster", suffix=".tif", **cache_params)
    cache_out.write_bytes(data)

    # Try to get basic info about the raster
    raster_info: dict = {
        "tif_path": str(out_path.resolve()),
        "layer_id": layer_id,
        "bbox": list(area_bbox) if area_bbox else None,
        "file_size_mb": round(len(data) / (1024 * 1024), 2),
        "fetched_at": datetime.now().isoformat(),
        "cached": False,
    }

    # Try to read shape info with xarray if available
    try:
        import rioxarray  # noqa: F401
        import xarray as xr

        da = xr.open_dataarray(out_path, engine="rasterio")
        raster_info["shape"] = list(da.shape)
        raster_info["crs"] = str(da.rio.crs) if hasattr(da, "rio") else None
        da.close()
    except Exception:
        pass

    return raster_info
