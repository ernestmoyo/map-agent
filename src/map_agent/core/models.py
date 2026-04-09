"""Pydantic models for tool inputs and outputs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class LayerInfo:
    """A single MAP geoserver layer."""

    layer_id: str
    workspace: str
    title: str
    abstract: str
    data_type: str  # "raster" or "vector"


@dataclass(frozen=True)
class BoundaryInfo:
    """Summary of an admin boundary unit."""

    name: str
    admin_level: int
    iso3: str
    bbox: tuple[float, float, float, float]  # (west, south, east, north)


@dataclass(frozen=True)
class Citation:
    """Dataset citation metadata."""

    dataset: str
    version: str
    doi: str
    accessed_at: datetime
    url: str
