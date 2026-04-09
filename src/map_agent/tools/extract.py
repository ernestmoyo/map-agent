"""Zonal statistics: summarize raster data by admin boundaries.

Wraps the rasterstats library to compute mean, min, max, count etc.
of a raster within each polygon of a boundary file.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import geopandas as gpd

from map_agent.core.config import settings

logger = logging.getLogger(__name__)


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
    from rasterstats import zonal_stats as rs_zonal_stats

    if stats is None:
        stats = ["mean", "min", "max", "count", "median"]

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

    # Compute stats
    results = rs_zonal_stats(
        str(boundaries),
        str(raster),
        stats=stats,
        geojson_out=False,
    )

    # Build output table
    table: list[dict] = []
    for i, row_stats in enumerate(results):
        zone_name = str(gdf.iloc[i].get(zone_name_column, f"Zone_{i}"))
        entry = {"zone": zone_name}
        for stat in stats:
            val = row_stats.get(stat)
            entry[stat] = round(val, 4) if isinstance(val, float) else val
        table.append(entry)

    # Sort by mean descending (most useful for identifying high-burden areas)
    if "mean" in stats:
        table.sort(key=lambda x: x.get("mean") or 0, reverse=True)

    # Save as CSV
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    csv_name = f"zonal_stats_{raster.stem}_{boundaries.stem}.csv"
    csv_path = settings.output_dir / csv_name

    import csv as csv_mod
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv_mod.DictWriter(f, fieldnames=["zone"] + stats)
        writer.writeheader()
        writer.writerows(table)

    return {
        "csv_path": str(csv_path.resolve()),
        "zone_count": len(table),
        "stats_computed": stats,
        "zone_name_column": zone_name_column,
        "table": table,
    }
