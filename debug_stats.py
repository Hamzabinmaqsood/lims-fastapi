"""Print Sentinel Hub's raw statistics response for one farm (debug only)."""

import asyncio
import json

from geoalchemy2.shape import to_shape

from app.db.session import SessionLocal
from app.integrations.sentinel import _call, build_stats_request
from app.modules.farms.models import Farm
from app.modules.report_content.service import load_zones


async def main() -> None:
    async with SessionLocal() as db:
        farm = await db.get(Farm, 3)
        zones = await load_zones(db)

    print("ZONES LOADED:", {k: v for k, v in zones.items() if k == "NDVI"})

    req = build_stats_request(to_shape(farm.boundary), zones)
    print("\nWE ASKED FOR:", json.dumps(req["calculations"]["ndvi"]))

    r = await _call("/api/v1/statistics", req, "application/json")
    data = r.json()["data"]
    print("\nINTERVALS RETURNED:", len(data))
    print("\nNEWEST NDVI OUTPUT:", json.dumps(data[-1]["outputs"]["ndvi"], indent=1)[:1500])


asyncio.run(main())
