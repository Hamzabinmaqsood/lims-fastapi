from fastapi import HTTPException
from geoalchemy2.shape import to_shape
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations import sentinel
from app.modules.farms.service import get_farm
from app.modules.users.models import User


async def farm_index_png(db: AsyncSession, user: User, farm_id: int, index: str) -> bytes:
    farm = await get_farm(db, user, farm_id)  # 404 if not the owner's farm
    return await sentinel.fetch_index_png(to_shape(farm.boundary), index)

async def farm_index_stats(db: AsyncSession, user: User, farm_id: int) -> dict:
    farm = await get_farm(db, user, farm_id)
    stats = await sentinel.fetch_index_stats(to_shape(farm.boundary))
    if stats is None:
        raise HTTPException(404, "No cloud-free satellite image in the last 30 days.")
    return stats
