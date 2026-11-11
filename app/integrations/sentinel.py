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
    "SAVI": (["B04", "B08"], "1.5 * (s.B08 - s.B04) / (s.B08 + s.B04 + 0.5)"),
    "MSAVI": (["B04", "B08"],
              "(2 * s.B08 + 1 - Math.sqrt(Math.pow(2 * s.B08 + 1, 2) - 8 * (s.B08 - s.B04))) / 2"),
    "NDMI": (["B08", "B11"], "(s.B08 - s.B11) / (s.B08 + s.B11)"),
    "NDRE": (["B05", "B08"], "(s.B08 - s.B05) / (s.B08 + s.B05)"),
    "RECI": (["B05", "B08"], "s.B08 / s.B05 - 1"),
}


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


# ---------------------------------------------------------------- auth

_token: str | None = None
_token_expires_at = 0.0
_token_lock = asyncio.Lock()


async def _get_token(client: httpx.AsyncClient) -> str:
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

def image_size(poly: Polygon, longest_side: int = 512) -> tuple[int, int]:
    """Width/height that keep the farm's real shape (a degree of longitude shrinks near the poles)."""
    min_lng, min_lat, max_lng, max_lat = poly.bounds
    width_m = (max_lng - min_lng) * math.cos(math.radians((min_lat + max_lat) / 2))
    height_m = max_lat - min_lat
    if width_m >= height_m:
        return longest_side, max(1, round(longest_side * height_m / width_m))
    return max(1, round(longest_side * width_m / height_m)), longest_side


def build_request(poly: Polygon, index: str, days: int = 30) -> dict:
    width, height = image_size(poly)
    today = date.today()
    return {
        "input": {
            "bounds": {
                "geometry": mapping(poly),  # GeoJSON, (lng, lat) order
                "properties": {"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"},
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
        "evalscript": evalscript(index),
    }


async def fetch_index_png(poly: Polygon, index: str) -> bytes:
    """PNG of `index` over the polygon, from the least cloudy image of the last 30 days."""
    if not settings.SH_CLIENT_ID:
        raise HTTPException(503, "Satellite service is not configured.")
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            token = await _get_token(client)
            r = await client.post(
                f"{settings.SH_BASE_URL}/api/v1/process",
                json=build_request(poly, index),
                headers={"Authorization": f"Bearer {token}", "Accept": "image/png"},
            )
            r.raise_for_status()
            return r.content
    except httpx.HTTPStatusError as exc:
        logger.error("Sentinel Hub %s: %s", exc.response.status_code, exc.response.text[:500])
        raise HTTPException(502, "Satellite service returned an error.") from exc
    except httpx.HTTPError as exc:
        logger.exception("Sentinel Hub unreachable")
        raise HTTPException(502, "Satellite service is unreachable.") from exc
