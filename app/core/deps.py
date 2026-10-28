from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_token
from app.db.session import DB
from app.modules.users.models import User

bearer = HTTPBearer(auto_error=False)  # adds the "Authorize" button in Swagger


async def get_current_user(
    db: DB,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if creds is None:
        raise HTTPException(401, "Authentication credentials were not provided.")
    try:
        user_id = decode_token(creds.credentials, "access")
    except ValueError as exc:
        raise HTTPException(401, str(exc)) from exc

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(401, "User not found or inactive")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
