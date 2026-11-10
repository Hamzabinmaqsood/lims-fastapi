from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.crops.models import CropType
from app.modules.growth_stages.models import GrowthStage, IndexRange
from app.modules.growth_stages.schemas import StageIn


async def list_stages(db: AsyncSession, crop_id: int) -> list[GrowthStage]:
    q = select(GrowthStage).where(GrowthStage.crop_id == crop_id).order_by(GrowthStage.day_from)
    return list((await db.scalars(q)).all())


async def _validate(db: AsyncSession, data: StageIn, exclude_id: int | None = None) -> None:
    if await db.get(CropType, data.crop_id) is None:
        raise HTTPException(400, {"crop_id": ["Invalid crop."]})

    # Two stages of the same crop must not cover the same day.
    overlap = select(GrowthStage.name).where(
        GrowthStage.crop_id == data.crop_id,
        GrowthStage.day_from <= data.day_to,
        GrowthStage.day_to >= data.day_from,
    )
    if exclude_id is not None:
        overlap = overlap.where(GrowthStage.id != exclude_id)
    clash = await db.scalar(overlap)
    if clash:
        raise HTTPException(400, {"day_from": [f"Days overlap with stage '{clash}'."]})


async def get_stage(db: AsyncSession, stage_id: int) -> GrowthStage:
    stage = await db.get(GrowthStage, stage_id)
    if stage is None:
        raise HTTPException(404, "Growth stage not found.")
    return stage


async def create_stage(db: AsyncSession, data: StageIn) -> GrowthStage:
    await _validate(db, data)
    stage = GrowthStage(
        crop_id=data.crop_id,
        name=data.name,
        day_from=data.day_from,
        day_to=data.day_to,
        ranges=[IndexRange(**r.model_dump()) for r in data.ranges],
    )
    db.add(stage)
    await db.commit()
    return stage


async def replace_stage(db: AsyncSession, stage_id: int, data: StageIn) -> GrowthStage:
    stage = await get_stage(db, stage_id)
    await _validate(db, data, exclude_id=stage_id)

    stage.crop_id, stage.name = data.crop_id, data.name
    stage.day_from, stage.day_to = data.day_from, data.day_to

    stage.ranges.clear()
    await db.flush()  # delete the old ranges BEFORE inserting new ones (unique stage+index)
    stage.ranges.extend(IndexRange(**r.model_dump()) for r in data.ranges)

    await db.commit()
    return stage


async def delete_stage(db: AsyncSession, stage_id: int) -> None:
    await db.delete(await get_stage(db, stage_id))
    await db.commit()
