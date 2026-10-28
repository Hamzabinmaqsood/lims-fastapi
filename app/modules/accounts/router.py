from fastapi import APIRouter

from app.db.session import DB
from app.modules.accounts import service
from app.modules.accounts.schemas import SignupIn, SignupOut

router = APIRouter(prefix="/user", tags=["accounts"])


@router.post("/signup/", response_model=SignupOut, status_code=201)
async def signup(data: SignupIn, db: DB) -> dict:
    user = await service.signup(db, data)
    return {
        "message": "User created successfully",
        "user_id": user.id,
        "username": user.username,
        "mobile_number": user.mobile_number,
    }
