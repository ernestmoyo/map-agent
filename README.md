<p align="center">
  <h1 align="center">map-agent</h1>
  <p align="center">
    <strong>A malaria research workbench for Claude Code</strong><br>
    Query the Malaria Atlas Project — prevalence, incidence, interventions, vectors, and more — from country down to district, using natural language.
  </p>
</p>

<p align="center">
  <a href="#installation">Installation</a> &middot;
  <a href="#commands">Commands</a> &middot;
  <a href="#data-available">Data</a> &middot;
  <a href="#architecture">Architecture</a> &middot;
  <a href="#contributing">Contributing</a>
</p>

---

```
/map "Pf prevalence trend in Tanzania by region, 2015-2020"
```

`map-agent` is a Python [MCP server](https://modelcontextprotocol.io/) that connects [Claude Code](https://claude.ai/code) directly to MAP's geoserver. Researchers get maps, data exports, and publication-ready citations — no R, no GIS software required.

---

## Why

The [Malaria Atlas Project](https://malariaatlas.org/) produces some of the most critical geospatial data in global health: modelled malaria prevalence, incidence, mortality, intervention coverage, vector species distributions, and blood disorder frequencies — at ~5 km resolution across Africa and beyond.

This data powers **Sub-National Tailoring (SNT)** — the WHO-recommended process where countries move from national averages to targeted, evidence-based intervention packages at the sub-national level. Risk maps feed directly into National Strategic Plans (NSPs), Global Fund applications, and surveillance guidelines.

But accessing MAP data today requires R fluency via the [`malariaAtlas`](https://github.com/malaria-atlas-project/malariaAtlas) package. That creates a barrier for programme managers, epidemiologists, and decision-makers who need the data but don't work in R.

**`map-agent` removes that barrier.** It talks directly to MAP's geoserver (WCS for rasters, WFS for vector data) from pure Python, and exposes everything as Claude Code tools invokable with natural language.

---

## Commands

| Command | Research Workflow | Example |
|:---|:---|:---|
| `/map` | Natural language — routes to the right workflow | `/map "Pf trend in Zambia Southern Province 2015-2020"` |
| `/map-prevalence` | Pf/Pv parasite rate maps with survey overlay | `/map-prevalence Tanzania admin1` |
| `/map-incidence` | Clinical incidence rates + time trends | `/map-incidence Kenya 2018-2022` |
| `/map-interventions` | ITN, IRS, ACT coverage — identify gaps | `/map-interventions Mozambique ITN` |
| `/map-vectors` | Dominant Anopheles species + suitability | `/map-vectors Nigeria` |
| `/map-boundaries` | Export admin shapefiles at any level | `/map-boundaries DRC admin2` |
| `/map-surveys` | Raw parasite rate survey points | `/map-surveys Ethiopia Pf 2015-2022` |
| `/map-blood` | Blood disorder frequencies (G6PD, Duffy, HbS, HbC) | `/map-blood G6PD West Africa` |
| `/map-compare` | Side-by-side: two years, metrics, or regions | `/map-compare Pf 2015 vs 2020 Tanzania` |
| `/map-catalog` | Browse available data for a country or topic | `/map-catalog Zambia` |
| `/map-export` | Package data as CSV + GeoJSON + citation | `/map-export Sengerema district` |

### Hierarchical drill-down

Every geographic command supports progressive drilling through a country's admin structure:

```
/map-prevalence Zambia
  -> Country-level choropleth by province
  -> "Drill into Southern Province?"
  -> Province-level choropleth by district  
  -> "Drill into Livingstone?"
  -> District-level detail + data export
```

Admin structures vary by country (some have 2 levels, some 4). The tool discovers what's available and presents your options.

### Always citable

Every output includes full citation metadata — dataset name, version, DOI, and access date — ready for publications, NSPs, and funding proposals.

---

## Data available

`map-agent` exposes MAP's full public geoserver catalog — **150+ raster layers** and **80+ vector datasets**:

| Category | What's Included | Data Type |
|:---|:---|:---|
| **Malaria** | Pf/Pv parasite rate, incidence (count + rate), mortality | Rasters (annual, multiple vintages) |
| **Interventions** | ITN access/use/use rate, IRS coverage, effective treatment | Rasters (Africa) |
| **Vectors** | 41 *Anopheles* species suitability, dominant vector surveys | Rasters + point data |
| **Blood disorders** | Duffy negativity, G6PD deficiency, sickle cell (HbS), HbC | Rasters (global) |
| **Accessibility** | Travel time to healthcare, friction surfaces | Rasters (global) |
| **Admin boundaries** | Country to sub-district (levels 0-3), multiple vintages | GeoJSON |
| **Survey data** | Pf/Pv parasite rate surveys, vector occurrence surveys | Point data |
| **Pre-aggregated** | Confirmed cases by admin1/2/3, age bands, yearly summaries | Tabular (MAP_READER) |

---

## Installation

### Prerequisites

- **Python 3.10+** (3.10-3.12 recommended; 3.13+ may need GDAL built from source)
- **[Claude Code](https://claude.ai/code)** — CLI, desktop app, or IDE extension
- **GDAL libraries** — for geospatial processing (see [detailed install guide](docs/INSTALL.md))

### Quick start

```bash
# 1. Install the package
pip install map-agent

# 2. Register the MCP server with Claude Code
claude mcp add map -- map-mcp

# 3. Install the slash commands
cp .claude/commands/map*.md ~/.claude/commands/

# 4. Open Claude Code and try it
#    /map-catalog Kenya
```

### From source

```bash
git clone https://github.com/ernestmoyo/map-agent.git
cd map-agent
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
# .venv\Scripts\activate       # Windows
pip install -e ".[dev]"
```

For GDAL/Windows troubleshooting and conda-based setup, see **[docs/INSTALL.md](docs/INSTALL.md)**.

---

## Architecture

```
Researcher in Claude Code
        |
        | /map "Pf prevalence in Tanzania by region"
        v
.claude/commands/map.md          <- domain knowledge + workflow heuristics
        |
        v
Claude interprets the question, calls MCP tools
        |
        |-- catalog_search -----> WCS/WFS GetCapabilities
        |-- get_boundaries -----> WFS Admin_Units (drill-down)
        |-- fetch_raster -------> WCS GetCoverage (GeoTIFF)
        |-- fetch_points -------> WFS GetFeature (GeoJSON)
        |-- compute_zonal_stats > rasterstats
        |-- generate_plot ------> matplotlib (PNG)
        |-- get_citation -------> DOI + version metadata
        |
        v
./map_out/
    *.tif            GeoTIFF rasters
    *.geojson        Boundaries, survey points
    *.csv            Zonal statistics tables
    *.png            Choropleths, trend charts
    citation.json    DOI, version, access date
```

### MCP tools

| Tool | Purpose |
|:---|:---|
| `catalog_search` | Discover available MAP layers by keyword |
| `get_boundaries` | Admin boundaries + sub-unit discovery for drill-down |
| `fetch_raster` | Download modelled surfaces (prevalence, incidence, coverage, etc.) |
| `fetch_points` | Download survey points and pre-aggregated admin statistics |
| `compute_zonal_stats` | Summarize rasters by admin zones |
| `generate_plot` | Choropleths, heatmaps, trend lines, point maps |
| `get_citation` | Dataset version, DOI, and formatted citation |

### Project structure

```
src/map_agent/
    server.py              MCP server (FastMCP) — thin routing layer
    core/
        config.py          Pydantic Settings (env vars, paths, timeouts)
        geoserver.py       WCS/WFS client factory with connection reuse
        cache.py           On-disk response cache with TTL
        models.py          Data models
    tools/
        catalog.py         Layer discovery and search
        wcs.py             Raster fetch via WCS 2.0.1
        wfs.py             Survey/vector data via WFS 2.0.0
        admin.py           Admin boundaries + country resolution
        extract.py         Zonal statistics (rasterstats)
        plot.py            Matplotlib visualizations
        citations.py       DOI/version tracking
```

The tools layer is **pure Python** — usable from Jupyter notebooks or scripts without the MCP server.

---

## Contributing

Contributions are welcome. This is an open-source project and we value input from the malaria research and geospatial communities.

**Areas where help is needed:**

- Testing with additional countries and admin structures across Africa
- Improving plot aesthetics and cartographic quality
- Adding support for custom shapefiles and user data overlays
- Performance optimization for large raster downloads
- Documentation, tutorials, and example workflows
- Translations for non-English-speaking NMCP teams

Please open an issue to discuss before submitting large changes.

---

## Background

This project is built by [Ernest Moyo](https://www.linkedin.com/in/ernest-moyo-96aa3813/), Research Scientist at the Malaria Atlas Project and PhD Scholar at the Vector Atlas / Nelson Mandela African Institute of Science and Technology (NM-AIST), Tanzania.

The design is grounded in practical experience supporting National Malaria Control Programmes (NMCPs) across Southern Africa — including risk mapping, sub-national tailoring, and evidence-to-policy translation with NMCPs in **Namibia, Zimbabwe, Angola, Mozambique, and South Africa**. Previously Regional Epidemiologist at the **Clinton Health Access Initiative (CHAI)**.

> *"The distance between a risk map and a programme decision is not just technical — it is relational. It requires trust, shared ownership, and the humility to let country teams lead the interpretation of their own data."*

The goal is to make MAP's data as accessible as possible to the people who use it to make decisions that save lives.

---

## Acknowledgements

Built on top of the extraordinary work of the **[Malaria Atlas Project](https://malariaatlas.org/)** at the University of Oxford / Telethon Kids Institute. MAP's open data and geoserver infrastructure make this project possible.

This tool queries MAP's public geoserver. Please respect fair-use guidelines: use reasonable request rates, cache results locally, and always cite the datasets you use.

---

## License

MIT. See [LICENSE](LICENSE) for details.
