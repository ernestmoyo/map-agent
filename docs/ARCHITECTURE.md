# Architecture

`map-agent` is a Python MCP (Model Context Protocol) server that exposes the Malaria Atlas Project's geoserver as Claude Code tools. Researchers interact via `/map-*` slash commands in Claude Code.

## System overview

```
Researcher in Claude Code
        |
        | types: /map "Pf prevalence trend in Tanzania 2015-2020"
        v
.claude/commands/map.md
        |
        | loads domain knowledge (glossary, heuristics, workflow)
        v
Claude interprets the question
        |
        | calls MCP tools via stdio
        v
map_agent.server (FastMCP)
        |
        |-- catalog_search  -->  tools/catalog.py  -->  WCS/WFS GetCapabilities
        |-- get_boundaries  -->  tools/admin.py    -->  WFS Admin_Units
        |-- fetch_raster    -->  tools/wcs.py      -->  WCS GetCoverage
        |-- fetch_points    -->  tools/wfs.py      -->  WFS GetFeature
        |-- zonal_stats     -->  tools/extract.py  -->  rasterstats
        |-- generate_plot   -->  tools/plot.py     -->  matplotlib
        |-- get_citation    -->  tools/citations.py
        |
        v
./map_out/<run>/
    *.tif          (GeoTIFF rasters)
    *.geojson      (boundaries, survey points)
    *.csv          (zonal statistics)
    *.png          (choropleths, trend charts)
    citation.json  (DOI, version, access date)
```

## Layers

### 1. Slash commands (`.claude/commands/map-*.md`)

Markdown files that load domain knowledge into Claude's context when invoked. Each command guides Claude through a specific research workflow (prevalence analysis, intervention gap identification, trend analysis, etc.).

The glossary, heuristics, and layer-to-tool mappings live here — not in the Python code. This means the domain logic is transparent and editable without touching Python.

### 2. MCP server (`src/map_agent/server.py`)

Thin FastMCP glue that registers 7 tools. Each `@mcp.tool()` function validates inputs, delegates to the tools layer, and returns JSON. Uses stdio transport for Claude Code integration.

### 3. Tools layer (`src/map_agent/tools/`)

Pure Python modules — independently usable from notebooks or scripts. No MCP dependency. Each module encapsulates one data-access or analysis pattern:

| Module | Responsibility |
|---|---|
| `catalog.py` | Layer discovery via GetCapabilities |
| `admin.py` | Admin boundaries + hierarchical drill-down |
| `wcs.py` | Raster download via WCS 2.0.1 |
| `wfs.py` | Vector/survey data via WFS 2.0.0 |
| `extract.py` | Zonal statistics (raster x polygon) |
| `plot.py` | Matplotlib visualizations |
| `citations.py` | DOI and version tracking |

### 4. Core (`src/map_agent/core/`)

Cross-cutting infrastructure:

| Module | Responsibility |
|---|---|
| `config.py` | Pydantic Settings — env vars, paths, timeouts |
| `geoserver.py` | WCS/WFS client factory with connection reuse |
| `cache.py` | On-disk response cache with TTL |
| `models.py` | Pydantic data models |

## Data flow example

**Question:** "Pf prevalence in Tanzania by region"

1. `/map` command loads glossary into Claude's context
2. Claude parses: species=Pf, metric=prevalence, country=Tanzania, level=admin1
3. `catalog_search("Pf parasite rate")` -> finds `Malaria__202508_Global_Pf_Parasite_Rate`
4. `get_boundaries("Tanzania", 1)` -> returns regions GeoJSON + lists districts for drill-down
5. `fetch_raster("Malaria__202508_Global_Pf_Parasite_Rate", country="Tanzania")` -> GeoTIFF clipped to TZA
6. `compute_zonal_stats(raster, boundaries)` -> CSV with mean PR per region
7. `generate_plot(style="choropleth")` -> PNG map
8. `get_citation("Malaria__202508_Global_Pf_Parasite_Rate")` -> DOI + formatted citation
9. Claude presents results and offers: "Drill into Mwanza region?"

## Design decisions

- **MCP over standalone CLI**: Target users are already in Claude Code. MCP makes tools first-class citizens.
- **Stdio transport**: Claude Code manages the server process lifecycle. No port management.
- **File paths over inline data**: Rasters are binary and large. Returning paths lets users open files in QGIS.
- **Domain knowledge in commands, not code**: Glossary and heuristics in markdown files are transparent and editable.
- **Pure Python tools layer**: Usable from notebooks without MCP. Tested independently.
- **pyogrio over fiona**: Better cross-platform wheel availability, especially on newer Python versions.

## Caching

- **Capabilities**: 24-hour TTL. GetCapabilities is slow (~180s).
- **Data**: 7-day TTL. Rasters and survey data don't change frequently.
- **Location**: `platformdirs.user_cache_dir("map_agent")` — OS-appropriate cache directory.
- **Key**: SHA-256 hash of (namespace, layer_id, bbox, time_params).

## Testing strategy

- **Unit tests**: Each tool module tested with `pytest-vcr` cassettes (recorded HTTP responses)
- **Integration tests**: MCP server round-trip tests
- **Live tests**: End-to-end against real geoserver (`@pytest.mark.network`)
- **Coverage target**: 80%+ on `src/map_agent/tools/` and `src/map_agent/core/`
