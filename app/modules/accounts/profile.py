from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.locations.models import District, Locality, Province, Tehsil
from app.modules.users.models import User

# Each field's share of 100%. Change the weights here only.
WEIGHTS = {
    "username": 15,
    "mobile_number": 15,
    "locality_id": 20,
    "cnic": 20,
    "email": 10,
    "profile_picture": 20,
}


def completion(user: User) -> int:
    return sum(w for field, w in WEIGHTS.items() if getattr(user, field))


async def profile_data(db: AsyncSession, user: User) -> dict:
    location = None
    if user.locality_id:
        row = (await db.execute(
            select(Locality.name, Tehsil.name, District.name, Province.name)
            .join(Tehsil, Locality.tehsil_id == Tehsil.id)
            .join(District, Tehsil.district_id == District.id)
            .join(Province, District.province_id == Province.id)
            .where(Locality.id == user.locality_id)
        )).one()
        location = {"locality": row[0], "tehsil": row[1], "district": row[2], "province": row[3]}

    return {
        "user_id": user.id,
        "username": user.username,
        "mobile_number": user.mobile_number,
        "email": user.email,
        "cnic": user.cnic,
        "profile_picture": user.profile_picture,
        "locality_id": user.locality_id,
        "location": location,
        "reference_code": user.reference_code,
        "profile_completion": completion(user),
        "missing_fields": [f for f in WEIGHTS if not getattr(user, f)],
    }
