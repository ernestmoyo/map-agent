# MAP glossary

> This file is loaded verbatim into the agent's system prompt. Keep it short, dense, and unambiguous.

## Parasites
- **Pf** — *Plasmodium falciparum*. Dominant in sub-Saharan Africa. Most lethal.
- **Pv** — *Plasmodium vivax*. Dominant outside Africa; relapsing.

## Metrics
- **PR (Parasite Rate)** — proportion of a sampled population that tests positive for parasites at one point in time. From **surveys**, expressed as a fraction or %. Often reported as `PfPR_2-10` (children aged 2–10).
- **Incidence** — new clinical cases per 1,000 population per year. From **modelled rasters**.
- **Mortality** — malaria deaths per 100,000 population per year. From **modelled rasters**.
- **Coverage** — fraction of population with access to an intervention (ITN, ACT, IRS).

## Data shapes
- **Survey points (WFS)** — geolocated PR or vector observations with year + sample size. Use for ground-truth dot maps.
- **Modelled rasters (WCS)** — annual gridded surfaces (~5 km). Use for trends, choropleths, country totals.

## Vectors
- 41 dominant *Anopheles* species; key complexes: *gambiae*, *funestus*, *arabiensis*, *stephensi* (urban, expanding).

## Geography
- Admin0 = country, Admin1 = province/region/state, Admin2 = district. Use ISO3 codes (TZA, KEN, NGA…).

## Heuristics for the agent
- "Trend" → annual rasters + zonal stats per year.
- "Where are the surveys?" → WFS PR points.
- "Which mosquitoes?" → WFS vector occurrence.
- "How many cases?" → incidence raster × population raster, summed by admin.
- Always cite the dataset version + DOI in the final answer.
