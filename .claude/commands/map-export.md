---
description: Export a complete data package for a region — GeoTIFF, GeoJSON, CSV, PNG, and citation in one go.
---

# /map-export

You are helping a researcher **export a complete data package** for a specific area.

## Workflow

1. Parse: country, region/district, what data they want (or "everything")
2. `get_boundaries` for the area
3. For each relevant dataset:
   - `fetch_raster` (prevalence, incidence, intervention coverage)
   - `compute_zonal_stats` to get admin-level summaries
   - `generate_plot` for visualizations
4. `fetch_points` for survey data if relevant
5. `get_citation` for every dataset used
6. List all output files in a clear summary

## What to export by default

If the user doesn't specify, export:
- Latest Pf prevalence raster + zonal stats
- Latest Pf incidence raster + zonal stats
- ITN coverage (if Africa) + zonal stats
- Admin boundaries at the requested level
- Survey points for the area
- Choropleths for prevalence and incidence
- Citations for everything

## Output format

Present a clear inventory of all files:

```
./map_out/
  TZA_admin1_Mwanza.geojson          <- boundaries
  Malaria_Pf_Parasite_Rate_TZA.tif   <- prevalence raster
  Malaria_Pf_Incidence_Rate_TZA.tif  <- incidence raster
  zonal_stats_prevalence_admin1.csv   <- prevalence by district
  zonal_stats_incidence_admin1.csv    <- incidence by district
  choropleth_prevalence.png           <- prevalence map
  choropleth_incidence.png            <- incidence map
  pf_surveys_TZA.geojson              <- survey points
  citation_prevalence.json            <- citation
  citation_incidence.json             <- citation
```

Tell the user these files are ready for:
- QGIS / ArcGIS (GeoTIFF, GeoJSON)
- Excel / Stata / R (CSV)
- Reports / presentations (PNG)
- Publications (citation JSON)

## User's request

$ARGUMENTS
