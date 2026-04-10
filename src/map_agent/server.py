"""MAP Research Workbench — MCP server for the Malaria Atlas Project.

Exposes MAP geoserver data as Claude Code tools. Researchers invoke these
via /map-* slash commands or directly through Claude's tool-calling interface.

Run:
    python -m map_agent.server     # stdio transport (for Claude Code)
    mcp dev src/map_agent/server.py  # inspector mode
"""
from __future__ import annotations

import json
from typing import Literal

from mcp.server.fastmcp import FastMCP

from map_agent.tools import admin, analyze as analyze_mod, catalog, citations, extract, plot, wcs, wfs

mcp = FastMCP(
    "Malaria Atlas Project",
    instructions=(
        "Research workbench for MAP geoserver data: prevalence, incidence, "
        "mortality, interventions, vectors, blood disorders, and admin boundaries "
        "across Africa. Supports hierarchical drill-down from country to district.\n\n"
        "DISCLAIMER: This is an independent personal tool, NOT an official product "
        "of the Malaria Atlas Project (MAP), University of Oxford, or Telethon Kids "
        "Institute. Data is sourced from MAP's public geoserver under CC BY 3.0. "
        "All outputs must include the dataset citation provided by get_citation()."
    ),
)


# ---------------------------------------------------------------------------
# Tool 1: catalog_search
# ---------------------------------------------------------------------------
@mcp.tool()
def catalog_search(
    query: str,
    data_type: Literal["raster", "vector", "all"] = "all",
) -> str:
    """Search available Malaria Atlas Project layers by keyword.

    Use this to discover what data is available before fetching it.
    Searches across layer IDs, titles, and workspaces.

    Workspaces include:
    - Malaria: Pf/Pv parasite rate, incidence, mortality (rasters)
    - Interventions: ITN access/use, IRS coverage, effective treatment (rasters)
    - Explorer: curated layers including Anopheles vector species (rasters + vectors)
    - Blood_Disorders: Duffy, G6PD, sickle cell, HbC frequencies (rasters)
    - Accessibility: travel time to healthcare, friction surfaces (rasters)
    - Admin_Units: admin boundaries at levels 0-3 (vectors)
    - MAP_READER: pre-aggregated cases/incidence by admin unit (vectors)
    - Malaria (WFS): parasite rate survey points (vectors)
    - Vector_Occurrence: dominant vector survey points (vectors)

    Examples:
        catalog_search("Pf prevalence") -> Pf parasite rate layers
        catalog_search("ITN", "raster") -> ITN coverage rasters
        catalog_search("Anopheles gambiae") -> gambiae suitability layers
        catalog_search("admin Tanzania", "vector") -> admin boundaries
        catalog_search("G6PD") -> G6PD deficiency frequency layers

    Args:
        query: Search term. Try parasite names (Pf, Pv), metrics (incidence,
               prevalence, mortality), interventions (ITN, IRS, ACT), vector
               species (gambiae, funestus), or blood disorders (G6PD, Duffy).
        data_type: Filter results — "raster" for modelled surfaces,
                   "vector" for survey points/boundaries, "all" for both.

    Returns:
        JSON array of matching layers with layer_id, workspace, title, data_type.
    """
    results = catalog.search(query, data_type)
    if not results:
        return json.dumps({"message": f"No layers found matching '{query}'", "results": []})
    return json.dumps({"count": len(results), "results": results}, indent=2)


# ---------------------------------------------------------------------------
# Tool 2: get_boundaries
# ---------------------------------------------------------------------------
@mcp.tool()
def get_boundaries(
    country: str,
    admin_level: int = 0,
    name_filter: str | None = None,
) -> str:
    """Get admin boundaries for a country with sub-unit discovery.

    Returns the boundary as a GeoJSON file and lists all sub-units at the
    next admin level — enabling hierarchical drill-down from country to district.

    Admin levels:
    - 0: Country
    - 1: Province / Region / State
    - 2: District / County / LGA
    - 3: Sub-district (where available)

    Not all countries have all levels. The response tells you what's available.

    Examples:
        get_boundaries("Tanzania")  -> country boundary + lists all regions
        get_boundaries("Tanzania", 1)  -> all regions + lists districts per region
        get_boundaries("Tanzania", 1, "Mwanza")  -> Mwanza region + its districts
        get_boundaries("Namibia", 2)  -> all districts in Namibia

    Args:
        country: Country name or ISO3 code (e.g., "Tanzania", "TZA", "Kenya", "KEN").
        admin_level: 0 (country), 1 (province), 2 (district), 3 (sub-district).
        name_filter: Optional name to filter within the level (e.g., "Mwanza").

    Returns:
        JSON with: geojson_path, country ISO3, bbox, list of units at this level,
        list of sub-units at the next level, and a drill_down_hint.
    """
    result = admin.get_boundaries(country, admin_level, name_filter)
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Tool 3: fetch_raster
# ---------------------------------------------------------------------------
@mcp.tool()
def fetch_raster(
    layer_id: str,
    country: str | None = None,
    admin1: str | None = None,
    bbox: list[float] | None = None,
    year: int | None = None,
) -> str:
    """Download a modelled raster surface from MAP's geoserver.

    Use this for: prevalence maps, incidence surfaces, mortality rates,
    intervention coverage, vector species suitability, blood disorder
    frequencies, and accessibility layers.

    The raster is automatically clipped to the specified country or region.
    Returns a GeoTIFF file path.

    Common layer patterns (use catalog_search to find exact IDs):
    - Malaria__202508_Global_Pf_Parasite_Rate
    - Malaria__202508_Global_Pf_Incidence_Rate
    - Interventions__202508_Africa_Insecticide_Treated_Net_Use
    - Explorer__2010_Anopheles_gambiae_ss
    - Blood_Disorders__201201_Global_G6PDd_Allele_Frequency
    - Accessibility__202001_Global_Walking_Only_Travel_Time_To_Healthcare

    Args:
        layer_id: Full WCS coverage ID from catalog_search.
        country: Country name or ISO3 code to clip to (e.g., "Tanzania", "TZA").
        admin1: Province/region name to clip to (requires country).
        bbox: Explicit bounding box [west, south, east, north] in degrees.
        year: Year for time-aware layers (reserved for future use).

    Returns:
        JSON with: tif_path, layer_id, bbox, file_size_mb, shape.
    """
    result = wcs.fetch_raster(layer_id, country, admin1, bbox, year)
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Tool 4: fetch_points
# ---------------------------------------------------------------------------
@mcp.tool()
def fetch_points(
    dataset: str,
    country: str | None = None,
    bbox: list[float] | None = None,
    year_range: list[int] | None = None,
    max_features: int = 5000,
) -> str:
    """Download survey points or pre-aggregated admin statistics from MAP.

    Use this for: parasite rate survey data, vector occurrence observations,
    and MAP_READER pre-aggregated case/incidence data by admin unit.

    Shorthand dataset names:
    - "pf_surveys" — Pf parasite rate survey points
    - "pv_surveys" — Pv parasite rate survey points
    - "vector_occurrence" — dominant vector species survey points
    - "cases_admin1_pf" — pre-aggregated Pf cases at admin1 level
    - "cases_admin2_pf" — pre-aggregated Pf cases at admin2 level
    - "yearly_cases_admin1" — yearly confirmed case summaries by admin1
    - "yearly_api_admin1" — yearly API (annual parasite incidence) by admin1
    - "anopheline_data" — Anopheles species occurrence records
    - "pr_data" — all parasite rate data from the Explorer

    Or use a full WFS layer ID (e.g., "Malaria:202406_Global_Pf_Parasite_Rate_Surveys").

    Args:
        dataset: Shorthand name or full WFS layer ID.
        country: Country name or ISO3 to filter by.
        bbox: Bounding box [west, south, east, north] in degrees.
        year_range: [start_year, end_year] to filter temporal data.
        max_features: Max features to return (default 5000).

    Returns:
        JSON with: geojson_path, feature_count, columns, sample_data, bbox.
    """
    result = wfs.fetch_points(dataset, country, bbox, year_range, max_features)
    return json.dumps(result, indent=2, default=str)


# ---------------------------------------------------------------------------
# Tool 5: zonal_stats
# ---------------------------------------------------------------------------
@mcp.tool()
def compute_zonal_stats(
    raster_path: str,
    boundaries_path: str,
    stats: list[str] | None = None,
    zone_name_column: str | None = None,
) -> str:
    """Compute zonal statistics of a raster within admin boundary polygons.

    Use this to summarize raster data (prevalence, incidence, coverage)
    by admin zones (provinces, districts). Essential for creating
    admin-level summary tables and choropleth data.

    The output is sorted by mean value (highest first) to quickly
    identify high-burden areas.

    Args:
        raster_path: Path to GeoTIFF (from fetch_raster).
        boundaries_path: Path to GeoJSON (from get_boundaries).
        stats: Statistics to compute. Defaults to ["mean","min","max","count","median"].
        zone_name_column: Column for zone names (auto-detected if omitted).

    Returns:
        JSON with: csv_path, table (zone-level stats), zone_count.
    """
    result = extract.zonal_stats(raster_path, boundaries_path, stats, zone_name_column)
    return json.dumps(result, indent=2, default=str)


# ---------------------------------------------------------------------------
# Tool 6: plot_map
# ---------------------------------------------------------------------------
@mcp.tool()
def generate_plot(
    data_path: str,
    style: Literal["raster", "choropleth", "trend", "points"] = "raster",
    boundaries_path: str | None = None,
    title: str | None = None,
    layer_id: str | None = None,
    stats_csv_path: str | None = None,
    color_column: str | None = None,
    trend_data: list[dict] | None = None,
    x_column: str = "year",
    y_column: str = "mean",
    group_column: str | None = None,
) -> str:
    """Generate a map visualization (PNG).

    Supports four styles:
    - "raster": Heatmap of a raster surface (prevalence, incidence, etc.)
    - "choropleth": Admin zones coloured by a statistic (mean prevalence per district)
    - "trend": Time-series line chart (prevalence over years)
    - "points": Survey point locations on a map

    Automatically picks appropriate colour schemes based on the data type
    (red for prevalence, green for intervention coverage, etc.).

    Args:
        data_path: Path to GeoTIFF (raster/choropleth) or GeoJSON (points).
        style: Plot type — "raster", "choropleth", "trend", or "points".
        boundaries_path: Admin boundaries GeoJSON for overlay/choropleth.
        title: Plot title.
        layer_id: MAP layer ID (helps pick colourmap).
        stats_csv_path: Zonal stats CSV for choropleth colouring.
        color_column: Column to colour by.
        trend_data: Data for trend plots (list of {year, mean, zone} dicts).
        x_column: X-axis column for trends (default "year").
        y_column: Y-axis column for trends (default "mean").
        group_column: Grouping column for multi-line trends.

    Returns:
        JSON with: png_path.
    """
    result = plot.plot_map(
        data_path, boundaries_path, title, style, layer_id,
        stats_csv_path, color_column, trend_data, x_column, y_column, group_column,
    )
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Tool 7: get_citation
# ---------------------------------------------------------------------------
@mcp.tool()
def get_citation(layer_id: str) -> str:
    """Get citation metadata for a MAP dataset.

    ALWAYS call this after fetching data. Returns the dataset name, version,
    DOI, and a formatted citation string ready for publications, NSPs,
    and Global Fund applications.

    Args:
        layer_id: The MAP layer ID that was used to fetch data.

    Returns:
        JSON with: dataset, version, doi, citation_text, accessed_at.
    """
    result = citations.get_citation(layer_id)
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Tool 8: analyze (chain command)
# ---------------------------------------------------------------------------
@mcp.tool()
def analyze(
    metric: str,
    country: str,
    admin_level: int = 1,
    name_filter: str | None = None,
    plot_style: Literal["choropleth", "raster"] = "choropleth",
    stats: list[str] | None = None,
) -> str:
    """Run a complete analysis pipeline in ONE call — the chain command.

    Instead of calling 5 tools separately, this single call produces:
    boundaries + raster + zonal stats + plot + citation.

    Results include @refs (e.g., @R1, @B1, @S1) that you can use in
    subsequent tool calls instead of file paths.

    Metric shortcuts:
    - "pfpr" / "prevalence" → Pf Parasite Rate
    - "incidence" → Pf Incidence Rate
    - "mortality" → Pf Mortality Rate
    - "pvpr" → Pv Parasite Rate
    - "itn" / "itn_use" → ITN Use coverage
    - "irs" → IRS coverage
    - "act" → Effective Treatment
    - "g6pd" → G6PD deficiency allele frequency
    - "duffy" → Duffy negativity phenotype frequency
    - "sickle" / "hbs" → Sickle haemoglobin HbS
    - "hbc" → HbC allele frequency
    - "gambiae" / "funestus" / "arabiensis" → vector suitability
    - Or pass a full layer ID (e.g., "Malaria__202508_Global_Pf_Parasite_Rate")

    Examples:
        analyze("pfpr", "Kenya", 1) → PfPR by county with choropleth
        analyze("itn", "Tanzania", 2) → ITN coverage by district
        analyze("g6pd", "Nigeria", 1, plot_style="raster") → G6PD heatmap

    Args:
        metric: What to analyze — shortcut name or full layer ID.
        country: Country name or ISO3 code.
        admin_level: Admin level for breakdown (0-3). Default 1.
        name_filter: Optional name to filter within the admin level.
        plot_style: "choropleth" (default) or "raster".
        stats: Statistics to compute. Defaults to ["mean","min","max","median"].

    Returns:
        JSON with all artifacts: boundary, raster, stats table, plot, citation,
        @refs, validation warnings, and follow-up suggestions.
    """
    result = analyze_mod.analyze(metric, country, admin_level, name_filter, plot_style, stats)

    # Add suggestions
    from map_agent.core.analytics import get_suggestions
    result["suggestions"] = get_suggestions(
        country=result.get("boundary", {}).get("country") or country,
        last_layer_id=result.get("layer_id"),
    )

    return json.dumps(result, indent=2, default=str)


# ---------------------------------------------------------------------------
# Tool 9: session_status
# ---------------------------------------------------------------------------
@mcp.tool()
def session_status() -> str:
    """Show the current session state: @refs, geographic focus, and breadcrumb.

    Displays all active refs (@L, @R, @B, @S, @P) that can be used in
    place of layer IDs and file paths in subsequent tool calls.

    Also shows the current geographic focus (country, admin level),
    drill-down breadcrumb, and follow-up suggestions based on usage history.

    Returns:
        JSON with: focus, breadcrumb, refs, last_artifacts, usage_summary, suggestions.
    """
    from map_agent.core.analytics import get_suggestions, get_usage_summary
    from map_agent.core.session import session

    status = session.get_status()
    status["usage_summary"] = get_usage_summary()
    status["suggestions"] = get_suggestions(
        country=session.current_iso3,
        last_layer_id=session.last_layer_id,
    )
    return json.dumps(status, indent=2, default=str)


def main() -> None:
    """Entry point for the MCP server (stdio transport)."""
    mcp.run()


if __name__ == "__main__":
    main()
