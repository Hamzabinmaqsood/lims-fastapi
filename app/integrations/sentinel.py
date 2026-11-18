"""Sentinel Hub client: OAuth token + Process API (index images for a polygon)."""

import asyncio
import json
import logging
import math
import time
from datetime import date, timedelta

import httpx
from fastapi import HTTPException
from shapely.geometry import Polygon, mapping

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------- indices

# index → (bands it needs, formula in JavaScript; `s` is one pixel's band values)
FORMULAS: dict[str, tuple[list[str], str]] = {
    "NDVI": (["B04", "B08"], "(s.B08 - s.B04) / (s.B08 + s.B04)"),
    "SAVI": (["B04", "B08"], "1.428 * (s.B08 - s.B04) / (s.B08 + s.B04 + 0.428)"),
    "MSAVI": (["B04", "B08"],
              "(2 * s.B08 + 1 - Math.sqrt(Math.pow(2 * s.B08 + 1, 2) - 8 * (s.B08 - s.B04))) / 2"),
    "NDMI": (["B08", "B11"], "(s.B08 - s.B11) / (s.B08 + s.B11)"),
    "NDRE": (["B05", "B08"], "(s.B08 - s.B05) / (s.B08 + s.B05)"),
    "RECI": (["B04", "B05"], "s.B05 / s.B04 - 1"),
}

# Zone colour (from load_zones) → sub-map group. Change here if the senior wants other groups.
ZONE_GROUP = {"GREEN": "good", "LIGHT_GREEN": "good", "DARK_GREEN": "good",
              "YELLOW": "normal", "ORANGE": "normal", "RED": "bad"}
GROUP_CODE = {"good": 1, "normal": 2, "bad": 3}   # must match farm_mask.CLASSES


#Writes the small JavaScript program that runs on Sentinel Hub's servers to calculate and colour the index for each pixel.
def evalscript(index: str) -> str:
    """JavaScript that Sentinel Hub runs for every pixel: compute the index, colour it."""
    bands, formula = FORMULAS[index]
    return f"""//VERSION=3
function setup() {{
  return {{ input: [{{ bands: {json.dumps(bands + ["dataMask"])} }}], output: {{ bands: 4 }} }};
}}
const viz = new ColorRampVisualizer([
  [0.0, 0xd7191c], [0.2, 0xfdae61], [0.4, 0xffffbf], [0.6, 0xa6d96a], [0.8, 0x1a9641]
]);
function evaluatePixel(s) {{
  const value = {formula};
  return [...viz.process(value), s.dataMask];
}}"""


def _code(color: str) -> int:
    return GROUP_CODE[ZONE_GROUP.get(color.upper(), "normal")]


#Writes the script for the class map: one number per pixel (0 cloud/no data, 1 good, 2 normal, 3 bad), using the SAME zone limits as the percentages.
def class_evalscript(index: str, zone_list: list[tuple[str, float]]) -> str:
    bands, formula = FORMULAS[index]
    zones = sorted(zone_list, key=lambda z: z[1])            # lowest limit first
    checks = "\n".join(                                        # highest limit checked first
        f"  if (v >= {minimum}) return [{_code(color)}];" for color, minimum in reversed(zones[1:])
    )
    return f"""//VERSION=3
function setup() {{
  return {{
    input: [{{ bands: {json.dumps(bands + ["SCL", "dataMask"])} }}],
    output: {{ bands: 1, sampleType: "UINT8" }}
  }};
}}
const CLOUDY = [3, 8, 9, 10];
function evaluatePixel(s) {{
  if (!s.dataMask || CLOUDY.includes(s.SCL)) return [0];
  const v = {formula};
  if (!isFinite(v)) return [0];
{checks}
  return [{_code(zones[0][0])}];
}}"""


# ---------------------------------------------------------------- auth

_token: str | None = None
_token_expires_at = 0.0
_token_lock = asyncio.Lock()


async def _get_token(client: httpx.AsyncClient) -> str:    #Logs in to Sentinel Hub once and reuses the token until shortly before it expires. A lock makes sure the parallel downloads don't all log in.
    """Reuse the token until 60 s before it expires (don't log in on every request)."""
    global _token, _token_expires_at
    async with _token_lock:  # two requests at once must not both fetch a token
        if _token and time.time() < _token_expires_at - 60:
            return _token
        r = await client.post(settings.SH_TOKEN_URL, data={
            "grant_type": "client_credentials",
            "client_id": settings.SH_CLIENT_ID,
            "client_secret": settings.SH_CLIENT_SECRET,
        })
        r.raise_for_status()
        body = r.json()
        _token = body["access_token"]
        _token_expires_at = time.time() + body["expires_in"]
        return _token


# ---------------------------------------------------------------- request

def image_size(poly: Polygon, longest_side: int = 512) -> tuple[int, int]: #Picks the width and height so the image keeps the farm's real shape (it isn't stretched).
    """Width/height that keep the farm's real shape (a degree of longitude shrinks near the poles)."""
    min_lng, min_lat, max_lng, max_lat = poly.bounds
    width_m = (max_lng - min_lng) * math.cos(math.radians((min_lat + max_lat) / 2))
    height_m = max_lat - min_lat
    if width_m >= height_m:
        return longest_side, max(1, round(longest_side * height_m / width_m))
    return max(1, round(longest_side * width_m / height_m)), longest_side


#Builds the request: the farm's bounding box, the last 30 days, the least cloudy image, and the image size.
#`script` replaces the colour script (used for the class map); everything else stays identical so pixels line up.
def build_request(poly: Polygon, index: str, days: int = 30, script: str | None = None) -> dict:
    width, height = image_size(poly)
    today = date.today()
    return {
        "input": {
            "bounds": {
                # Bounding box, not the polygon: Sentinel Hub's Process API currently
                # crashes on polygon geometry (HV000028, Nov 2026). The Statistical API
                # still gets the exact polygon.
                "bbox": list(poly.bounds),  # [min_lng, min_lat, max_lng, max_lat]
                "properties": {"crs": CRS84},
            },
            "data": [{
                "type": "sentinel-2-l2a",
                "dataFilter": {
                    "timeRange": {
                        "from": f"{today - timedelta(days=days)}T00:00:00Z",
                        "to": f"{today}T23:59:59Z",
                    },
                    "maxCloudCoverage": 30,
                    "mosaickingOrder": "leastCC",  # pick the least cloudy picture
                },
            }],
        },
        "output": {
            "width": width,
            "height": height,
            "responses": [{"identifier": "default", "format": {"type": "image/png"}}],
        },
        "evalscript": script or evalscript(index),
    }


CRS84 = "http://www.opengis.net/def/crs/OGC/1.3/CRS84"


#Sends the request with a valid token, retries once on server errors, and turns failures into a clean 502.
async def _call(path: str, payload: dict, accept: str) -> httpx.Response:
    """POST to Sentinel Hub with a valid token. Turns failures into clean 502s."""
    if not settings.SH_CLIENT_ID:
        raise HTTPException(503, "Satellite service is not configured.")
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            token = await _get_token(client)
            for attempt in range(2):  # one retry: a 5xx is often temporary
                r = await client.post(
                    f"{settings.SH_BASE_URL}{path}",
                    json=payload,
                    headers={"Authorization": f"Bearer {token}", "Accept": accept},
                )
                if r.status_code < 500 or attempt == 1:
                    break
                await asyncio.sleep(1)
            r.raise_for_status()
            return r
    except httpx.HTTPStatusError as exc:
        logger.error("Sentinel Hub %s: %s", exc.response.status_code, exc.response.text[:500])
        raise HTTPException(502, "Satellite service returned an error.") from exc
    except httpx.HTTPError as exc:
        logger.exception("Sentinel Hub unreachable")
        raise HTTPException(502, "Satellite service is unreachable.") from exc


async def fetch_index_png(poly: Polygon, index: str, script: str | None = None) -> bytes:     #Downloads one index image (coloured, or the class map when `script` is given).
    """PNG of `index` over the polygon, from the least cloudy image of the last 30 days."""
    r = await _call("/api/v1/process", build_request(poly, index, script=script), "image/png")
    return r.content


# ---------------------------------------------------------------- statistics

def stats_evalscript() -> str:    #Writes the script that calculates all 6 indices at once and hides cloudy pixels.
    """All 6 indices in ONE request; cloudy pixels are masked out."""
    outputs = ", ".join(
        f'{{ id: "{name.lower()}", bands: 1, sampleType: "FLOAT32" }}' for name in FORMULAS
    )
    values = "\n".join(
        f"    {name.lower()}: [{formula}]," for name, (_, formula) in FORMULAS.items()
    )
    return f"""//VERSION=3
function setup() {{
  return {{
    input: [{{ bands: ["B04", "B05", "B08", "B11", "SCL", "dataMask"] }}],
    output: [{outputs}, {{ id: "dataMask", bands: 1 }}]
  }};
}}
// SCL = Sentinel-2's own pixel classification. Ignore: 3 cloud shadow, 8/9 cloud, 10 cirrus.
const CLOUDY = [3, 8, 9, 10];
function evaluatePixel(s) {{
  const clear = CLOUDY.includes(s.SCL) ? 0 : 1;
  return {{
{values}
    dataMask: [s.dataMask * clear]
  }};
}}"""


def build_stats_request(poly: Polygon, zones: dict, days: int = 30) -> dict:  #Builds the statistics request: the exact farm shape, 30 days, one result per satellite pass.
    # 10 m pixels expressed in degrees (1° latitude ≈ 111.32 km; longitude shrinks by cos(lat))
    res_lat = 10 / 111_320
    res_lng = res_lat / math.cos(math.radians(poly.centroid.y))
    today = date.today()
    return {
        "input": {
            "bounds": {"geometry": mapping(poly), "properties": {"crs": CRS84}},
            "data": [{"type": "sentinel-2-l2a", "dataFilter": {"maxCloudCoverage": 50}}],
        },
        "aggregation": {
            "timeRange": {
                "from": f"{today - timedelta(days=days)}T00:00:00Z",
                "to": f"{today}T23:59:59Z",
            },
            "aggregationInterval": {"of": "P1D"},
            "evalscript": stats_evalscript(),
            "resx": res_lng,
            "resy": res_lat,
        },
        "calculations": {   # ← top level, same level as "input" and "aggregation"
            name.lower(): {"histograms": {"default": {"bins": zone_edges(zones[name])}}}
            for name in FORMULAS
            if name in zones
        },
    }


def latest_clear_stats(body: dict, zones: dict, min_clear: float = 0.5) -> dict | None:       #Picks the newest day with at least half the farm cloud-free and extracts its averages and percentages.
    """Newest satellite pass where at least half the farm's pixels were cloud-free."""
    for item in sorted(body.get("data", []), key=lambda d: d["interval"]["from"], reverse=True):
        outputs = item["outputs"]
        first = outputs["ndvi"]["bands"]["B0"]["stats"]
        total, missing = first["sampleCount"], first["noDataCount"]
        if total == 0 or (total - missing) / total < min_clear:
            continue  # too cloudy that day

        zone_pct = {}
        for name, zone_list in zones.items():
            bins = outputs[name.lower()]["bands"]["B0"].get("histogram", {}).get("bins", [])
            counts = [b["count"] for b in bins]
            valid = sum(counts)
            if valid and len(counts) == len(zone_list):
                zone_pct[name] = {
                    color: round(100 * count / valid, 1)
                    for (color, _), count in zip(zone_list, counts)
                }

        return {
            "date": item["interval"]["from"][:10],
            "clear_pct": round(100 * (total - missing) / total),
            "indices": {
                name: round(outputs[name.lower()]["bands"]["B0"]["stats"]["mean"], 3)
                for name in FORMULAS
            },
            "zones": zone_pct,
        }
    return None


async def fetch_index_stats(poly: Polygon, zones: dict, days: int = 30) -> dict | None:  #Gets the farm's average value and colour percentages for each index from the satellite.
    r = await _call("/api/v1/statistics", build_stats_request(poly, zones, days), "application/json")
    return latest_clear_stats(r.json(), zones)


def zone_edges(zone_list: list[tuple[str, float]]) -> list[float]:  #Turns the colour thresholds into histogram boundaries, so the satellite counts pixels per colour.
    """[("RED",-1),("YELLOW",0.4),("LIGHT_GREEN",0.65),("GREEN",0.8)] → [-1000, 0.4, 0.65, 0.8, 1000].
    Wide outer edges so no pixel ever falls outside a bin."""
    return [-1000.0] + [value for _, value in zone_list[1:]] + [1000.0]


# ---------------------------------------------------------------- many images at once

#Runs several downloads at once; a failed one becomes None instead of breaking the rest.
async def _gather_named(jobs: dict) -> dict[str, bytes | None]:
    names = list(jobs)
    results = await asyncio.gather(*jobs.values(), return_exceptions=True)
    out: dict[str, bytes | None] = {}
    for name, result in zip(names, results):
        if isinstance(result, Exception):
            logger.warning("Image for %s failed: %s", name, result)
            out[name] = None
        else:
            out[name] = result
    return out


async def fetch_all_index_pngs(poly: Polygon) -> dict[str, bytes | None]: #All 6 coloured images at once.
    return await _gather_named({name: fetch_index_png(poly, name) for name in FORMULAS})


async def fetch_all_class_pngs(poly: Polygon, zones: dict) -> dict[str, bytes | None]: #All class maps at once (only indices that have zones).
    return await _gather_named({
        name: fetch_index_png(poly, name, class_evalscript(name, zones[name]))
        for name in FORMULAS if name in zones
    })
