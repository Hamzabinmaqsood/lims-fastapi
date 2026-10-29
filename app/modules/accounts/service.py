from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.modules.accounts.schemas import SignupIn
from app.modules.users.models import ROLE_FARMER, Role, User

from app.modules.locations.models import Locality

import secrets


# No 0/O or 1/I, so codes are easy to read and type.
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


async def new_reference_code(db: AsyncSession) -> str:
    while True:
        code = "".join(secrets.choice(ALPHABET) for _ in range(8))
        if not await db.scalar(select(User.id).where(User.reference_code == code)):
            return code


async def signup(db: AsyncSession, data: SignupIn) -> User:
    taken = await db.scalar(select(User.id).where(User.mobile_number == data.mobile_number))
    if taken:
        raise HTTPException(400, {"mobile_number": ["This mobile number is already registered."]})

    farmer = await db.scalar(select(Role).where(Role.name == ROLE_FARMER))
    if await db.get(Locality, data.locality_id) is None:
        raise HTTPException(400, {"locality_id": ["Invalid city/village."]})

    referrer_id = None
    if data.reference_code:
        referrer_id = await db.scalar(
            select(User.id).where(User.reference_code == data.reference_code.upper())
        )
        if referrer_id is None:
            raise HTTPException(400, {"reference_code": ["Invalid reference code."]})
    user = User(
        username=data.username.lower(),
        mobile_number=data.mobile_number,
        password=hash_password(data.password),
        role=farmer,
        locality_id=data.locality_id,
        reference_code=await new_reference_code(db),
        referred_by_id=referrer_id,
    )
    db.add(user)
    await db.commit()
    return user

