---
description: Blood disorder frequency maps — G6PD deficiency, Duffy negativity, sickle cell (HbS), HbC. Pharmacogenomics relevance.
---

# /map-blood

You are helping a researcher explore **blood disorder frequency data** from MAP.

## Workflow

1. Parse: disorder type (G6PD, Duffy, HbS/sickle, HbC), country/region
2. `catalog_search` to find the layer. Key layers:
   - `Blood_Disorders__201201_Global_G6PDd_Allele_Frequency`
   - `Blood_Disorders__201201_Global_Duffy_Negativity_Phenotype_Frequency`
   - `Blood_Disorders__201201_Global_Sickle_Haemoglobin_HbS_Allele_Frequency`
   - `Blood_Disorders__201201_Africa_HbC_Allele_Frequency`
3. `get_boundaries` if clipping to a country
4. `fetch_raster` → `compute_zonal_stats` → `generate_plot`
5. `get_citation`

## Key domain knowledge — pharmacogenomics relevance

- **G6PD deficiency**: Affects safety of **primaquine and tafenoquine** (8-aminoquinolines) used for Pv radical cure and Pf gametocyte clearance. High-frequency areas need point-of-care testing before prescribing.
- **Duffy negativity**: Near-fixation in sub-Saharan Africa. Protective against **Pv infection** — explains why Pv is rare in Africa.
- **Sickle cell trait (HbAS)**: Heterozygotes have ~50% reduced risk of severe Pf malaria. The balancing selection maintains HbS at high frequency in malaria-endemic areas.
- **HbC**: Similar protective effect to HbS, concentrated in West Africa (highest in Burkina Faso, Ghana, Mali).
- These maps are from 2012 vintage — the underlying genetic frequencies change slowly, so they remain relevant.
- Cross-referencing G6PD with Pv treatment areas is critical for **pharmacovigilance** and treatment guidelines.

## Output

- Raster or choropleth map of allele/phenotype frequency
- Admin-level summary table
- Note the pharmacogenomics implications
- Citation

## User's request

$ARGUMENTS
