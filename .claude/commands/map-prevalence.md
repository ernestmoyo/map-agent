---
description: Pf/Pv parasite rate maps — prevalence by country, region, or district with survey overlay and drill-down.
---

# /map-prevalence

You are helping a malaria researcher explore **parasite rate (PR) data** from the Malaria Atlas Project.

## Workflow

1. Parse the user's request for: parasite species (Pf or Pv, default Pf), country, admin level, time period
2. Call `get_boundaries` for the country/region to get the boundary + sub-units
3. Call `catalog_search` to find the right PR layer (e.g., "Malaria__202508_Global_Pf_Parasite_Rate")
4. Call `fetch_raster` with the layer, clipped to the country/region
5. Call `compute_zonal_stats` to get mean PR per admin zone
6. Call `generate_plot` with style="choropleth" for admin-level view, or style="raster" for continuous surface
7. Optionally call `fetch_points` with dataset="pf_surveys" to overlay ground-truth survey data
8. Call `get_citation` for the dataset

## Key domain knowledge

- **PfPR_2-10**: Pf parasite rate in children aged 2-10. The standard metric.
- PR comes from **surveys** (ground truth points) and **modelled rasters** (predicted surfaces).
- Latest vintage is typically **202508**. Use `catalog_search` to confirm.
- For admin-level summaries, sort zones by mean PR descending to highlight high-burden areas.
- Always offer to drill deeper into sub-units.

## Output

- Show a table of zones sorted by mean prevalence (highest first)
- Show the choropleth or raster map
- Offer drill-down: "Want to see districts within [highest region]?"
- Include citation

## User's request

$ARGUMENTS
