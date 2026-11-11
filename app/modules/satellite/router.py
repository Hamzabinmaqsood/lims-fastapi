from typing import Literal

from fastapi import APIRouter, Response

from app.core.deps import CurrentUser
from app.db.session import DB
from app.modules.satellite import service

router = APIRouter(prefix="/farms", tags=["satellite"])

IndexName = Literal["NDVI", "SAVI", "MSAVI", "NDMI", "NDRE", "RECI"]


@router.get("/{farm_id}/satellite/stats/")
async def farm_index_stats(farm_id: int, user: CurrentUser, db: DB):
    return await service.farm_index_stats(db, user, farm_id)

@router.get(
    "/{farm_id}/satellite/{index}/",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}},
)
async def farm_index_image(farm_id: int, index: IndexName, user: CurrentUser, db: DB):
    png = await service.farm_index_png(db, user, farm_id, index)
    return Response(png, media_type="image/png")

@router.get("/{farm_id}/health/")
async def farm_health(farm_id: int, user: CurrentUser, db: DB):
    return await service.farm_health(db, user, farm_id)
