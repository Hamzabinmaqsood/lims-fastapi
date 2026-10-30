from fastapi import APIRouter

from app.db.session import DB
from app.modules.crops import service
from app.modules.crops.schemas import CropSeasonOut, CropTypeOut

router = APIRouter(prefix="/crops", tags=["crops"])


@router.get("/seasons/", response_model=list[CropSeasonOut])
async def seasons(db: DB):
    return await service.list_seasons(db)


@router.get("/types/", response_model=list[CropTypeOut])
async def crop_types(db: DB, season_id: int | None = None):
    return await service.list_crops(db, season_id)
