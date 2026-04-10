"""Zonal statistics: summarize raster data by admin boundaries.

Uses rasterio + geopandas + numpy to compute mean, min, max, count etc.
of a raster within each polygon of a boundary file.
"""
from __future__ import annotations

import csv as csv_mod
import logging
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask as rio_mask
from shapely.geometry import mapping

from map_agent.core.config import settings

logger = logging.getLogger(__name__)


def _compute_stats_for_zone(
    raster_path: Path,
    geometry,
    stats: list[str],
    nodata: float | None,
) -> dict[str, float | int | None]:
    """Compute statistics for a single zone geometry against a raster."""
    with rasterio.open(raster_path) as src:
        try:
            out_image, _ = rio_mask(src, [mapping(geometry)], crop=True, nodata=nodata)
        except ValueError:
            return {s: None for s in stats}

    # Use band 1 (index 0)
    data = out_image[0]

    # Mask nodata values
    if nodata is not None:
        valid = data[data != nodata]
    else:
        valid = data[np.isfinite(data)]

    if len(valid) == 0:
        return {s: None for s in stats}

    result: dict[str, float | int | None] = {}
    for stat in stats:
        if stat == "mean":
            result[stat] = float(np.mean(valid))
        elif stat == "min":
            result[stat] = float(np.min(valid))
        elif stat == "max":
            result[stat] = float(np.max(valid))
        elif stat == "median":
            result[stat] = float(np.median(valid))
        elif stat == "count":
            result[stat] = int(len(valid))
        elif stat == "sum":
            result[stat] = float(np.sum(valid))
        elif stat == "std":
            result[stat] = float(np.std(valid))
    return result


def zonal_stats(
    raster_path: str,
    boundaries_path: str,
    stats: list[str] | None = None,
    zone_name_column: str | None = None,
) -> dict:
    """Compute zonal statistics of a raster within admin boundary polygons.

    Args:
        raster_path: Path to a GeoTIFF file (from fetch_raster).
        boundaries_path: Path to a GeoJSON file (from get_boundaries).
        stats: Statistics to compute. Defaults to ["mean", "min", "max", "count", "median"].
        zone_name_column: Column in the boundaries file to use as zone names.
                          Auto-detected if not specified.

    Returns:
        Dict with: csv_path, table (list of dicts), zone_count, stats_computed.
    """
    if stats is None:
        stats = ["mean", "min", "max", "count", "median"]

    # Resolve @R/@B refs
    from map_agent.core.session import session
    raster_path = session.resolve_if_ref(raster_path)
    boundaries_path = session.resolve_if_ref(boundaries_path)

    raster = Path(raster_path)
    if not raster.exists():
        return {"error": f"Raster file not found: {raster_path}"}

    boundaries = Path(boundaries_path)
    if not boundaries.exists():
        return {"error": f"Boundaries file not found: {boundaries_path}"}

    # Read boundaries
    gdf = gpd.read_file(boundaries)
    if gdf.empty:
        return {"error": "Boundaries file contains no features."}

    # Auto-detect zone name column
    if zone_name_column is None:
        for candidate in ["name_1", "name_2", "name_3", "name_0", "NAME_1", "NAME_2", "name", "NAME"]:
            if candidate in gdf.columns:
                zone_name_column = candidate
                break
    if zone_name_column is None:
        zone_name_column = gdf.columns[0]

    logger.info(
        "Computing zonal stats: %s × %s (%d zones, stats=%s)",
        raster.name, boundaries.name, len(gdf), stats,
    )

    # Get nodata value from raster
    with rasterio.open(raster) as src:
        nodata = src.nodata
        raster_crs = src.crs

    # Reproject boundaries to raster CRS if needed
    if gdf.crs and raster_crs and gdf.crs != raster_crs:
        gdf = gdf.to_crs(raster_crs)

    # Compute stats per zone
    table: list[dict] = []
    for i, row in gdf.iterrows():
        zone_name = str(row.get(zone_name_column, f"Zone_{i}"))
        zone_stats = _compute_stats_for_zone(raster, row.geometry, stats, nodata)
        entry = {"zone": zone_name}
        for stat in stats:
            val = zone_stats.get(stat)
            entry[stat] = round(val, 4) if isinstance(val, float) else val
        table.append(entry)

    # Sort by mean descending (most useful for identifying high-burden areas)
    if "mean" in stats:
        table.sort(key=lambda x: x.get("mean") or 0, reverse=True)

    # Save as CSV
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    csv_name = f"zonal_stats_{raster.stem}_{boundaries.stem}.csv"
    csv_path = settings.output_dir / csv_name

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv_mod.DictWriter(f, fieldnames=["zone"] + stats)
        writer.writeheader()
        writer.writerows(table)

    # Register ref, validate, and log
    from map_agent.core.analytics import log_tool_call
    from map_agent.core.validate import validate_zonal_stats

    csv_str = str(csv_path.resolve())
    stats_ref = session.register_ref("S", csv_str, f"stats {raster.stem}")
    session.last_stats_path = csv_str

    stats_warnings = validate_zonal_stats(table, stats)
    log_tool_call("compute_zonal_stats", extra={"raster": raster.name, "zones": len(table)})

    return {
        "ref": stats_ref,
        "csv_path": csv_str,
        "zone_count": len(table),
        "stats_computed": stats,
        "zone_name_column": zone_name_column,
        "table": table,
        "warnings": stats_warnings,
    }
