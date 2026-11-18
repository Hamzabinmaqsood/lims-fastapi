import asyncio

from geoalchemy2.shape import to_shape
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.integrations import sentinel
from app.modules.crops.models import CropType
from app.modules.farms.service import get_farm
from app.modules.report_content.service import load_zones
from app.modules.reports.pdf import build_pdf
from app.modules.satellite.service import check_ready, farm_health_for
from app.modules.users.models import User


# Gathers everything the PDF needs: farm, health, images, class maps, crop name.
async def report_data(db: AsyncSession, user: User, farm_id: int) -> dict:
    farm = await get_farm(db, user, farm_id)  # ownership check, ONE query
    check_ready(farm)                         # cheap 400s before any satellite call
    poly = to_shape(farm.boundary)            # stored PostGIS boundary → Shapely polygon
    zones = await load_zones(db)              # colour limits; loaded BEFORE downloads start (one session, one query at a time)

    # Start BOTH sets of images (6 coloured + 6 class maps) in the background...
    downloads = asyncio.gather(
        sentinel.fetch_all_index_pngs(poly),
        sentinel.fetch_all_class_pngs(poly, zones),
    )
    try:
        # ...while the DB queries + statistics run here.
        health = await farm_health_for(db, farm)
    except BaseException:
        downloads.cancel()  # health failed → don't leave downloads running
        raise
    images, class_images = await downloads

    crop = await db.get(CropType, farm.crop_id) if farm.crop_id else None
    return {
        **health,
        "images": images,
        "class_images": class_images,
        "farm": {
            "name": farm.name,
            "crop": crop.name if crop else None,
            "area_acres": float(farm.area_acres),
            "sowing_date": farm.sowing_date,
            "ring": [list(p) for p in poly.exterior.coords],  # [lng, lat] points for the outline
        },
    }


# Collects the report data, then builds the PDF in a background thread.
async def report_pdf(db: AsyncSession, user: User, farm_id: int) -> bytes:
    data = await report_data(db, user, farm_id)
    return await run_in_threadpool(build_pdf, data)
