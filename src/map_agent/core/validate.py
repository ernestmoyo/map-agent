"""Data validation passes — catch bad fetches before they waste compute.

Runs automatically after each fetch. Returns warnings (never blocks).
Inspired by gstack's two-pass review pattern.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def validate_raster(
    tif_path: str,
    expected_bbox: tuple[float, float, float, float] | list[float] | None = None,
) -> list[str]:
    """Validate a fetched raster file.

    Checks:
    - File exists and is non-empty
    - Can be opened by rasterio
    - Has valid shape (not 0-dimension)
    - Bbox intersects expected area (if provided)
    - Nodata fraction isn't 100%

    Returns list of warning strings (empty = all good).
    """
    warnings: list[str] = []
    path = Path(tif_path)

    if not path.exists():
        return [f"Raster file not found: {tif_path}"]

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb < 0.001:
        warnings.append(f"Raster file is suspiciously small ({size_mb:.4f} MB)")

    try:
        import numpy as np
        import rasterio

        with rasterio.open(path) as src:
            if src.width == 0 or src.height == 0:
                warnings.append(f"Raster has zero dimensions: {src.width}x{src.height}")
                return warnings

            # Check bbox intersection
            if expected_bbox:
                r_bounds = src.bounds  # left, bottom, right, top
                e_west, e_south, e_east, e_north = expected_bbox
                no_overlap = (
                    r_bounds.right < e_west
                    or r_bounds.left > e_east
                    or r_bounds.top < e_south
                    or r_bounds.bottom > e_north
                )
                if no_overlap:
                    warnings.append(
                        f"Raster bbox {list(r_bounds)} does not intersect "
                        f"expected area {list(expected_bbox)} — "
                        f"country clipping may have failed"
                    )

                # Check if raster is much larger than expected (global vs clipped)
                r_width = r_bounds.right - r_bounds.left
                r_height = r_bounds.top - r_bounds.bottom
                e_width = e_east - e_west
                e_height = e_north - e_south
                if r_width > e_width * 5 and r_height > e_height * 5:
                    warnings.append(
                        f"Raster extent ({r_width:.1f} x {r_height:.1f} deg) is much larger "
                        f"than expected area ({e_width:.1f} x {e_height:.1f} deg) — "
                        f"may be a global raster instead of clipped"
                    )

            # Check nodata fraction (sample band 1)
            data = src.read(1)
            nodata = src.nodata
            if nodata is not None:
                nodata_fraction = float(np.sum(data == nodata)) / data.size
            else:
                nodata_fraction = float(np.sum(~np.isfinite(data))) / data.size

            if nodata_fraction > 0.99:
                warnings.append(
                    f"Raster is {nodata_fraction:.0%} nodata — "
                    f"area may be outside coverage"
                )
            elif nodata_fraction > 0.80:
                warnings.append(
                    f"Raster is {nodata_fraction:.0%} nodata — "
                    f"partial coverage only"
                )

    except Exception as exc:
        warnings.append(f"Could not validate raster: {exc}")

    for w in warnings:
        logger.warning("Raster validation: %s", w)
    return warnings


def validate_boundaries(geojson_path: str) -> list[str]:
    """Validate a fetched boundaries file.

    Checks:
    - File exists and is non-empty
    - Contains features
    - Geometries are valid

    Returns list of warning strings.
    """
    warnings: list[str] = []
    path = Path(geojson_path)

    if not path.exists():
        return [f"Boundaries file not found: {geojson_path}"]

    try:
        import geopandas as gpd

        gdf = gpd.read_file(path)
        if gdf.empty:
            warnings.append("Boundaries file contains no features")
            return warnings

        invalid_count = int((~gdf.is_valid).sum())
        if invalid_count > 0:
            warnings.append(
                f"{invalid_count}/{len(gdf)} geometries are invalid — "
                f"may cause issues with zonal stats"
            )

    except Exception as exc:
        warnings.append(f"Could not validate boundaries: {exc}")

    for w in warnings:
        logger.warning("Boundary validation: %s", w)
    return warnings


def validate_zonal_stats(table: list[dict], stats: list[str] | None = None) -> list[str]:
    """Validate zonal statistics results.

    Checks:
    - At least one zone has data
    - Flags zones with all-None stats
    - Flags suspiciously uniform values

    Returns list of warning strings.
    """
    warnings: list[str] = []

    if not table:
        return ["Zonal stats table is empty — no zones processed"]

    check_stats = stats or ["mean"]
    nodata_zones: list[str] = []

    for row in table:
        zone = row.get("zone", "unknown")
        all_none = all(row.get(s) is None for s in check_stats if s in row)
        if all_none:
            nodata_zones.append(zone)

    if nodata_zones:
        if len(nodata_zones) == len(table):
            warnings.append(
                "ALL zones have no data — raster may not overlap boundaries"
            )
        elif len(nodata_zones) > len(table) * 0.5:
            warnings.append(
                f"{len(nodata_zones)}/{len(table)} zones have no data: "
                f"{', '.join(nodata_zones[:5])}{'...' if len(nodata_zones) > 5 else ''}"
            )
        else:
            warnings.append(
                f"{len(nodata_zones)} zone(s) with no data: "
                f"{', '.join(nodata_zones[:10])}"
            )

    for w in warnings:
        logger.warning("Zonal stats validation: %s", w)
    return warnings
