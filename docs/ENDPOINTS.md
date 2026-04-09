# MAP geoserver endpoints

> ⚠️ Phase-1 spike will confirm/correct these. Treat as a starting hypothesis until `scripts/spike_capabilities.py` runs green.

## Base
- Public data portal: https://data.malariaatlas.org/
- Suspected geoserver root: `https://data.malariaatlas.org/geoserver`

## Services
| Service | URL pattern | Use |
|---|---|---|
| WMS | `…/geoserver/ows?service=WMS&version=1.3.0&request=GetCapabilities` | Tile previews |
| WCS | `…/geoserver/ows?service=WCS&version=2.0.1&request=GetCapabilities` | Raster download (modelled prevalence/incidence/mortality/intervention coverage) |
| WFS | `…/geoserver/ows?service=WFS&version=2.0.0&request=GetCapabilities` | Survey points (PR), vector occurrence |

## Layer themes (expected)
- `Malaria` workspace — Pf/Pv parasite rate, incidence, mortality (annual rasters)
- `Interventions` workspace — ITN coverage, ACT, IRS
- `Vector` workspace — dominant Anopheles species occurrence + suitability
- `Accessibility` workspace — travel time to healthcare
- `Explorer` workspace — curated layers exposed in the web data explorer

## Pagination / fair use
- Add `User-Agent: map-agent/<version> (+contact)` to every request.
- Local cache (see `cache.py`) keyed by full URL + params.
- Backoff on HTTP 429 / 5xx with `httpx` + jitter.

## TODO during spike
- [ ] Confirm geoserver root URL
- [ ] Record canonical layer IDs per theme
- [ ] Note any layers that require auth / API key
- [ ] Capture DOI metadata location (often in WCS `DescribeCoverage` keywords)
