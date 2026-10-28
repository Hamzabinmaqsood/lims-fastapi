from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.modules.accounts.schemas import SignupIn
from app.modules.users.models import ROLE_FARMER, Role, User


async def signup(db: AsyncSession, data: SignupIn) -> User:
    taken = await db.scalar(select(User.id).where(User.mobile_number == data.mobile_number))
    if taken:
        raise HTTPException(400, {"mobile_number": ["This mobile number is already registered."]})

    farmer = await db.scalar(select(Role).where(Role.name == ROLE_FARMER))
    user = User(
        username=data.username.lower(),
        mobile_number=data.mobile_number,
        password=hash_password(data.password),
        role=farmer,
    )
    db.add(user)
    await db.commit()
    return user
