"""Admin boundaries: country/region/district lookup with sub-unit discovery.

Uses MAP's WFS Admin_Units layers (latest vintage: 202403) to provide
hierarchical geographic drill-down. Each query returns the requested
boundary AND lists available sub-units for further drilling.
"""
from __future__ import annotations

import json
import logging
from io import BytesIO
from pathlib import Path
from typing import Any

import geopandas as gpd
import requests

from map_agent.core.cache import get_cached_path, cache_path_for
from map_agent.core.config import settings

logger = logging.getLogger(__name__)

# Latest admin boundary vintage on MAP geoserver
_ADMIN_VINTAGE = "202403"

# Common country name aliases -> ISO3
_COUNTRY_ALIASES: dict[str, str] = {
    "tanzania": "TZA", "kenya": "KEN", "nigeria": "NGA", "zambia": "ZMB",
    "zimbabwe": "ZWE", "mozambique": "MOZ", "angola": "AGO", "namibia": "NAM",
    "south africa": "ZAF", "drc": "COD", "congo": "COD",
    "democratic republic of the congo": "COD", "dr congo": "COD",
    "ethiopia": "ETH", "uganda": "UGA", "malawi": "MWI", "rwanda": "RWA",
    "burundi": "BDI", "madagascar": "MDG", "cameroon": "CMR", "ghana": "GHA",
    "senegal": "SEN", "mali": "MLI", "burkina faso": "BFA", "niger": "NER",
    "chad": "TCD", "sudan": "SDN", "south sudan": "SSD", "somalia": "SOM",
    "eritrea": "ERI", "guinea": "GIN", "sierra leone": "SLE",
    "liberia": "LBR", "cote d'ivoire": "CIV", "ivory coast": "CIV",
    "togo": "TGO", "benin": "BEN", "gabon": "GAB",
    "equatorial guinea": "GNQ", "congo brazzaville": "COG",
    "republic of the congo": "COG", "central african republic": "CAF",
    "botswana": "BWA", "eswatini": "SWZ", "swaziland": "SWZ",
    "lesotho": "LSO", "comoros": "COM", "mauritius": "MUS",
    "cape verde": "CPV", "sao tome": "STP", "gambia": "GMB",
    "guinea-bissau": "GNB",
}


def _layer_name(admin_level: int) -> str:
    """Return the WFS layer name for a given admin level."""
    return f"Admin_Units:{_ADMIN_VINTAGE}_Global_Admin_{admin_level}"


def resolve_country(name_or_iso3: str) -> str:
    """Resolve a country name or ISO3 code to an uppercase ISO3 code.

    Accepts: "Tanzania", "tanzania", "TZA", "tza"
    Returns: "TZA"
    """
    upper = name_or_iso3.strip().upper()
    if len(upper) == 3 and upper.isalpha():
        return upper
    lower = name_or_iso3.strip().lower()
    iso3 = _COUNTRY_ALIASES.get(lower)
    if iso3:
        return iso3
    raise ValueError(
        f"Could not resolve country '{name_or_iso3}'. "
        f"Try an ISO3 code (e.g., TZA, KEN) or a common name."
    )


def _fetch_admin_gdf(
    admin_level: int,
    iso3: str | None = None,
    name_filter: str | None = None,
) -> gpd.GeoDataFrame:
    """Fetch admin boundaries from WFS as a GeoDataFrame.

    Uses cache when available. Filters by country ISO3 and optional name.
    """
    cache_params = {"level": admin_level, "iso3": iso3 or "all", "name": name_filter or ""}
    cached = get_cached_path("boundaries", suffix=".geojson", **cache_params)
    if cached is not None:
        return gpd.read_file(cached)

    layer = _layer_name(admin_level)

    # Build CQL filter — use 'iso' column (not 'iso3') per MAP schema
    cql_parts: list[str] = []
    if iso3:
        cql_parts.append(f"iso='{iso3}'")
    if name_filter:
        cql_parts.append(
            f"(strToUpperCase(name_0) LIKE '%{name_filter.upper()}%' OR "
            f"strToUpperCase(name_1) LIKE '%{name_filter.upper()}%' OR "
            f"strToUpperCase(name_2) LIKE '%{name_filter.upper()}%')"
        )

    # Use direct HTTP request — OWSLib WFS doesn't support GeoServer's
    # vendor-specific CQL_FILTER parameter in any version.
    params: dict[str, str] = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": layer,
        "outputFormat": "application/json",
        "maxFeatures": "500",
    }
    if cql_parts:
        params["CQL_FILTER"] = " AND ".join(cql_parts)

    logger.info("Fetching %s (iso3=%s, name=%s)", layer, iso3, name_filter)
    response = requests.get(
        f"{settings.geoserver_root}/wfs",
        params=params,
        timeout=settings.request_timeout,
    )
    response.raise_for_status()
    data = response.content

    gdf = gpd.read_file(BytesIO(data))
    if gdf.empty:
        return gdf

    # Cache the result
    out_path = cache_path_for("boundaries", suffix=".geojson", **cache_params)
    gdf.to_file(out_path, driver="GeoJSON")

    return gdf


def _detect_name_column(gdf: gpd.GeoDataFrame, admin_level: int) -> str:
    """Find the best name column for a given admin level."""
    candidates = [f"name_{admin_level}", f"NAME_{admin_level}", "name", "NAME"]
    for col in candidates:
        if col in gdf.columns:
            return col
    # Fallback: first column with 'name' in it
    for col in gdf.columns:
        if "name" in col.lower():
            return col
    return gdf.columns[0]


def _detect_max_admin_level(gdf: gpd.GeoDataFrame) -> int:
    """Detect the deepest admin level available in a GeoDataFrame."""
    for level in (3, 2, 1, 0):
        if f"name_{level}" in gdf.columns or f"NAME_{level}" in gdf.columns:
            return level
    return 0


def get_boundaries(
    country: str,
    admin_level: int = 0,
    name_filter: str | None = None,
) -> dict:
    """Get admin boundaries for a country with sub-unit discovery.

    This is the core tool for hierarchical drill-down. It returns:
    1. The GeoJSON boundary file path
    2. A summary of the area (name, bbox, feature count)
    3. A list of available sub-units for further drilling

    Args:
        country: Country name or ISO3 code (e.g., "Tanzania", "TZA").
        admin_level: Admin level 0 (country) to 3 (sub-district).
        name_filter: Optional name to filter within the admin level
                     (e.g., "Mwanza" to get Mwanza region).

    Returns:
        Dict with keys: geojson_path, summary, sub_units, bbox
    """
    iso3 = resolve_country(country)

    # Fetch the requested boundaries
    gdf = _fetch_admin_gdf(admin_level, iso3=iso3, name_filter=name_filter)

    if gdf.empty:
        return {
            "error": f"No admin{admin_level} boundaries found for {iso3}"
            + (f" matching '{name_filter}'" if name_filter else ""),
            "suggestion": "Try a different admin level or check the country name.",
        }

    # Save to output dir
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    label = name_filter.replace(" ", "_") if name_filter else iso3
    out_path = settings.output_dir / f"{iso3}_admin{admin_level}_{label}.geojson"
    gdf.to_file(out_path, driver="GeoJSON")

    # Build summary
    name_col = _detect_name_column(gdf, admin_level)
    bounds = gdf.total_bounds  # (minx, miny, maxx, maxy)
    bbox = [float(bounds[0]), float(bounds[1]), float(bounds[2]), float(bounds[3])]

    unit_names = sorted(gdf[name_col].dropna().unique().tolist()) if name_col in gdf.columns else []

    # Try to discover sub-units at the next admin level
    sub_units: list[str] = []
    next_level = admin_level + 1
    if next_level <= 3:
        try:
            sub_gdf = _fetch_admin_gdf(next_level, iso3=iso3, name_filter=name_filter)
            if not sub_gdf.empty:
                sub_name_col = _detect_name_column(sub_gdf, next_level)
                sub_units = sorted(sub_gdf[sub_name_col].dropna().unique().tolist())
        except Exception as exc:
            logger.warning("Could not fetch admin%d sub-units: %s", next_level, exc)

    # Register ref and update session
    from map_agent.core.analytics import log_tool_call
    from map_agent.core.session import session
    from map_agent.core.validate import validate_boundaries

    path_str = str(out_path.resolve())
    label = f"{iso3} admin{admin_level}"
    if name_filter:
        label += f" ({name_filter})"
    boundary_ref = session.register_ref("B", path_str, label)
    session.last_boundary_path = path_str
    session.set_focus(iso3=iso3, admin_level=admin_level, bbox=bbox, name_filter=name_filter)

    bnd_warnings = validate_boundaries(path_str)

    log_tool_call("get_boundaries", country=iso3, admin_level=admin_level)

    return {
        "ref": boundary_ref,
        "geojson_path": path_str,
        "country": iso3,
        "admin_level": admin_level,
        "feature_count": len(gdf),
        "bbox": bbox,
        "units": unit_names[:50],  # Cap at 50 for readability
        "sub_units_available": len(sub_units) > 0,
        "sub_units_level": next_level if sub_units else None,
        "sub_units": sub_units[:100],  # Cap at 100
        "drill_down_hint": (
            f"To drill deeper, call get_boundaries('{iso3}', {next_level}, '<name>')"
            if sub_units
            else "This is the deepest admin level available for this area."
        ),
        "warnings": bnd_warnings,
    }
