from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.modules.crops.models import CropType
from app.modules.farms.service import get_farm
from app.modules.reports.pdf import build_pdf
from app.modules.satellite.service import farm_health
from app.modules.users.models import User


async def report_data(db: AsyncSession, user: User, farm_id: int) -> dict:
    farm = await get_farm(db, user, farm_id)          # ownership check first
    health = await farm_health(db, user, farm_id)     # stage, satellite values, texts
    crop = await db.get(CropType, farm.crop_id) if farm.crop_id else None
    return {
        **health,
        "farm": {
            "name": farm.name,
            "crop": crop.name if crop else None,
            "area_acres": float(farm.area_acres),
            "sowing_date": farm.sowing_date,
        },
    }


async def report_pdf(db: AsyncSession, user: User, farm_id: int) -> bytes:
    data = await report_data(db, user, farm_id)
    # ReportLab is CPU-heavy and blocking → run it in a thread, not on the event loop.
    return await run_in_threadpool(build_pdf, data)
