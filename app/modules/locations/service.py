from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.locations.models import District, Locality, Province, Tehsil


async def list_provinces(db: AsyncSession) -> list[Province]:
    q = select(Province).order_by(Province.name)
    return list((await db.scalars(q)).all())


async def list_districts(db: AsyncSession, province_id: int) -> list[District]:
    q = select(District).where(District.province_id == province_id).order_by(District.name)
    return list((await db.scalars(q)).all())


async def list_tehsils(db: AsyncSession, district_id: int) -> list[Tehsil]:
    q = select(Tehsil).where(Tehsil.district_id == district_id).order_by(Tehsil.name)
    return list((await db.scalars(q)).all())


async def list_localities(db: AsyncSession, tehsil_id: int) -> list[Locality]:
    q = select(Locality).where(Locality.tehsil_id == tehsil_id).order_by(Locality.name)
    return list((await db.scalars(q)).all())
