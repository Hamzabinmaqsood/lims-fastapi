from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_token_pair, verify_password
from app.modules.auth.schemas import LoginIn
from app.modules.users.models import User


async def login(db: AsyncSession, data: LoginIn) -> dict:
    user = await db.scalar(select(User).where(User.mobile_number == data.mobile_number))

    # Same message for "no such user" and "wrong password", so attackers
    # can't discover which mobile numbers are registered.
    if user is None or not verify_password(data.password, user.password):
        raise HTTPException(401, "No active account found with the given credentials")
    if not user.is_active:
        raise HTTPException(401, "No active account found with the given credentials")

    user.last_login = datetime.now(UTC)
    await db.commit()

    return {
        **create_token_pair(user.id),
        "user_id": user.id,
        "user_role": user.role.name,
        "user_name": user.username,
    }
