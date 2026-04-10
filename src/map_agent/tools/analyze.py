"""Composite analysis: single-call workflow inspired by gstack's chain command.

Runs the full pipeline in one call:
    catalog_search → get_boundaries → fetch_raster → zonal_stats → plot → citation

Accepts natural parameters instead of layer IDs and file paths.
"""
from __future__ import annotations

import logging
from typing import Any, Literal

from map_agent.core.analytics import log_tool_call
from map_agent.core.session import session
from map_agent.core.validate import validate_boundaries, validate_raster, validate_zonal_stats
from map_agent.tools import admin, catalog, citations, extract, plot, wcs

logger = logging.getLogger(__name__)

# Map natural metric names to catalog search terms and layer patterns
_METRIC_ALIASES: dict[str, str] = {
    "pfpr": "Pf Parasite Rate",
    "pf_prevalence": "Pf Parasite Rate",
    "prevalence": "Pf Parasite Rate",
    "pf_incidence": "Pf Incidence Rate",
    "incidence": "Pf Incidence Rate",
    "pf_mortality": "Pf Mortality Rate",
    "mortality": "Pf Mortality Rate",
    "pvpr": "Pv Parasite Rate",
    "pv_prevalence": "Pv Parasite Rate",
    "itn": "Insecticide Treated Net Use",
    "itn_access": "Insecticide Treated Net Access",
    "itn_use": "Insecticide Treated Net Use",
    "irs": "Indoor Residual Spraying",
    "act": "Effective Treatment",
    "g6pd": "G6PDd Allele Frequency",
    "duffy": "Duffy Negativity",
    "sickle": "Sickle Haemoglobin HbS",
    "hbs": "Sickle Haemoglobin HbS",
    "hbc": "HbC Allele Frequency",
    "gambiae": "Anopheles gambiae",
    "funestus": "Anopheles funestus",
    "arabiensis": "Anopheles arabiensis",
    "accessibility": "Travel Time To Healthcare",
}


def _find_best_layer(metric: str) -> str | None:
    """Find the best matching layer ID for a natural metric name."""
    search_term = _METRIC_ALIASES.get(metric.lower().strip(), metric)
    results = catalog.search(search_term, data_type="raster")
    if not results:
        return None

    # Prefer: latest vintage, primary workspace, and exact search term match
    search_lower = search_term.lower()

    def score(layer: dict) -> tuple[int, int, str]:
        lid = layer["layer_id"]
        lid_lower = lid.lower()
        ws = layer.get("workspace", "")

        # Workspace priority
        ws_priority = {"Malaria": 3, "Interventions": 3, "Blood_Disorders": 2, "Explorer": 1}.get(ws, 0)

        # Exact match bonus: all search tokens appear in the layer ID
        tokens = search_lower.split()
        exact_match = 1 if all(t in lid_lower for t in tokens) else 0

        return (exact_match, ws_priority, lid)

    results.sort(key=score, reverse=True)
    return results[0]["layer_id"]


def analyze(
    metric: str,
    country: str,
    admin_level: int = 1,
    name_filter: str | None = None,
    plot_style: Literal["choropleth", "raster"] = "choropleth",
    stats: list[str] | None = None,
) -> dict[str, Any]:
    """Run a complete analysis pipeline in a single call.

    This is the "chain command" — one call produces boundaries, raster,
    zonal stats, a plot, and a citation.

    Args:
        metric: What to analyze. Natural names like "pfpr", "incidence",
                "itn", "g6pd", "gambiae", or a full layer ID.
        country: Country name or ISO3 code.
        admin_level: Admin level for zonal breakdown (0-3). Default 1 (provinces).
        name_filter: Optional name to filter within the admin level.
        plot_style: "choropleth" (default) or "raster".
        stats: Statistics to compute. Defaults to ["mean", "min", "max", "median"].

    Returns:
        Dict with all artifacts: boundary, raster, stats, plot, citation,
        refs, validation warnings, and suggestions.
    """
    if stats is None:
        stats = ["mean", "min", "max", "median"]

    result: dict[str, Any] = {"metric": metric, "country": country, "admin_level": admin_level}
    warnings: list[str] = []

    # Step 1: Resolve layer
    if "__" in metric or ":" in metric:
        layer_id = metric  # Already a full layer ID
    else:
        layer_id = _find_best_layer(metric)
        if not layer_id:
            return {"error": f"No layer found for metric '{metric}'", "suggestion": "Try catalog_search to find available layers."}

    result["layer_id"] = layer_id
    session.last_layer_id = layer_id
    layer_ref = session.register_ref("L", layer_id, metric)
    result["layer_ref"] = layer_ref

    # Step 2: Get boundaries
    logger.info("analyze: fetching boundaries for %s admin%d", country, admin_level)
    boundary_result = admin.get_boundaries(country, admin_level, name_filter)
    if "error" in boundary_result:
        return {"error": boundary_result["error"], "step": "get_boundaries"}

    boundary_path = boundary_result["geojson_path"]
    iso3 = boundary_result.get("country", country)
    bbox = boundary_result.get("bbox")

    boundary_ref = session.register_ref("B", boundary_path, f"{iso3} admin{admin_level}")
    session.last_boundary_path = boundary_path
    session.set_focus(country=country, iso3=iso3, admin_level=admin_level, bbox=bbox, name_filter=name_filter)

    bnd_warnings = validate_boundaries(boundary_path)
    warnings.extend(bnd_warnings)

    result["boundary"] = {
        "ref": boundary_ref,
        "path": boundary_path,
        "feature_count": boundary_result.get("feature_count"),
        "units": boundary_result.get("units", []),
        "sub_units": boundary_result.get("sub_units", []),
    }

    # Step 3: Fetch raster
    logger.info("analyze: fetching raster %s for %s", layer_id, iso3)
    raster_result = wcs.fetch_raster(layer_id, country=iso3)
    if "error" in raster_result:
        return {"error": raster_result["error"], "step": "fetch_raster", "boundary": result.get("boundary")}

    raster_path = raster_result["tif_path"]
    raster_ref = session.register_ref("R", raster_path, f"{metric} {iso3}")
    session.last_raster_path = raster_path

    raster_warnings = validate_raster(raster_path, expected_bbox=bbox)
    warnings.extend(raster_warnings)

    result["raster"] = {
        "ref": raster_ref,
        "path": raster_path,
        "file_size_mb": raster_result.get("file_size_mb"),
        "cached": raster_result.get("cached", False),
    }

    # Step 4: Zonal stats
    logger.info("analyze: computing zonal stats")
    stats_result = extract.zonal_stats(raster_path, boundary_path, stats=stats)
    if "error" in stats_result:
        result["stats_error"] = stats_result["error"]
    else:
        stats_path = stats_result["csv_path"]
        stats_ref = session.register_ref("S", stats_path, f"stats {metric} {iso3}")
        session.last_stats_path = stats_path

        stats_warnings = validate_zonal_stats(stats_result.get("table", []), stats)
        warnings.extend(stats_warnings)

        result["stats"] = {
            "ref": stats_ref,
            "csv_path": stats_path,
            "zone_count": stats_result.get("zone_count"),
            "table": stats_result.get("table", []),
        }

    # Step 5: Plot
    logger.info("analyze: generating %s plot", plot_style)
    title = f"{metric.upper()} by Admin{admin_level} — {iso3}"
    if name_filter:
        title += f" ({name_filter})"

    plot_result = plot.plot_map(
        data_path=raster_path,
        boundaries_path=boundary_path,
        title=title,
        style=plot_style,
        layer_id=layer_id,
        stats_csv_path=stats_result.get("csv_path") if "stats" in result else None,
        color_column="mean",
    )
    if "error" not in plot_result:
        plot_path = plot_result["png_path"]
        plot_ref = session.register_ref("P", plot_path, f"plot {metric} {iso3}")
        result["plot"] = {"ref": plot_ref, "path": plot_path}

    # Step 6: Citation
    citation_result = citations.get_citation(layer_id)
    result["citation"] = {
        "text": citation_result.get("citation_text"),
        "doi": citation_result.get("doi_url"),
    }

    # Attach validation warnings
    result["warnings"] = warnings

    # Log analytics
    log_tool_call(
        "analyze",
        country=iso3,
        layer_id=layer_id,
        admin_level=admin_level,
        extra={"metric": metric, "plot_style": plot_style},
    )

    return result
