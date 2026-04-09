# Installation guide

## Prerequisites

1. **Python 3.10-3.12** (recommended). Python 3.13+ works but may require building some geo libraries from source.
2. **GDAL libraries** — needed for rasterio/rioxarray. Install via:
   - **macOS**: `brew install gdal`
   - **Ubuntu/Debian**: `sudo apt install gdal-bin libgdal-dev`
   - **Windows**: Install via [OSGeo4W](https://trac.osgeo.org/osgeo4w/) or use conda (see below)
   - **conda** (any OS): `conda install -c conda-forge gdal rasterio geopandas`
3. **Claude Code** — CLI, desktop app, or IDE extension. Get it at [claude.ai/code](https://claude.ai/code)

## Option A: pip install (recommended)

```bash
pip install map-agent
```

## Option B: From source (for contributors)

```bash
git clone https://github.com/ernes/map_ai_agents.git
cd map_ai_agents
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
# .venv\Scripts\activate       # Windows
pip install -e ".[dev]"
```

## Option C: conda (best for Windows / GDAL issues)

```bash
conda create -n map-agent python=3.12
conda activate map-agent
conda install -c conda-forge gdal rasterio geopandas rasterstats
pip install map-agent
```

## Configure Claude Code

### Step 1: Add the MCP server

```bash
claude mcp add map -- map-mcp
```

Or manually edit `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "map": {
      "command": "map-mcp",
      "args": []
    }
  }
}
```

If installed from source, use:

```json
{
  "mcpServers": {
    "map": {
      "command": "/path/to/.venv/bin/python",
      "args": ["-m", "map_agent.server"]
    }
  }
}
```

### Step 2: Install the slash commands

Copy the command files to your Claude Code commands directory:

```bash
# From the project directory
cp .claude/commands/map*.md ~/.claude/commands/
```

### Step 3: Verify

Restart Claude Code, then type:

```
/map-catalog Kenya
```

You should see a list of available MAP data layers.

## Troubleshooting

### "No module named 'rasterio'" or GDAL errors

GDAL is the most common installation issue. Solutions:
1. Use conda: `conda install -c conda-forge rasterio geopandas`
2. On Windows, install the GDAL wheel from [Christoph Gohlke's page](https://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal)
3. On macOS: `brew install gdal && pip install rasterio`

### MCP server not starting

Check the server starts manually:

```bash
python -m map_agent.server
```

If it hangs (waiting for stdio input), that's correct — it's waiting for Claude Code to connect.

### Slow first query

The first `catalog_search` call takes ~60-180 seconds because it fetches GetCapabilities from the MAP geoserver. Results are cached for 24 hours after that.

### Output directory

By default, outputs go to `./map_out/` in your working directory. Override with:

```bash
export MAP_AGENT_OUTPUT_DIR=/path/to/your/output
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `MAP_AGENT_OUTPUT_DIR` | `./map_out` | Where to save output files |
| `MAP_AGENT_CACHE_DIR` | OS cache dir | Where to cache geoserver responses |
| `MAP_AGENT_REQUEST_TIMEOUT` | `180` | Geoserver request timeout (seconds) |
| `MAP_AGENT_CAPABILITIES_TTL` | `86400` | Cache TTL for GetCapabilities (seconds) |
| `MAP_AGENT_DATA_TTL` | `604800` | Cache TTL for data downloads (seconds) |
