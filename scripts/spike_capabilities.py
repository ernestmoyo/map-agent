"""Phase-1 spike: prove we can talk to MAP geoserver from pure Python.

Run:
    python scripts/spike_capabilities.py

Outputs:
    scripts/_spike_out/capabilities_summary.txt
    scripts/_spike_out/spike_tanzania.png
"""
from __future__ import annotations

from pathlib import Path

from owslib.wcs import WebCoverageService
from owslib.wfs import WebFeatureService

# Hypothesis — confirm/correct during the spike.
GEOSERVER_ROOT = "https://data.malariaatlas.org/geoserver"
WCS_URL = f"{GEOSERVER_ROOT}/ows?service=WCS&version=2.0.1"
WFS_URL = f"{GEOSERVER_ROOT}/ows?service=WFS&version=2.0.0"

OUT = Path(__file__).parent / "_spike_out"
OUT.mkdir(exist_ok=True)


def dump_capabilities() -> None:
    summary: list[str] = []

    summary.append("=== WCS coverages ===")
    wcs = WebCoverageService(WCS_URL, version="2.0.1", timeout=180)
    for cov_id in sorted(wcs.contents):
        summary.append(f"  {cov_id}")

    summary.append("\n=== WFS feature types ===")
    wfs = WebFeatureService(WFS_URL, version="2.0.0", timeout=180)
    for ft in sorted(wfs.contents):
        summary.append(f"  {ft}")

    (OUT / "capabilities_summary.txt").write_text("\n".join(summary), encoding="utf-8")
    print(f"Wrote {OUT / 'capabilities_summary.txt'}")


def fetch_tanzania_pf_raster() -> None:
    """Pull a Pf parasite-rate raster clipped to Tanzania bbox and plot it."""
    import matplotlib.pyplot as plt
    import rioxarray  # noqa: F401  (registers .rio accessor)
    import xarray as xr

    # Tanzania rough bbox: lon 29.34..40.44, lat -11.75..-0.99
    tza_bbox = (29.34, -11.75, 40.44, -0.99)

    wcs = WebCoverageService(WCS_URL, version="2.0.1", timeout=180)
    # Pick the first coverage whose ID looks like a Pf parasite-rate layer.
    candidates = [c for c in wcs.contents if "Pf" in c and ("Parasite" in c or "PR" in c)]
    if not candidates:
        print("No obvious Pf PR coverage found — inspect capabilities_summary.txt and edit script.")
        return
    cov_id = candidates[0]
    print(f"Using coverage: {cov_id}")

    response = wcs.getCoverage(
        identifier=[cov_id],
        format="image/tiff",
        subsets=[("Long", tza_bbox[0], tza_bbox[2]), ("Lat", tza_bbox[1], tza_bbox[3])],
    )
    tif_path = OUT / "spike_tanzania.tif"
    tif_path.write_bytes(response.read())

    da = xr.open_dataarray(tif_path, engine="rasterio")
    fig, ax = plt.subplots(figsize=(6, 6))
    da.squeeze().plot(ax=ax)
    ax.set_title(f"{cov_id}\nTanzania")
    fig.savefig(OUT / "spike_tanzania.png", dpi=150, bbox_inches="tight")
    print(f"Wrote {OUT / 'spike_tanzania.png'}")


if __name__ == "__main__":
    dump_capabilities()
    fetch_tanzania_pf_raster()
