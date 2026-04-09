---
description: Browse available MAP data — search by country, topic, metric, or keyword.
---

# /map-catalog

You are helping a researcher discover **what MAP data is available**.

## Workflow

1. Call `catalog_search` with the user's query
2. Group results by workspace/category for clarity
3. Highlight the most relevant and latest vintage layers
4. Suggest which `/map-*` command to use for each category

## Presentation

Organize results into clear categories:

| Category | Slash command | What's available |
|---|---|---|
| Prevalence | `/map-prevalence` | Pf/Pv parasite rate rasters + surveys |
| Incidence | `/map-incidence` | Pf/Pv incidence rate/count + pre-aggregated stats |
| Mortality | `/map` | Pf mortality rate/count |
| Interventions | `/map-interventions` | ITN access/use, IRS, effective treatment |
| Vectors | `/map-vectors` | 41 Anopheles species suitability + occurrence |
| Blood disorders | `/map-blood` | G6PD, Duffy, HbS, HbC frequencies |
| Accessibility | `/map` | Travel time to healthcare, friction surfaces |
| Boundaries | `/map-boundaries` | Admin levels 0-3, multiple vintages |
| Surveys | `/map-surveys` | Pf/Pv PR surveys, vector occurrence |
| Pre-aggregated | `/map-incidence` | Admin-level case summaries (MAP_READER) |

## Key notes

- Latest raster vintage is typically **202508** (August 2025 release)
- Latest boundary vintage is **202403**
- Some layers are Africa-only (interventions), others are global (malaria, blood disorders)
- Multiple vintages exist — latest is usually best unless comparing methodology changes
- If the user asks about a specific country, also check what admin levels are available with `get_boundaries`

## User's request

$ARGUMENTS
