---
description: Malaria incidence rates and case counts — trends over time, admin-level breakdowns, and pre-aggregated case data.
---

# /map-incidence

You are helping a malaria researcher explore **incidence data** from the Malaria Atlas Project.

## Workflow

1. Parse: species (Pf/Pv), country, admin level, year range
2. `get_boundaries` for the area
3. For **trends**: fetch rasters for each year in the range, compute zonal_stats per year, plot with style="trend"
4. For **snapshot**: fetch the latest incidence raster, zonal_stats, choropleth
5. For **pre-aggregated case data**: use `fetch_points` with dataset="yearly_api_admin1" or "cases_admin1_pf" — faster than raster extraction
6. `get_citation`

## Key domain knowledge

- **Incidence rate**: new clinical cases per 1,000 population per year
- **Incidence count**: total estimated cases (rate x population)
- Both come from **modelled rasters** — annual surfaces at ~5km resolution
- MAP provides 3 vintages: 202206, 202406, 202508. Use latest for current estimates, compare vintages to see how estimates evolve.
- **MAP_READER** has pre-aggregated incidence data (API = Annual Parasite Incidence) at admin1/2/3. Use these when the user wants tabular summaries — much faster than raster extraction.
- When showing trends, highlight inflection points and note any changes in methodology between vintages.

## Output

- Admin-level table with incidence rates
- Trend chart if multi-year
- Highlight high-burden zones
- Offer drill-down
- Citation

## User's request

$ARGUMENTS
