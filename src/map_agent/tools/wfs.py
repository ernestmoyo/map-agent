"""Vector/survey data fetch via WFS — survey points and pre-aggregated stats.

Fetches parasite rate surveys, vector occurrence data, and MAP_READER
pre-aggregated admin-level statistics.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import geopandas as gpd

from map_agent.core.cache import cache_path_for, get_cached_path
from map_agent.core.config import settings
from map_agent.core.geoserver import get_wfs_client
from map_agent.tools.admin import resolve_country, get_boundaries

logger = logging.getLogger(__name__)

# Well-known WFS datasets for convenience lookups
KNOWN_DATASETS: dict[str, str] = {
    "pf_surveys": "Malaria:202406_Global_Pf_Parasite_Rate_Surveys",
    "pv_surveys": "Malaria:202406_Global_Pv_Parasite_Rate_Surveys",
    "vector_occurrence": "Vector_Occurrence:201201_Global_Dominant_Vector_Surveys",
    "pf_confidence": "Malaria:202406_Global_Pf_Parasite_Rate_Confidence",
    "anopheline_data": "Explorer:Anopheline_Data",
    "pr_data": "Explorer:PR_Data",
    "public_pf_data": "Explorer:public_pf_data",
    "public_pv_data": "Explorer:public_pv_data",
    # MAP_READER pre-aggregated stats
    "cases_admin1_pf": "MAP_READER:map_data_estate_detail_admin1_api_mean_pf",
    "cases_admin1_pv": "MAP_READER:map_data_estate_detail_admin1_api_mean_pv",
    "cases_admin2_pf": "MAP_READER:map_data_estate_detail_admin2_api_mean_pf",
    "cases_admin2_pv": "MAP_READER:map_data_estate_detail_admin2_api_mean_pv",
    "cases_admin3_pf": "MAP_READER:map_data_estate_detail_admin3_api_mean_pf",
    "cases_admin3_pv": "MAP_READER:map_data_estate_detail_admin3_api_mean_pv",
    "conf_cases_admin1_pf": "MAP_READER:map_data_estate_detail_admin1_conf_c_pf",
    "conf_cases_admin1_pv": "MAP_READER:map_data_estate_detail_admin1_conf_c_pv",
    "yearly_cases_admin1": "MAP_READER:map_data_estate_summary_admin1_conf_cases_years",
    "yearly_cases_admin2": "MAP_READER:map_data_estate_summary_admin2_conf_cases_years",
    "yearly_api_admin1": "MAP_READER:map_data_estate_summary_admin1_api_years",
    "yearly_api_admin2": "MAP_READER:map_data_estate_summary_admin2_api_years",
}


def _resolve_dataset(dataset: str) -> str:
    """Resolve a shorthand dataset name to a full WFS layer ID."""
    if dataset in KNOWN_DATASETS:
        return KNOWN_DATASETS[dataset]
    # If it contains a colon, assume it's already a full layer ID
    if ":" in dataset:
        return dataset
    # Try fuzzy match
    lower = dataset.lower()
    for key, value in KNOWN_DATASETS.items():
        if lower in key or lower in value.lower():
            return value
    raise ValueError(
        f"Unknown dataset '{dataset}'. Known datasets: {list(KNOWN_DATASETS.keys())}"
    )


def fetch_points(
    dataset: str,
    country: str | None = None,
    bbox: list[float] | None = None,
    year_range: list[int] | None = None,
    max_features: int = 5000,
) -> dict:
    """Download vector/survey data from MAP's WFS service.

    Args:
        dataset: Dataset name — either a shorthand (e.g., "pf_surveys",
                 "vector_occurrence", "cases_admin1_pf") or a full WFS
                 layer ID (e.g., "Malaria:202406_Global_Pf_Parasite_Rate_Surveys").
        country: Optional country name or ISO3 to filter by.
        bbox: Optional bounding box [west, south, east, north].
        year_range: Optional [start_year, end_year] to filter temporal data.
        max_features: Maximum features to return (default 5000).

    Returns:
        Dict with: geojson_path, feature_count, columns, bbox, sample_data.
    """
    layer_id = _resolve_dataset(dataset)

    # Resolve bbox from country if needed
    area_bbox = None
    iso3 = None
    if bbox and len(bbox) == 4:
        area_bbox = tuple(bbox)
    elif country:
        iso3 = resolve_country(country)
        result = get_boundaries(iso3, 0)
        if "bbox" in result:
            area_bbox = tuple(result["bbox"])

    # Check cache
    cache_params = {
        "layer": layer_id,
        "iso3": iso3 or "all",
        "bbox": area_bbox,
        "years": year_range,
    }
    cached = get_cached_path("points", suffix=".geojson", **cache_params)
    if cached is not None:
        gdf = gpd.read_file(cached)
        return _build_response(gdf, str(cached.resolve()), layer_id, cached=True)

    # Build WFS request
    wfs = get_wfs_client()
    kwargs: dict[str, Any] = {
        "typename": [layer_id],
        "outputFormat": "application/json",
        "maxfeatures": max_features,
    }

    # CQL filter for country and year range
    cql_parts: list[str] = []
    if iso3:
        # Try common column names for country filtering
        cql_parts.append(
            f"(country_id='{iso3}' OR iso3='{iso3}' OR iso='{iso3}' OR "
            f"country='{iso3}')"
        )
    if year_range and len(year_range) == 2:
        cql_parts.append(f"year_start>={year_range[0]} AND year_start<={year_range[1]}")

    if area_bbox and not cql_parts:
        # Use BBOX filter when no CQL is needed
        kwargs["bbox"] = list(area_bbox) + ["EPSG:4326"]
    elif area_bbox and cql_parts:
        # Combine BBOX with CQL
        cql_parts.append(
            f"BBOX(the_geom,{area_bbox[0]},{area_bbox[1]},{area_bbox[2]},{area_bbox[3]})"
        )

    if cql_parts:
        kwargs["cql_filter"] = " AND ".join(cql_parts)

    logger.info("Fetching %s (iso3=%s, bbox=%s)", layer_id, iso3, area_bbox)

    try:
        response = wfs.getfeature(**kwargs)
        data = response.read()
    except Exception as exc:
        # If CQL filter fails (column names vary), try with just bbox
        logger.warning("CQL filter failed (%s), retrying with bbox only", exc)
        kwargs.pop("cql_filter", None)
        if area_bbox:
            kwargs["bbox"] = list(area_bbox) + ["EPSG:4326"]
        response = wfs.getfeature(**kwargs)
        data = response.read()

    gdf = gpd.read_file(BytesIO(data))

    if gdf.empty:
        return {
            "error": f"No features found for {layer_id}",
            "country": iso3,
            "suggestion": "Try a broader search or different dataset.",
            "available_datasets": list(KNOWN_DATASETS.keys()),
        }

    # Save output
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    label = iso3 or "global"
    safe_name = layer_id.replace(":", "_").replace("__", "_")
    out_path = settings.output_dir / f"{safe_name}_{label}.geojson"
    gdf.to_file(out_path, driver="GeoJSON")

    # Cache
    cache_out = cache_path_for("points", suffix=".geojson", **cache_params)
    gdf.to_file(cache_out, driver="GeoJSON")

    return _build_response(gdf, str(out_path.resolve()), layer_id, cached=False)


def _build_response(
    gdf: gpd.GeoDataFrame, path: str, layer_id: str, cached: bool
) -> dict:
    """Build a standardised response dict from a GeoDataFrame."""
    # Get a sample of data for preview (first 5 rows, non-geometry columns)
    non_geom_cols = [c for c in gdf.columns if c != "geometry"]
    sample = gdf[non_geom_cols].head(5).to_dict(orient="records")

    # Detect useful columns
    bounds = gdf.total_bounds
    return {
        "geojson_path": path,
        "layer_id": layer_id,
        "feature_count": len(gdf),
        "columns": non_geom_cols,
        "bbox": [float(bounds[0]), float(bounds[1]), float(bounds[2]), float(bounds[3])],
        "sample_data": sample,
        "fetched_at": datetime.now().isoformat(),
        "cached": cached,
    }
