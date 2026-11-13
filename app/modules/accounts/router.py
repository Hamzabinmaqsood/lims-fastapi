from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import ValidationError

from app.core.deps import CurrentUser
from app.db.session import DB
from app.modules.accounts import service

# from app.modules.accounts.profile import profile_data
from app.modules.accounts.schemas import DetailsIn, ProfileUpdate, SignupIn, SignupOut

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
@router.patch("/profile/details/")
async def update_details(
    user: CurrentUser,
    db: DB,
    cnic: str | None = Form(None),
    email: str | None = Form(None),
    profile_picture: UploadFile | None = File(None),
) -> dict:
    try:
        details = DetailsIn(cnic=cnic, email=email)
    except ValidationError as exc:
        raise HTTPException(422, exc.errors(include_url=False)) from exc

    user = await service.update_details(db, user, details.cnic, details.email, profile_picture)
    return await service.profile_data(db, user)
