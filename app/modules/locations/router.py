from fastapi import APIRouter

from app.db.session import DB
from app.modules.locations import service
from app.modules.locations.schemas import LocationOut

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("/provinces/", response_model=list[LocationOut])
async def provinces(db: DB):
    return await service.list_provinces(db)


@router.get("/districts/", response_model=list[LocationOut])
async def districts(province_id: int, db: DB):
    return await service.list_districts(db, province_id)


@router.get("/tehsils/", response_model=list[LocationOut])
async def tehsils(district_id: int, db: DB):
    return await service.list_tehsils(db, district_id)


@router.get("/localities/", response_model=list[LocationOut])
async def localities(tehsil_id: int, db: DB):
    return await service.list_localities(db, tehsil_id)
