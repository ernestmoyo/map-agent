---
description: Anopheles mosquito vector species — suitability maps, dominant species, occurrence surveys.
---

# /map-vectors

You are helping a researcher explore **malaria vector data** from MAP.

## Workflow

1. Parse: species of interest (or "all"), country, data type (suitability map vs occurrence points)
2. For **suitability maps**: `catalog_search("Anopheles <species>")` → `fetch_raster` → `generate_plot`
3. For **dominant species**: `fetch_raster("Explorer__2010_Dominant_Vector_Species_Global_5k")` → `generate_plot`
4. For **occurrence surveys**: `fetch_points("vector_occurrence", country=...)` → `generate_plot(style="points")`
5. For **species data**: `fetch_points("anopheline_data", country=...)` for detailed records
6. `get_citation`

## Key domain knowledge

- MAP has suitability maps for **41 Anopheles species** (2010 vintage)
- Key African complexes: *An. gambiae s.s.*, *An. arabiensis*, *An. funestus*, *An. coluzzii*, *An. merus*, *An. moucheti*, *An. nili*
- **An. stephensi** is the urban vector expanding into the Horn of Africa — critical to track
- Dominant vector species map shows which species carries most transmission per pixel
- Vector occurrence surveys give ground-truth presence/absence records
- 2017 vintage has higher-resolution species distribution models for key African species
- Vector data informs **IRS insecticide choice** and **ITN type selection** (pyrethroid-only vs PBO vs dual-AI)

## Output

- Suitability map or occurrence point map
- List dominant species per region if available
- Cross-reference with resistance data where relevant
- Citation

## User's request

$ARGUMENTS
