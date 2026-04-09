"""Layer catalog: search available MAP geoserver layers."""
from __future__ import annotations

from map_agent.core.geoserver import get_wcs_client, get_wfs_client
from map_agent.core.models import LayerInfo


def _parse_workspace(layer_id: str) -> tuple[str, str]:
    """Split 'Workspace__LayerName' or 'Workspace:LayerName' into (workspace, id)."""
    for sep in ("__", ":"):
        if sep in layer_id:
            parts = layer_id.split(sep, 1)
            return parts[0], layer_id
    return "", layer_id


def _build_raster_index() -> list[LayerInfo]:
    """Fetch WCS capabilities and return a list of raster layers."""
    wcs = get_wcs_client()
    results: list[LayerInfo] = []
    for cov_id in sorted(wcs.contents):
        workspace, _ = _parse_workspace(cov_id)
        cov = wcs.contents[cov_id]
        results.append(
            LayerInfo(
                layer_id=cov_id,
                workspace=workspace,
                title=getattr(cov, "title", cov_id),
                abstract=getattr(cov, "abstract", ""),
                data_type="raster",
            )
        )
    return results


def _build_vector_index() -> list[LayerInfo]:
    """Fetch WFS capabilities and return a list of vector layers."""
    wfs = get_wfs_client()
    results: list[LayerInfo] = []
    for ft_id in sorted(wfs.contents):
        workspace, _ = _parse_workspace(ft_id)
        ft = wfs.contents[ft_id]
        results.append(
            LayerInfo(
                layer_id=ft_id,
                workspace=workspace,
                title=getattr(ft, "title", ft_id),
                abstract=getattr(ft, "abstract", ""),
                data_type="vector",
            )
        )
    return results


def search(query: str, data_type: str = "all") -> list[dict]:
    """Search MAP layers by keyword.

    Args:
        query: Search term (case-insensitive substring match across id, title, workspace).
        data_type: Filter by "raster", "vector", or "all".

    Returns:
        List of matching layers as dicts, up to 30 results.
    """
    layers: list[LayerInfo] = []
    if data_type in ("raster", "all"):
        layers.extend(_build_raster_index())
    if data_type in ("vector", "all"):
        layers.extend(_build_vector_index())

    query_lower = query.lower()
    tokens = query_lower.split()

    scored: list[tuple[int, LayerInfo]] = []
    for layer in layers:
        searchable = f"{layer.layer_id} {layer.title} {layer.workspace} {layer.abstract}".lower()
        hits = sum(1 for token in tokens if token in searchable)
        if hits > 0:
            scored.append((hits, layer))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [
        {
            "layer_id": layer.layer_id,
            "workspace": layer.workspace,
            "title": layer.title,
            "data_type": layer.data_type,
            "abstract": layer.abstract[:200] if layer.abstract else "",
        }
        for _, layer in scored[:30]
    ]
