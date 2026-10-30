import secrets

from fastapi import HTTPException,UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.modules.accounts.schemas import ProfileUpdate, SignupIn
from app.modules.locations.models import District, Locality, Province, Tehsil
from app.modules.users.models import ROLE_FARMER, Role, User
from app.core.storage import upload_image
# ---------------------------------------------------------------- reference codes

# No 0/O or 1/I, so codes are easy to read and type.
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


async def new_reference_code(db: AsyncSession) -> str:
    while True:
        code = "".join(secrets.choice(ALPHABET) for _ in range(8))
        if not await db.scalar(select(User.id).where(User.reference_code == code)):
            return code

LOCATION_FIELDS = ("province_id", "district_id", "tehsil_id", "locality_id")

async def validate_location(
    db: AsyncSession, province_id: int, district_id: int, tehsil_id: int, locality_id: int
) -> None:
    """One query: does this locality really belong to this tehsil/district/province?"""
    match = await db.scalar(
        select(Locality.id)
        .join(Tehsil, Locality.tehsil_id == Tehsil.id)
        .join(District, Tehsil.district_id == District.id)
        .where(
            Locality.id == locality_id,
            Tehsil.id == tehsil_id,
            District.id == district_id,
            District.province_id == province_id,
        )
    )
    if match is None:
        raise HTTPException(400, {"location": ["Province, district, tehsil and city/village do not match."]})
# ---------------------------------------------------------------- signup

async def signup(db: AsyncSession, data: SignupIn) -> User:
    taken = await db.scalar(select(User.id).where(User.mobile_number == data.mobile_number))
    if taken:
        raise HTTPException(400, {"mobile_number": ["This mobile number is already registered."]})

    await validate_location(db, data.province_id, data.district_id, data.tehsil_id, data.locality_id)

    referrer_id = None
    if data.reference_code:
        referrer_id = await db.scalar(
            select(User.id).where(User.reference_code == data.reference_code.upper())
        )
        if referrer_id is None:
            raise HTTPException(400, {"reference_code": ["Invalid reference code."]})

    farmer = await db.scalar(select(Role).where(Role.name == ROLE_FARMER))
    user = User(
        username=data.username.lower(),
        mobile_number=data.mobile_number,
        password=hash_password(data.password),
        role=farmer,
        reference_code=await new_reference_code(db),
        referred_by_id=referrer_id,
        province_id=data.province_id,
        district_id=data.district_id,
        tehsil_id=data.tehsil_id,
        locality_id=data.locality_id,
    )
    db.add(user)
    await db.commit()
    return user


# ---------------------------------------------------------------- profile

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


async def update_profile(db: AsyncSession, user: User, data: ProfileUpdate) -> User:
    changes = data.model_dump(exclude_unset=True)  # only fields actually sent

    sent = [f for f in LOCATION_FIELDS if f in changes]
    if sent:
        if len(sent) != 4:
            raise HTTPException(400, {"location": ["Send all of province_id, district_id, tehsil_id and locality_id."]})
        await validate_location(db, *(changes[f] for f in LOCATION_FIELDS))
    # if changes.get("cnic"):
    #     taken = await db.scalar(
    #         select(User.id).where(User.cnic == changes["cnic"], User.id != user.id)
    #     )
    #     if taken:
    #         raise HTTPException(400, {"cnic": ["This CNIC is already registered."]})

    for field, value in changes.items():
        setattr(user, field, value)
    await db.commit()
    return user

async def update_details(
    db: AsyncSession,
    user: User,
    cnic: str | None,
    email: str | None,
    profile_picture: UploadFile | None,
) -> User:
    if cnic is not None:
        taken = await db.scalar(select(User.id).where(User.cnic == cnic, User.id != user.id))
        if taken:
            raise HTTPException(400, {"cnic": ["This CNIC is already registered."]})
        user.cnic = cnic
    if email is not None:
        user.email = email
    if profile_picture is not None:
        user.profile_picture = await upload_image(profile_picture, folder="lims/profile_pictures")

    await db.commit()
    return user
