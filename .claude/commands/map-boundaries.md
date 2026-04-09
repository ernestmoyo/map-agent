---
description: Export admin boundary shapefiles at any level — country, province, district, sub-district.
---

# /map-boundaries

You are helping a researcher get **admin boundary files** from MAP.

## Workflow

1. Parse: country, admin level (0-3), optional name filter
2. `get_boundaries(country, admin_level, name_filter)`
3. The response includes:
   - GeoJSON file path (ready for use in GIS tools)
   - List of all units at this level
   - List of sub-units at the next level
4. Present the results clearly and offer drill-down

## Key domain knowledge

- Admin levels: 0 = country, 1 = province/region, 2 = district/county, 3 = sub-district
- Not all countries have all 4 levels — the tool tells you what's available
- Latest vintage is **202403** (April 2024)
- Simplified versions exist (_mg_5k) for faster rendering — full versions for analysis
- The GeoJSON output works in QGIS, R, Python, and web mapping tools
- Boundary files are essential for zonal statistics and choropleth maps
- When a researcher asks for "shapefiles", provide the GeoJSON and note it's compatible with most GIS software

## Output

- File path to the GeoJSON
- Table of admin units with names
- Sub-units available for drill-down
- Bbox for the area

## User's request

$ARGUMENTS
