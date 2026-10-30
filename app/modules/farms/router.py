from fastapi import APIRouter

from app.core.deps import CurrentUser
from app.db.session import DB
from app.modules.farms import service
from app.modules.farms.schemas import FarmIn, FarmOut, FarmUpdate

router = APIRouter(prefix="/farms", tags=["farms"])


@router.get("/", response_model=list[FarmOut])
async def list_farms(user: CurrentUser, db: DB):
    return [service.farm_out(f) for f in await service.list_farms(db, user)]


@router.post("/", response_model=FarmOut, status_code=201)
async def create_farm(data: FarmIn, user: CurrentUser, db: DB):
    return service.farm_out(await service.create_farm(db, user, data))


@router.get("/{farm_id}/", response_model=FarmOut)
async def get_farm(farm_id: int, user: CurrentUser, db: DB):
    return service.farm_out(await service.get_farm(db, user, farm_id))


@router.patch("/{farm_id}/", response_model=FarmOut)
async def update_farm(farm_id: int, data: FarmUpdate, user: CurrentUser, db: DB):
    return service.farm_out(await service.update_farm(db, user, farm_id, data))


@router.delete("/{farm_id}/", status_code=204)
async def delete_farm(farm_id: int, user: CurrentUser, db: DB) -> None:
    await service.delete_farm(db, user, farm_id)
