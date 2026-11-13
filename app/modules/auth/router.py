from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.deps import CurrentUser
from app.core.security import create_token_pair, decode_token
from app.db.session import DB
from app.modules.auth import service
from app.modules.auth.schemas import LoginIn, LoginOut

router = APIRouter(tags=["auth"])


@router.post("/token/", response_model=LoginOut)
async def login(data: LoginIn, db: DB) -> dict:
    return await service.login(db, data)


class RefreshIn(BaseModel):
    refresh: str


@router.get("/verify-token/")
async def verify_token(user: CurrentUser) -> dict:
    return {"valid": True, "user_id": user.id, "user_name": user.username}


@router.post("/token/refresh/")
async def refresh_token(data: RefreshIn, db: DB) -> dict:
    try:
        user_id = decode_token(data.refresh, "refresh")
    except ValueError as exc:
        raise HTTPException(401, str(exc)) from exc
    return create_token_pair(user_id)
