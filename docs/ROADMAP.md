# Roadmap

## Current status: Phase 1 complete (MCP server + slash commands)

### Phase 1: Foundation (COMPLETE)

- [x] MCP server with 7 tools (catalog, boundaries, raster, points, zonal stats, plot, citation)
- [x] 11 slash commands covering all MAP data domains
- [x] Core infrastructure (config, geoserver client factory, caching, models)
- [x] Hierarchical admin drill-down (country -> province -> district -> sub-district)
- [x] 45+ African country name aliases for user-friendly input
- [x] Publication-ready citations with DOI tracking
- [x] README with install instructions for self-service

### Phase 2: Hardening

- [ ] VCR cassette tests for all tool modules (80%+ coverage)
- [ ] Integration tests for MCP server round-trip
- [ ] Error handling: timeouts, missing layers, invalid country names, empty results
- [ ] Progress notifications for long WCS downloads
- [ ] Rate limiting and backoff for geoserver requests
- [ ] Validate GDAL/rasterio installation at startup with helpful error message

### Phase 3: Enhanced analysis

- [ ] Trend analysis automation (multi-year raster fetch + zonal stats pipeline)
- [ ] Intervention gap analysis (cross-reference prevalence with coverage)
- [ ] Population-weighted zonal statistics
- [ ] Risk stratification support (classify zones by burden thresholds)
- [ ] Support for MAP_READER pre-aggregated data in all relevant commands

### Phase 4: User data integration

- [ ] Custom shapefile upload for overlay with MAP surfaces
- [ ] CSV overlay (user's intervention data + MAP prevalence)
- [ ] DHIS2 data integration for routine data comparison
- [ ] Support for non-MAP rasters (user-provided GeoTIFFs)

### Phase 5: Distribution and community

- [ ] PyPI release
- [ ] GitHub Actions CI (lint + test, no network)
- [ ] Example Jupyter notebooks (tools layer walkthrough)
- [ ] CONTRIBUTING.md with development setup guide
- [ ] Tutorial: "SNT with map-agent" (prevalence -> stratification -> intervention targeting)
- [ ] Community feedback from NMCP users

### Future ideas

- Web-based version (Streamlit/Gradio) for non-Claude-Code users
- Temporal animation support (animated GIFs of prevalence over time)
- Integration with impact modelling tools
- Support for other disease maps (NTDs, TB)
- R package wrapper for researchers who prefer R
