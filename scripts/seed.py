"""Seed demo data: 50 farmers (1–3 farms each) + 10 Response Team members, all with one password.

    SEED_PASSWORD='...' python -m scripts.seed

Safe to run twice: existing mobile numbers are skipped. Fixed random seed → same data every run.
"""

import asyncio
import math
import os
import random
import secrets
from datetime import timedelta

from geoalchemy2.shape import from_shape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.core.time import today_pk
from app.db.session import SessionLocal          # ← your app's session factory (see note below)
from app.modules.crops.models import CropSeason, CropType
from app.modules.farms.models import Farm
from app.modules.farms.service import build_polygon, calc_acres, check_min_area
from app.modules.users.models import ROLE_FARMER, ROLE_RESPONSE_TEAM, Role, User

N_FARMERS, N_TEAM = 50, 10
FARMER_MOBILE = "030090{:05d}"   # 03009000001 … 03009000050
TEAM_MOBILE = "031090{:05d}"     # 03109000001 … 03109000010

FIRST = ["Muhammad", "Ali", "Ahmed", "Usman", "Bilal", "Hamza", "Imran", "Asif", "Tariq", "Zahid",
         "Rashid", "Naveed", "Kashif", "Shahid", "Arshad", "Waseem", "Fahad", "Saeed", "Iqbal", "Nadeem"]
LAST = ["Khan", "Ahmad", "Hussain", "Iqbal", "Akram", "Javed", "Raza", "Shah", "Butt", "Chaudhry",
        "Malik", "Gondal", "Bhatti", "Warraich", "Cheema"]

# Farming areas of Punjab (lat, lng). Fields are scattered a few km around these.
VILLAGES = [
    (31.42, 73.08),  # Faisalabad
    (30.67, 73.11),  # Sahiwal
    (30.20, 71.47),  # Multan
    (32.16, 74.19),  # Gujranwala
    (30.81, 73.45),  # Okara
    (31.71, 73.98),  # Sheikhupura
    (29.39, 71.68),  # Bahawalpur
    (32.07, 72.67),  # Sargodha
]

DEFAULT_CROPS = {"Kharif": ["Cotton", "Rice", "Maize"], "Rabi": ["Wheat", "Mustard"]}


async def get_role(db: AsyncSession, name: str) -> Role:
    role = await db.scalar(select(Role).where(Role.name == name))
    if role is None:
        role = Role(name=name)
        db.add(role)
        await db.flush()
    return role


async def get_crops(db: AsyncSession) -> list[CropType]:
    """Use the crops already in the DB; add a few only if there are none."""
    crops = list((await db.scalars(select(CropType))).all())
    if crops:
        return crops
    next_crop_id = 1
    for season_id, (season, names) in enumerate(DEFAULT_CROPS.items(), start=1):
        db.add(CropSeason(id=season_id, name=season))
        for name in names:
            db.add(CropType(id=next_crop_id, season_id=season_id, name=name))
            next_crop_id += 1
    await db.flush()
    return list((await db.scalars(select(CropType))).all())


def field_points(rng: random.Random) -> list[tuple[float, float]]:
    """A slightly irregular 4-corner field of roughly 1–5 acres, as [(lat, lng), ...] like the app sends."""
    lat0, lng0 = rng.choice(VILLAGES)
    lat0 += rng.uniform(-0.05, 0.05)                       # spread ~5 km around the village
    lng0 += rng.uniform(-0.05, 0.05)
    w, h = rng.uniform(60, 150), rng.uniform(60, 130)      # metres
    angle = math.radians(rng.uniform(0, 90))
    m_lat = 1 / 111_320                                    # degrees per metre
    m_lng = m_lat / math.cos(math.radians(lat0))
    points = []
    for x, y in [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]:
        x, y = x + rng.uniform(-8, 8), y + rng.uniform(-8, 8)          # not a perfect rectangle
        rx, ry = x * math.cos(angle) - y * math.sin(angle), x * math.sin(angle) + y * math.cos(angle)
        points.append((lat0 + ry * m_lat, lng0 + rx * m_lng))
    return points


async def make_user(db, rng, role, mobile, password_hash) -> User | None:
    if await db.scalar(select(User.id).where(User.mobile_number == mobile)):
        return None                                        # already seeded → skip
    user = User(
        role_id=role.id,
        username=f"{rng.choice(FIRST)} {rng.choice(LAST)}",
        mobile_number=mobile,
        password=password_hash,
        reference_code=secrets.token_hex(4).upper(),       # 8 chars, unique
    )
    db.add(user)
    await db.flush()                                       # get user.id for the farms
    return user


async def seed(db: AsyncSession, password: str) -> dict:
    rng = random.Random(42)                                # same data on every run
    password_hash = hash_password(password)                # hash ONCE (bcrypt is slow on purpose)
    farmer_role = await get_role(db, ROLE_FARMER)
    team_role = await get_role(db, ROLE_RESPONSE_TEAM)
    crops = await get_crops(db)
    made = {"farmers": 0, "team": 0, "farms": 0}

    for n in range(1, N_TEAM + 1):
        if await make_user(db, rng, team_role, TEAM_MOBILE.format(n), password_hash):
            made["team"] += 1

    for n in range(1, N_FARMERS + 1):
        farmer = await make_user(db, rng, farmer_role, FARMER_MOBILE.format(n), password_hash)
        n_farms = rng.randint(1, 3)                        # drawn even when skipped → runs stay identical
        if farmer is None:
            continue
        made["farmers"] += 1
        for k in range(1, n_farms + 1):
            poly = build_polygon(field_points(rng))
            acres = await calc_acres(db, poly)
            check_min_area(acres)
            crop = rng.choice(crops)
            db.add(Farm(
                owner_id=farmer.id,
                name=f"Farm {k}",
                boundary=from_shape(poly, srid=4326),
                area_acres=acres,
                crop_season_id=crop.season_id,
                crop_id=crop.id,
                sowing_date=today_pk() - timedelta(days=rng.randint(30, 120)),
            ))
            made["farms"] += 1

    await db.commit()                                      # all or nothing
    return made


async def main() -> None:
    password = os.environ.get("SEED_PASSWORD")
    if not password or len(password) < 8:
        raise SystemExit("Set SEED_PASSWORD (at least 8 characters).")
    async with SessionLocal() as db:
        print(await seed(db, password))


if __name__ == "__main__":
    asyncio.run(main())
