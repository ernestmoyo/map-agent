---
description: ITN, IRS, and ACT coverage maps — identify coverage gaps and intervention targeting opportunities.
---

# /map-interventions

You are helping a malaria researcher explore **intervention coverage data** from MAP.

## Workflow

1. Parse: intervention type (ITN/IRS/ACT), metric (access/use/use_rate), country, admin level
2. `get_boundaries` for the area
3. `catalog_search` for the intervention layer. Key layers:
   - ITN access: `Interventions__202508_Africa_Insecticide_Treated_Net_Access`
   - ITN use: `Interventions__202508_Africa_Insecticide_Treated_Net_Use`
   - ITN use rate: `Interventions__202508_Africa_Insecticide_Treated_Net_Use_Rate`
   - IRS coverage: `Interventions__202508_Africa_IRS_Coverage`
   - Effective treatment: `Interventions__202508_Global_Antimalarial_Effective_Treatment`
4. `fetch_raster` clipped to country
5. `compute_zonal_stats` by admin zones
6. `generate_plot` with style="choropleth" — use green colourmap for coverage
7. `get_citation`

## Key domain knowledge

- **ITN access** vs **use** vs **use rate**: Access = has a net. Use = slept under it. Use rate = use/access.
- **IRS coverage**: fraction of households sprayed with residual insecticide.
- **Effective treatment (ACT)**: fraction receiving artemisinin-based combination therapy.
- Coverage data is **Africa-only** for ITN/IRS. Effective treatment is global.
- Gaps between access and use indicate behavioural/awareness issues, not supply.
- Cross-reference with prevalence to identify areas with high burden AND low coverage — prime intervention targets.
- This data directly feeds into SNT (Sub-National Tailoring) for intervention planning.

## Output

- Coverage table by admin zone (sorted by lowest coverage first — gaps)
- Choropleth map
- Highlight zones below national average
- If the user provides prevalence context, identify "high burden, low coverage" zones
- Citation

## User's request

$ARGUMENTS
