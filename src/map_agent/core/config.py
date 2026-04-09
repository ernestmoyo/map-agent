"""Application settings, read from environment variables with MAP_AGENT_ prefix."""
from __future__ import annotations

from pathlib import Path

from platformdirs import user_cache_dir
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """MAP Agent configuration.

    All fields can be overridden via environment variables prefixed with MAP_AGENT_.
    Example: MAP_AGENT_OUTPUT_DIR=./my_output
    """

    model_config = {"env_prefix": "MAP_AGENT_"}

    geoserver_root: str = "https://data.malariaatlas.org/geoserver"
    output_dir: Path = Path("./map_out")
    cache_dir: Path = Path(user_cache_dir("map_agent"))
    user_agent: str = "map-agent/0.1.0 (+https://github.com/ernes/map_ai_agents)"

    # Cache TTLs in seconds
    capabilities_ttl: int = 86_400  # 24 hours
    data_ttl: int = 604_800  # 7 days

    # Geoserver request timeout in seconds
    request_timeout: int = 180

    @property
    def wcs_url(self) -> str:
        return f"{self.geoserver_root}/ows?service=WCS&version=2.0.1"

    @property
    def wfs_url(self) -> str:
        return f"{self.geoserver_root}/ows?service=WFS&version=2.0.0"


# Module-level singleton — import this wherever settings are needed.
settings = Settings()
