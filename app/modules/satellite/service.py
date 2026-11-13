from fastapi import HTTPException
from geoalchemy2.shape import to_shape
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations import sentinel
from app.modules.farms.service import get_farm
from app.modules.users.models import User

from datetime import date
from app.modules.growth_stages.service import stage_for_day

from app.modules.satellite.health import add_zones, assess

from app.core.time import today_pk

from app.modules.report_content.render import attach_texts
from app.modules.report_content.service import load_texts, load_zones

from app.modules.farms.models import Farm

async def farm_index_png(db: AsyncSession, user: User, farm_id: int, index: str) -> bytes:
    farm = await get_farm(db, user, farm_id)  # 404 if not the owner's farm
    return await sentinel.fetch_index_png(to_shape(farm.boundary), index)

async def farm_index_stats(db: AsyncSession, user: User, farm_id: int) -> dict:
    farm = await get_farm(db, user, farm_id)
    zones = await load_zones(db)
    stats = await sentinel.fetch_index_stats(to_shape(farm.boundary), zones)
    if stats is None:
        raise HTTPException(404, "No cloud-free satellite image in the last 30 days.")
    return stats


async def farm_health(db: AsyncSession, user: User, farm_id: int) -> dict:
    farm = await get_farm(db, user, farm_id)

    # Cheap checks FIRST, before the slow, paid satellite call.
    if farm.crop_id is None or farm.sowing_date is None:
        raise HTTPException(400, "Set the farm's crop and sowing date first.")
    days = (today_pk() - farm.sowing_date).days
    if days < 0:
        raise HTTPException(400, "Sowing date is in the future.")
    stage = await stage_for_day(db, farm.crop_id, days)

    zones = await load_zones(db)
    stats = await sentinel.fetch_index_stats(to_shape(farm.boundary), zones)
    if stats is None:
        raise HTTPException(404, "No cloud-free satellite image in the last 30 days.")

    return {
        "farm_id": farm.id,
        "days_since_sowing": days,
        "stage": None if stage is None else
            {"name": stage.name, "day_from": stage.day_from, "day_to": stage.day_to},
        "satellite_date": stats["date"],
        "clear_pct": stats["clear_pct"],
        "indices": attach_texts(add_zones(assess(stats["indices"], stage.ranges if stage else []), stats["zones"]),*await load_texts(db),),
    }


def check_ready(farm: Farm) -> int:
    """Cheap checks; returns the crop's age in days."""
    if farm.crop_id is None or farm.sowing_date is None:
        raise HTTPException(400, "Set the farm's crop and sowing date first.")
    days = (today_pk() - farm.sowing_date).days
    if days < 0:
        raise HTTPException(400, "Sowing date is in the future.")
    return days


async def farm_health_for(db: AsyncSession, farm: Farm) -> dict:
    """Health for an already-loaded (and ownership-checked) farm."""
    days = check_ready(farm)
    stage = await stage_for_day(db, farm.crop_id, days)

    zones = await load_zones(db)
    stats = await sentinel.fetch_index_stats(to_shape(farm.boundary), zones)
    if stats is None:
        raise HTTPException(404, "No cloud-free satellite image in the last 30 days.")

    return {
        "farm_id": farm.id,
        "days_since_sowing": days,
        "stage": None if stage is None else
            {"name": stage.name, "day_from": stage.day_from, "day_to": stage.day_to},
        "satellite_date": stats["date"],
        "clear_pct": stats["clear_pct"],
        "indices": attach_texts(
            add_zones(assess(stats["indices"], stage.ranges if stage else []), stats["zones"]),
            *await load_texts(db),
        ),
    }


async def farm_health(db: AsyncSession, user: User, farm_id: int) -> dict:
    return await farm_health_for(db, await get_farm(db, user, farm_id))
