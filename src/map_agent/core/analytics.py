"""Usage analytics: track queries and suggest related analyses.

Logs every tool call to a JSON-lines file. Builds a researcher profile
over time to proactively suggest relevant data.
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from map_agent.core.config import settings

logger = logging.getLogger(__name__)

_LOG_FILENAME = "usage_log.jsonl"


def _log_path() -> Path:
    """Return the analytics log file path."""
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    return settings.output_dir / _LOG_FILENAME


def log_tool_call(
    tool: str,
    country: str | None = None,
    layer_id: str | None = None,
    admin_level: int | None = None,
    dataset: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Append a tool call record to the analytics log."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tool": tool,
        "country": country,
        "layer_id": layer_id,
        "admin_level": admin_level,
        "dataset": dataset,
    }
    if extra:
        record.update(extra)

    # Remove None values for cleaner logs
    record = {k: v for k, v in record.items() if v is not None}

    try:
        with open(_log_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as exc:
        logger.debug("Failed to write analytics: %s", exc)


def _read_log() -> list[dict]:
    """Read all log entries."""
    path = _log_path()
    if not path.exists():
        return []
    entries: list[dict] = []
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def get_usage_summary() -> dict[str, Any]:
    """Return a summary of tool usage patterns."""
    entries = _read_log()
    if not entries:
        return {"message": "No usage history yet.", "total_queries": 0}

    countries = Counter(e.get("country") for e in entries if e.get("country"))
    tools = Counter(e["tool"] for e in entries)
    layers = Counter(e.get("layer_id") for e in entries if e.get("layer_id"))

    return {
        "total_queries": len(entries),
        "top_countries": countries.most_common(10),
        "top_tools": tools.most_common(),
        "top_layers": layers.most_common(10),
        "first_query": entries[0].get("ts"),
        "last_query": entries[-1].get("ts"),
    }


# Suggestion templates keyed by what the researcher has already done
_FOLLOW_UP_SUGGESTIONS: dict[str, list[str]] = {
    "Parasite_Rate": [
        "Compare with ITN coverage to identify intervention gaps",
        "Fetch incidence data to see clinical burden",
        "Drill down to district level for hotspot identification",
        "Overlay survey points for ground-truth validation",
    ],
    "Incidence": [
        "Compare with mortality to assess case fatality",
        "Check intervention coverage (ITN, IRS, ACT)",
        "Look at trends over multiple years",
        "Drill down to identify high-burden districts",
    ],
    "Intervention": [
        "Compare intervention coverage with prevalence",
        "Check if high-burden areas have low coverage",
        "Look at coverage trends over time",
    ],
    "Blood_Disorders": [
        "Overlay with Pv prevalence (Duffy negativity affects Pv)",
        "Check G6PD deficiency for primaquine safety assessment",
        "Compare HbS frequency with Pf prevalence",
    ],
    "Vector": [
        "Check vector species suitability against prevalence",
        "Compare dominant species with IRS coverage",
        "Look at funestus vs gambiae distribution",
    ],
}


def get_suggestions(
    country: str | None = None,
    last_layer_id: str | None = None,
) -> list[str]:
    """Suggest follow-up analyses based on usage history and current context."""
    suggestions: list[str] = []

    # Suggest based on what was just fetched
    if last_layer_id:
        for key, tips in _FOLLOW_UP_SUGGESTIONS.items():
            if key.lower() in last_layer_id.lower():
                suggestions.extend(tips)
                break

    # Suggest based on usage patterns
    entries = _read_log()
    if entries and country:
        country_entries = [e for e in entries if e.get("country") == country]
        used_tools = {e["tool"] for e in country_entries}

        if "fetch_raster" in used_tools and "compute_zonal_stats" not in used_tools:
            suggestions.append("Run zonal stats to get admin-level summaries")
        if "compute_zonal_stats" in used_tools and "generate_plot" not in used_tools:
            suggestions.append("Generate a choropleth map from the zonal stats")
        if "get_boundaries" in used_tools and "fetch_points" not in used_tools:
            suggestions.append("Fetch survey points for ground-truth validation")

    return suggestions[:5]  # Cap at 5
