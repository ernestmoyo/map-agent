<p align="center">
  <h1 align="center">map-agent</h1>
  <p align="center">
    <strong>A malaria research workbench for Claude Code</strong><br>
    Query the Malaria Atlas Project — prevalence, incidence, interventions, vectors, and more — from country down to district, using natural language.
  </p>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> &middot;
  <a href="#commands">Commands</a> &middot;
  <a href="#data-available">Data</a> &middot;
  <a href="#architecture">Architecture</a> &middot;
  <a href="#contributing">Contributing</a>
</p>

> **Disclaimer:** This is an independent personal project. Data is sourced from MAP's public geoserver under [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/). All outputs must include the dataset citation.

---

```
/map "Pf prevalence in Rwanda by district"
```

`map-agent` is a Python [MCP server](https://modelcontextprotocol.io/) that connects [Claude Code](https://claude.ai/code) directly to MAP's geoserver. Researchers get maps, data exports, and publication-ready citations — no R, no GIS software required.

---

## Why

The [Malaria Atlas Project](https://malariaatlas.org/) produces some of the most critical geospatial data in global health: modelled malaria prevalence, incidence, mortality, intervention coverage, vector species distributions, and blood disorder frequencies — at ~5 km resolution across Africa and beyond.

This data powers **Sub-National Tailoring (SNT)** — the WHO-recommended process where countries move from national averages to targeted, evidence-based intervention packages at the sub-national level. Risk maps feed directly into National Strategic Plans (NSPs), Global Fund applications, and surveillance guidelines.

But accessing MAP data today requires R fluency via the [`malariaAtlas`](https://github.com/malaria-atlas-project/malariaAtlas) package. That creates a barrier for programme managers, epidemiologists, and decision-makers who need the data but don't work in R.

**`map-agent` removes that barrier.** It talks directly to MAP's geoserver (WCS for rasters, WFS for vector data) from pure Python, and exposes everything as Claude Code tools invokable with natural language.

---

## Quick start

### Prerequisites

| Requirement | Version | Notes |
|:---|:---|:---|
| Python | 3.10 - 3.12 | 3.13+ may need GDAL built from source |
| Claude Code | Latest | CLI, desktop app, or IDE extension |
| GDAL | System libs | Required for rasterio/geopandas ([install guide](docs/INSTALL.md)) |

### Option A: Install from source (recommended)

```bash
# 1. Clone the repo
git clone https://github.com/ernestmoyo/map-agent.git
cd map-agent

# 2. Create a virtual environment
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate

# 3. Install the package + dependencies
pip install -e ".[dev]"

# 4. Verify it works (this queries the MAP geoserver)
python -c "from map_agent.tools.catalog import search; print(search('Pf prevalence', 'raster')[:2])"
```

### Option B: pip install (once published)

```bash
pip install map-agent
```

### Register with Claude Code

The repo includes a `.mcp.json` that Claude Code auto-detects when you open the project directory. If you need to register manually:

```bash
# Linux/macOS
claude mcp add map -- .venv/bin/python -m map_agent.server

# Windows
claude mcp add map -- .venv\Scripts\python -m map_agent.server
```

### Install the slash commands

```bash
# Copy the /map-* commands to your Claude Code commands directory
# Linux/macOS:
cp .claude/commands/map*.md ~/.claude/commands/

# Windows (PowerShell):
Copy-Item .claude\commands\map*.md ~\.claude\commands\
```

### Verify everything works

Open Claude Code in the project directory and try:

```
/map-catalog Kenya
```

You should see a list of available MAP layers for Kenya.

---

## Commands

### The chain command (new — one call does everything)

For standard queries, use `/map` with natural language. The `analyze` tool runs the entire pipeline in a single call:

```
/map "pfpr Rwanda by district"
```

This executes: boundaries + raster + zonal stats + choropleth + citation — all at once.

**Metric shortcuts** you can use with analyze:

| Shortcut | What it fetches |
|:---|:---|
| `pfpr`, `prevalence` | Pf Parasite Rate |
| `incidence` | Pf Incidence Rate |
| `itn`, `itn_use` | ITN Use coverage |
| `irs` | Indoor Residual Spraying coverage |
| `g6pd` | G6PD deficiency allele frequency |
| `duffy` | Duffy negativity phenotype frequency |
| `sickle`, `hbs` | Sickle haemoglobin HbS |
| `gambiae`, `funestus` | Anopheles species suitability |
| `accessibility` | Travel time to healthcare |

### All slash commands

| Command | Research Workflow | Example |
|:---|:---|:---|
| `/map` | Natural language — routes to the right workflow | `/map "Pf trend in Zambia 2015-2020"` |
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

### @ref system

All tools return short reference codes that you can use in follow-up calls instead of long file paths:

```
catalog_search("Pf prevalence")  -> @L1, @L2, @L3 (layer IDs)
fetch_raster("@L1", "Kenya")     -> @R1 (raster file path)
get_boundaries("Kenya", 1)       -> @B1 (boundary file path)
compute_zonal_stats("@R1", "@B1") -> @S1 (stats CSV path)
```

Use `session_status` to see all active refs and current geographic focus.

### Always citable

Every output includes full citation metadata — dataset name, version, DOI, access date, and license (CC BY 3.0) — ready for publications, NSPs, and funding proposals.

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

## Architecture

```
Researcher in Claude Code
        |
        | /map "Pf prevalence in Rwanda by district"
        v
.claude/commands/map.md          <- domain knowledge + workflow heuristics
        |
        v
Claude interprets the question, calls MCP tools
        |
        |-- analyze ------------> one-call chain (all steps below)
        |-- catalog_search -----> WCS/WFS GetCapabilities
        |-- get_boundaries -----> WFS Admin_Units (drill-down)
        |-- fetch_raster -------> WCS GetCoverage (GeoTIFF)
        |-- fetch_points -------> WFS GetFeature (GeoJSON)
        |-- compute_zonal_stats > rasterio + numpy
        |-- generate_plot ------> matplotlib (PNG)
        |-- get_citation -------> DOI + version metadata
        |-- session_status -----> refs, focus, suggestions
        |
        v
./map_out/                       (gitignored — never committed)
    *.tif            GeoTIFF rasters
    *.geojson        Boundaries, survey points
    *.csv            Zonal statistics tables
    *.png            Choropleths, trend charts
    citation.json    DOI, version, access date
    usage_log.jsonl  Tool call analytics
```

### MCP tools

| Tool | Purpose |
|:---|:---|
| `analyze` | **Chain command** — runs the full pipeline in one call |
| `catalog_search` | Discover available MAP layers by keyword |
| `get_boundaries` | Admin boundaries + sub-unit discovery for drill-down |
| `fetch_raster` | Download modelled surfaces (prevalence, incidence, coverage, etc.) |
| `fetch_points` | Download survey points and pre-aggregated admin statistics |
| `compute_zonal_stats` | Summarize rasters by admin zones |
| `generate_plot` | Choropleths, heatmaps, trend lines, point maps |
| `get_citation` | Dataset version, DOI, and formatted citation |
| `session_status` | Active refs, geographic focus, usage suggestions |

### Project structure

```
src/map_agent/
    server.py              MCP server (FastMCP) — thin routing layer
    core/
        config.py          Pydantic Settings (env vars, paths, timeouts)
        geoserver.py       WCS/WFS client factory with connection reuse
        cache.py           On-disk response cache with TTL
        models.py          Data models (LayerInfo, BoundaryInfo, Citation)
        session.py         @ref system, geographic context, breadcrumb
        validate.py        Data validation (raster, boundary, zonal stats)
        analytics.py       Usage tracking + follow-up suggestions
    tools/
        analyze.py         Chain command — one call, full pipeline
        catalog.py         Layer discovery and search
        wcs.py             Raster fetch via WCS 2.0.1
        wfs.py             Survey/vector data via WFS 1.1.0
        admin.py           Admin boundaries + country resolution
        extract.py         Zonal statistics (rasterio + numpy)
        plot.py            Matplotlib visualizations (intelligent scale)
        citations.py       DOI/version tracking + CC BY 3.0 compliance
```

The tools layer is **pure Python** — usable from Jupyter notebooks or scripts without the MCP server:

```python
from map_agent.tools.admin import get_boundaries
from map_agent.tools.wcs import fetch_raster
from map_agent.tools.extract import zonal_stats

boundaries = get_boundaries("Rwanda", admin_level=2)
raster = fetch_raster("Malaria__202508_Global_Pf_Parasite_Rate", country="Rwanda")
stats = zonal_stats(raster["tif_path"], boundaries["geojson_path"])
```

### Intelligent choropleth scale

The plotting system automatically selects the right classification scheme:

| Data situation | Scale used | Why |
|:---|:---|:---|
| Prevalence data spanning WHO thresholds | Epidemiological breakpoints (1%, 5%, 10%, 25%, 50%) | Matches how malaria programmes think |
| Narrow data range (CV < 0.5) | Quantile classification | Maximises visual contrast |
| Wide data range | Natural breaks (Jenks) | Optimal class separation |
| Few zones (< 5) | Continuous linear | Classification not useful |

### Data validation

All tools automatically validate their output and include a `warnings` field:

- Raster bbox doesn't match expected area (country clipping failed)
- Global raster returned instead of country-clipped
- Zones with 100% nodata (raster doesn't overlap boundaries)
- Invalid boundary geometries
- Restricted survey records (flagged "No permission to release data")

---

## Configuration

All settings can be overridden via environment variables with the `MAP_AGENT_` prefix:

| Variable | Default | Description |
|:---|:---|:---|
| `MAP_AGENT_OUTPUT_DIR` | `./map_out` | Where generated files go |
| `MAP_AGENT_CACHE_DIR` | OS cache dir | On-disk response cache |
| `MAP_AGENT_REQUEST_TIMEOUT` | `180` | Geoserver request timeout (seconds) |
| `MAP_AGENT_DATA_TTL` | `604800` | Cache TTL for data (7 days) |
| `MAP_AGENT_CAPABILITIES_TTL` | `86400` | Cache TTL for catalog (24 hours) |

---

## Contributing

Contributions are welcome. This is an independent open-source project and we value input from the malaria research and geospatial communities.

### Getting started

```bash
# Fork + clone the repo
git clone https://github.com/<your-username>/map-agent.git
cd map-agent

# Set up dev environment
python -m venv .venv
source .venv/bin/activate        # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"

# Verify your setup
python -c "from map_agent.server import mcp; print('Server loads OK')"

# Run tests
pytest
```

### Areas where help is needed

- **Testing with more countries** — admin structures vary widely across Africa
- **Plot quality** — better cartographic aesthetics, legends, labels
- **Trend workflows** — multi-year analysis and time series automation
- **Custom shapefile support** — user-provided boundaries for non-MAP areas
- **Performance** — large raster tiling, concurrent downloads
- **Documentation** — tutorials, example notebooks, video walkthroughs
- **Translations** — for non-English-speaking NMCP teams

### Before submitting

- Open an issue to discuss large changes before writing code
- Keep PRs focused — one feature or fix per PR
- Run `ruff check src/` and `mypy src/` before submitting
- All data outputs go in `map_out/` (gitignored) — never commit data files

---

## Data license

- **This project's code**: [MIT License](LICENSE)
- **MAP data**: [Creative Commons Attribution 3.0 (CC BY 3.0)](https://creativecommons.org/licenses/by/3.0/)

You are free to use, share, and build on MAP data for any purpose (including commercial) as long as you provide attribution. The `get_citation` tool generates the required citation automatically.

Some survey point records are flagged "No permission to release data" by MAP. These records lack PR values and should not be redistributed individually. Aggregated outputs derived from the full dataset are permitted.

---

## Background

This project is built by [Ernest Moyo](https://www.linkedin.com/in/ernest-moyo-96aa3813/), Research Scientist and PhD Scholar.

The design is grounded in practical experience supporting National Malaria Control Programmes (NMCPs) across Southern Africa — including risk mapping, sub-national tailoring, and evidence-to-policy translation with NMCPs in **Namibia, Zimbabwe, Angola, Mozambique, and South Africa**.

> *"The distance between a risk map and a programme decision is not just technical — it is relational. It requires trust, shared ownership, and the humility to let country teams lead the interpretation of their own data."*

The goal is to make MAP's data as accessible as possible to the people who use it to make decisions that save lives.

---

## Acknowledgements

Built on top of the extraordinary work of the **[Malaria Atlas Project](https://malariaatlas.org/)** at the University of Oxford / Telethon Kids Institute. MAP's open data and geoserver infrastructure make this project possible.

This tool queries MAP's public geoserver under [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/). Please respect fair-use guidelines: use reasonable request rates, cache results locally, and always cite the datasets you use.

---

## License

MIT. See [LICENSE](LICENSE) for details.
