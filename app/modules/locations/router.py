from fastapi import APIRouter
from sqlalchemy import select

from app.db.session import DB
from app.modules.locations.models import District, Locality, Province, Tehsil
from app.modules.locations.schemas import LocationOut

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("/provinces/", response_model=list[LocationOut])
async def provinces(db: DB):
    return (await db.scalars(select(Province).order_by(Province.name))).all()


@router.get("/districts/", response_model=list[LocationOut])
async def districts(province_id: int, db: DB):
    q = select(District).where(District.province_id == province_id).order_by(District.name)
    return (await db.scalars(q)).all()


@router.get("/tehsils/", response_model=list[LocationOut])
async def tehsils(district_id: int, db: DB):
    q = select(Tehsil).where(Tehsil.district_id == district_id).order_by(Tehsil.name)
    return (await db.scalars(q)).all()


@router.get("/localities/", response_model=list[LocationOut])
async def localities(tehsil_id: int, db: DB):
    q = select(Locality).where(Locality.tehsil_id == tehsil_id).order_by(Locality.name)
    return (await db.scalars(q)).all()
