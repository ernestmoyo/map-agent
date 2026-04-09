"""Shared WCS / WFS client factory with connection reuse."""
from __future__ import annotations

from functools import lru_cache

from owslib.wcs import WebCoverageService
from owslib.wfs import WebFeatureService

from map_agent.core.config import settings


@lru_cache(maxsize=1)
def get_wcs_client() -> WebCoverageService:
    """Return a cached WCS 2.0.1 client connected to the MAP geoserver."""
    return WebCoverageService(
        settings.wcs_url,
        version="2.0.1",
        timeout=settings.request_timeout,
    )


@lru_cache(maxsize=1)
def get_wfs_client() -> WebFeatureService:
    """Return a cached WFS 2.0.0 client connected to the MAP geoserver."""
    return WebFeatureService(
        settings.wfs_url,
        version="2.0.0",
        timeout=settings.request_timeout,
    )
