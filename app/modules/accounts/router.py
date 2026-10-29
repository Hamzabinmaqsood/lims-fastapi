from fastapi import APIRouter, HTTPException

from app.db.session import DB
from app.modules.accounts import service
from app.modules.accounts.schemas import SignupIn, SignupOut
from app.core.deps import CurrentUser
from app.modules.accounts.profile import profile_data
from app.modules.accounts.schemas import ProfileUpdate
from app.modules.locations.models import Locality
from app.modules.users.models import User
from sqlalchemy import select

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
    return await profile_data(db, user)


@router.patch("/profile/")
async def update_profile(data: ProfileUpdate, user: CurrentUser, db: DB) -> dict:
    changes = data.model_dump(exclude_unset=True)  # only fields actually sent

    if "locality_id" in changes and await db.get(Locality, changes["locality_id"]) is None:
        raise HTTPException(400, {"locality_id": ["Invalid city/village."]})
    if changes.get("cnic"):
        taken = await db.scalar(
            select(User.id).where(User.cnic == changes["cnic"], User.id != user.id)
        )
        if taken:
            raise HTTPException(400, {"cnic": ["This CNIC is already registered."]})

    for field, value in changes.items():
        setattr(user, field, value)
    await db.commit()
    return await profile_data(db, user)
