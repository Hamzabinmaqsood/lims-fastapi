from fastapi import APIRouter

from app.db.session import DB
from app.modules.accounts import service
from app.modules.accounts.schemas import SignupIn, SignupOut
from app.core.deps import CurrentUser
from app.modules.accounts.profile import profile_data
from app.modules.accounts.schemas import ProfileUpdate

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


@router.get("/profile/")
async def get_profile(user: CurrentUser, db: DB) -> dict:
    return await service.profile_data(db, user)


@router.patch("/profile/")
async def update_profile(data: ProfileUpdate, user: CurrentUser, db: DB) -> dict:
    user = await service.update_profile(db, user, data)
    return await service.profile_data(db, user)
