from decimal import Decimal

from fastapi import HTTPException
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Polygon
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.crops.models import CropType
from app.modules.farms.models import Farm
from app.modules.farms.schemas import FarmIn, FarmUpdate
from app.modules.locations.models import District
from app.modules.users.models import User



SQ_METERS_PER_ACRE = Decimal("4046.8564224")
MIN_ACRES = Decimal("0.10")

def check_min_area(acres: Decimal) -> None:
    if acres < MIN_ACRES:
        raise HTTPException(400, {"boundary": [f"Farm is too small ({acres} acres). Minimum is {MIN_ACRES} acres."]})

# ---------------------------------------------------------------- geometry

def build_polygon(points: list[tuple[float, float]]) -> Polygon:
    """[(lat, lng), ...] from the app → a closed, valid Shapely polygon in (lng, lat)."""
    ring = [(lng, lat) for lat, lng in points]
    if ring[0] != ring[-1]:
        ring.append(ring[0])  # a polygon must end where it starts
    poly = Polygon(ring)
    if not poly.is_valid:
        raise HTTPException(400, {"boundary": ["Invalid shape: the boundary lines cross each other."]})
    return poly


async def calc_acres(db: AsyncSession, poly: Polygon) -> Decimal:
    """Ask PostGIS for the real area. ::geography = measure on the Earth's curve, in m²."""
    m2 = await db.scalar(
        text("SELECT ST_Area(ST_GeomFromText(:wkt, 4326)::geography)"), {"wkt": poly.wkt}
    )
    return round(Decimal(str(m2)) / SQ_METERS_PER_ACRE, 2)


def farm_out(farm: Farm) -> dict:
    coords = list(to_shape(farm.boundary).exterior.coords)[:-1]  # drop the closing point
    return {
        "id": farm.id,
        "name": farm.name,
        "boundary": [[lat, lng] for lng, lat in coords],  # back to the app's [lat, lng]
        "area_acres": float(farm.area_acres),
        "crop_season_id": farm.crop_season_id,
        "crop_id": farm.crop_id,
        "district_id": farm.district_id,
        "sowing_date": farm.sowing_date,
        "created_at": farm.created_at,
    }


# ---------------------------------------------------------------- validation

async def validate_refs(
    db: AsyncSession, district_id: int | None, crop_season_id: int | None, crop_id: int | None
) -> None:
    if district_id is not None and await db.get(District, district_id) is None:
        raise HTTPException(400, {"district_id": ["Invalid district."]})
    if crop_id is not None:
        crop = await db.get(CropType, crop_id)
        if crop is None or (crop_season_id is not None and crop.season_id != crop_season_id):
            raise HTTPException(400, {"crop_id": ["Invalid crop for this season."]})


# ---------------------------------------------------------------- CRUD

async def create_farm(db: AsyncSession, user: User, data: FarmIn) -> Farm:
    poly = build_polygon(data.boundary)
    await validate_refs(db, data.district_id, data.crop_season_id, data.crop_id)

    acres = await calc_acres(db, poly)
    check_min_area(acres)
    farm = Farm(
        owner_id=user.id,
        name=data.name,
        boundary=from_shape(poly, srid=4326),
        area_acres=acres,
        crop_season_id=data.crop_season_id,
        crop_id=data.crop_id,
        district_id=data.district_id,
        sowing_date=data.sowing_date,
    )
    db.add(farm)
    await db.commit()
    await db.refresh(farm)  # load created_at, which the DATABASE filled in
    return farm


async def list_farms(db: AsyncSession, user: User) -> list[Farm]:
    q = select(Farm).where(Farm.owner_id == user.id).order_by(Farm.created_at.desc())
    return list((await db.scalars(q)).all())


async def get_farm(db: AsyncSession, user: User, farm_id: int) -> Farm:
    """Only the owner's farm. Someone else's farm looks exactly like a missing one."""
    farm = await db.scalar(select(Farm).where(Farm.id == farm_id, Farm.owner_id == user.id))
    if farm is None:
        raise HTTPException(404, "Farm not found.")
    return farm


async def update_farm(db: AsyncSession, user: User, farm_id: int, data: FarmUpdate) -> Farm:
    farm = await get_farm(db, user, farm_id)
    changes = data.model_dump(exclude_unset=True)

    if "boundary" in changes:
        poly = build_polygon(changes.pop("boundary"))
        farm.boundary = from_shape(poly, srid=4326)
        acres = await calc_acres(db, poly)
        check_min_area(acres)
        farm.area_acres = acres

    await validate_refs(
        db,
        changes.get("district_id", farm.district_id),
        changes.get("crop_season_id", farm.crop_season_id),
        changes.get("crop_id", farm.crop_id),
    )
    for field, value in changes.items():
        setattr(farm, field, value)

    await db.commit()
    await db.refresh(farm)
    return farm


async def delete_farm(db: AsyncSession, user: User, farm_id: int) -> None:
    farm = await get_farm(db, user, farm_id)
    await db.delete(farm)
    await db.commit()
