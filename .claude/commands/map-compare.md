---
description: Side-by-side comparison — two years, two metrics, or two regions.
---

# /map-compare

You are helping a researcher make **comparisons** using MAP data.

## Workflow

Parse what's being compared:

### Two time periods (e.g., "Pf 2015 vs 2020 Tanzania")
1. `get_boundaries` for the country
2. `fetch_raster` + `compute_zonal_stats` for each year
3. Compute the difference (later year - earlier year) per zone
4. Present both tables and the change
5. `generate_plot` for each year
6. `get_citation`

### Two metrics (e.g., "prevalence vs ITN coverage Kenya")
1. `get_boundaries`
2. Fetch and compute zonal_stats for each metric
3. Present both tables side by side
4. Highlight mismatches (high prevalence + low coverage = priority)
5. `get_citation` for both datasets

### Two regions (e.g., "Zambia vs Zimbabwe Pf incidence")
1. `get_boundaries` for each country
2. Fetch and compute for each
3. Present comparison table
4. `get_citation`

## Key domain knowledge

- Temporal comparisons: be aware that different **vintages** (202206 vs 202508) may use updated methodology. Changes could reflect real trends OR improved modelling. Note this to the researcher.
- Metric comparisons: cross-referencing prevalence with intervention coverage is the foundation of **intervention gap analysis** in SNT.
- Regional comparisons: useful for **cross-border** dynamics (e.g., imported cases between Namibia and Angola).
- Always show both absolute values and the difference/ratio.

## Output

- Comparison table with both datasets
- Change/difference column
- Highlight notable patterns
- Maps for visual comparison
- Citations for all datasets used

## User's request

$ARGUMENTS
