import asyncio

from geoalchemy2.shape import to_shape
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.integrations import sentinel
from app.modules.crops.models import CropType
from app.modules.farms.service import get_farm
from app.modules.reports.pdf import build_pdf
from app.modules.satellite.service import check_ready, farm_health_for
from app.modules.users.models import User


async def report_data(db: AsyncSession, user: User, farm_id: int) -> dict:
    farm = await get_farm(db, user, farm_id)  # ownership check, ONE query
    check_ready(farm)                         # cheap 400s before any satellite call
    poly = to_shape(farm.boundary)

    # Start downloading the 6 images in the background...
    images_task = asyncio.create_task(sentinel.fetch_all_index_pngs(poly))
    try:
        # ...while the DB queries + statistics run here.
        health = await farm_health_for(db, farm)
    except BaseException:
        images_task.cancel()  # health failed → don't leave downloads running
        raise
    images = await images_task

    crop = await db.get(CropType, farm.crop_id) if farm.crop_id else None
    return {
        **health,
        "images": images,
        "farm": {
            "name": farm.name,
            "crop": crop.name if crop else None,
            "area_acres": float(farm.area_acres),
            "sowing_date": farm.sowing_date,
            "ring": [list(p) for p in poly.exterior.coords],  # [lng, lat] points for the outline
        },
    }


async def report_pdf(db: AsyncSession, user: User, farm_id: int) -> bytes:
    data = await report_data(db, user, farm_id)
    return await run_in_threadpool(build_pdf, data)
