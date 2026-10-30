from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.crops.models import CropSeason, CropType


async def list_seasons(db: AsyncSession) -> list[CropSeason]:
    return list((await db.scalars(select(CropSeason).order_by(CropSeason.name))).all())


async def list_crops(db: AsyncSession, season_id: int | None) -> list[CropType]:
    q = select(CropType).order_by(CropType.name)
    if season_id is not None:  # optional filter
        q = q.where(CropType.season_id == season_id)
    return list((await db.scalars(q)).all())
