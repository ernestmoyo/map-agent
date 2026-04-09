"""Visualization: choropleths, raster heatmaps, trend lines, point maps.

Generates publication-quality PNG plots from MAP data using matplotlib.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

from map_agent.core.config import settings

logger = logging.getLogger(__name__)

# MAP-inspired colour scheme
_CMAP_PREVALENCE = "YlOrRd"
_CMAP_INCIDENCE = "OrRd"
_CMAP_INTERVENTIONS = "YlGn"
_CMAP_DEFAULT = "viridis"


def _guess_colormap(title: str | None, layer_id: str | None) -> str:
    """Pick a sensible colourmap based on the data being plotted."""
    hint = (title or "").lower() + " " + (layer_id or "").lower()
    if any(k in hint for k in ("prevalence", "parasite", "pr", "pfpr")):
        return _CMAP_PREVALENCE
    if any(k in hint for k in ("incidence", "mortality", "cases")):
        return _CMAP_INCIDENCE
    if any(k in hint for k in ("itn", "irs", "act", "treatment", "coverage", "intervention")):
        return _CMAP_INTERVENTIONS
    return _CMAP_DEFAULT


def _setup_figure(title: str | None = None) -> tuple[plt.Figure, plt.Axes]:
    """Create a figure with consistent styling."""
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    if title:
        ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    return fig, ax


def plot_raster(
    raster_path: str,
    boundaries_path: str | None = None,
    title: str | None = None,
    layer_id: str | None = None,
) -> dict:
    """Plot a raster surface with optional admin boundary overlay.

    Args:
        raster_path: Path to GeoTIFF file.
        boundaries_path: Optional GeoJSON boundaries to overlay.
        title: Plot title.
        layer_id: Layer ID (used to pick colourmap).

    Returns:
        Dict with: png_path.
    """
    import rioxarray  # noqa: F401
    import xarray as xr

    raster = Path(raster_path)
    if not raster.exists():
        return {"error": f"Raster file not found: {raster_path}"}

    da = xr.open_dataarray(raster, engine="rasterio")
    cmap = _guess_colormap(title, layer_id)

    fig, ax = _setup_figure(title)
    da.squeeze().plot(ax=ax, cmap=cmap, add_colorbar=True)

    if boundaries_path:
        bounds_file = Path(boundaries_path)
        if bounds_file.exists():
            gdf = gpd.read_file(bounds_file)
            gdf.boundary.plot(ax=ax, color="black", linewidth=0.8)

    plt.tight_layout()
    png_path = settings.output_dir / f"{raster.stem}.png"
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    da.close()

    return {"png_path": str(png_path.resolve())}


def plot_choropleth(
    boundaries_path: str,
    data_column: str | None = None,
    stats_csv_path: str | None = None,
    title: str | None = None,
    layer_id: str | None = None,
) -> dict:
    """Plot a choropleth map coloured by a data column or zonal stats.

    If stats_csv_path is provided, joins the stats to boundaries by zone name.

    Args:
        boundaries_path: Path to GeoJSON file.
        data_column: Column name to colour by (in the GeoJSON).
        stats_csv_path: Optional path to zonal stats CSV (from zonal_stats tool).
        title: Plot title.
        layer_id: Layer ID (for colourmap selection).

    Returns:
        Dict with: png_path.
    """
    import pandas as pd

    gdf = gpd.read_file(boundaries_path)
    if gdf.empty:
        return {"error": "No features in boundaries file."}

    # If stats CSV provided, join it to the boundaries
    if stats_csv_path:
        stats_df = pd.read_csv(stats_csv_path)
        # Find a matching name column in the GeoDataFrame
        name_col = None
        for candidate in ["name_1", "name_2", "name_3", "name_0", "name", "NAME"]:
            if candidate in gdf.columns:
                name_col = candidate
                break
        if name_col and "zone" in stats_df.columns:
            gdf = gdf.merge(stats_df, left_on=name_col, right_on="zone", how="left")
            if data_column is None:
                data_column = "mean"  # Default to mean from zonal stats

    if data_column is None or data_column not in gdf.columns:
        # Find first numeric column
        numeric_cols = gdf.select_dtypes(include=[np.number]).columns.tolist()
        numeric_cols = [c for c in numeric_cols if c != "geometry"]
        if numeric_cols:
            data_column = numeric_cols[0]
        else:
            return {"error": f"No numeric column found to plot. Available: {list(gdf.columns)}"}

    cmap = _guess_colormap(title, layer_id)
    fig, ax = _setup_figure(title)

    gdf.plot(
        column=data_column,
        ax=ax,
        cmap=cmap,
        legend=True,
        edgecolor="black",
        linewidth=0.5,
        missing_kwds={"color": "lightgrey", "label": "No data"},
    )

    plt.tight_layout()
    stem = Path(boundaries_path).stem
    png_path = settings.output_dir / f"choropleth_{stem}_{data_column}.png"
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return {"png_path": str(png_path.resolve())}


def plot_trend(
    data: list[dict],
    x_column: str = "year",
    y_column: str = "mean",
    group_column: str | None = None,
    title: str | None = None,
) -> dict:
    """Plot a time-series trend line.

    Args:
        data: List of dicts with at least x_column and y_column keys.
              Typically output from multiple zonal_stats runs.
        x_column: Column for x-axis (usually "year").
        y_column: Column for y-axis (usually "mean").
        group_column: Optional column to group by (e.g., zone names).
        title: Plot title.

    Returns:
        Dict with: png_path.
    """
    import pandas as pd

    df = pd.DataFrame(data)
    if df.empty:
        return {"error": "No data provided for trend plot."}

    fig, ax = _setup_figure(title)

    if group_column and group_column in df.columns:
        for name, group in df.groupby(group_column):
            group_sorted = group.sort_values(x_column)
            ax.plot(group_sorted[x_column], group_sorted[y_column], marker="o", label=str(name))
        ax.legend(fontsize=8, loc="best")
    else:
        df_sorted = df.sort_values(x_column)
        ax.plot(df_sorted[x_column], df_sorted[y_column], marker="o", linewidth=2, color="#d62728")

    ax.set_xlabel(x_column.replace("_", " ").title())
    ax.set_ylabel(y_column.replace("_", " ").title())
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    safe_title = (title or "trend").replace(" ", "_")[:40]
    png_path = settings.output_dir / f"trend_{safe_title}.png"
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return {"png_path": str(png_path.resolve())}


def plot_points(
    geojson_path: str,
    color_column: str | None = None,
    boundaries_path: str | None = None,
    title: str | None = None,
) -> dict:
    """Plot survey points on a map with optional boundary overlay.

    Args:
        geojson_path: Path to GeoJSON with point features.
        color_column: Optional column to colour points by.
        boundaries_path: Optional admin boundaries for context.
        title: Plot title.

    Returns:
        Dict with: png_path.
    """
    gdf = gpd.read_file(geojson_path)
    if gdf.empty:
        return {"error": "No features in GeoJSON file."}

    fig, ax = _setup_figure(title)

    # Plot boundaries first as background
    if boundaries_path:
        bounds_file = Path(boundaries_path)
        if bounds_file.exists():
            bgdf = gpd.read_file(bounds_file)
            bgdf.plot(ax=ax, color="lightgrey", edgecolor="black", linewidth=0.5)

    # Plot points
    plot_kwargs: dict[str, Any] = {
        "ax": ax,
        "markersize": 15,
        "alpha": 0.7,
        "edgecolor": "black",
        "linewidth": 0.3,
    }
    if color_column and color_column in gdf.columns:
        gdf.plot(column=color_column, cmap="YlOrRd", legend=True, **plot_kwargs)
    else:
        gdf.plot(color="#d62728", **plot_kwargs)

    plt.tight_layout()
    stem = Path(geojson_path).stem
    png_path = settings.output_dir / f"points_{stem}.png"
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return {"png_path": str(png_path.resolve())}


def plot_map(
    data_path: str,
    boundaries_path: str | None = None,
    title: str | None = None,
    style: str = "raster",
    layer_id: str | None = None,
    stats_csv_path: str | None = None,
    color_column: str | None = None,
    trend_data: list[dict] | None = None,
    x_column: str = "year",
    y_column: str = "mean",
    group_column: str | None = None,
) -> dict:
    """Generate a visualization — the main plotting entry point.

    Routes to the appropriate plot type based on style parameter.

    Args:
        data_path: Path to GeoTIFF (raster/choropleth) or GeoJSON (points).
        boundaries_path: Admin boundaries GeoJSON (for overlay or choropleth).
        title: Plot title.
        style: "raster", "choropleth", "trend", or "points".
        layer_id: MAP layer ID (for colourmap selection).
        stats_csv_path: Zonal stats CSV (for choropleth colouring).
        color_column: Column to colour by.
        trend_data: Data for trend plots (list of dicts).
        x_column: X-axis column for trends.
        y_column: Y-axis column for trends.
        group_column: Grouping column for multi-line trends.

    Returns:
        Dict with: png_path.
    """
    if style == "raster":
        return plot_raster(data_path, boundaries_path, title, layer_id)
    elif style == "choropleth":
        return plot_choropleth(
            boundaries_path or data_path,
            data_column=color_column,
            stats_csv_path=stats_csv_path,
            title=title,
            layer_id=layer_id,
        )
    elif style == "trend":
        if trend_data:
            return plot_trend(trend_data, x_column, y_column, group_column, title)
        return {"error": "Trend style requires trend_data parameter."}
    elif style == "points":
        return plot_points(data_path, color_column, boundaries_path, title)
    else:
        return {"error": f"Unknown style '{style}'. Use: raster, choropleth, trend, points."}
