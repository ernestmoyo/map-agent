---
description: Raw parasite rate survey data — geolocated PR observations with year, sample size, and prevalence.
---

# /map-surveys

You are helping a researcher access **survey point data** from MAP.

## Workflow

1. Parse: species (Pf/Pv), country, year range
2. `get_boundaries` for geographic context
3. `fetch_points` with the appropriate dataset:
   - "pf_surveys" for Pf parasite rate surveys
   - "pv_surveys" for Pv surveys
   - "pr_data" or "public_pf_data" for broader Explorer datasets
4. `generate_plot(style="points", boundaries_path=...)` to show survey locations
5. `get_citation`

## Key domain knowledge

- Survey data is **ground truth** — actual field measurements, not modelled estimates
- Each point has: location, year, sample size, prevalence (positive/examined)
- PfPR_2-10 is standardised to children aged 2-10 for comparability
- Survey density varies hugely — some countries have hundreds of surveys, others very few
- Gaps in survey coverage reveal where the modelled surfaces have the most uncertainty
- Survey data is what the modelled raster surfaces are trained on
- Researchers often want this to validate models or for meta-analyses

## Output

- Point map showing survey locations
- Summary table: number of surveys by year, geographic spread
- Sample of the raw data (first few rows)
- File path to the GeoJSON for further analysis
- Citation

## User's request

$ARGUMENTS
