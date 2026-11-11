from fastapi import HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.crops.models import CropType
from app.modules.growth_stages.models import GrowthStage, IndexRange
from app.modules.growth_stages.schemas import StageIn

from starlette.concurrency import run_in_threadpool
from app.modules.growth_stages.importer import build_stages, read_rows

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


async def import_stages(db: AsyncSession, crop_id: int, content: bytes, filename: str) -> dict:
    if await db.get(CropType, crop_id) is None:
        raise HTTPException(404, "Crop not found.")

    try:
        # openpyxl is blocking (sync), so read the file in a worker thread.
        rows = await run_in_threadpool(read_rows, content, filename)
    except ValueError as exc:
        raise HTTPException(400, {"file": [str(exc)]}) from exc
    except Exception as exc:
        raise HTTPException(400, {"file": ["Could not read the file. Is it a valid Excel/CSV file?"]}) from exc
    if not rows:
        raise HTTPException(400, {"file": ["The file has no data rows."]})

    stages, errors = build_stages(rows, crop_id)
    if errors:
        raise HTTPException(400, {"message": "Nothing was imported. Fix these rows and try again.",
                                  "errors": errors})

    # Replace this crop's stages: delete + insert in ONE transaction.
    await db.execute(delete(GrowthStage).where(GrowthStage.crop_id == crop_id))
    for s in stages:
        db.add(GrowthStage(
            crop_id=crop_id, name=s.name, day_from=s.day_from, day_to=s.day_to,
            ranges=[IndexRange(**r.model_dump()) for r in s.ranges],
        ))
    await db.commit()
    return {"crop_id": crop_id, "imported": len(stages)}


async def stage_for_day(db: AsyncSession, crop_id: int, day: int) -> GrowthStage | None:
    q = select(GrowthStage).where(
        GrowthStage.crop_id == crop_id,
        GrowthStage.day_from <= day,
        GrowthStage.day_to >= day,
    )
    return await db.scalar(q)
